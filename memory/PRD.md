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
- 2026-06: MVP — auth (JWT + Google), multi-tenant, Patients/Appointments/Prescriptions/Pharmacy/LabTests CRUD, Staff, Dashboard, Stripe patient invoices, AI assistant. Tested 100%.
- 2026-06: Automation (Email/WhatsApp pluggable), Public API + API keys, Docs. Tested.
- 2026-06: Patient Portal, scheduled reminders cron, booking widget, per-tenant integrations. Tested.
- 2026-06: Market-readiness hardening — password policy, login brute-force lockout, password reset, payload sanitization, CORS-from-env; audit logging (+ /audit-logs UI); PHI fix (patient_id linkage); flexible AI provider selection (emergent/openai/anthropic/gemini) with managed-key transparency; SaaS subscription plans (free/starter/pro) with staff/patient limits + Stripe upgrade; GDPR export + patient erasure + consent; Terms/Privacy pages; /api/health. Tested 18/18 new + 100% frontend. Fixed: reset token no longer persisted to notification log; atomic login-fail counter.

## Deferred (legal/infra — cannot be code-completed in-app)
- HIPAA/GDPR certification, signed BAAs with sub-processors, encryption-at-rest (MongoDB Atlas prod), live Stripe (claim account at deploy), formal pen-test, durable job queue for reminders, Sentry/observability DSN, full server.py modular split, currency/plan catalog config, restricting clinic_admin from minting super_admin.

## Backlog / Remaining
- P1: split server.py into modules; make reminders durable; restrict role escalation; add lockout audit events.
- P2: per-event channel targeting; analytics/reports; object-storage file uploads; i18n; accessibility pass.

## Test Credentials
Super Admin: mac11rs.com@gmail.com / Admin@12345
