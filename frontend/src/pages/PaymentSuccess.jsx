import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { CheckCircle2, Loader2, XCircle } from "lucide-react";

export default function PaymentSuccess() {
  const [status, setStatus] = useState("checking");
  const navigate = useNavigate();

  useEffect(() => {
    const sid = new URLSearchParams(window.location.search).get("session_id");
    if (!sid) { setStatus("error"); return; }
    let tries = 0;
    const poll = async () => {
      tries += 1;
      try {
        const r = await api.get(`/payments/status/${sid}`);
        if (r.data.payment_status === "paid") { setStatus("paid"); return; }
        if (["expired", "failed"].includes(r.data.status)) { setStatus("error"); return; }
      } catch { /* keep polling */ }
      if (tries < 8) setTimeout(poll, 2000); else setStatus("timeout");
    };
    poll();
  }, []);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-6" data-testid="payment-result">
      <div className="card-shadow w-full max-w-md rounded-2xl border border-border/70 bg-card p-10 text-center">
        {status === "checking" && (<><Loader2 className="mx-auto mb-4 h-12 w-12 animate-spin text-primary" /><h1 className="font-serif text-2xl">Confirming payment…</h1></>)}
        {status === "paid" && (<><CheckCircle2 className="mx-auto mb-4 h-14 w-14 text-emerald-600" /><h1 className="font-serif text-3xl">Payment successful</h1><p className="mt-2 text-muted-foreground">The invoice has been marked as paid.</p></>)}
        {(status === "error" || status === "timeout") && (<><XCircle className="mx-auto mb-4 h-14 w-14 text-destructive" /><h1 className="font-serif text-2xl">{status === "timeout" ? "Still processing" : "Payment not completed"}</h1><p className="mt-2 text-muted-foreground">Check the billing page for the latest status.</p></>)}
        <Button className="mt-6 rounded-full" onClick={() => navigate("/app/billing")} data-testid="back-to-billing-btn">Back to Billing</Button>
      </div>
    </div>
  );
}
