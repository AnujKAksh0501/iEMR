import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { portalApi } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { HeartPulse, CalendarDays, Pill, Receipt, LogOut } from "lucide-react";

function Section({ icon: Icon, title, children }) {
  return (
    <Card className="card-shadow border-border/70 p-6">
      <div className="mb-4 flex items-center gap-2">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary"><Icon className="h-5 w-5" /></div>
        <h2 className="font-serif text-xl">{title}</h2>
      </div>
      {children}
    </Card>
  );
}

export default function PortalHome() {
  const navigate = useNavigate();
  const [me, setMe] = useState(null);
  const [appts, setAppts] = useState([]);
  const [rx, setRx] = useState([]);
  const [inv, setInv] = useState([]);

  useEffect(() => {
    if (!localStorage.getItem("emr_portal_token")) { navigate("/portal/login"); return; }
    portalApi.get("/portal/me").then((r) => setMe(r.data)).catch(() => { localStorage.removeItem("emr_portal_token"); navigate("/portal/login"); });
    portalApi.get("/portal/appointments").then((r) => setAppts(r.data)).catch(() => {});
    portalApi.get("/portal/prescriptions").then((r) => setRx(r.data)).catch(() => {});
    portalApi.get("/portal/invoices").then((r) => setInv(r.data)).catch(() => {});
  }, [navigate]);

  const logout = () => { localStorage.removeItem("emr_portal_token"); navigate("/portal/login"); };
  const empty = (t) => <p className="text-sm text-muted-foreground">{t}</p>;

  return (
    <div className="min-h-screen bg-background" data-testid="portal-home">
      <header className="border-b bg-primary text-primary-foreground">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2">
            <HeartPulse className="h-6 w-6" />
            <div className="leading-tight">
              <div className="font-serif text-xl">Patient Portal</div>
              <div className="text-xs text-primary-foreground/70">{me?.clinic}</div>
            </div>
          </div>
          <Button variant="ghost" onClick={logout} data-testid="portal-logout-btn"
            className="text-primary-foreground hover:bg-primary-foreground/10">
            <LogOut className="mr-1 h-4 w-4" /> Sign out
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-5xl space-y-6 px-6 py-8">
        <div>
          <p className="text-sm text-muted-foreground">Welcome,</p>
          <h1 className="font-serif text-4xl">{me?.patient?.name || "…"}</h1>
        </div>

        <Section icon={CalendarDays} title="My Appointments">
          {appts.length === 0 ? empty("No appointments scheduled.") : (
            <div className="space-y-2">
              {appts.map((a) => (
                <div key={a.id} className="flex flex-wrap items-center justify-between rounded-lg border border-border/60 p-3 text-sm" data-testid="portal-appt">
                  <div><span className="font-medium">{a.date} {a.time}</span> · {a.doctor || "Doctor"} · {a.reason || "Visit"}</div>
                  <Badge variant="outline">{a.status || "Scheduled"}</Badge>
                </div>
              ))}
            </div>
          )}
        </Section>

        <Section icon={Pill} title="My Prescriptions">
          {rx.length === 0 ? empty("No prescriptions on record.") : (
            <div className="space-y-2">
              {rx.map((p) => (
                <div key={p.id} className="rounded-lg border border-border/60 p-3 text-sm">
                  <span className="font-medium">{p.medication}</span> — {p.dosage}, {p.frequency}{p.duration ? `, ${p.duration}` : ""}
                </div>
              ))}
            </div>
          )}
        </Section>

        <Section icon={Receipt} title="My Invoices">
          {inv.length === 0 ? empty("No invoices yet.") : (
            <div className="space-y-2">
              {inv.map((i) => (
                <div key={i.id} className="flex items-center justify-between rounded-lg border border-border/60 p-3 text-sm">
                  <div>{i.description || "Invoice"} · <span className="mono">${Number(i.amount).toFixed(2)}</span></div>
                  <Badge className={`border-0 ${i.payment_status === "paid" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>
                    {i.payment_status === "paid" ? "Paid" : "Pending"}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </Section>
      </main>
    </div>
  );
}
