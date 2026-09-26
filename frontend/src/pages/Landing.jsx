import { useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  Activity, Users, CalendarDays, Pill, FlaskConical, Receipt, Sparkles, ShieldCheck, ArrowRight, Building2,
} from "lucide-react";

const FEATURES = [
  { icon: Users, title: "Patient Records", desc: "Complete EMR with demographics, history and conditions." },
  { icon: CalendarDays, title: "Appointments", desc: "Scheduling across doctors and departments." },
  { icon: Pill, title: "Prescriptions", desc: "Digital medication orders with dosage tracking." },
  { icon: FlaskConical, title: "Lab & Diagnostics", desc: "Order tests and record results in one place." },
  { icon: Building2, title: "Pharmacy", desc: "Inventory, pricing and automatic reorder alerts." },
  { icon: Receipt, title: "Billing & Payments", desc: "Invoices with secure Stripe checkout." },
  { icon: Sparkles, title: "AI Clinical Assistant", desc: "Note summaries and decision support, on demand." },
  { icon: ShieldCheck, title: "Multi-tenant & Secure", desc: "Isolated data per clinic with role-based access." },
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-background">
      <header className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Activity className="h-5 w-5" />
          </div>
          <span className="font-serif text-2xl text-primary">MediCore</span>
        </div>
        <div className="flex items-center gap-2">
          <Link to="/portal/login"><Button variant="ghost" data-testid="nav-portal-btn">Patient Portal</Button></Link>
          <Link to="/login"><Button variant="ghost" data-testid="nav-login-btn">Sign in</Button></Link>
          <Link to="/register"><Button className="rounded-full" data-testid="nav-register-btn">Get started</Button></Link>
        </div>
      </header>

      <section className="mx-auto grid max-w-7xl items-center gap-12 px-6 py-16 lg:grid-cols-2 lg:py-24">
        <div>
          <span className="inline-flex items-center gap-2 rounded-full bg-accent/15 px-3 py-1 text-xs font-medium text-accent-foreground">
            Enterprise-grade EMR SaaS
          </span>
          <h1 className="mt-5 font-serif text-5xl leading-[1.05] text-foreground sm:text-6xl">
            Run your entire clinic from a single, calm workspace.
          </h1>
          <p className="mt-5 max-w-lg text-lg text-muted-foreground">
            MediCore unifies patients, appointments, pharmacy, labs, billing and AI clinical support — built for hospitals, clinics and independent doctors.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/register">
              <Button size="lg" className="rounded-full" data-testid="hero-cta-btn">
                Start free <ArrowRight className="ml-1 h-4 w-4" />
              </Button>
            </Link>
            <Link to="/login"><Button size="lg" variant="outline" className="rounded-full">Sign in</Button></Link>
          </div>
        </div>
        <div className="relative">
          <img
            src="https://images.unsplash.com/photo-1631217868264-e5b90bb7e133?w=1000&q=80"
            alt="Clinical team"
            className="card-shadow w-full rounded-2xl object-cover"
          />
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 pb-24">
        <h2 className="mb-2 font-serif text-3xl sm:text-4xl">Everything a practice needs</h2>
        <p className="mb-10 text-muted-foreground">One platform, every workflow.</p>
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((f) => (
            <div key={f.title} className="card-shadow rounded-xl border border-border/70 bg-card p-6">
              <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <f.icon className="h-5 w-5" />
              </div>
              <h3 className="font-serif text-xl">{f.title}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="border-t bg-primary py-10 text-primary-foreground">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-6 sm:flex-row">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            <span className="font-serif text-xl">MediCore</span>
          </div>
          <p className="text-sm text-primary-foreground/60">© 2026 MediCore. Enterprise EMR SaaS.</p>
          <div className="flex gap-4 text-sm text-primary-foreground/70">
            <Link to="/terms" className="hover:text-primary-foreground">Terms</Link>
            <Link to="/privacy" className="hover:text-primary-foreground">Privacy</Link>
            <Link to="/portal/login" className="hover:text-primary-foreground">Patient Portal</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
