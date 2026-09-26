import { useEffect, useState } from "react";
import api, { formatApiError } from "@/lib/api";
import { PageHeader } from "@/components/CrudModule";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import IntegrationsPanel from "@/components/IntegrationsPanel";
import { Mail, MessageCircle, CheckCircle2, AlertCircle, Send } from "lucide-react";
import { toast } from "sonner";

const EVENT_LABELS = {
  appointment_booked: "Appointment booked",
  appointment_reminder: "Appointment reminder",
  lab_results_ready: "Lab results ready",
  invoice_created: "Invoice created",
  payment_received: "Payment received",
};

export default function Automation() {
  const [status, setStatus] = useState(null);
  const [logs, setLogs] = useState([]);
  const [test, setTest] = useState({ email: "", phone: "" });

  const loadStatus = () => api.get("/notifications/status").then((r) => setStatus(r.data)).catch(() => {});
  const loadLogs = () => api.get("/notifications").then((r) => setLogs(r.data)).catch(() => {});
  useEffect(() => { loadStatus(); loadLogs(); }, []);

  const toggleEvent = async (key, val) => {
    const events = { ...status.events, [key]: val };
    setStatus({ ...status, events });
    await api.put("/notifications/settings", { events });
  };
  const toggleChannel = async (key, val) => {
    const channels = { ...status.channels, [key]: val };
    setStatus({ ...status, channels });
    await api.put("/notifications/settings", { channels });
  };
  const sendTest = async () => {
    try {
      const r = await api.post("/notifications/test", test);
      toast.success(r.data.email_configured || r.data.whatsapp_configured
        ? "Test dispatched — check the log below" : "Logged (providers not configured yet)");
      loadLogs();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const StatusPill = ({ ok }) => (
    <Badge className={`border-0 ${ok ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>
      {ok ? "Connected" : "Not configured"}
    </Badge>
  );

  return (
    <div data-testid="page-automation">
      <PageHeader title="Automation" subtitle="WhatsApp & Email notifications for key clinic events" />

      <IntegrationsPanel />

      <div className="mb-6 grid gap-4 sm:grid-cols-2">
        <Card className="card-shadow border-border/70 p-5">
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2"><Mail className="h-5 w-5 text-primary" /><span className="font-medium">Email (SMTP)</span></div>
            <StatusPill ok={status?.email_configured} />
          </div>
          <p className="text-sm text-muted-foreground">
            {status?.email_configured ? "Emails will be delivered via your configured SMTP provider."
              : "Add SMTP_HOST, SMTP_USER, SMTP_PASSWORD in Secrets to enable email."}
          </p>
        </Card>
        <Card className="card-shadow border-border/70 p-5">
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2"><MessageCircle className="h-5 w-5 text-primary" /><span className="font-medium">WhatsApp (Twilio)</span></div>
            <StatusPill ok={status?.whatsapp_configured} />
          </div>
          <p className="text-sm text-muted-foreground">
            {status?.whatsapp_configured ? "WhatsApp messages will be sent via Twilio."
              : "Add TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM in Secrets to enable WhatsApp."}
          </p>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="card-shadow border-border/70 p-6 lg:col-span-1">
          <h3 className="mb-4 font-serif text-xl">Channels & Events</h3>
          <div className="mb-4 space-y-3">
            {["email", "whatsapp"].map((c) => (
              <div key={c} className="flex items-center justify-between">
                <Label className="capitalize">{c}</Label>
                <Switch data-testid={`channel-${c}`} checked={!!status?.channels?.[c]}
                  onCheckedChange={(v) => toggleChannel(c, v)} />
              </div>
            ))}
          </div>
          <div className="border-t pt-4 space-y-3">
            {Object.keys(EVENT_LABELS).map((k) => (
              <div key={k} className="flex items-center justify-between">
                <Label className="text-sm">{EVENT_LABELS[k]}</Label>
                <Switch data-testid={`event-${k}`} checked={!!status?.events?.[k]}
                  onCheckedChange={(v) => toggleEvent(k, v)} />
              </div>
            ))}
          </div>
          <div className="mt-6 border-t pt-4">
            <Label className="text-sm">Send a test</Label>
            <Input className="mt-2" placeholder="test email" value={test.email}
              data-testid="test-email" onChange={(e) => setTest({ ...test, email: e.target.value })} />
            <Input className="mt-2" placeholder="whatsapp e.g. +14155551234" value={test.phone}
              data-testid="test-phone" onChange={(e) => setTest({ ...test, phone: e.target.value })} />
            <Button className="mt-3 w-full" onClick={sendTest} data-testid="send-test-btn">
              <Send className="mr-1 h-4 w-4" /> Send test
            </Button>
          </div>
        </Card>

        <Card className="card-shadow border-border/70 p-6 lg:col-span-2">
          <h3 className="mb-4 font-serif text-xl">Notification Log</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-muted/60 text-left text-xs uppercase text-muted-foreground">
                <tr><th className="px-3 py-2">Channel</th><th className="px-3 py-2">Event</th><th className="px-3 py-2">To</th><th className="px-3 py-2">Status</th></tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {logs.length === 0 ? (
                  <tr><td colSpan={4} className="px-3 py-10 text-center text-muted-foreground">No notifications sent yet.</td></tr>
                ) : logs.map((l) => (
                  <tr key={l.id} data-testid="notif-row">
                    <td className="px-3 py-2 capitalize">{l.channel}</td>
                    <td className="px-3 py-2">{EVENT_LABELS[l.event] || l.event}</td>
                    <td className="px-3 py-2">{l.to}</td>
                    <td className="px-3 py-2">
                      {l.status === "sent"
                        ? <span className="inline-flex items-center gap-1 text-emerald-700"><CheckCircle2 className="h-4 w-4" />sent</span>
                        : <span className="inline-flex items-center gap-1 text-amber-700"><AlertCircle className="h-4 w-4" />{l.status?.startsWith("skipped") ? "not configured" : l.status}</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </div>
  );
}
