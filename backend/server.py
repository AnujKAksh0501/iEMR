import os
import uuid
import logging
import requests
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from dotenv import load_dotenv
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import bcrypt
import jwt
from pymongo import ReturnDocument
from fastapi import FastAPI, APIRouter, Request, HTTPException, Depends
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta, StreamDone
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("emr")

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

JWT_SECRET = os.environ['JWT_SECRET']
JWT_ALG = "HS256"
EMERGENT_LLM_KEY = os.environ['EMERGENT_LLM_KEY']

app = FastAPI()
api = APIRouter(prefix="/api")

ROLES = ["super_admin", "clinic_admin", "doctor", "nurse", "pharmacist", "lab_tech", "receptionist"]

# ---------- helpers ----------
def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False

def create_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(days=7), "type": "access"}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def clean(doc: dict) -> dict:
    if not doc:
        return doc
    doc.pop("_id", None)
    doc.pop("password_hash", None)
    return doc

async def get_current_user(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else None
    if not token:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
    user = await db.users.find_one({"id": payload["sub"]})
    if not user:
        raise HTTPException(401, "User not found")
    return clean(dict(user))

def require_roles(*roles):
    async def checker(user: dict = Depends(get_current_user)):
        if roles and user["role"] not in roles:
            raise HTTPException(403, "Insufficient permissions")
        return user
    return checker

# ---------- security / compliance / plans (market-ready hardening) ----------
PASSWORD_MIN = 8
def validate_password(pw: str):
    if not pw or len(pw) < PASSWORD_MIN:
        raise HTTPException(400, f"Password must be at least {PASSWORD_MIN} characters")
    if not (any(c.isupper() for c in pw) and any(c.islower() for c in pw) and any(c.isdigit() for c in pw)):
        raise HTTPException(400, "Password must include upper and lower case letters and a number")

MAX_LOGIN_FAILS = 5
LOCKOUT_MINUTES = 15
async def check_lockout(email: str):
    rec = await db.login_attempts.find_one({"email": email})
    if rec and rec.get("locked_until"):
        try:
            lu = datetime.fromisoformat(rec["locked_until"])
        except Exception:
            lu = None
        if lu and lu > datetime.now(timezone.utc):
            raise HTTPException(429, "Too many failed attempts. Please try again later.")

async def record_login_fail(email: str):
    rec = await db.login_attempts.find_one_and_update(
        {"email": email}, {"$inc": {"fails": 1}, "$set": {"updated_at": now_iso()}},
        upsert=True, return_document=ReturnDocument.AFTER)
    if rec.get("fails", 0) >= MAX_LOGIN_FAILS:
        await db.login_attempts.update_one({"email": email}, {"$set": {
            "locked_until": (datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)).isoformat(),
            "fails": 0}})

async def clear_login_fails(email: str):
    await db.login_attempts.delete_one({"email": email})

def client_ip(request: Request) -> str:
    return (request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            or (request.client.host if request.client else "unknown"))

async def audit(actor, tenant_id, action, resource, resource_id=None, ip=None, meta=None):
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()), "actor": actor, "tenant_id": tenant_id, "action": action,
        "resource": resource, "resource_id": resource_id, "ip": ip,
        "meta": meta or {}, "created_at": now_iso()})

_BLOCKED_KEYS = {"_id", "tenant_id", "id", "password_hash", "key_hash", "role"}
def sanitize_payload(body) -> dict:
    if not isinstance(body, dict):
        raise HTTPException(400, "Invalid payload")
    if len(body) > 60:
        raise HTTPException(400, "Too many fields in payload")
    out = {}
    for k, v in body.items():
        if not isinstance(k, str) or k in _BLOCKED_KEYS or k.startswith("$") or "." in k:
            continue
        if isinstance(v, str) and len(v) > 20000:
            raise HTTPException(400, f"Field '{k}' exceeds maximum length")
        out[k] = v
    return out

# Pluggable AI providers — connect any LLM by choosing a provider + key.
AI_PROVIDERS = {
    "emergent": ["model"],
    "openai": ["api_key", "model"],
    "anthropic": ["api_key", "model"],
    "gemini": ["api_key", "model"],
}
AI_DEFAULT_MODELS = {"emergent": "gpt-5.4", "openai": "gpt-5.4",
                     "anthropic": "claude-sonnet-4-6", "gemini": "gemini-3-flash"}
def resolve_ai_cfg(integ):
    cfg = (integ or {}).get("ai") or {}
    provider = cfg.get("provider") or "emergent"
    model = cfg.get("model") or AI_DEFAULT_MODELS.get(provider, "gpt-5.4")
    if provider == "emergent":
        return {"provider": "openai", "api_key": EMERGENT_LLM_KEY, "model": model, "display": "emergent"}
    key = cfg.get("api_key")
    if not key:  # provider chosen but no key yet → fall back to managed key
        return {"provider": "openai", "api_key": EMERGENT_LLM_KEY, "model": AI_DEFAULT_MODELS["emergent"], "display": "emergent"}
    return {"provider": provider, "api_key": key, "model": model, "display": provider}

# SaaS subscription plans (bill the clinics).
PLANS = {
    "free": {"id": "free", "name": "Free", "price": 0, "max_staff": 3, "max_patients": 50},
    "starter": {"id": "starter", "name": "Starter", "price": 49, "max_staff": 10, "max_patients": 1000},
    "pro": {"id": "pro", "name": "Pro", "price": 199, "max_staff": 100, "max_patients": 100000},
}
async def get_subscription(tenant_id: str) -> dict:
    sub = await db.subscriptions.find_one({"tenant_id": tenant_id})
    if not sub:
        sub = {"tenant_id": tenant_id, "plan": "free", "status": "active", "created_at": now_iso()}
        await db.subscriptions.insert_one(dict(sub))
    return clean(dict(sub))

async def enforce_limit(tenant_id: str, kind: str):
    sub = await get_subscription(tenant_id)
    plan = PLANS.get(sub.get("plan", "free"), PLANS["free"])
    if kind == "staff" and await db.users.count_documents({"tenant_id": tenant_id}) >= plan["max_staff"]:
        raise HTTPException(402, f"Your {plan['name']} plan allows {plan['max_staff']} staff members. Upgrade to add more.")
    if kind == "patients" and await db.patients.count_documents({"tenant_id": tenant_id}) >= plan["max_patients"]:
        raise HTTPException(402, f"Your {plan['name']} plan allows {plan['max_patients']} patients. Upgrade to add more.")

async def link_patient_id(coll: str, doc: dict, tenant_id: str):
    if coll in ("appointments", "prescriptions", "labtests", "invoices") and doc.get("patient") and not doc.get("patient_id"):
        p = await db.patients.find_one({"name": doc.get("patient"), "tenant_id": tenant_id})
        if p:
            doc["patient_id"] = p["id"]

# ---------- models ----------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    name: str
    clinic_name: str

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class GoogleIn(BaseModel):
    session_id: str

class StaffIn(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str

class ChatIn(BaseModel):
    message: str
    session_id: Optional[str] = None
    context: Optional[str] = None

class CheckoutIn(BaseModel):
    invoice_id: str
    origin_url: str

# ---------- auth ----------
@api.post("/auth/register")
async def register(body: RegisterIn, request: Request):
    validate_password(body.password)
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "Email already registered")
    tenant_id = str(uuid.uuid4())
    await db.tenants.insert_one({"id": tenant_id, "name": body.clinic_name, "created_at": now_iso()})
    await db.subscriptions.insert_one({"tenant_id": tenant_id, "plan": "free", "status": "active", "created_at": now_iso()})
    uid = str(uuid.uuid4())
    user = {"id": uid, "email": email, "password_hash": hash_password(body.password),
            "name": body.name, "role": "clinic_admin", "tenant_id": tenant_id,
            "clinic_name": body.clinic_name, "created_at": now_iso(), "auth": "jwt"}
    await db.users.insert_one(dict(user))
    await audit(email, tenant_id, "register", "user", uid, client_ip(request))
    return {"token": create_token(uid), "user": clean(dict(user))}

@api.post("/auth/login")
async def login(body: LoginIn, request: Request):
    email = body.email.lower()
    await check_lockout(email)
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user.get("password_hash", "")):
        await record_login_fail(email)
        await audit(email, (user or {}).get("tenant_id"), "login_failed", "user", (user or {}).get("id"), client_ip(request))
        raise HTTPException(401, "Invalid email or password")
    await clear_login_fails(email)
    await audit(email, user["tenant_id"], "login", "user", user["id"], client_ip(request))
    return {"token": create_token(user["id"]), "user": clean(dict(user))}

@api.post("/auth/google")
async def google_auth(body: GoogleIn):
    try:
        r = requests.get("https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                         headers={"X-Session-ID": body.session_id}, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        raise HTTPException(401, f"Google auth failed: {e}")
    email = data["email"].lower()
    user = await db.users.find_one({"email": email})
    if not user:
        tenant_id = str(uuid.uuid4())
        cname = f"{data.get('name', 'My')} Clinic"
        await db.tenants.insert_one({"id": tenant_id, "name": cname, "created_at": now_iso()})
        uid = str(uuid.uuid4())
        user = {"id": uid, "email": email, "name": data.get("name", email), "role": "clinic_admin",
                "tenant_id": tenant_id, "clinic_name": cname, "picture": data.get("picture"),
                "created_at": now_iso(), "auth": "google"}
        await db.users.insert_one(dict(user))
    return {"token": create_token(user["id"]), "user": clean(dict(user))}

@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user

# ---------- staff ----------
@api.get("/staff")
async def list_staff(user: dict = Depends(get_current_user)):
    docs = await db.users.find({"tenant_id": user["tenant_id"]}).to_list(1000)
    return [clean(dict(d)) for d in docs]

@api.post("/staff")
async def add_staff(body: StaffIn, request: Request, user: dict = Depends(require_roles("clinic_admin", "super_admin"))):
    if body.role not in ROLES:
        raise HTTPException(400, "Invalid role")
    validate_password(body.password)
    await enforce_limit(user["tenant_id"], "staff")
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "Email already registered")
    uid = str(uuid.uuid4())
    doc = {"id": uid, "email": email, "password_hash": hash_password(body.password),
           "name": body.name, "role": body.role, "tenant_id": user["tenant_id"],
           "clinic_name": user.get("clinic_name"), "created_at": now_iso(), "auth": "jwt"}
    await db.users.insert_one(dict(doc))
    await audit(user["email"], user["tenant_id"], "create", "staff", uid, client_ip(request), {"role": body.role})
    return clean(dict(doc))

@api.delete("/staff/{sid}")
async def del_staff(sid: str, request: Request, user: dict = Depends(require_roles("clinic_admin", "super_admin"))):
    if sid == user["id"]:
        raise HTTPException(400, "Cannot delete yourself")
    await db.users.delete_one({"id": sid, "tenant_id": user["tenant_id"]})
    await audit(user["email"], user["tenant_id"], "delete", "staff", sid, client_ip(request))
    return {"ok": True}

# ---------- notifications / automation ----------
import smtplib
import hashlib
import secrets
import hmac
import asyncio
import re
from email.mime.text import MIMEText

EVENTS = {
    "appointment_booked": "Appointment Confirmed",
    "appointment_reminder": "Appointment Reminder",
    "lab_results_ready": "Lab Results Ready",
    "invoice_created": "New Invoice",
    "payment_received": "Payment Received",
}

# Pluggable provider schemas: swap any platform by supplying its keys.
EMAIL_PROVIDERS = {
    "smtp": ["host", "port", "username", "password", "from_email"],
    "sendgrid": ["api_key", "from_email"],
    "resend": ["api_key", "from_email"],
    "mailgun": ["api_key", "domain", "from_email"],
}
WHATSAPP_PROVIDERS = {
    "twilio": ["account_sid", "auth_token", "from_number"],
    "meta": ["phone_number_id", "access_token"],
}
SECRET_FIELDS = {"password", "api_key", "auth_token", "access_token"}

def _env_email_cfg():
    if os.environ.get("SMTP_HOST") and os.environ.get("SMTP_USER") and os.environ.get("SMTP_PASSWORD"):
        return {"provider": "smtp", "host": os.environ["SMTP_HOST"], "port": os.environ.get("SMTP_PORT", "587"),
                "username": os.environ["SMTP_USER"], "password": os.environ["SMTP_PASSWORD"],
                "from_email": os.environ.get("SMTP_FROM") or os.environ["SMTP_USER"]}
    return None

def _env_wa_cfg():
    if os.environ.get("TWILIO_ACCOUNT_SID") and os.environ.get("TWILIO_AUTH_TOKEN") and os.environ.get("TWILIO_WHATSAPP_FROM"):
        return {"provider": "twilio", "account_sid": os.environ["TWILIO_ACCOUNT_SID"],
                "auth_token": os.environ["TWILIO_AUTH_TOKEN"], "from_number": os.environ["TWILIO_WHATSAPP_FROM"]}
    return None

def _cfg_complete(cfg, providers):
    if not cfg:
        return False
    p = cfg.get("provider")
    return bool(p in providers and all(cfg.get(f) for f in providers[p]))

def resolve_email_cfg(integ):
    cfg = (integ or {}).get("email")
    return cfg if _cfg_complete(cfg, EMAIL_PROVIDERS) else _env_email_cfg()

def resolve_whatsapp_cfg(integ):
    cfg = (integ or {}).get("whatsapp")
    return cfg if _cfg_complete(cfg, WHATSAPP_PROVIDERS) else _env_wa_cfg()

def email_configured_for(integ):
    return resolve_email_cfg(integ) is not None

def whatsapp_configured_for(integ):
    return resolve_whatsapp_cfg(integ) is not None

def send_email_via(cfg, to, subject, body):
    p = cfg["provider"]
    if p == "smtp":
        sender = cfg.get("from_email") or cfg["username"]
        msg = MIMEText(body, "plain"); msg["Subject"] = subject; msg["From"] = sender; msg["To"] = to
        with smtplib.SMTP(cfg["host"], int(cfg.get("port", 587)), timeout=15) as s:
            s.starttls(); s.login(cfg["username"], cfg["password"]); s.sendmail(sender, [to], msg.as_string())
    elif p == "sendgrid":
        r = requests.post("https://api.sendgrid.com/v3/mail/send",
            headers={"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"},
            json={"personalizations": [{"to": [{"email": to}]}], "from": {"email": cfg["from_email"]},
                  "subject": subject, "content": [{"type": "text/plain", "value": body}]}, timeout=15)
        r.raise_for_status()
    elif p == "resend":
        r = requests.post("https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {cfg['api_key']}"},
            json={"from": cfg["from_email"], "to": [to], "subject": subject, "text": body}, timeout=15)
        r.raise_for_status()
    elif p == "mailgun":
        r = requests.post(f"https://api.mailgun.net/v3/{cfg['domain']}/messages",
            auth=("api", cfg["api_key"]),
            data={"from": cfg["from_email"], "to": to, "subject": subject, "text": body}, timeout=15)
        r.raise_for_status()

def send_whatsapp_via(cfg, to, body):
    p = cfg["provider"]
    if p == "twilio":
        frm = cfg["from_number"]
        to_wa = to if str(to).startswith("whatsapp:") else f"whatsapp:{to}"
        frm_wa = frm if str(frm).startswith("whatsapp:") else f"whatsapp:{frm}"
        r = requests.post(f"https://api.twilio.com/2010-04-01/Accounts/{cfg['account_sid']}/Messages.json",
            data={"From": frm_wa, "To": to_wa, "Body": body}, auth=(cfg["account_sid"], cfg["auth_token"]), timeout=15)
        r.raise_for_status()
    elif p == "meta":
        to_num = str(to).replace("whatsapp:", "").lstrip("+")
        r = requests.post(f"https://graph.facebook.com/v20.0/{cfg['phone_number_id']}/messages",
            headers={"Authorization": f"Bearer {cfg['access_token']}"},
            json={"messaging_product": "whatsapp", "to": to_num, "type": "text", "text": {"body": body}}, timeout=15)
        r.raise_for_status()

async def get_settings(tenant_id: str) -> dict:
    s = await db.tenant_settings.find_one({"tenant_id": tenant_id})
    if not s:
        s = {"tenant_id": tenant_id, "events": {k: True for k in EVENTS},
             "channels": {"email": True, "whatsapp": True}, "integrations": {}}
        await db.tenant_settings.insert_one(dict(s))
    s = clean(dict(s))
    s.setdefault("integrations", {})
    return s

async def log_notification(tenant_id, channel, to, subject, body, status, event):
    await db.notifications.insert_one({"id": str(uuid.uuid4()), "tenant_id": tenant_id,
        "channel": channel, "to": to, "subject": subject, "body": body,
        "status": status, "event": event, "created_at": now_iso()})

async def notify(tenant_id, event, to_email, to_phone, subject, body):
    st = await get_settings(tenant_id)
    if not st.get("events", {}).get(event, True):
        return
    ch = st.get("channels", {})
    integ = st.get("integrations", {})
    if ch.get("email", True) and to_email:
        cfg = resolve_email_cfg(integ)
        if cfg:
            try: send_email_via(cfg, to_email, subject, body); status = "sent"
            except Exception as e: status = f"failed: {e}"[:180]
        else: status = "skipped_not_configured"
        await log_notification(tenant_id, "email", to_email, subject, body, status, event)
    if ch.get("whatsapp", True) and to_phone:
        cfg = resolve_whatsapp_cfg(integ)
        if cfg:
            try: send_whatsapp_via(cfg, to_phone, f"{subject}\n\n{body}"); status = "sent"
            except Exception as e: status = f"failed: {e}"[:180]
        else: status = "skipped_not_configured"
        await log_notification(tenant_id, "whatsapp", to_phone, subject, body, status, event)

def hash_key(k: str) -> str:
    return hashlib.sha256(k.encode()).hexdigest()

async def get_tenant_by_api_key(request: Request) -> str:
    key = request.headers.get("X-API-Key")
    if not key:
        raise HTTPException(401, "Missing X-API-Key header")
    doc = await db.api_keys.find_one({"key_hash": hash_key(key), "active": True})
    if not doc:
        raise HTTPException(401, "Invalid or revoked API key")
    await db.api_keys.update_one({"id": doc["id"]}, {"$set": {"last_used": now_iso()}})
    return doc["tenant_id"]

# ---------- generic CRUD factory ----------
def register_crud(name: str, coll: str, on_create=None, on_update=None):
    @api.get(f"/{name}")
    async def _list(user: dict = Depends(get_current_user), coll=coll):
        docs = await db[coll].find({"tenant_id": user["tenant_id"]}).sort("created_at", -1).to_list(2000)
        return [clean(dict(d)) for d in docs]

    @api.post(f"/{name}")
    async def _create(body: dict, request: Request, user: dict = Depends(get_current_user), coll=coll):
        doc = sanitize_payload(body)
        if coll == "patients":
            await enforce_limit(user["tenant_id"], "patients")
        doc["id"] = str(uuid.uuid4())
        doc["tenant_id"] = user["tenant_id"]
        doc["created_by"] = user["name"]
        doc["created_at"] = now_iso()
        await link_patient_id(coll, doc, user["tenant_id"])
        await db[coll].insert_one(dict(doc))
        await audit(user["email"], user["tenant_id"], "create", coll, doc["id"], client_ip(request))
        if on_create:
            await on_create(user, doc)
        return clean(dict(doc))

    @api.put(f"/{name}/{{item_id}}")
    async def _update(item_id: str, body: dict, request: Request, user: dict = Depends(get_current_user), coll=coll):
        upd = sanitize_payload(body)
        await db[coll].update_one({"id": item_id, "tenant_id": user["tenant_id"]}, {"$set": upd})
        doc = await db[coll].find_one({"id": item_id, "tenant_id": user["tenant_id"]})
        await audit(user["email"], user["tenant_id"], "update", coll, item_id, client_ip(request))
        if on_update and doc:
            await on_update(user, dict(doc))
        return clean(dict(doc))

    @api.delete(f"/{name}/{{item_id}}")
    async def _delete(item_id: str, request: Request, user: dict = Depends(get_current_user), coll=coll):
        await db[coll].delete_one({"id": item_id, "tenant_id": user["tenant_id"]})
        await audit(user["email"], user["tenant_id"], "delete", coll, item_id, client_ip(request))
        return {"ok": True}

async def _appt_created(user, doc):
    pt = await db.patients.find_one({"name": doc.get("patient"), "tenant_id": user["tenant_id"]})
    email = (pt or {}).get("email") or doc.get("email")
    phone = (pt or {}).get("phone") or doc.get("phone")
    body = f"Dear {doc.get('patient','patient')}, your appointment with {doc.get('doctor','our clinic')} is confirmed for {doc.get('date','')} {doc.get('time','')}."
    await notify(user["tenant_id"], "appointment_booked", email, phone,
                 f"Appointment Confirmed - {user.get('clinic_name','')}", body)

async def _lab_updated(user, doc):
    if str(doc.get("status")) == "Completed":
        pt = await db.patients.find_one({"name": doc.get("patient"), "tenant_id": user["tenant_id"]})
        email = (pt or {}).get("email"); phone = (pt or {}).get("phone")
        body = f"Dear {doc.get('patient','patient')}, your {doc.get('test_name','lab test')} results are ready. Please contact the clinic."
        await notify(user["tenant_id"], "lab_results_ready", email, phone, "Lab Results Ready", body)

register_crud("patients", "patients")
register_crud("appointments", "appointments", on_create=_appt_created)
register_crud("prescriptions", "prescriptions")
register_crud("medications", "medications")
register_crud("labtests", "labtests", on_update=_lab_updated)

@api.post("/appointments/{item_id}/remind")
async def remind_appointment(item_id: str, user: dict = Depends(get_current_user)):
    appt = await db.appointments.find_one({"id": item_id, "tenant_id": user["tenant_id"]})
    if not appt:
        raise HTTPException(404, "Appointment not found")
    pt = await db.patients.find_one({"name": appt.get("patient"), "tenant_id": user["tenant_id"]})
    email = (pt or {}).get("email") or appt.get("email")
    phone = (pt or {}).get("phone") or appt.get("phone")
    body = f"Reminder: {appt.get('patient','')} has an appointment with {appt.get('doctor','our clinic')} on {appt.get('date','')} at {appt.get('time','')}."
    await notify(user["tenant_id"], "appointment_reminder", email, phone,
                 f"Appointment Reminder - {user.get('clinic_name','')}", body)
    return {"ok": True}

# ---------- dashboard ----------
@api.get("/dashboard/stats")
async def stats(user: dict = Depends(get_current_user)):
    t = user["tenant_id"]
    today = datetime.now(timezone.utc).date().isoformat()
    appts = await db.appointments.find({"tenant_id": t}).to_list(5000)
    todays = [a for a in appts if str(a.get("date", "")).startswith(today)]
    meds = await db.medications.find({"tenant_id": t}).to_list(5000)
    low_stock = [m for m in meds if float(m.get("stock", 0) or 0) <= float(m.get("reorder_level", 0) or 0)]
    invoices = await db.invoices.find({"tenant_id": t}).to_list(5000)
    revenue = sum(float(i.get("amount", 0) or 0) for i in invoices if i.get("payment_status") == "paid")
    return {
        "patients": await db.patients.count_documents({"tenant_id": t}),
        "appointments_today": len(todays),
        "appointments_total": len(appts),
        "prescriptions": await db.prescriptions.count_documents({"tenant_id": t}),
        "labtests": await db.labtests.count_documents({"tenant_id": t}),
        "medications": len(meds),
        "low_stock": len(low_stock),
        "staff": await db.users.count_documents({"tenant_id": t}),
        "revenue": round(revenue, 2),
        "pending_invoices": len([i for i in invoices if i.get("payment_status") != "paid"]),
    }

# ---------- invoices + payments ----------
@api.get("/invoices")
async def list_invoices(user: dict = Depends(get_current_user)):
    docs = await db.invoices.find({"tenant_id": user["tenant_id"]}).sort("created_at", -1).to_list(2000)
    return [clean(dict(d)) for d in docs]

@api.post("/invoices")
async def create_invoice(body: dict, request: Request, user: dict = Depends(get_current_user)):
    doc = sanitize_payload(body)
    doc["id"] = str(uuid.uuid4())
    doc["tenant_id"] = user["tenant_id"]
    doc["amount"] = float(body.get("amount", 0) or 0)
    doc["payment_status"] = "pending"
    doc["status"] = "unpaid"
    doc["created_at"] = now_iso()
    await link_patient_id("invoices", doc, user["tenant_id"])
    await db.invoices.insert_one(dict(doc))
    await audit(user["email"], user["tenant_id"], "create", "invoices", doc["id"], client_ip(request))
    pt = await db.patients.find_one({"name": doc.get("patient"), "tenant_id": user["tenant_id"]})
    await notify(user["tenant_id"], "invoice_created",
                 (pt or {}).get("email"), (pt or {}).get("phone"),
                 f"New Invoice - {user.get('clinic_name','')}",
                 f"Dear {doc.get('patient','patient')}, an invoice of ${doc.get('amount',0)} has been generated. {doc.get('description','')}")
    return clean(dict(doc))

@api.delete("/invoices/{iid}")
async def del_invoice(iid: str, user: dict = Depends(get_current_user)):
    await db.invoices.delete_one({"id": iid, "tenant_id": user["tenant_id"]})
    return {"ok": True}

@api.post("/payments/checkout")
async def checkout(body: CheckoutIn, request: Request, user: dict = Depends(get_current_user)):
    inv = await db.invoices.find_one({"id": body.invoice_id, "tenant_id": user["tenant_id"]})
    if not inv:
        raise HTTPException(404, "Invoice not found")
    amount = float(inv.get("amount", 0) or 0)
    if amount <= 0:
        raise HTTPException(400, "Invalid invoice amount")
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    sc = StripeCheckout(api_key=os.environ["STRIPE_API_KEY"], webhook_url=webhook_url)
    req = CheckoutSessionRequest(
        amount=amount, currency="usd",
        success_url=f"{body.origin_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{body.origin_url}/billing",
        metadata={"invoice_id": body.invoice_id, "tenant_id": user["tenant_id"]},
    )
    session = await sc.create_checkout_session(req)
    await db.payment_transactions.insert_one({
        "id": str(uuid.uuid4()), "session_id": session.session_id, "invoice_id": body.invoice_id,
        "tenant_id": user["tenant_id"], "amount": amount, "currency": "usd",
        "status": "initiated", "payment_status": "pending",
        "created_at": now_iso(), "updated_at": now_iso(),
    })
    return {"checkout_url": session.url, "session_id": session.session_id}

@api.get("/payments/status/{session_id}")
async def payment_status(session_id: str):
    rec = await db.payment_transactions.find_one({"session_id": session_id})
    if not rec:
        raise HTTPException(404, "Transaction not found")
    if rec.get("payment_status") != "paid":
        try:
            sc = StripeCheckout(api_key=os.environ["STRIPE_API_KEY"], webhook_url="")
            s = await sc.get_checkout_status(session_id)
            if s.payment_status == "paid" or s.status == "complete":
                await db.payment_transactions.update_one(
                    {"session_id": session_id, "payment_status": {"$ne": "paid"}},
                    {"$set": {"status": "completed", "payment_status": "paid", "updated_at": now_iso()}})
                if rec.get("kind") == "subscription":
                    await db.subscriptions.update_one({"tenant_id": rec["tenant_id"]},
                        {"$set": {"plan": rec.get("plan", "free"), "status": "active", "updated_at": now_iso()}}, upsert=True)
                else:
                    await db.invoices.update_one({"id": rec["invoice_id"]},
                        {"$set": {"payment_status": "paid", "status": "paid", "paid_at": now_iso()}})
                    inv = await db.invoices.find_one({"id": rec["invoice_id"]})
                    if inv:
                        pt = await db.patients.find_one({"name": inv.get("patient"), "tenant_id": inv.get("tenant_id")})
                        await notify(inv.get("tenant_id"), "payment_received",
                                     (pt or {}).get("email"), (pt or {}).get("phone"),
                                     "Payment Received",
                                     f"We have received your payment of ${inv.get('amount',0)}. Thank you!")
                rec = await db.payment_transactions.find_one({"session_id": session_id})
        except Exception as e:
            logger.warning(f"stripe status err: {e}")
    return {"session_id": rec["session_id"], "status": rec["status"], "payment_status": rec["payment_status"]}

@api.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
    try:
        sc = StripeCheckout(api_key=os.environ["STRIPE_API_KEY"], webhook_url="")
        resp = await sc.handle_webhook(body, sig)
        if resp.payment_status == "paid":
            await db.payment_transactions.update_one(
                {"session_id": resp.session_id, "payment_status": {"$ne": "paid"}},
                {"$set": {"status": "completed", "payment_status": "paid", "updated_at": now_iso()}})
            meta = resp.metadata or {}
            if meta.get("kind") == "subscription" and meta.get("tenant_id"):
                await db.subscriptions.update_one({"tenant_id": meta["tenant_id"]},
                    {"$set": {"plan": meta.get("plan", "free"), "status": "active", "updated_at": now_iso()}}, upsert=True)
            inv_id = meta.get("invoice_id")
            if inv_id:
                await db.invoices.update_one({"id": inv_id},
                    {"$set": {"payment_status": "paid", "status": "paid", "paid_at": now_iso()}})
    except Exception as e:
        logger.warning(f"webhook err: {e}")
    return {"status": "ok"}

# ---------- AI assistant ----------
@api.post("/assistant/chat")
async def assistant_chat(body: ChatIn, user: dict = Depends(get_current_user)):
    sid = body.session_id or str(uuid.uuid4())
    st = await get_settings(user["tenant_id"])
    ai = resolve_ai_cfg(st.get("integrations", {}))
    sys = ("You are MedAssist, an AI clinical assistant embedded in an EMR used by licensed clinicians. "
           "Help with clinical note summaries, differential considerations, drug-interaction awareness, and documentation. "
           "You are informational decision-support ONLY and are NOT a medical device; you do not provide definitive "
           "diagnoses or treatment orders. Always recommend independent clinician verification for any clinical decision, "
           "flag red-flag/emergency symptoms, and never fabricate patient data. Keep responses concise and evidence-based, "
           "and end with: 'For clinician review — verify before acting.'")
    chat = LlmChat(api_key=ai["api_key"], session_id=sid, system_message=sys).with_model(ai["provider"], ai["model"])
    text = body.message + (f"\n\nClinical context:\n{body.context}" if body.context else "")
    reply = ""
    try:
        async for ev in chat.stream_message(UserMessage(text=text)):
            if isinstance(ev, TextDelta):
                reply += ev.content
            elif isinstance(ev, StreamDone):
                break
    except Exception as e:
        logger.warning(f"AI error: {e}")
        raise HTTPException(502, "AI provider error. Check your AI integration settings/key.")
    await db.chat_messages.insert_one({"id": str(uuid.uuid4()), "tenant_id": user["tenant_id"],
        "user_id": user["id"], "session_id": sid, "message": body.message, "reply": reply,
        "provider": ai["display"], "model": ai["model"], "created_at": now_iso()})
    await audit(user["email"], user["tenant_id"], "ai_query", "assistant", sid, None,
                {"provider": ai["display"], "model": ai["model"]})
    return {"reply": reply, "session_id": sid, "provider": ai["display"], "model": ai["model"],
            "using_managed_key": ai["display"] == "emergent"}

# ---------- API keys (developer) ----------
@api.get("/apikeys")
async def list_api_keys(user: dict = Depends(get_current_user)):
    docs = await db.api_keys.find({"tenant_id": user["tenant_id"]}).sort("created_at", -1).to_list(500)
    return [{"id": d["id"], "name": d.get("name"), "prefix": d.get("prefix"),
             "active": d.get("active", True), "last_used": d.get("last_used"),
             "created_at": d.get("created_at")} for d in docs]

@api.post("/apikeys")
async def create_api_key(body: dict, user: dict = Depends(require_roles("clinic_admin", "super_admin"))):
    raw = "mk_live_" + secrets.token_hex(24)
    doc = {"id": str(uuid.uuid4()), "tenant_id": user["tenant_id"], "name": body.get("name", "Untitled key"),
           "key_hash": hash_key(raw), "prefix": raw[:14], "active": True,
           "last_used": None, "created_at": now_iso()}
    await db.api_keys.insert_one(dict(doc))
    return {"id": doc["id"], "name": doc["name"], "api_key": raw, "prefix": doc["prefix"]}

@api.delete("/apikeys/{kid}")
async def revoke_api_key(kid: str, user: dict = Depends(require_roles("clinic_admin", "super_admin"))):
    await db.api_keys.delete_one({"id": kid, "tenant_id": user["tenant_id"]})
    return {"ok": True}

# ---------- notifications endpoints ----------
@api.get("/notifications")
async def list_notifications(user: dict = Depends(get_current_user)):
    docs = await db.notifications.find({"tenant_id": user["tenant_id"]}).sort("created_at", -1).to_list(300)
    return [clean(dict(d)) for d in docs]

@api.get("/notifications/status")
async def notif_status(user: dict = Depends(get_current_user)):
    st = await get_settings(user["tenant_id"])
    integ = st.get("integrations", {})
    return {"email_configured": email_configured_for(integ), "whatsapp_configured": whatsapp_configured_for(integ),
            "events": st.get("events", {}), "channels": st.get("channels", {}),
            "available_events": EVENTS}

@api.put("/notifications/settings")
async def update_settings(body: dict, user: dict = Depends(get_current_user)):
    upd = {}
    if "events" in body: upd["events"] = body["events"]
    if "channels" in body: upd["channels"] = body["channels"]
    await db.tenant_settings.update_one({"tenant_id": user["tenant_id"]}, {"$set": upd}, upsert=True)
    return await get_settings(user["tenant_id"])

@api.post("/notifications/test")
async def test_notification(body: dict, user: dict = Depends(get_current_user)):
    await notify(user["tenant_id"], "appointment_booked", body.get("email"), body.get("phone"),
                 f"Test message - {user.get('clinic_name','')}",
                 "This is a test notification from your MediCore automation settings.")
    st = await get_settings(user["tenant_id"]); integ = st.get("integrations", {})
    return {"ok": True, "email_configured": email_configured_for(integ), "whatsapp_configured": whatsapp_configured_for(integ)}

# ---------- PUBLIC API (external website integration, X-API-Key auth) ----------
public_api = APIRouter(prefix="/api/public")

@public_api.get("/ping")
async def pub_ping(request: Request):
    t = await get_tenant_by_api_key(request)
    tenant = await db.tenants.find_one({"id": t})
    return {"ok": True, "clinic": (tenant or {}).get("name")}

@public_api.get("/availability")
async def pub_availability(date: str, request: Request):
    t = await get_tenant_by_api_key(request)
    appts = await db.appointments.find({"tenant_id": t, "date": date}).to_list(1000)
    booked = [a.get("time") for a in appts if a.get("time")]
    all_slots = [f"{h:02d}:{m:02d}" for h in range(9, 17) for m in (0, 30)]
    return {"date": date, "available": [s for s in all_slots if s not in booked], "booked": booked}

@public_api.get("/patients")
async def pub_list_patients(request: Request):
    t = await get_tenant_by_api_key(request)
    docs = await db.patients.find({"tenant_id": t}).sort("created_at", -1).to_list(2000)
    return [clean(dict(d)) for d in docs]

@public_api.post("/patients")
async def pub_create_patient(body: dict, request: Request):
    t = await get_tenant_by_api_key(request)
    doc = dict(body); doc["id"] = str(uuid.uuid4()); doc["tenant_id"] = t
    doc["created_by"] = "api"; doc["created_at"] = now_iso()
    await db.patients.insert_one(dict(doc)); return clean(dict(doc))

@public_api.put("/patients/{pid}")
async def pub_update_patient(pid: str, body: dict, request: Request):
    t = await get_tenant_by_api_key(request)
    body.pop("id", None); body.pop("_id", None); body.pop("tenant_id", None)
    await db.patients.update_one({"id": pid, "tenant_id": t}, {"$set": body})
    return clean(dict(await db.patients.find_one({"id": pid, "tenant_id": t})))

@public_api.get("/appointments")
async def pub_list_appts(request: Request):
    t = await get_tenant_by_api_key(request)
    docs = await db.appointments.find({"tenant_id": t}).sort("created_at", -1).to_list(2000)
    return [clean(dict(d)) for d in docs]

@public_api.post("/appointments")
async def pub_create_appt(body: dict, request: Request):
    t = await get_tenant_by_api_key(request)
    doc = dict(body); doc["id"] = str(uuid.uuid4()); doc["tenant_id"] = t
    doc["status"] = doc.get("status", "Scheduled"); doc["created_by"] = "api"; doc["created_at"] = now_iso()
    await db.appointments.insert_one(dict(doc))
    tenant = await db.tenants.find_one({"id": t})
    await notify(t, "appointment_booked", doc.get("email"), doc.get("phone"),
                 f"Appointment Confirmed - {(tenant or {}).get('name','')}",
                 f"Dear {doc.get('patient','patient')}, your appointment is confirmed for {doc.get('date','')} {doc.get('time','')}.")
    return clean(dict(doc))

@public_api.put("/appointments/{aid}")
async def pub_update_appt(aid: str, body: dict, request: Request):
    t = await get_tenant_by_api_key(request)
    body.pop("id", None); body.pop("_id", None); body.pop("tenant_id", None)
    await db.appointments.update_one({"id": aid, "tenant_id": t}, {"$set": body})
    return clean(dict(await db.appointments.find_one({"id": aid, "tenant_id": t})))

# ---------- pluggable integrations config ----------
def _mask_cfg(cfg):
    if not cfg:
        return {}
    return {k: ("********" if (k in SECRET_FIELDS and v) else v) for k, v in cfg.items()}

@api.get("/integrations")
async def get_integrations(user: dict = Depends(get_current_user)):
    st = await get_settings(user["tenant_id"])
    integ = st.get("integrations", {})
    return {
        "email": {"provider": (integ.get("email") or {}).get("provider"),
                  "config": _mask_cfg(integ.get("email")), "configured": email_configured_for(integ)},
        "whatsapp": {"provider": (integ.get("whatsapp") or {}).get("provider"),
                     "config": _mask_cfg(integ.get("whatsapp")), "configured": whatsapp_configured_for(integ)},
        "ai": {"provider": (integ.get("ai") or {}).get("provider") or "emergent",
               "config": _mask_cfg(integ.get("ai")),
               "configured": bool(((integ.get("ai") or {}).get("provider") or "emergent") == "emergent" or (integ.get("ai") or {}).get("api_key")),
               "using_managed_key": resolve_ai_cfg(integ)["display"] == "emergent"},
        "email_providers": EMAIL_PROVIDERS, "whatsapp_providers": WHATSAPP_PROVIDERS,
        "ai_providers": AI_PROVIDERS, "ai_default_models": AI_DEFAULT_MODELS,
        "secret_fields": sorted(SECRET_FIELDS),
    }

@api.put("/integrations")
async def put_integrations(body: dict, user: dict = Depends(require_roles("clinic_admin", "super_admin"))):
    st = await get_settings(user["tenant_id"])
    integ = st.get("integrations", {}) or {}
    for channel in ("email", "whatsapp", "ai"):
        if channel in body:
            incoming = body[channel] or {}
            merged = dict(integ.get(channel, {}) or {})
            # keep existing secret when the UI sends the masked placeholder back
            for k, v in incoming.items():
                if k in SECRET_FIELDS and v == "********":
                    continue
                merged[k] = v
            integ[channel] = merged
    await db.tenant_settings.update_one({"tenant_id": user["tenant_id"]},
                                        {"$set": {"integrations": integ}}, upsert=True)
    return {"ok": True}

# ---------- Patient Portal ----------
class PortalLoginIn(BaseModel):
    email: EmailStr
    phone: str

def create_patient_token(pid: str, tenant_id: str) -> str:
    payload = {"sub": pid, "tenant_id": tenant_id, "type": "patient",
               "exp": datetime.now(timezone.utc) + timedelta(days=7)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

async def get_current_patient(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else None
    if not token:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
    if payload.get("type") != "patient":
        raise HTTPException(401, "Not a patient session")
    pt = await db.patients.find_one({"id": payload["sub"], "tenant_id": payload["tenant_id"]})
    if not pt:
        raise HTTPException(401, "Patient not found")
    return clean(dict(pt))

@api.post("/portal/login")
async def portal_login(body: PortalLoginIn):
    email = body.email.lower().strip()
    phone = body.phone.strip()
    await check_lockout(f"portal:{email}")
    pt = await db.patients.find_one({
        "email": {"$regex": f"^{re.escape(email)}$", "$options": "i"}, "phone": phone})
    if not pt:
        await record_login_fail(f"portal:{email}")
        raise HTTPException(401, "No matching patient record. Please confirm the email and phone your clinic has on file.")
    await clear_login_fails(f"portal:{email}")
    tenant = await db.tenants.find_one({"id": pt["tenant_id"]})
    await audit(email, pt["tenant_id"], "portal_login", "patient", pt["id"])
    return {"token": create_patient_token(pt["id"], pt["tenant_id"]),
            "patient": clean(dict(pt)), "clinic": (tenant or {}).get("name")}

@api.get("/portal/me")
async def portal_me(pt: dict = Depends(get_current_patient)):
    tenant = await db.tenants.find_one({"id": pt["tenant_id"]})
    return {"patient": pt, "clinic": (tenant or {}).get("name")}

def _portal_match(pt):
    # Prefer patient_id linkage; only fall back to name for legacy records lacking an id.
    return {"tenant_id": pt["tenant_id"], "$or": [
        {"patient_id": pt["id"]},
        {"patient_id": {"$exists": False}, "patient": pt["name"]}]}

@api.get("/portal/appointments")
async def portal_appointments(pt: dict = Depends(get_current_patient)):
    docs = await db.appointments.find(_portal_match(pt)).sort("created_at", -1).to_list(1000)
    return [clean(dict(d)) for d in docs]

@api.get("/portal/prescriptions")
async def portal_prescriptions(pt: dict = Depends(get_current_patient)):
    docs = await db.prescriptions.find(_portal_match(pt)).sort("created_at", -1).to_list(1000)
    return [clean(dict(d)) for d in docs]

@api.get("/portal/invoices")
async def portal_invoices(pt: dict = Depends(get_current_patient)):
    docs = await db.invoices.find(_portal_match(pt)).sort("created_at", -1).to_list(1000)
    return [clean(dict(d)) for d in docs]

# ---------- SaaS subscription, compliance & account recovery ----------
class ResetReqIn(BaseModel):
    email: EmailStr

class ResetConfirmIn(BaseModel):
    token: str
    password: str

@api.get("/subscription")
async def subscription_get(user: dict = Depends(get_current_user)):
    sub = await get_subscription(user["tenant_id"])
    plan = PLANS.get(sub.get("plan", "free"), PLANS["free"])
    staff = await db.users.count_documents({"tenant_id": user["tenant_id"]})
    patients = await db.patients.count_documents({"tenant_id": user["tenant_id"]})
    return {"subscription": sub, "plan": plan, "plans": PLANS, "usage": {"staff": staff, "patients": patients}}

@api.post("/subscription/checkout")
async def subscription_checkout(body: dict, request: Request, user: dict = Depends(require_roles("clinic_admin", "super_admin"))):
    plan_id = body.get("plan")
    if plan_id not in PLANS or PLANS[plan_id]["price"] <= 0:
        raise HTTPException(400, "Invalid plan selection")
    origin = (body.get("origin_url") or str(request.base_url)).rstrip("/")
    sc = StripeCheckout(api_key=os.environ["STRIPE_API_KEY"], webhook_url=f"{str(request.base_url)}api/webhook/stripe")
    req = CheckoutSessionRequest(
        amount=float(PLANS[plan_id]["price"]), currency="usd",
        success_url=f"{origin}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{origin}/app/subscription",
        metadata={"kind": "subscription", "plan": plan_id, "tenant_id": user["tenant_id"]})
    session = await sc.create_checkout_session(req)
    await db.payment_transactions.insert_one({"id": str(uuid.uuid4()), "session_id": session.session_id,
        "kind": "subscription", "plan": plan_id, "tenant_id": user["tenant_id"],
        "amount": float(PLANS[plan_id]["price"]), "currency": "usd", "status": "initiated",
        "payment_status": "pending", "created_at": now_iso(), "updated_at": now_iso()})
    await audit(user["email"], user["tenant_id"], "subscription_checkout", "subscription", plan_id, client_ip(request))
    return {"checkout_url": session.url, "session_id": session.session_id}

@api.get("/audit-logs")
async def list_audit_logs(user: dict = Depends(require_roles("clinic_admin", "super_admin"))):
    docs = await db.audit_logs.find({"tenant_id": user["tenant_id"]}).sort("created_at", -1).to_list(500)
    return [clean(dict(d)) for d in docs]

@api.get("/compliance/export")
async def compliance_export(user: dict = Depends(require_roles("clinic_admin", "super_admin"))):
    t = user["tenant_id"]; out = {}
    for c in ["patients", "appointments", "prescriptions", "labtests", "medications", "invoices"]:
        docs = await db[c].find({"tenant_id": t}).to_list(100000)
        out[c] = [clean(dict(d)) for d in docs]
    await audit(user["email"], t, "export", "tenant_data", t)
    return out

@api.delete("/compliance/patient/{pid}")
async def compliance_delete_patient(pid: str, request: Request, user: dict = Depends(require_roles("clinic_admin", "super_admin"))):
    pt = await db.patients.find_one({"id": pid, "tenant_id": user["tenant_id"]})
    if not pt:
        raise HTTPException(404, "Patient not found")
    for c in ["appointments", "prescriptions", "labtests", "invoices"]:
        await db[c].delete_many({"tenant_id": user["tenant_id"], "$or": [{"patient_id": pid}, {"patient": pt.get("name")}]})
    await db.patients.delete_one({"id": pid, "tenant_id": user["tenant_id"]})
    await audit(user["email"], user["tenant_id"], "erase", "patient", pid, client_ip(request))
    return {"ok": True}

@api.put("/patients/{pid}/consent")
async def set_patient_consent(pid: str, body: dict, user: dict = Depends(get_current_user)):
    await db.patients.update_one({"id": pid, "tenant_id": user["tenant_id"]},
        {"$set": {"consent": bool(body.get("consent")), "consent_at": now_iso()}})
    await audit(user["email"], user["tenant_id"], "consent", "patient", pid, None, {"consent": bool(body.get("consent"))})
    return {"ok": True}

@api.post("/auth/request-reset")
async def request_password_reset(body: ResetReqIn):
    user = await db.users.find_one({"email": body.email.lower()})
    dev_token = None
    if user:
        token = secrets.token_urlsafe(32)
        await db.password_resets.insert_one({"email": user["email"], "token": token,
            "expires": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "used": False, "created_at": now_iso()})
        # Deliver the code by email directly — never persist the token in the notification log.
        st = await get_settings(user["tenant_id"])
        cfg = resolve_email_cfg(st.get("integrations", {}))
        if cfg:
            try:
                send_email_via(cfg, user["email"], "Password reset code",
                               f"Your password reset code is: {token}\nIt expires in 1 hour.")
            except Exception as e:
                logger.warning(f"reset email failed: {e}")
        else:
            dev_token = token  # surfaced only when no email provider is configured yet
        await audit(user["email"], user["tenant_id"], "password_reset_request", "user", user["id"])
    return {"ok": True, "dev_token": dev_token}

@api.post("/auth/reset")
async def confirm_password_reset(body: ResetConfirmIn):
    validate_password(body.password)
    rec = await db.password_resets.find_one({"token": body.token, "used": False})
    if not rec or datetime.fromisoformat(rec["expires"]) < datetime.now(timezone.utc):
        raise HTTPException(400, "Invalid or expired reset token")
    await db.users.update_one({"email": rec["email"]}, {"$set": {"password_hash": hash_password(body.password)}})
    await db.password_resets.update_one({"_id": rec["_id"]}, {"$set": {"used": True}})
    await clear_login_fails(rec["email"])
    return {"ok": True}

# ---------- Scheduled reminders (platform cron) ----------
async def _run_appointment_reminders():
    tomorrow = (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat()
    appts = await db.appointments.find({"date": tomorrow, "reminder_sent": {"$ne": True}}).to_list(5000)
    for a in appts:
        pt = await db.patients.find_one({"name": a.get("patient"), "tenant_id": a.get("tenant_id")})
        email = (pt or {}).get("email") or a.get("email")
        phone = (pt or {}).get("phone") or a.get("phone")
        tenant = await db.tenants.find_one({"id": a.get("tenant_id")})
        body = (f"Reminder: {a.get('patient','')}, you have an appointment with "
                f"{a.get('doctor','our clinic')} tomorrow ({a.get('date','')}) at {a.get('time','')}.")
        await notify(a.get("tenant_id"), "appointment_reminder", email, phone,
                     f"Appointment Reminder - {(tenant or {}).get('name','')}", body)
        await db.appointments.update_one({"id": a["id"]}, {"$set": {"reminder_sent": True}})

@api.post("/cron/appointment-reminders")
async def cron_appointment_reminders(request: Request):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    expected = os.environ.get("WEBHOOK_CRON_SECRET", "")
    auth = request.headers.get("Authorization", "")
    provided = auth[7:] if auth.startswith("Bearer ") else ""
    if not expected or not hmac.compare_digest(provided, expected):
        raise HTTPException(401, "Unauthorized")
    asyncio.create_task(_run_appointment_reminders())
    return {"status": "accepted"}

# ---------- Embeddable website booking widget ----------
from fastapi.responses import Response

WIDGET_JS = r"""(function(){
  var s = document.currentScript;
  var key = s.getAttribute('data-api-key');
  var clinic = s.getAttribute('data-clinic') || 'Book an Appointment';
  var base = new URL(s.src).origin + '/api/public';
  var host = document.getElementById('medicore-booking');
  if(!host){ host = document.createElement('div'); s.parentNode.insertBefore(host, s.nextSibling); }
  function val(id){ var el = host.querySelector('#'+id); return el ? el.value : ''; }
  host.innerHTML = '<div style="font-family:system-ui,sans-serif;max-width:420px;border:1px solid #e5e2da;border-radius:14px;padding:22px;background:#fff;box-shadow:0 10px 30px -14px rgba(15,62,46,.28)">'
    + '<h3 style="margin:0 0 16px;color:#0F3E2E;font-size:20px">'+clinic+'</h3>'
    + '<div id="mc-form"></div><div id="mc-msg" style="margin-top:10px;font-size:14px"></div>'
    + '<div style="margin-top:12px;font-size:11px;color:#9a978e">Powered by MediCore</div></div>';
  var f = host.querySelector('#mc-form');
  function inp(ph,type,id){ return '<input id="'+id+'" type="'+type+'" placeholder="'+ph+'" style="width:100%;box-sizing:border-box;margin-bottom:10px;padding:11px;border:1px solid #d8d3c8;border-radius:9px;font-size:14px"/>'; }
  f.innerHTML = inp('Full name','text','mc-name')+inp('Email','email','mc-email')+inp('Phone e.g. +14155550100','text','mc-phone')
    + inp('','date','mc-date')
    + '<select id="mc-time" style="width:100%;box-sizing:border-box;margin-bottom:10px;padding:11px;border:1px solid #d8d3c8;border-radius:9px;font-size:14px"><option value="">Pick a date first</option></select>'
    + inp('Reason for visit','text','mc-reason')
    + '<button id="mc-submit" style="width:100%;padding:12px;background:#0F3E2E;color:#fff;border:0;border-radius:999px;cursor:pointer;font-size:15px">Book appointment</button>';
  host.querySelector('#mc-date').addEventListener('change', function(){
    var t = host.querySelector('#mc-time'); t.innerHTML = '<option>Loading...</option>';
    fetch(base+'/availability?date='+val('mc-date'), {headers:{'X-API-Key':key}})
      .then(function(r){return r.json();})
      .then(function(d){ t.innerHTML = (d.available||[]).map(function(x){return '<option>'+x+'</option>';}).join('') || '<option value="">No open slots</option>'; })
      .catch(function(){ t.innerHTML = '<option value="">Could not load slots</option>'; });
  });
  host.querySelector('#mc-submit').addEventListener('click', function(){
    var msg = host.querySelector('#mc-msg');
    var payload = { patient:val('mc-name'), email:val('mc-email'), phone:val('mc-phone'), date:val('mc-date'), time:val('mc-time'), reason:val('mc-reason'), status:'Scheduled' };
    if(!payload.patient||!payload.date||!payload.time){ msg.style.color='#b45309'; msg.textContent='Please add your name, date and time.'; return; }
    msg.style.color='#0F3E2E'; msg.textContent='Booking...';
    fetch(base+'/appointments', {method:'POST',headers:{'X-API-Key':key,'Content-Type':'application/json'},body:JSON.stringify(payload)})
      .then(function(r){ if(!r.ok) throw new Error('x'); return r.json(); })
      .then(function(){ msg.style.color='#047857'; msg.textContent='Appointment booked! The clinic will confirm shortly.'; f.querySelectorAll('input,select').forEach(function(e){e.value='';}); })
      .catch(function(){ msg.style.color='#b91c1c'; msg.textContent='Could not book right now. Please try again.'; });
  });
})();"""

@app.get("/api/public/widget.js")
async def booking_widget_js():
    return Response(content=WIDGET_JS, media_type="application/javascript")

app.include_router(api)
app.include_router(public_api)
_cors = os.environ.get("CORS_ORIGINS", "*").strip()
if _cors and _cors != "*":
    _origins = [o.strip() for o in _cors.split(",") if o.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"])
else:
    app.add_middleware(CORSMiddleware, allow_origin_regex=".*", allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"])

@app.get("/api/health")
async def health():
    try:
        await db.command("ping")
        return {"status": "ok", "db": "up"}
    except Exception:
        return {"status": "degraded", "db": "down"}

@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("tenant_id")
    await db.audit_logs.create_index([("tenant_id", 1), ("created_at", -1)])
    await db.login_attempts.create_index("email", unique=True)
    await db.password_resets.create_index("token")
    admin_email = os.environ["ADMIN_EMAIL"].lower()
    admin_pw = os.environ["ADMIN_PASSWORD"]
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        tenant_id = str(uuid.uuid4())
        await db.tenants.insert_one({"id": tenant_id, "name": "Emergent Health HQ", "created_at": now_iso()})
        await db.users.insert_one({"id": str(uuid.uuid4()), "email": admin_email,
            "password_hash": hash_password(admin_pw), "name": "System Owner", "role": "super_admin",
            "tenant_id": tenant_id, "clinic_name": "Emergent Health HQ", "created_at": now_iso(), "auth": "jwt"})
        logger.info("Seeded admin user")

@app.on_event("shutdown")
async def shutdown():
    client.close()
