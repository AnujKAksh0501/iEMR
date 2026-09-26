"""Iteration 4 backend tests: password policy, lockout, reset, AI providers,
audit logs, PHI patient_id linkage, subscription enforcement, sanitization,
GDPR export/erasure, and /api/health.
"""
import os
import uuid
import time

import pytest
import requests

_env = {}
try:
    with open("/app/frontend/.env") as _f:
        for _line in _f:
            if "=" in _line:
                _k, _v = _line.strip().split("=", 1)
                _env[_k] = _v.strip('"').strip("'")
except Exception:
    pass
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _env.get("REACT_APP_BACKEND_URL", "")).rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL not set"
API = f"{BASE_URL}/api"


def _rand():
    return uuid.uuid4().hex[:8]


def _h(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


def _register(pw="Passw0rd1"):
    email = f"TEST_{_rand()}@demo.com"
    body = {"email": email, "password": pw, "name": "T Admin", "clinic_name": f"TEST_C_{_rand()}"}
    r = requests.post(f"{API}/auth/register", json=body, timeout=20)
    return r, email, body


@pytest.fixture(scope="module")
def clinic():
    r, email, body = _register()
    assert r.status_code == 200, r.text
    d = r.json()
    return {"token": d["token"], "email": email, "password": body["password"], "user": d["user"]}


# ============ Health ============
class TestHealth:
    def test_health_ok(self):
        r = requests.get(f"{API}/health", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "ok" and d["db"] == "up"


# ============ Password policy ============
class TestPasswordPolicy:
    def test_weak_password_rejected(self):
        body = {"email": f"TEST_{_rand()}@demo.com", "password": "abc",
                "name": "x", "clinic_name": "TEST_C"}
        r = requests.post(f"{API}/auth/register", json=body, timeout=20)
        assert r.status_code == 400

    def test_missing_upper_rejected(self):
        body = {"email": f"TEST_{_rand()}@demo.com", "password": "password1",
                "name": "x", "clinic_name": "TEST_C"}
        r = requests.post(f"{API}/auth/register", json=body, timeout=20)
        assert r.status_code == 400

    def test_strong_password_creates_free_sub(self, clinic):
        r = requests.get(f"{API}/subscription", headers=_h(clinic["token"]), timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d["subscription"]["plan"] == "free"
        assert d["plan"]["max_staff"] == 3
        assert "plans" in d and "usage" in d


# ============ Login brute force lockout ============
class TestLockout:
    def test_lockout_after_5_fails(self):
        r, email, body = _register()
        assert r.status_code == 200
        # 5 failed attempts
        for i in range(5):
            rr = requests.post(f"{API}/auth/login",
                               json={"email": email, "password": "WrongPass1"}, timeout=20)
            assert rr.status_code == 401
        # Correct password should now be locked
        rr = requests.post(f"{API}/auth/login",
                           json={"email": email, "password": body["password"]}, timeout=20)
        assert rr.status_code == 429


# ============ Password reset ============
class TestReset:
    def test_reset_full_flow(self):
        r, email, body = _register()
        assert r.status_code == 200
        # Request reset
        rr = requests.post(f"{API}/auth/request-reset", json={"email": email}, timeout=20)
        assert rr.status_code == 200
        d = rr.json()
        assert d["ok"] is True
        token = d.get("dev_token")
        assert token, "dev_token should be surfaced when email not configured"

        # Weak new pw rejected
        rw = requests.post(f"{API}/auth/reset", json={"token": token, "password": "abc"}, timeout=20)
        assert rw.status_code == 400

        # Strong new pw succeeds
        newpw = "NewPass9z"
        ro = requests.post(f"{API}/auth/reset", json={"token": token, "password": newpw}, timeout=20)
        assert ro.status_code == 200

        # Old pw no longer works
        rold = requests.post(f"{API}/auth/login",
                             json={"email": email, "password": body["password"]}, timeout=20)
        assert rold.status_code == 401
        # New pw works
        rnew = requests.post(f"{API}/auth/login",
                             json={"email": email, "password": newpw}, timeout=20)
        assert rnew.status_code == 200

    def test_reset_invalid_token(self):
        r = requests.post(f"{API}/auth/reset",
                          json={"token": "bogusnothere", "password": "GoodPass1"}, timeout=20)
        assert r.status_code == 400


# ============ AI provider config ============
class TestAI:
    def test_ai_config_and_chat(self, clinic):
        # set emergent + model
        body = {"ai": {"provider": "emergent", "model": "gpt-5.4"}}
        r = requests.put(f"{API}/integrations", json=body, headers=_h(clinic["token"]), timeout=20)
        assert r.status_code == 200

        # get shows ai section + ai_providers
        rg = requests.get(f"{API}/integrations", headers=_h(clinic["token"]), timeout=20)
        assert rg.status_code == 200
        d = rg.json()
        assert "ai" in d and d["ai"]["provider"] == "emergent"
        assert set(["emergent", "openai", "anthropic", "gemini"]).issubset(set(d["ai_providers"].keys()))

        # Chat returns provider+model
        rc = requests.post(f"{API}/assistant/chat",
                           json={"message": "Say hi in one word."},
                           headers=_h(clinic["token"]), timeout=90)
        assert rc.status_code == 200, rc.text
        dc = rc.json()
        assert "reply" in dc and dc.get("provider") == "emergent"
        assert dc.get("model") == "gpt-5.4"

    def test_ai_key_masked(self, clinic):
        body = {"ai": {"provider": "openai", "api_key": "sk_real_openai_key", "model": "gpt-5.4"}}
        r = requests.put(f"{API}/integrations", json=body, headers=_h(clinic["token"]), timeout=20)
        assert r.status_code == 200
        rg = requests.get(f"{API}/integrations", headers=_h(clinic["token"]), timeout=20).json()
        assert rg["ai"]["config"].get("api_key") == "********"
        # revert to emergent so chat tests elsewhere still work
        requests.put(f"{API}/integrations",
                     json={"ai": {"provider": "emergent", "model": "gpt-5.4"}},
                     headers=_h(clinic["token"]), timeout=20)


# ============ Audit logging ============
class TestAudit:
    def test_audit_logs_populated(self, clinic):
        # trigger a create
        pt = {"name": f"TEST_AuditPt_{_rand()}", "email": f"TEST_ap_{_rand()}@x.com",
              "phone": f"+141555{_rand()[:5]}", "age": 22, "gender": "M"}
        r = requests.post(f"{API}/patients", json=pt, headers=_h(clinic["token"]), timeout=20)
        assert r.status_code == 200

        rg = requests.get(f"{API}/audit-logs", headers=_h(clinic["token"]), timeout=20)
        assert rg.status_code == 200
        logs = rg.json()
        assert isinstance(logs, list) and len(logs) > 0
        sample = logs[0]
        for k in ("actor", "action", "resource", "ip"):
            assert k in sample
        actions = {l.get("action") for l in logs}
        assert "create" in actions or "login" in actions or "register" in actions

    def test_audit_forbidden_for_non_admin(self):
        # Use a fresh clinic to avoid interfering with the free-plan staff cap.
        r, _email, body = _register()
        assert r.status_code == 200
        tok = r.json()["token"]
        pw = "StaffPass1"
        staff = {"email": f"TEST_doc_{_rand()}@x.com", "password": pw,
                 "name": "Doc", "role": "doctor"}
        rs = requests.post(f"{API}/staff", json=staff, headers=_h(tok), timeout=20)
        assert rs.status_code == 200, rs.text
        # login as doctor
        rl = requests.post(f"{API}/auth/login",
                           json={"email": staff["email"], "password": pw}, timeout=20)
        assert rl.status_code == 200
        dtok = rl.json()["token"]
        # doctor cannot read audit logs
        ra = requests.get(f"{API}/audit-logs", headers=_h(dtok), timeout=20)
        assert ra.status_code == 403


# ============ PHI patient_id linkage ============
class TestPHILinkage:
    def test_same_name_patients_isolated(self, clinic):
        name = f"TEST_John_{_rand()}"
        p1 = {"name": name, "email": f"TEST_j1_{_rand()}@x.com",
              "phone": f"+141555{_rand()[:5]}", "age": 40, "gender": "M"}
        p2 = {"name": name, "email": f"TEST_j2_{_rand()}@x.com",
              "phone": f"+141666{_rand()[:5]}", "age": 41, "gender": "M"}
        r1 = requests.post(f"{API}/patients", json=p1, headers=_h(clinic["token"]), timeout=20)
        r2 = requests.post(f"{API}/patients", json=p2, headers=_h(clinic["token"]), timeout=20)
        assert r1.status_code == 200 and r2.status_code == 200
        pt1 = r1.json(); pt2 = r2.json()

        # Appt referencing patient by name; server should link patient_id.
        # It'll match the first name found; we control by using patient_id in ID lookups.
        # To make test deterministic, create appt via explicit patient_id
        appt = {"patient": name, "patient_id": pt1["id"], "doctor": "Dr Z",
                "date": "2030-01-01", "time": "10:00", "status": "Scheduled"}
        ra = requests.post(f"{API}/appointments", json=appt, headers=_h(clinic["token"]), timeout=20)
        # sanitize strips no allowed keys; patient_id passes through since not in blocked list
        assert ra.status_code == 200

        # Portal-login as p1
        pl1 = requests.post(f"{API}/portal/login",
                            json={"email": pt1["email"], "phone": pt1["phone"]}, timeout=20)
        assert pl1.status_code == 200
        tok1 = pl1.json()["token"]

        # Portal-login as p2
        pl2 = requests.post(f"{API}/portal/login",
                            json={"email": pt2["email"], "phone": pt2["phone"]}, timeout=20)
        assert pl2.status_code == 200
        tok2 = pl2.json()["token"]

        a1 = requests.get(f"{API}/portal/appointments", headers=_h(tok1), timeout=20).json()
        a2 = requests.get(f"{API}/portal/appointments", headers=_h(tok2), timeout=20).json()

        # p1 sees the linked appt, p2 must NOT see it (new appt carries patient_id)
        assert any(a.get("patient_id") == pt1["id"] for a in a1)
        assert all(a.get("patient_id") != pt1["id"] for a in a2)


# ============ Subscription enforcement ============
class TestSubscription:
    def test_free_plan_staff_limit(self, clinic):
        # Free plan max_staff=3 (admin=1 already, TestAudit added a doctor => 2). Fill to 3, then 4th should 402.
        # Query current count
        st = requests.get(f"{API}/staff", headers=_h(clinic["token"]), timeout=20).json()
        cur = len(st)
        # add up to 3 total
        added_ok = 0
        for i in range(max(0, 3 - cur)):
            s = {"email": f"TEST_fill_{_rand()}@x.com", "password": "Passw0rd1",
                 "name": f"F{i}", "role": "nurse"}
            r = requests.post(f"{API}/staff", json=s, headers=_h(clinic["token"]), timeout=20)
            assert r.status_code == 200, r.text
            added_ok += 1
        # one more should be 402
        s = {"email": f"TEST_over_{_rand()}@x.com", "password": "Passw0rd1",
             "name": "Over", "role": "nurse"}
        r = requests.post(f"{API}/staff", json=s, headers=_h(clinic["token"]), timeout=20)
        assert r.status_code == 402, f"expected 402, got {r.status_code}: {r.text}"

    def test_checkout_pro_returns_url(self, clinic):
        r = requests.post(f"{API}/subscription/checkout",
                          json={"plan": "pro", "origin_url": BASE_URL},
                          headers=_h(clinic["token"]), timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("checkout_url", "").startswith("https://")

    def test_checkout_invalid_plan(self, clinic):
        r = requests.post(f"{API}/subscription/checkout",
                          json={"plan": "bogus"},
                          headers=_h(clinic["token"]), timeout=20)
        assert r.status_code == 400


# ============ Payload sanitization ============
class TestSanitization:
    def test_operator_key_stripped(self, clinic):
        body = {"name": f"TEST_San_{_rand()}", "$where": "1==1",
                "bad.key": "x", "email": f"TEST_san_{_rand()}@x.com",
                "phone": "+14155550999", "age": 30, "gender": "F"}
        r = requests.post(f"{API}/patients", json=body, headers=_h(clinic["token"]), timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert "$where" not in d and "bad.key" not in d

    def test_role_tenant_id_not_overridable(self, clinic):
        # patient body with role/tenant_id keys — should be stripped
        body = {"name": f"TEST_San2_{_rand()}", "role": "super_admin",
                "tenant_id": "attacker", "email": f"TEST_san2_{_rand()}@x.com",
                "phone": "+14155550998", "age": 30, "gender": "F"}
        r = requests.post(f"{API}/patients", json=body, headers=_h(clinic["token"]), timeout=20)
        assert r.status_code == 200
        d = r.json()
        # tenant_id must be the caller's tenant, not "attacker"
        assert d.get("tenant_id") == clinic["user"]["tenant_id"]
        assert d.get("role") != "super_admin"


# ============ GDPR export + erasure ============
class TestGDPR:
    def test_export_and_erasure(self, clinic):
        # Create a patient + appointment
        name = f"TEST_Erase_{_rand()}"
        pt = {"name": name, "email": f"TEST_er_{_rand()}@x.com",
              "phone": "+14155550777", "age": 44, "gender": "F"}
        rp = requests.post(f"{API}/patients", json=pt, headers=_h(clinic["token"]), timeout=20)
        assert rp.status_code == 200
        pid = rp.json()["id"]
        appt = {"patient": name, "patient_id": pid, "doctor": "Dr E",
                "date": "2030-06-01", "time": "10:00", "status": "Scheduled"}
        ra = requests.post(f"{API}/appointments", json=appt, headers=_h(clinic["token"]), timeout=20)
        assert ra.status_code == 200

        # Export
        re_ = requests.get(f"{API}/compliance/export", headers=_h(clinic["token"]), timeout=30)
        assert re_.status_code == 200
        ex = re_.json()
        for c in ["patients", "appointments", "prescriptions", "labtests", "medications", "invoices"]:
            assert c in ex
        assert any(p["id"] == pid for p in ex["patients"])

        # Erase
        rd = requests.delete(f"{API}/compliance/patient/{pid}",
                             headers=_h(clinic["token"]), timeout=30)
        assert rd.status_code == 200

        # Confirm patient + appt gone
        appts = requests.get(f"{API}/appointments", headers=_h(clinic["token"]), timeout=20).json()
        assert all(a.get("patient_id") != pid for a in appts)
        pats = requests.get(f"{API}/patients", headers=_h(clinic["token"]), timeout=20).json()
        assert all(p["id"] != pid for p in pats)

        # Audit trail contains erase
        logs = requests.get(f"{API}/audit-logs", headers=_h(clinic["token"]), timeout=20).json()
        assert any(l.get("action") == "erase" and l.get("resource_id") == pid for l in logs)
