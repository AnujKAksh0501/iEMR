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
async def register(body: RegisterIn):
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "Email already registered")
    tenant_id = str(uuid.uuid4())
    await db.tenants.insert_one({"id": tenant_id, "name": body.clinic_name, "created_at": now_iso()})
    uid = str(uuid.uuid4())
    user = {"id": uid, "email": email, "password_hash": hash_password(body.password),
            "name": body.name, "role": "clinic_admin", "tenant_id": tenant_id,
            "clinic_name": body.clinic_name, "created_at": now_iso(), "auth": "jwt"}
    await db.users.insert_one(dict(user))
    return {"token": create_token(uid), "user": clean(dict(user))}

@api.post("/auth/login")
async def login(body: LoginIn):
    user = await db.users.find_one({"email": body.email.lower()})
    if not user or not verify_password(body.password, user.get("password_hash", "")):
        raise HTTPException(401, "Invalid email or password")
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
async def add_staff(body: StaffIn, user: dict = Depends(require_roles("clinic_admin", "super_admin"))):
    if body.role not in ROLES:
        raise HTTPException(400, "Invalid role")
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "Email already registered")
    uid = str(uuid.uuid4())
    doc = {"id": uid, "email": email, "password_hash": hash_password(body.password),
           "name": body.name, "role": body.role, "tenant_id": user["tenant_id"],
           "clinic_name": user.get("clinic_name"), "created_at": now_iso(), "auth": "jwt"}
    await db.users.insert_one(dict(doc))
    return clean(dict(doc))

@api.delete("/staff/{sid}")
async def del_staff(sid: str, user: dict = Depends(require_roles("clinic_admin", "super_admin"))):
    if sid == user["id"]:
        raise HTTPException(400, "Cannot delete yourself")
    await db.users.delete_one({"id": sid, "tenant_id": user["tenant_id"]})
    return {"ok": True}

# ---------- generic CRUD factory ----------
def register_crud(name: str, coll: str):
    @api.get(f"/{name}")
    async def _list(user: dict = Depends(get_current_user), coll=coll):
        docs = await db[coll].find({"tenant_id": user["tenant_id"]}).sort("created_at", -1).to_list(2000)
        return [clean(dict(d)) for d in docs]

    @api.post(f"/{name}")
    async def _create(body: dict, user: dict = Depends(get_current_user), coll=coll):
        doc = dict(body)
        doc["id"] = str(uuid.uuid4())
        doc["tenant_id"] = user["tenant_id"]
        doc["created_by"] = user["name"]
        doc["created_at"] = now_iso()
        await db[coll].insert_one(dict(doc))
        return clean(dict(doc))

    @api.put(f"/{name}/{{item_id}}")
    async def _update(item_id: str, body: dict, user: dict = Depends(get_current_user), coll=coll):
        body.pop("id", None); body.pop("_id", None); body.pop("tenant_id", None)
        await db[coll].update_one({"id": item_id, "tenant_id": user["tenant_id"]}, {"$set": body})
        doc = await db[coll].find_one({"id": item_id, "tenant_id": user["tenant_id"]})
        return clean(dict(doc))

    @api.delete(f"/{name}/{{item_id}}")
    async def _delete(item_id: str, user: dict = Depends(get_current_user), coll=coll):
        await db[coll].delete_one({"id": item_id, "tenant_id": user["tenant_id"]})
        return {"ok": True}

for n, c in [("patients", "patients"), ("appointments", "appointments"),
             ("prescriptions", "prescriptions"), ("medications", "medications"),
             ("labtests", "labtests")]:
    register_crud(n, c)

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
async def create_invoice(body: dict, user: dict = Depends(get_current_user)):
    doc = dict(body)
    doc["id"] = str(uuid.uuid4())
    doc["tenant_id"] = user["tenant_id"]
    doc["amount"] = float(body.get("amount", 0) or 0)
    doc["payment_status"] = "pending"
    doc["status"] = "unpaid"
    doc["created_at"] = now_iso()
    await db.invoices.insert_one(dict(doc))
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
                await db.invoices.update_one({"id": rec["invoice_id"]},
                    {"$set": {"payment_status": "paid", "status": "paid", "paid_at": now_iso()}})
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
            inv_id = (resp.metadata or {}).get("invoice_id")
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
    sys = ("You are MedAssist, an AI clinical assistant embedded in an EMR used by clinicians. "
           "Help with clinical note summaries, differential diagnoses, drug interactions, and documentation. "
           "Be concise and evidence-based. Always add a brief disclaimer that outputs need clinician review "
           "for critical decisions. Never fabricate patient data.")
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=sid, system_message=sys).with_model("openai", "gpt-5.4")
    text = body.message + (f"\n\nClinical context:\n{body.context}" if body.context else "")
    reply = ""
    async for ev in chat.stream_message(UserMessage(text=text)):
        if isinstance(ev, TextDelta):
            reply += ev.content
        elif isinstance(ev, StreamDone):
            break
    await db.chat_messages.insert_one({"id": str(uuid.uuid4()), "tenant_id": user["tenant_id"],
        "user_id": user["id"], "session_id": sid, "message": body.message, "reply": reply,
        "created_at": now_iso()})
    return {"reply": reply, "session_id": sid}

app.include_router(api)
app.add_middleware(CORSMiddleware, allow_origin_regex=".*", allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("tenant_id")
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
