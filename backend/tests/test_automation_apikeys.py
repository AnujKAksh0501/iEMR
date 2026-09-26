"""Backend tests for iteration 2: notifications automation, API keys, public API, regression."""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://healthvault-multi.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
PUBLIC = f"{BASE_URL}/api/public"

SUPER_EMAIL = "mac11rs.com@gmail.com"
SUPER_PASS = "Admin@12345"


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def super_token():
    r = requests.post(f"{API}/auth/login", json={"email": SUPER_EMAIL, "password": SUPER_PASS}, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def super_headers(super_token):
    return {"Authorization": f"Bearer {super_token}"}


@pytest.fixture(scope="module")
def tenant_a():
    """Register a fresh tenant A."""
    email = f"tenanta_{uuid.uuid4().hex[:8]}@test.com"
    r = requests.post(f"{API}/auth/register", json={
        "email": email, "password": "Passw0rd!", "name": "Owner A", "clinic_name": "Clinic A"
    }, timeout=20)
    assert r.status_code == 200, r.text
    d = r.json()
    return {"token": d["token"], "user": d["user"], "headers": {"Authorization": f"Bearer {d['token']}"}}


@pytest.fixture(scope="module")
def tenant_b():
    email = f"tenantb_{uuid.uuid4().hex[:8]}@test.com"
    r = requests.post(f"{API}/auth/register", json={
        "email": email, "password": "Passw0rd!", "name": "Owner B", "clinic_name": "Clinic B"
    }, timeout=20)
    assert r.status_code == 200, r.text
    d = r.json()
    return {"token": d["token"], "user": d["user"], "headers": {"Authorization": f"Bearer {d['token']}"}}


# ---------- notifications: status + settings ----------
class TestNotificationsStatus:
    def test_status_unconfigured(self, tenant_a):
        r = requests.get(f"{API}/notifications/status", headers=tenant_a["headers"], timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["email_configured"] is False
        assert d["whatsapp_configured"] is False
        assert isinstance(d.get("events"), dict)
        assert isinstance(d.get("channels"), dict)
        # default: appointment_booked should be enabled
        assert d["events"].get("appointment_booked") is True
        assert d["channels"].get("email") is True
        assert d["channels"].get("whatsapp") is True
        assert "available_events" in d

    def test_toggle_settings_persists(self, tenant_a):
        payload = {
            "events": {"appointment_booked": True, "appointment_reminder": False,
                       "lab_results_ready": True, "invoice_created": True, "payment_received": True},
            "channels": {"email": True, "whatsapp": False},
        }
        r = requests.put(f"{API}/notifications/settings", json=payload, headers=tenant_a["headers"], timeout=15)
        assert r.status_code == 200
        # verify via status
        r2 = requests.get(f"{API}/notifications/status", headers=tenant_a["headers"], timeout=15)
        d = r2.json()
        assert d["events"]["appointment_reminder"] is False
        assert d["channels"]["whatsapp"] is False
        # reset back so downstream tests get whatsapp
        requests.put(f"{API}/notifications/settings",
                     json={"events": {k: True for k in d["available_events"]},
                           "channels": {"email": True, "whatsapp": True}},
                     headers=tenant_a["headers"], timeout=15)


# ---------- automation triggers ----------
class TestAutomationTriggers:
    def test_appointment_creation_logs_skipped(self, tenant_a):
        # create patient with email + phone
        p = requests.post(f"{API}/patients", json={
            "name": "TEST_Patient_A", "email": "a@x.com", "phone": "+15551234567"
        }, headers=tenant_a["headers"], timeout=15)
        assert p.status_code == 200
        # create appointment for that patient
        a = requests.post(f"{API}/appointments", json={
            "patient": "TEST_Patient_A", "doctor": "Dr. A", "date": "2026-02-01", "time": "10:00"
        }, headers=tenant_a["headers"], timeout=15)
        assert a.status_code == 200
        time.sleep(0.5)
        n = requests.get(f"{API}/notifications", headers=tenant_a["headers"], timeout=15).json()
        appt_logs = [x for x in n if x.get("event") == "appointment_booked"]
        assert len(appt_logs) >= 1
        # since providers unset, expect skipped_not_configured
        assert any(x["status"] == "skipped_not_configured" for x in appt_logs)
        # both email and whatsapp channels expected
        channels = {x["channel"] for x in appt_logs}
        assert "email" in channels
        assert "whatsapp" in channels

    def test_lab_completed_triggers_notification(self, tenant_a):
        lab = requests.post(f"{API}/labtests", json={
            "patient": "TEST_Patient_A", "test_name": "CBC", "status": "Pending"
        }, headers=tenant_a["headers"], timeout=15).json()
        assert lab.get("id")
        u = requests.put(f"{API}/labtests/{lab['id']}", json={"status": "Completed"},
                         headers=tenant_a["headers"], timeout=15)
        assert u.status_code == 200
        time.sleep(0.5)
        n = requests.get(f"{API}/notifications", headers=tenant_a["headers"], timeout=15).json()
        assert any(x.get("event") == "lab_results_ready" for x in n)

    def test_invoice_creation_triggers(self, tenant_a):
        inv = requests.post(f"{API}/invoices", json={
            "patient": "TEST_Patient_A", "amount": 25, "description": "consult"
        }, headers=tenant_a["headers"], timeout=15)
        assert inv.status_code == 200
        time.sleep(0.5)
        n = requests.get(f"{API}/notifications", headers=tenant_a["headers"], timeout=15).json()
        assert any(x.get("event") == "invoice_created" for x in n)

    def test_test_notification_endpoint(self, tenant_a):
        r = requests.post(f"{API}/notifications/test",
                          json={"email": "test@x.com", "phone": "+15550000000"},
                          headers=tenant_a["headers"], timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True
        assert d["email_configured"] is False
        assert d["whatsapp_configured"] is False


@pytest.fixture(scope="module")
def api_key_a(tenant_a):
    r = requests.post(f"{API}/apikeys", json={"name": "TEST_Key"},
                      headers=tenant_a["headers"], timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("api_key", "").startswith("mk_live_")
    return d


# ---------- API keys ----------
class TestApiKeys:
    def test_create_key(self, api_key_a):
        assert api_key_a.get("api_key", "").startswith("mk_live_")
        assert api_key_a.get("prefix")
        assert api_key_a.get("id")

    def test_list_keys_masked(self, tenant_a, api_key_a):
        r = requests.get(f"{API}/apikeys", headers=tenant_a["headers"], timeout=15)
        assert r.status_code == 200
        arr = r.json()
        target = next((x for x in arr if x["id"] == api_key_a["id"]), None)
        assert target is not None
        assert "api_key" not in target
        assert target["prefix"] == api_key_a["prefix"]
        assert target["active"] is True

    def test_revoke_key(self, tenant_a):
        # create a second, revoke it, then verify public call fails
        r = requests.post(f"{API}/apikeys", json={"name": "TEST_Revoke"},
                          headers=tenant_a["headers"], timeout=15)
        d = r.json()
        rev_key = d["api_key"]; rev_id = d["id"]
        drop = requests.delete(f"{API}/apikeys/{rev_id}", headers=tenant_a["headers"], timeout=15)
        assert drop.status_code == 200
        # attempt public call with revoked key
        p = requests.get(f"{PUBLIC}/ping", headers={"X-API-Key": rev_key}, timeout=15)
        assert p.status_code == 401


# ---------- Public API ----------
class TestPublicApi:
    def test_no_key(self):
        r = requests.get(f"{PUBLIC}/ping", timeout=15)
        assert r.status_code == 401

    def test_invalid_key(self):
        r = requests.get(f"{PUBLIC}/ping", headers={"X-API-Key": "bogus_123"}, timeout=15)
        assert r.status_code == 401

    def test_ping_valid(self, tenant_a, api_key_a):
        key = api_key_a["api_key"]
        r = requests.get(f"{PUBLIC}/ping", headers={"X-API-Key": key}, timeout=15)
        assert r.status_code == 200
        assert r.json()["ok"] is True
        assert r.json().get("clinic") == "Clinic A"

    def test_availability(self, tenant_a, api_key_a):
        key = api_key_a["api_key"]
        r = requests.get(f"{PUBLIC}/availability", params={"date": "2026-02-01"},
                         headers={"X-API-Key": key}, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "available" in d and "booked" in d
        # earlier we booked 10:00 on 2026-02-01
        assert "10:00" in d["booked"]
        assert "10:00" not in d["available"]

    def test_patients_crud(self, tenant_a, api_key_a):
        key = api_key_a["api_key"]
        c = requests.post(f"{PUBLIC}/patients", json={"name": "TEST_PubPatient", "email": "pp@x.com"},
                          headers={"X-API-Key": key}, timeout=15)
        assert c.status_code == 200
        pid = c.json()["id"]
        lst = requests.get(f"{PUBLIC}/patients", headers={"X-API-Key": key}, timeout=15).json()
        assert any(p["id"] == pid for p in lst)
        u = requests.put(f"{PUBLIC}/patients/{pid}", json={"phone": "+15559998888"},
                        headers={"X-API-Key": key}, timeout=15)
        assert u.status_code == 200
        assert u.json().get("phone") == "+15559998888"

    def test_public_booking_triggers_notification(self, tenant_a, api_key_a):
        key = api_key_a["api_key"]
        r = requests.post(f"{PUBLIC}/appointments", json={
            "patient": "TEST_PubBook", "doctor": "Dr. Ext", "date": "2026-02-02",
            "time": "11:00", "email": "e@x.com", "phone": "+15551110000"
        }, headers={"X-API-Key": key}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json().get("id")
        time.sleep(0.5)
        # verify a notification log exists for that tenant
        n = requests.get(f"{API}/notifications", headers=tenant_a["headers"], timeout=15).json()
        assert any(x.get("event") == "appointment_booked" and x.get("to") in ("e@x.com", "+15551110000") for x in n)

    def test_tenant_isolation(self, tenant_a, tenant_b):
        # create a key for tenant B
        rb = requests.post(f"{API}/apikeys", json={"name": "TEST_KeyB"},
                           headers=tenant_b["headers"], timeout=15).json()
        key_b = rb["api_key"]
        # tenant A patients created earlier should NOT be visible via tenant B's key
        patients_b = requests.get(f"{PUBLIC}/patients", headers={"X-API-Key": key_b}, timeout=15).json()
        names = {p.get("name") for p in patients_b}
        assert "TEST_Patient_A" not in names
        assert "TEST_PubPatient" not in names
        # ping should return tenant B's clinic
        pong = requests.get(f"{PUBLIC}/ping", headers={"X-API-Key": key_b}, timeout=15).json()
        assert pong["clinic"] == "Clinic B"


# ---------- Regression: core modules still work ----------
class TestRegression:
    def test_auth_me(self, super_headers):
        r = requests.get(f"{API}/auth/me", headers=super_headers, timeout=15)
        assert r.status_code == 200
        assert r.json()["role"] == "super_admin"

    def test_dashboard_stats(self, tenant_a):
        r = requests.get(f"{API}/dashboard/stats", headers=tenant_a["headers"], timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ["patients", "appointments_total", "prescriptions", "labtests",
                  "medications", "low_stock", "staff", "revenue", "pending_invoices"]:
            assert k in d

    def test_prescription_medication_staff(self, tenant_a):
        # prescription
        r = requests.post(f"{API}/prescriptions", json={"patient": "TEST_Patient_A", "drug": "Amox"},
                          headers=tenant_a["headers"], timeout=15)
        assert r.status_code == 200
        # medication
        r = requests.post(f"{API}/medications", json={"name": "TEST_Med", "stock": 5, "reorder_level": 10},
                          headers=tenant_a["headers"], timeout=15)
        assert r.status_code == 200
        # staff
        r = requests.post(f"{API}/staff", json={
            "email": f"nurse_{uuid.uuid4().hex[:6]}@x.com", "password": "P@ss1234",
            "name": "Nurse T", "role": "nurse"}, headers=tenant_a["headers"], timeout=15)
        assert r.status_code == 200

    def test_assistant_chat(self, tenant_a):
        r = requests.post(f"{API}/assistant/chat", json={"message": "hi"},
                          headers=tenant_a["headers"], timeout=60)
        assert r.status_code == 200
        assert r.json().get("reply")
