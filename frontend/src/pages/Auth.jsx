import { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import api, { API, formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Activity } from "lucide-react";
import { toast } from "sonner";

export default function Auth({ mode }) {
  const isLogin = mode === "login";
  const { user, login, register, googleLogin } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "", name: "", clinic_name: "" });
  const [loading, setLoading] = useState(false);
  const [forgot, setForgot] = useState(null); // null | 'request' | 'confirm'
  const [reset, setReset] = useState({ email: "", token: "", password: "" });

  useEffect(() => { if (user) navigate("/app"); }, [user, navigate]);

  // Handle Emergent Google auth redirect (session_id in URL fragment)
  useEffect(() => {
    const hash = window.location.hash;
    if (hash.includes("session_id=")) {
      const sid = new URLSearchParams(hash.substring(1)).get("session_id");
      if (sid) {
        setLoading(true);
        googleLogin(sid)
          .then(() => { window.location.hash = ""; navigate("/app"); })
          .catch((e) => { toast.error(formatApiError(e.response?.data?.detail)); setLoading(false); });
      }
    }
    // eslint-disable-next-line
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (isLogin) await login(form.email, form.password);
      else await register(form);
      navigate("/app");
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
      setLoading(false);
    }
  };

  const googleAuth = () => {
    const redirect = `${window.location.origin}/login`;
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirect)}`;
  };

  const requestReset = async () => {
    try {
      const r = await axios.post(`${API}/auth/request-reset`, { email: reset.email });
      if (r.data.dev_token) {
        setReset((s) => ({ ...s, token: r.data.dev_token }));
        toast.info("Email not configured — reset code prefilled for you.");
      } else {
        toast.success("If that email exists, a reset code has been sent.");
      }
      setForgot("confirm");
    } catch (err) { toast.error(formatApiError(err.response?.data?.detail)); }
  };
  const confirmReset = async () => {
    try {
      await axios.post(`${API}/auth/reset`, { token: reset.token, password: reset.password });
      toast.success("Password updated. Please sign in.");
      setForgot(null);
    } catch (err) { toast.error(formatApiError(err.response?.data?.detail)); }
  };

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="relative hidden lg:block">
        <img
          src="https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?w=1200&q=80"
          alt="Modern hospital"
          className="h-full w-full object-cover"
        />
        <div className="absolute inset-0 bg-primary/70" />
        <div className="absolute bottom-0 p-12 text-primary-foreground">
          <div className="mb-4 flex items-center gap-2">
            <Activity className="h-6 w-6" />
            <span className="font-serif text-2xl">MediCore</span>
          </div>
          <h2 className="font-serif text-4xl leading-tight">The operating system for modern clinics.</h2>
          <p className="mt-3 max-w-md text-primary-foreground/80">
            Patients, appointments, pharmacy, labs, billing and an AI clinical assistant — unified in one secure, multi-tenant platform.
          </p>
        </div>
      </div>

      <div className="flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm">
          <Link to="/" className="mb-8 flex items-center gap-2 lg:hidden">
            <Activity className="h-6 w-6 text-primary" />
            <span className="font-serif text-2xl text-primary">MediCore</span>
          </Link>
          <h1 className="font-serif text-3xl">{isLogin ? "Welcome back" : "Create your clinic"}</h1>
          <p className="mb-6 mt-1 text-sm text-muted-foreground">
            {isLogin ? "Sign in to your workspace" : "Start your clinic in minutes"}
          </p>

          <Button variant="outline" className="mb-4 w-full" onClick={googleAuth} data-testid="google-auth-btn">
            <img src="https://www.svgrepo.com/show/475656/google-color.svg" alt="" className="mr-2 h-4 w-4" />
            Continue with Google
          </Button>
          <div className="relative mb-4 text-center">
            <span className="relative z-10 bg-background px-3 text-xs text-muted-foreground">or</span>
            <div className="absolute left-0 top-1/2 h-px w-full bg-border" />
          </div>

          <form onSubmit={submit} className="space-y-4">
            {!isLogin && (
              <>
                <div className="grid gap-1.5"><Label htmlFor="name">Your name</Label>
                  <Input id="name" data-testid="auth-name" value={form.name} required
                    onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
                <div className="grid gap-1.5"><Label htmlFor="clinic">Clinic / Hospital name</Label>
                  <Input id="clinic" data-testid="auth-clinic" value={form.clinic_name} required
                    onChange={(e) => setForm({ ...form, clinic_name: e.target.value })} /></div>
              </>
            )}
            <div className="grid gap-1.5"><Label htmlFor="email">Email</Label>
              <Input id="email" data-testid="auth-email" type="email" value={form.email} required
                onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
            <div className="grid gap-1.5"><Label htmlFor="password">Password</Label>
              <Input id="password" data-testid="auth-password" type="password" value={form.password} required
                onChange={(e) => setForm({ ...form, password: e.target.value })} /></div>
            <Button type="submit" className="w-full" disabled={loading} data-testid="auth-submit-btn">
              {loading ? "Please wait…" : isLogin ? "Sign in" : "Create clinic"}
            </Button>
          </form>

          {isLogin && (
            <button onClick={() => { setForgot("request"); setReset({ email: form.email, token: "", password: "" }); }}
              className="mt-3 w-full text-center text-xs text-muted-foreground hover:text-primary" data-testid="forgot-password-link">
              Forgot password?
            </button>
          )}

          {forgot && (
            <div className="mt-4 rounded-xl border border-border/70 bg-muted/30 p-4" data-testid="forgot-box">
              {forgot === "request" ? (
                <>
                  <Label className="text-sm">Reset your password</Label>
                  <Input className="mt-2" data-testid="reset-email" type="email" placeholder="Your account email"
                    value={reset.email} onChange={(e) => setReset({ ...reset, email: e.target.value })} />
                  <div className="mt-3 flex gap-2">
                    <Button size="sm" onClick={requestReset} data-testid="reset-request-btn">Send reset code</Button>
                    <Button size="sm" variant="ghost" onClick={() => setForgot(null)}>Cancel</Button>
                  </div>
                </>
              ) : (
                <>
                  <Label className="text-sm">Enter code & new password</Label>
                  <Input className="mt-2" data-testid="reset-token" placeholder="Reset code"
                    value={reset.token} onChange={(e) => setReset({ ...reset, token: e.target.value })} />
                  <Input className="mt-2" data-testid="reset-password" type="password" placeholder="New password (8+ chars, mixed case & number)"
                    value={reset.password} onChange={(e) => setReset({ ...reset, password: e.target.value })} />
                  <div className="mt-3 flex gap-2">
                    <Button size="sm" onClick={confirmReset} data-testid="reset-confirm-btn">Update password</Button>
                    <Button size="sm" variant="ghost" onClick={() => setForgot(null)}>Cancel</Button>
                  </div>
                </>
              )}
            </div>
          )}

          <p className="mt-6 text-center text-sm text-muted-foreground">
            {isLogin ? "New clinic?" : "Already have an account?"}{" "}
            <Link to={isLogin ? "/register" : "/login"} className="font-medium text-primary underline-offset-4 hover:underline" data-testid="auth-switch-link">
              {isLogin ? "Create one" : "Sign in"}
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
