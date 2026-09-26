import { useEffect, useState } from "react";
import { portalApi, formatApiError } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import api from "@/lib/api";
import { Plug, Save } from "lucide-react";

const LABELS = {
  host: "SMTP Host", port: "Port", username: "Username", password: "Password", from_email: "From email",
  api_key: "API Key", domain: "Domain", account_sid: "Account SID", auth_token: "Auth Token",
  from_number: "From number (whatsapp:+1...)", phone_number_id: "Phone Number ID", access_token: "Access Token",
};

function ChannelConfig({ channel, providers, secretFields, value, onSave }) {
  const [form, setForm] = useState(value || { provider: "" });
  useEffect(() => { setForm(value || { provider: "" }); }, [value]);
  const provider = form.provider || "";
  const fields = provider && providers[provider] ? providers[provider] : [];

  const setProvider = (p) => setForm({ provider: p });
  const setField = (k, v) => setForm((s) => ({ ...s, [k]: v }));

  return (
    <div className="rounded-xl border border-border/70 p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="font-medium capitalize">{channel}</span>
      </div>
      <Label className="text-xs">Provider</Label>
      <Select value={provider} onValueChange={setProvider}>
        <SelectTrigger className="mt-1" data-testid={`integ-${channel}-provider`}><SelectValue placeholder="Choose a provider" /></SelectTrigger>
        <SelectContent>
          {Object.keys(providers).map((p) => <SelectItem key={p} value={p} className="capitalize">{p}</SelectItem>)}
        </SelectContent>
      </Select>
      {fields.map((f) => (
        <div key={f} className="mt-3">
          <Label className="text-xs">{LABELS[f] || f}</Label>
          <Input
            className="mt-1"
            data-testid={`integ-${channel}-${f}`}
            type={secretFields.includes(f) ? "password" : "text"}
            value={form[f] || ""}
            onChange={(e) => setField(f, e.target.value)}
          />
        </div>
      ))}
      <Button className="mt-4 w-full" data-testid={`integ-${channel}-save`}
        onClick={() => onSave(channel, form)}>
        <Save className="mr-1 h-4 w-4" /> Save {channel}
      </Button>
    </div>
  );
}

export default function IntegrationsPanel() {
  const [data, setData] = useState(null);

  const load = () => api.get("/integrations").then((r) => setData(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const save = async (channel, form) => {
    try {
      await api.put("/integrations", { [channel]: form });
      toast.success(`${channel} provider saved`);
      load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  if (!data) return null;
  const emailValue = { provider: data.email.provider || "", ...data.email.config };
  const waValue = { provider: data.whatsapp.provider || "", ...data.whatsapp.config };

  return (
    <Card className="card-shadow mb-6 border-border/70 p-6" data-testid="integrations-panel">
      <div className="mb-4 flex items-center gap-2">
        <Plug className="h-5 w-5 text-primary" />
        <h3 className="font-serif text-xl">Integrations — plug in any provider</h3>
      </div>
      <p className="mb-4 text-sm text-muted-foreground">
        Swap in any email or WhatsApp platform by selecting it and pasting its keys. Saved keys are stored securely and shown masked.
      </p>
      <div className="grid gap-4 sm:grid-cols-2">
        <ChannelConfig channel="email" providers={data.email_providers} secretFields={data.secret_fields} value={emailValue} onSave={save} />
        <ChannelConfig channel="whatsapp" providers={data.whatsapp_providers} secretFields={data.secret_fields} value={waValue} onSave={save} />
      </div>
    </Card>
  );
}
