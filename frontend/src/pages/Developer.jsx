import { useEffect, useState } from "react";
import api, { formatApiError, API } from "@/lib/api";
import { PageHeader } from "@/components/CrudModule";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Plus, Trash2, Copy, KeyRound, Check } from "lucide-react";
import { toast } from "sonner";

export default function Developer() {
  const [keys, setKeys] = useState([]);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [newKey, setNewKey] = useState(null);
  const [copied, setCopied] = useState("");

  const load = () => api.get("/apikeys").then((r) => setKeys(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const create = async () => {
    try {
      const r = await api.post("/apikeys", { name: name || "Website key" });
      setNewKey(r.data); setName(""); load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };
  const revoke = async (id) => {
    if (!window.confirm("Revoke this API key? Websites using it will lose access.")) return;
    await api.delete(`/apikeys/${id}`); load();
  };
  const copy = (text, id) => { navigator.clipboard.writeText(text); setCopied(id); toast.success("Copied"); setTimeout(() => setCopied(""), 1500); };

  const snippet = `curl -X POST "${API}/public/appointments" \\
  -H "X-API-Key: YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"patient":"Jane Doe","email":"jane@mail.com","phone":"+14155550100","doctor":"Dr. Smith","date":"2026-07-01","time":"10:00","reason":"Consultation"}'`;

  const widgetSnippet = `<div id="medicore-booking"></div>
<script src="${API}/public/widget.js"
  data-api-key="YOUR_API_KEY"
  data-clinic="Your Clinic Name"></script>`;

  return (
    <div data-testid="page-developer">
      <PageHeader
        title="Developer API"
        subtitle="Connect your website or app to your clinic dashboard"
        action={
          <Button className="rounded-full" data-testid="create-key-btn"
            onClick={() => { setNewKey(null); setOpen(true); }}>
            <Plus className="mr-1 h-4 w-4" /> New API Key
          </Button>
        }
      />

      <Card className="card-shadow mb-6 border-border/70 p-6">
        <h3 className="mb-2 font-serif text-xl">Base URL</h3>
        <div className="flex items-center gap-2">
          <code className="mono flex-1 rounded-lg bg-muted px-3 py-2 text-sm">{API}/public</code>
          <Button size="icon" variant="outline" onClick={() => copy(`${API}/public`, "base")}>
            {copied === "base" ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
          </Button>
        </div>
        <p className="mt-3 text-sm text-muted-foreground">Authenticate every request with header <code className="mono">X-API-Key: &lt;your key&gt;</code></p>
        <div className="mt-4">
          <Label className="text-sm">Example — book an appointment from your site</Label>
          <pre className="mono mt-2 overflow-x-auto rounded-lg bg-primary p-4 text-xs text-primary-foreground">{snippet}</pre>
        </div>
        <div className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
          {[
            ["GET", "/public/availability?date=YYYY-MM-DD"],
            ["GET", "/public/patients"],
            ["POST", "/public/patients"],
            ["PUT", "/public/patients/{id}"],
            ["GET", "/public/appointments"],
            ["POST", "/public/appointments"],
            ["PUT", "/public/appointments/{id}"],
            ["GET", "/public/ping"],
          ].map(([m, p]) => (
            <div key={p} className="flex items-center gap-2">
              <Badge variant="outline" className="mono w-14 justify-center">{m}</Badge>
              <code className="mono text-xs">{p}</code>
            </div>
          ))}
        </div>
      </Card>

      <Card className="card-shadow mb-6 border-border/70 p-6" data-testid="widget-card">
        <h3 className="mb-2 font-serif text-xl">Website Booking Widget</h3>
        <p className="mb-3 text-sm text-muted-foreground">
          Drop this snippet into any page of your website. Patients can check availability and book directly into your clinic.
          Replace <code className="mono">YOUR_API_KEY</code> with a key from the table below.
        </p>
        <div className="flex items-start gap-2">
          <pre className="mono flex-1 overflow-x-auto rounded-lg bg-primary p-4 text-xs text-primary-foreground">{widgetSnippet}</pre>
          <Button size="icon" variant="outline" onClick={() => copy(widgetSnippet, "widget")} data-testid="copy-widget-btn">
            {copied === "widget" ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
          </Button>
        </div>
      </Card>

      <Card className="card-shadow overflow-hidden border-border/70">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/60 text-left text-xs uppercase text-muted-foreground">
              <tr><th className="px-4 py-3">Name</th><th className="px-4 py-3">Key</th><th className="px-4 py-3">Last used</th><th className="px-4 py-3 text-right">Actions</th></tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {keys.length === 0 ? (
                <tr><td colSpan={4} className="px-4 py-12 text-center text-muted-foreground">No API keys yet.</td></tr>
              ) : keys.map((k) => (
                <tr key={k.id} data-testid="apikey-row">
                  <td className="px-4 py-3 font-medium">{k.name}</td>
                  <td className="px-4 py-3 mono text-xs">{k.prefix}••••••••</td>
                  <td className="px-4 py-3 text-muted-foreground">{k.last_used ? new Date(k.last_used).toLocaleString() : "Never"}</td>
                  <td className="px-4 py-3 text-right">
                    <Button size="icon" variant="ghost" onClick={() => revoke(k.id)} data-testid="revoke-key-btn">
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader><DialogTitle className="font-serif text-2xl">{newKey ? "API Key Created" : "New API Key"}</DialogTitle></DialogHeader>
          {newKey ? (
            <div className="py-2">
              <p className="mb-2 text-sm text-muted-foreground">Copy this key now — it won't be shown again.</p>
              <div className="flex items-center gap-2">
                <code className="mono flex-1 break-all rounded-lg bg-muted px-3 py-2 text-xs" data-testid="new-key-value">{newKey.api_key}</code>
                <Button size="icon" variant="outline" onClick={() => copy(newKey.api_key, "new")}>
                  {copied === "new" ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                </Button>
              </div>
            </div>
          ) : (
            <div className="grid gap-2 py-2">
              <Label>Key name</Label>
              <Input data-testid="key-name" value={name} placeholder="e.g. Marketing website"
                onChange={(e) => setName(e.target.value)} />
            </div>
          )}
          <DialogFooter>
            {newKey ? (
              <Button onClick={() => setOpen(false)}>Done</Button>
            ) : (
              <>
                <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
                <Button onClick={create} data-testid="save-key-btn"><KeyRound className="mr-1 h-4 w-4" />Generate</Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
