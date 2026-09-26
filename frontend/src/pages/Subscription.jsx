import { useEffect, useState } from "react";
import api, { formatApiError } from "@/lib/api";
import { PageHeader } from "@/components/CrudModule";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Check, Zap } from "lucide-react";
import { toast } from "sonner";

export default function Subscription() {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState("");

  const load = () => api.get("/subscription").then((r) => setData(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const upgrade = async (planId) => {
    setBusy(planId);
    try {
      const r = await api.post("/subscription/checkout", { plan: planId, origin_url: window.location.origin });
      window.location.href = r.data.checkout_url;
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); setBusy(""); }
  };

  if (!data) return null;
  const current = data.subscription.plan;
  const order = ["free", "starter", "pro"];

  return (
    <div data-testid="page-subscription">
      <PageHeader title="Subscription" subtitle="Your clinic's plan, usage and billing" />

      <Card className="card-shadow mb-6 border-border/70 p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="text-sm text-muted-foreground">Current plan</div>
            <div className="font-serif text-3xl capitalize">{data.plan.name}</div>
          </div>
          <div className="flex gap-8 text-sm">
            <div><div className="text-muted-foreground">Staff</div><div className="mono text-lg">{data.usage.staff} / {data.plan.max_staff}</div></div>
            <div><div className="text-muted-foreground">Patients</div><div className="mono text-lg">{data.usage.patients} / {data.plan.max_patients}</div></div>
          </div>
        </div>
      </Card>

      <div className="grid gap-5 md:grid-cols-3">
        {order.map((pid) => {
          const p = data.plans[pid];
          const isCurrent = pid === current;
          return (
            <Card key={pid} data-testid={`plan-${pid}`}
              className={`card-shadow border-border/70 p-6 ${pid === "pro" ? "ring-2 ring-accent" : ""}`}>
              <div className="flex items-center justify-between">
                <h3 className="font-serif text-2xl">{p.name}</h3>
                {pid === "pro" && <Badge className="border-0 bg-accent text-accent-foreground">Popular</Badge>}
              </div>
              <div className="mt-2 mono text-3xl">${p.price}<span className="text-sm text-muted-foreground">/mo</span></div>
              <ul className="mt-4 space-y-2 text-sm">
                <li className="flex items-center gap-2"><Check className="h-4 w-4 text-primary" /> Up to {p.max_staff} staff</li>
                <li className="flex items-center gap-2"><Check className="h-4 w-4 text-primary" /> Up to {p.max_patients.toLocaleString()} patients</li>
                <li className="flex items-center gap-2"><Check className="h-4 w-4 text-primary" /> All clinical modules & AI</li>
              </ul>
              <div className="mt-6">
                {isCurrent ? (
                  <Button disabled className="w-full" variant="outline">Current plan</Button>
                ) : p.price === 0 ? (
                  <Button disabled className="w-full" variant="outline">Downgrade via support</Button>
                ) : (
                  <Button className="w-full rounded-full" data-testid={`upgrade-${pid}-btn`}
                    disabled={busy === pid} onClick={() => upgrade(pid)}>
                    <Zap className="mr-1 h-4 w-4" /> {busy === pid ? "…" : `Upgrade to ${p.name}`}
                  </Button>
                )}
              </div>
            </Card>
          );
        })}
      </div>
      <p className="mt-4 text-xs text-muted-foreground">Payments are processed securely by Stripe. Test mode is active until you connect a live Stripe account at deploy time.</p>
    </div>
  );
}
