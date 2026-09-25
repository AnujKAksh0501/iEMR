import { useEffect, useState } from "react";
import api, { formatApiError } from "@/lib/api";
import { PageHeader } from "@/components/CrudModule";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Plus, Trash2, CreditCard } from "lucide-react";
import { toast } from "sonner";

export default function Billing() {
  const [invoices, setInvoices] = useState([]);
  const [patients, setPatients] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({});
  const [paying, setPaying] = useState(null);

  const load = () => api.get("/invoices").then((r) => setInvoices(r.data)).catch(() => {});
  useEffect(() => {
    load();
    api.get("/patients").then((r) => setPatients(r.data)).catch(() => {});
  }, []);

  const save = async () => {
    try {
      await api.post("/invoices", { ...form, amount: Number(form.amount) });
      toast.success("Invoice created");
      setOpen(false); setForm({}); load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const remove = async (id) => {
    if (!window.confirm("Delete this invoice?")) return;
    try { await api.delete(`/invoices/${id}`); load(); } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const pay = async (inv) => {
    setPaying(inv.id);
    try {
      const r = await api.post("/payments/checkout", { invoice_id: inv.id, origin_url: window.location.origin });
      window.location.href = r.data.checkout_url;
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); setPaying(null); }
  };

  return (
    <div data-testid="page-billing">
      <PageHeader
        title="Billing"
        subtitle="Patient invoices and secure payments"
        action={
          <Button onClick={() => setOpen(true)} data-testid="add-invoice-btn" className="rounded-full">
            <Plus className="mr-1 h-4 w-4" /> New Invoice
          </Button>
        }
      />
      <Card className="card-shadow overflow-hidden border-border/70">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/60 text-left text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="px-4 py-3 font-medium">Patient</th>
                <th className="px-4 py-3 font-medium">Description</th>
                <th className="px-4 py-3 font-medium">Amount</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 text-right font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {invoices.length === 0 ? (
                <tr><td colSpan={5} className="px-4 py-12 text-center text-muted-foreground">No invoices yet.</td></tr>
              ) : invoices.map((inv) => (
                <tr key={inv.id} className="hover:bg-muted/30" data-testid="row-invoice">
                  <td className="px-4 py-3">{inv.patient || "—"}</td>
                  <td className="px-4 py-3">{inv.description || "—"}</td>
                  <td className="px-4 py-3 mono">${Number(inv.amount).toFixed(2)}</td>
                  <td className="px-4 py-3">
                    <Badge className={`border-0 ${inv.payment_status === "paid" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>
                      {inv.payment_status === "paid" ? "Paid" : "Pending"}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-2">
                      {inv.payment_status !== "paid" && (
                        <Button size="sm" onClick={() => pay(inv)} disabled={paying === inv.id} data-testid="pay-invoice-btn">
                          <CreditCard className="mr-1 h-4 w-4" /> {paying === inv.id ? "…" : "Pay"}
                        </Button>
                      )}
                      <Button size="icon" variant="ghost" onClick={() => remove(inv.id)}>
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader><DialogTitle className="font-serif text-2xl">New Invoice</DialogTitle></DialogHeader>
          <div className="grid gap-4 py-2">
            <div className="grid gap-1.5"><Label>Patient</Label>
              <Select value={form.patient || ""} onValueChange={(v) => setForm({ ...form, patient: v })}>
                <SelectTrigger data-testid="invoice-patient"><SelectValue placeholder="Select patient" /></SelectTrigger>
                <SelectContent>{patients.map((p) => <SelectItem key={p.id} value={p.name}>{p.name}</SelectItem>)}</SelectContent>
              </Select></div>
            <div className="grid gap-1.5"><Label>Description</Label>
              <Input data-testid="invoice-description" value={form.description || ""} onChange={(e) => setForm({ ...form, description: e.target.value })} /></div>
            <div className="grid gap-1.5"><Label>Amount ($)</Label>
              <Input data-testid="invoice-amount" type="number" value={form.amount || ""} onChange={(e) => setForm({ ...form, amount: e.target.value })} /></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button onClick={save} data-testid="save-invoice-btn">Create</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
