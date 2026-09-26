"""Iteration 3 backend tests: integrations, patient portal, cron reminders, widget."""
import os
import uuid
import time
from datetime import datetime, timezone, timedelta

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
CRON_SECRET = "cr0n_9f2b7a41d8e34c05b6a1f7e0c2d4a8b6e1f3c5d7a9b0e2f4c6a8d1b3e5f7a90"


def _rand():
    return uuid.uuid4().hex[:8]


def _register_clinic():
    email = f"TEST_{_rand()}@demo.com"
    body = {"email": email, "password": "Passw0rd!", "name": "Test Admin", "clinic_name": f"TEST_Clinic_{_rand()}"}
    r = requests.post(f"{API}/auth/register", json=body, timeout=20)
    assert r.status_code == 200, r.text
    d = r.json()
    return d["token"], email


def _h(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def clinic_a():
    tok, email = _register_clinic()
    return {"token": tok, "email": email}


@pytest.fixture(scope="module")
def clinic_b():
    tok, email = _register_clinic()
    return {"token": tok, "email": email}


@pytest.fixture(scope="module")
def patient_a(clinic_a):
    p = {
        "name": f"TEST_Patient_{_rand()}",
        "email": f"TEST_pt_{_rand()}@demo.com",
        "phone": f"+1415555{_rand()[:4]}",
        "age": 30, "gender": "F",
    }
    r = requests.post(f"{API}/patients", json=p, headers=_h(clinic_a["token"]), timeout=20)
    assert r.status_code == 200, r.text
    return r.json()


# ============ Integrations ============
class TestIntegrations:
    def test_get_schemas(self, clinic_a):
        r = requests.get(f"{API}/integrations", headers=_h(clinic_a["token"]), timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert "resend" in d["email_providers"]
        assert "twilio" in d["whatsapp_providers"]
        assert d["email"]["configured"] in (False, True)

    def test_put_and_mask(self, clinic_a):
        body = {"email": {"provider": "resend", "api_key": "sk_real_secret_123", "from_email": "a@b.com"}}
        r = requests.put(f"{API}/integrations", json=body, headers=_h(clinic_a["token"]), timeout=20)
        assert r.status_code == 200, r.text
        # Re-fetch
        r2 = requests.get(f"{API}/integrations", headers=_h(clinic_a["token"]), timeout=20).json()
        assert r2["email"]["provider"] == "resend"
        assert r2["email"]["configured"] is True
        assert r2["email"]["config"]["api_key"] == "********"
        assert r2["email"]["config"]["from_email"] == "a@b.com"

    def test_masked_preserves_secret(self, clinic_a):
        # Save again passing masked back — should NOT overwrite the real key
        body = {"email": {"provider": "resend", "api_key": "********", "from_email": "changed@b.com"}}
        r = requests.put(f"{API}/integrations", json=body, headers=_h(clinic_a["token"]), timeout=20)
        assert r.status_code == 200
        r2 = requests.get(f"{API}/integrations", headers=_h(clinic_a["token"]), timeout=20).json()
        assert r2["email"]["configured"] is True  # still configured -> real key preserved
        assert r2["email"]["config"]["from_email"] == "changed@b.com"

    def test_clear_provider(self, clinic_a):
        body = {"email": {"provider": "", "api_key": "", "from_email": ""}}
        r = requests.put(f"{API}/integrations", json=body, headers=_h(clinic_a["token"]), timeout=20)
        assert r.status_code == 200
        r2 = requests.get(f"{API}/integrations", headers=_h(clinic_a["token"]), timeout=20).json()
        assert r2["email"]["configured"] is False

    def test_tenant_isolation(self, clinic_a, clinic_b):
        # Configure email on A
        body = {"email": {"provider": "sendgrid", "api_key": "A_SECRET_KEY", "from_email": "a@a.com"}}
        requests.put(f"{API}/integrations", json=body, headers=_h(clinic_a["token"]), timeout=20)
        # B should not see it
        rb = requests.get(f"{API}/integrations", headers=_h(clinic_b["token"]), timeout=20).json()
        assert rb["email"]["configured"] is False
        assert rb["email"]["provider"] in (None, "")


# ============ Patient Portal ============
class TestPortal:
    def test_login_success(self, patient_a):
        body = {"email": patient_a["email"].upper(), "phone": patient_a["phone"]}
        r = requests.post(f"{API}/portal/login", json=body, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "token" in d and d["patient"]["id"] == patient_a["id"]

    def test_login_bad(self):
        r = requests.post(f"{API}/portal/login",
                          json={"email": "nobody@x.com", "phone": "+10000000000"}, timeout=20)
        assert r.status_code == 401

    def test_portal_me_and_scoping(self, patient_a, clinic_a, clinic_b):
        # login
        ptok = requests.post(f"{API}/portal/login",
                             json={"email": patient_a["email"], "phone": patient_a["phone"]},
                             timeout=20).json()["token"]
        # create an appointment for this patient in tenant A
        tomorrow = (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat()
        appt = {"patient": patient_a["name"], "doctor": "Dr. X",
                "date": tomorrow, "time": "10:00", "status": "Scheduled"}
        ra = requests.post(f"{API}/appointments", json=appt, headers=_h(clinic_a["token"]), timeout=20)
        assert ra.status_code == 200, ra.text

        # portal/me
        me = requests.get(f"{API}/portal/me", headers=_h(ptok), timeout=20)
        assert me.status_code == 200
        assert me.json()["patient"]["id"] == patient_a["id"]

        # appts
        appts = requests.get(f"{API}/portal/appointments", headers=_h(ptok), timeout=20)
        assert appts.status_code == 200
        arr = appts.json()
        assert len(arr) >= 1
        assert all(a["patient"] == patient_a["name"] for a in arr)

        # patient token must NOT work on staff endpoints
        rs = requests.get(f"{API}/patients", headers=_h(ptok), timeout=20)
        assert rs.status_code == 401

        # staff (clinic A) token must NOT work on portal endpoints
        rp = requests.get(f"{API}/portal/me", headers=_h(clinic_a["token"]), timeout=20)
        assert rp.status_code == 401

        # store for cron test
        TestPortal._appt_date = tomorrow
        TestPortal._appt_id = ra.json()["id"]
        TestPortal._ptok = ptok

    def test_portal_prescriptions_invoices_empty_ok(self, patient_a):
        ptok = requests.post(f"{API}/portal/login",
                             json={"email": patient_a["email"], "phone": patient_a["phone"]},
                             timeout=20).json()["token"]
        for path in ("prescriptions", "invoices"):
            r = requests.get(f"{API}/portal/{path}", headers=_h(ptok), timeout=20)
            assert r.status_code == 200
            assert isinstance(r.json(), list)


# ============ Cron ============
class TestCron:
    def test_no_auth_401(self):
        r = requests.post(f"{API}/cron/appointment-reminders", timeout=20)
        assert r.status_code == 401

    def test_bad_secret_401(self):
        r = requests.post(f"{API}/cron/appointment-reminders",
                          headers={"Authorization": "Bearer wrong"}, timeout=20)
        assert r.status_code == 401

    def test_run_cron(self, clinic_a, patient_a):
        # ensure at least one appt tomorrow (created in TestPortal, but also create here to be independent)
        tomorrow = (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat()
        appt = {"patient": patient_a["name"], "doctor": "Dr. Cron",
                "date": tomorrow, "time": "11:00", "status": "Scheduled"}
        ra = requests.post(f"{API}/appointments", json=appt, headers=_h(clinic_a["token"]), timeout=20)
        assert ra.status_code == 200
        aid = ra.json()["id"]

        r = requests.post(f"{API}/cron/appointment-reminders",
                          headers={"Authorization": f"Bearer {CRON_SECRET}"}, timeout=20)
        assert r.status_code == 200
        assert r.json()["status"] == "accepted"

        # Wait for background task
        time.sleep(3)

        # Verify reminder_sent flipped
        appts = requests.get(f"{API}/appointments", headers=_h(clinic_a["token"]), timeout=20).json()
        target = next((a for a in appts if a["id"] == aid), None)
        assert target is not None
        assert target.get("reminder_sent") is True

        # Verify appointment_reminder notification logged (skipped_not_configured is fine)
        # Clear email config on A first to guarantee skipped
        # (Actually earlier tests set sendgrid, but api_key placeholder still counts as configured;
        # accept either 'sent' or 'skipped_not_configured' or 'failed:...')
        notifs = requests.get(f"{API}/notifications", headers=_h(clinic_a["token"]), timeout=20).json()
        rems = [n for n in notifs if n.get("event") == "appointment_reminder"]
        assert len(rems) >= 1


# ============ Widget ============
class TestWidget:
    def test_widget_js(self):
        r = requests.get(f"{BASE_URL}/api/public/widget.js", timeout=20)
        assert r.status_code == 200
        ct = r.headers.get("content-type", "")
        assert "javascript" in ct
        assert "medicore-booking" in r.text or "mc-submit" in r.text


# ============ Regression sanity ============
class TestRegression:
    def test_admin_login(self):
        r = requests.post(f"{API}/auth/login",
                          json={"email": "mac11rs.com@gmail.com", "password": "Admin@12345"}, timeout=20)
        assert r.status_code == 200
        assert "token" in r.json()

    def test_dashboard_stats(self, clinic_a):
        r = requests.get(f"{API}/dashboard/stats", headers=_h(clinic_a["token"]), timeout=20)
        assert r.status_code == 200
