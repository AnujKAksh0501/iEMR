import { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import axios from "axios";
import { API, formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Activity, HeartPulse } from "lucide-react";
import { toast } from "sonner";

export default function PortalLogin() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", phone: "" });
  const [loading, setLoading] = useState(false);

  useEffect(() => { if (localStorage.getItem("emr_portal_token")) navigate("/portal"); }, [navigate]);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const r = await axios.post(`${API}/portal/login`, form);
      localStorage.setItem("emr_portal_token", r.data.token);
      navigate("/portal");
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-primary px-6">
      <div className="w-full max-w-sm rounded-2xl bg-card p-8 card-shadow">
        <div className="mb-6 flex items-center gap-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent text-accent-foreground">
            <HeartPulse className="h-5 w-5" />
          </div>
          <div className="leading-tight">
            <div className="font-serif text-xl text-primary">Patient Portal</div>
            <div className="text-xs text-muted-foreground">Secure access to your care</div>
          </div>
        </div>
        <h1 className="font-serif text-2xl">Sign in</h1>
        <p className="mb-6 mt-1 text-sm text-muted-foreground">Use the email and phone number your clinic has on file.</p>
        <form onSubmit={submit} className="space-y-4">
          <div className="grid gap-1.5"><Label htmlFor="email">Email</Label>
            <Input id="email" data-testid="portal-email" type="email" required value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
          <div className="grid gap-1.5"><Label htmlFor="phone">Phone</Label>
            <Input id="phone" data-testid="portal-phone" required value={form.phone} placeholder="+14155551234"
              onChange={(e) => setForm({ ...form, phone: e.target.value })} /></div>
          <Button type="submit" className="w-full" disabled={loading} data-testid="portal-login-btn">
            {loading ? "Signing in…" : "Access my records"}
          </Button>
        </form>
        <Link to="/" className="mt-6 flex items-center justify-center gap-1 text-xs text-muted-foreground hover:text-primary">
          <Activity className="h-3.5 w-3.5" /> Back to MediCore
        </Link>
      </div>
    </div>
  );
}
