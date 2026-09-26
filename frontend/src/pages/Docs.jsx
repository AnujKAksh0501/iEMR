import { useState } from "react";
import { API } from "@/lib/api";
import { PageHeader } from "@/components/CrudModule";
import { Card } from "@/components/ui/card";
import {
  Users, CalendarDays, Pill, Package, FlaskConical, Receipt, Sparkles, Bell, Code2, UserCog, ShieldCheck,
} from "lucide-react";

const SECTIONS = [
  { id: "getting-started", title: "Getting Started" },
  { id: "modules", title: "Core Modules" },
  { id: "roles", title: "Roles & Access" },
  { id: "automation", title: "Automation" },
  { id: "api", title: "Website / API Integration" },
];

const MODULES = [
  { icon: Users, title: "Patients", body: "Create and maintain complete patient records: demographics, contact, blood group, address and clinical notes. Patient names power selections across appointments, prescriptions, labs and billing." },
  { icon: CalendarDays, title: "Appointments", body: "Book visits against a patient and doctor with date, time, reason and status (Scheduled, Completed, Cancelled, No-show). Booking triggers an automatic confirmation." },
  { icon: Pill, title: "Prescriptions", body: "Record medication orders with dosage, frequency and duration, linked to a patient and prescriber." },
  { icon: Package, title: "Pharmacy", body: "Track inventory with stock, unit, price, supplier and expiry. Items at or below their reorder level are flagged as 'Reorder'." },
  { icon: FlaskConical, title: "Lab Tests", body: "Order diagnostics, capture sample type and record results. Marking a test 'Completed' notifies the patient their results are ready." },
  { icon: UserCog, title: "Staff", body: "Clinic admins invite team members and assign roles that control what each user can manage." },
  { icon: Receipt, title: "Billing", body: "Generate patient invoices and collect payment through secure Stripe checkout. Paid invoices update automatically." },
  { icon: Sparkles, title: "AI Assistant", body: "MedAssist helps with note summaries, drug interactions, differentials and documentation. Always for clinician review." },
];

export default function Docs() {
  const [active, setActive] = useState("getting-started");
  const go = (id) => { setActive(id); document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" }); };

  return (
    <div data-testid="page-docs">
      <PageHeader title="Documentation" subtitle="How to use MediCore and connect your own website" />
      <div className="grid gap-8 lg:grid-cols-[220px_1fr]">
        <nav className="hidden lg:block">
          <div className="sticky top-24 space-y-1">
            {SECTIONS.map((s) => (
              <button key={s.id} onClick={() => go(s.id)} data-testid={`doc-nav-${s.id}`}
                className={`block w-full rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                  active === s.id ? "bg-primary/10 font-medium text-primary" : "text-muted-foreground hover:bg-muted"}`}>
                {s.title}
              </button>
            ))}
          </div>
        </nav>

        <div className="max-w-3xl space-y-10">
          <section id="getting-started">
            <h2 className="font-serif text-3xl">Getting Started</h2>
            <p className="mt-3 text-muted-foreground">
              MediCore is a multi-tenant EMR. Each clinic is an isolated workspace — your data is never visible to other clinics.
              When you register, a clinic workspace is created and you become its administrator.
            </p>
            <ol className="mt-4 list-decimal space-y-2 pl-5 text-sm">
              <li>Add your team on the <b>Staff</b> page and assign roles.</li>
              <li>Create patient records under <b>Patients</b>.</li>
              <li>Book appointments, write prescriptions, order lab tests and manage pharmacy stock.</li>
              <li>Raise invoices and collect payment under <b>Billing</b>.</li>
              <li>Turn on notifications under <b>Automation</b> and connect your website via <b>Developer API</b>.</li>
            </ol>
          </section>

          <section id="modules">
            <h2 className="font-serif text-3xl">Core Modules</h2>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              {MODULES.map((m) => (
                <Card key={m.title} className="card-shadow border-border/70 p-5">
                  <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary"><m.icon className="h-5 w-5" /></div>
                  <h3 className="font-serif text-xl">{m.title}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">{m.body}</p>
                </Card>
              ))}
            </div>
          </section>

          <section id="roles">
            <h2 className="font-serif text-3xl">Roles & Access</h2>
            <Card className="card-shadow mt-4 border-border/70 p-5">
              <div className="mb-3 flex items-center gap-2 text-primary"><ShieldCheck className="h-5 w-5" /><span className="font-medium">Role-based access</span></div>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><b>Super Admin</b> — platform owner, full access across the workspace.</li>
                <li><b>Clinic Admin</b> — manages staff, API keys, billing and all clinical data.</li>
                <li><b>Doctor / Nurse</b> — patients, appointments, prescriptions, lab tests.</li>
                <li><b>Pharmacist</b> — pharmacy inventory and prescriptions.</li>
                <li><b>Lab Tech</b> — lab tests and results.</li>
                <li><b>Receptionist</b> — appointments and patient intake.</li>
              </ul>
            </Card>
          </section>

          <section id="automation">
            <h2 className="font-serif text-3xl">Automation</h2>
            <div className="mt-3 flex items-start gap-3 text-muted-foreground">
              <Bell className="mt-1 h-5 w-5 shrink-0 text-primary" />
              <p className="text-sm">
                MediCore can automatically message patients over <b>Email</b> and <b>WhatsApp</b> when an appointment is booked,
                a reminder is due, lab results are ready, or an invoice/payment occurs. Toggle channels and events on the
                <b> Automation</b> page. Providers stay in a safe "not configured" state until you add credentials in Secrets:
              </p>
            </div>
            <ul className="mt-3 space-y-1 pl-5 text-sm">
              <li><b>Email:</b> <code className="mono">SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM</code></li>
              <li><b>WhatsApp (Twilio):</b> <code className="mono">TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM</code></li>
            </ul>
          </section>

          <section id="api">
            <h2 className="font-serif text-3xl">Website / API Integration</h2>
            <div className="mt-3 flex items-start gap-3 text-muted-foreground">
              <Code2 className="mt-1 h-5 w-5 shrink-0 text-primary" />
              <p className="text-sm">
                Generate an API key on the <b>Developer API</b> page and let your public website book appointments, register
                patients and check availability directly against your workspace. Every request needs the header
                <code className="mono"> X-API-Key</code>.
              </p>
            </div>
            <pre className="mono mt-4 overflow-x-auto rounded-lg bg-primary p-4 text-xs text-primary-foreground">{`# Check open slots
curl "${API}/public/availability?date=2026-07-01" -H "X-API-Key: YOUR_KEY"

# Book an appointment
curl -X POST "${API}/public/appointments" \\
  -H "X-API-Key: YOUR_KEY" -H "Content-Type: application/json" \\
  -d '{"patient":"Jane Doe","phone":"+14155550100","email":"jane@mail.com","date":"2026-07-01","time":"10:00"}'`}</pre>
          </section>
        </div>
      </div>
    </div>
  );
}
