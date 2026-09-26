# MediCore — Enterprise Multi-Tenant EMR SaaS

## Original Problem Statement
Build an enterprise-grade EMR SaaS with a multi-tenant system usable by any clinic/hospital/doctor for all their work: medication, pharmacy, lab tests, appointments, etc. Later extended with WhatsApp+Email automation, a public API for websites to connect to the dashboard, and in-app documentation.

## Architecture
- Frontend: Vite + React 19 + Tailwind v4 + shadcn/ui. Design: Nordic Pine (#0F3E2E) + Alabaster (#FBF9F5), Instrument Serif / Plus Jakarta Sans / JetBrains Mono.
- Backend: FastAPI + MongoDB (motor). All routes under /api. UUID string IDs (no ObjectId leaks).
- Auth: JWT Bearer tokens in localStorage + Emergent-managed Google OAuth. Roles: super_admin, clinic_admin, doctor, nurse, pharmacist, lab_tech, receptionist.
- Multi-tenancy: every record scoped by tenant_id from the authenticated user; each clinic is an isolated workspace.

## User Personas
- Clinic Admin (owner): manages staff, API keys, billing, all clinical data.
- Clinicians (doctor/nurse), Pharmacist, Lab Tech, Receptionist: scoped clinical work.
- External website/app: uses public API with X-API-Key to book appointments / register patients.

## Core Requirements (static)
Patients, Appointments, Prescriptions, Pharmacy inventory, Lab tests, Staff/roles, Billing (Stripe), AI clinical assistant, Notification automation, Public API, Documentation.

## Implemented
- 2026-06: MVP — auth (JWT + Google), multi-tenant, Patients/Appointments/Prescriptions/Pharmacy/LabTests CRUD, Staff management, Dashboard stats+chart, Stripe invoices/checkout, AI assistant (gpt-5.4 via Emergent LLM key). Tested 100%.
- 2026-06: Advanced iteration — Email (SMTP) + WhatsApp (Twilio) notification automation with per-event/per-channel toggles and notification log (providers safe "not configured" until keys added); events: appointment_booked, appointment_reminder, lab_results_ready, invoice_created, payment_received. Public API (X-API-Key) with availability/patients/appointments read-write, tenant-scoped. Developer API-keys page + in-app Documentation page. Tested 20/20 backend + 100% frontend.

## Integrations & Keys
- EMERGENT_LLM_KEY (set), STRIPE_API_KEY=sk_test_emergent (set, Flow B).
- Deferred (empty in .env, user to add): SMTP_HOST/PORT/USER/PASSWORD/FROM, TWILIO_ACCOUNT_SID/AUTH_TOKEN/WHATSAPP_FROM.

## Backlog / Remaining
- P1: Pydantic validation on public endpoints; soft-revoke API keys (audit trail); scheduled reminders (cron) instead of manual /remind.
- P2: Per-event channel targeting; patient portal; role-scoped route guards on frontend; analytics/reports; document/file uploads (object storage); split server.py into modules.

## Test Credentials
Super Admin: mac11rs.com@gmail.com / Admin@12345
