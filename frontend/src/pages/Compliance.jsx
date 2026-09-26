import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { formatApiError } from "@/lib/api";
import { PageHeader } from "@/components/CrudModule";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ShieldCheck, Download, FileText, History } from "lucide-react";
import { toast } from "sonner";

export default function Compliance() {
  const [logs, setLogs] = useState([]);

  useEffect(() => { api.get("/audit-logs").then((r) => setLogs(r.data)).catch(() => {}); }, []);

  const exportData = async () => {
    try {
      const r = await api.get("/compliance/export");
      const blob = new Blob([JSON.stringify(r.data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `clinic-data-export-${Date.now()}.json`; a.click();
      URL.revokeObjectURL(url);
      toast.success("Data export downloaded");
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  return (
    <div data-testid="page-compliance">
      <PageHeader title="Compliance & Security" subtitle="Audit trail, data rights and governance" />

      <div className="mb-6 grid gap-4 md:grid-cols-3">
        <Card className="card-shadow border-border/70 p-5">
          <div className="mb-2 flex items-center gap-2 text-primary"><Download className="h-5 w-5" /><span className="font-medium">Data export (GDPR)</span></div>
          <p className="mb-3 text-sm text-muted-foreground">Download a full JSON export of your clinic's records.</p>
          <Button size="sm" onClick={exportData} data-testid="export-data-btn">Export all data</Button>
        </Card>
        <Card className="card-shadow border-border/70 p-5">
          <div className="mb-2 flex items-center gap-2 text-primary"><ShieldCheck className="h-5 w-5" /><span className="font-medium">Right to erasure</span></div>
          <p className="text-sm text-muted-foreground">Delete a patient and all linked records from the Patients page (removes appointments, prescriptions, labs & invoices).</p>
        </Card>
        <Card className="card-shadow border-border/70 p-5">
          <div className="mb-2 flex items-center gap-2 text-primary"><FileText className="h-5 w-5" /><span className="font-medium">Legal</span></div>
          <p className="text-sm text-muted-foreground">
            Review our <Link to="/terms" className="text-primary underline">Terms</Link> and{" "}
            <Link to="/privacy" className="text-primary underline">Privacy Policy</Link>. Sign BAAs with your sub-processors before handling real PHI.
          </p>
        </Card>
      </div>

      <Card className="card-shadow border-border/70 p-6">
        <div className="mb-4 flex items-center gap-2"><History className="h-5 w-5 text-primary" /><h3 className="font-serif text-xl">Audit Trail</h3></div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/60 text-left text-xs uppercase text-muted-foreground">
              <tr><th className="px-3 py-2">When</th><th className="px-3 py-2">Actor</th><th className="px-3 py-2">Action</th><th className="px-3 py-2">Resource</th><th className="px-3 py-2">IP</th></tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {logs.length === 0 ? (
                <tr><td colSpan={5} className="px-3 py-10 text-center text-muted-foreground">No audit events yet.</td></tr>
              ) : logs.map((l) => (
                <tr key={l.id} data-testid="audit-row">
                  <td className="px-3 py-2 text-muted-foreground">{new Date(l.created_at).toLocaleString()}</td>
                  <td className="px-3 py-2">{l.actor}</td>
                  <td className="px-3 py-2"><span className="mono">{l.action}</span></td>
                  <td className="px-3 py-2">{l.resource}{l.resource_id ? ` · ${String(l.resource_id).slice(0, 8)}` : ""}</td>
                  <td className="px-3 py-2 text-muted-foreground">{l.ip || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
