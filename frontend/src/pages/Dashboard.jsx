import { useEffect, useState } from "react";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Card } from "@/components/ui/card";
import { useNavigate } from "react-router-dom";
import {
  Users, CalendarDays, Pill, FlaskConical, Package, DollarSign, AlertTriangle, UserCog, Receipt,
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from "recharts";

const CARDS = [
  { key: "patients", label: "Patients", icon: Users, to: "/app/patients", color: "156 61% 25%" },
  { key: "appointments_today", label: "Today's Appointments", icon: CalendarDays, to: "/app/appointments", color: "197 40% 40%" },
  { key: "prescriptions", label: "Prescriptions", icon: Pill, to: "/app/prescriptions", color: "12 60% 55%" },
  { key: "labtests", label: "Lab Tests", icon: FlaskConical, to: "/app/labtests", color: "270 30% 50%" },
  { key: "medications", label: "Pharmacy Items", icon: Package, to: "/app/pharmacy", color: "41 54% 45%" },
  { key: "staff", label: "Staff", icon: UserCog, to: "/app/staff", color: "156 30% 30%" },
];

export default function Dashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const navigate = useNavigate();

  useEffect(() => { api.get("/dashboard/stats").then((r) => setStats(r.data)).catch(() => {}); }, []);

  const chartData = stats ? [
    { name: "Patients", value: stats.patients },
    { name: "Appts", value: stats.appointments_total },
    { name: "Rx", value: stats.prescriptions },
    { name: "Labs", value: stats.labtests },
    { name: "Pharma", value: stats.medications },
  ] : [];
  const colors = ["#0F3E2E", "#3d6d80", "#c8683f", "#7a5e9e", "#b78c30"];

  return (
    <div data-testid="page-dashboard">
      <div className="mb-8">
        <p className="text-sm text-muted-foreground">Welcome back,</p>
        <h1 className="font-serif text-4xl text-foreground">{user?.name}</h1>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
        {CARDS.map((c) => (
          <Card
            key={c.key}
            onClick={() => navigate(c.to)}
            data-testid={`stat-${c.key}`}
            className="card-shadow cursor-pointer border-border/70 p-4 transition-transform hover:-translate-y-0.5"
          >
            <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg"
              style={{ backgroundColor: `hsl(${c.color} / 0.12)`, color: `hsl(${c.color})` }}>
              <c.icon className="h-5 w-5" />
            </div>
            <div className="mono text-3xl font-semibold text-foreground">{stats ? stats[c.key] : "—"}</div>
            <div className="mt-1 text-xs text-muted-foreground">{c.label}</div>
          </Card>
        ))}
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <Card className="card-shadow border-border/70 p-6 lg:col-span-2">
          <h2 className="mb-4 font-serif text-2xl">Clinic Activity</h2>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={chartData}>
              <XAxis dataKey="name" tickLine={false} axisLine={false} fontSize={12} />
              <YAxis tickLine={false} axisLine={false} fontSize={12} allowDecimals={false} />
              <Tooltip cursor={{ fill: "rgba(15,62,46,0.05)" }} />
              <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                {chartData.map((_, i) => <Cell key={i} fill={colors[i]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <div className="space-y-4">
          <Card className="card-shadow border-border/70 p-5">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-100 text-emerald-700">
                <DollarSign className="h-5 w-5" />
              </div>
              <div>
                <div className="mono text-2xl font-semibold">${stats ? stats.revenue : "—"}</div>
                <div className="text-xs text-muted-foreground">Revenue collected</div>
              </div>
            </div>
          </Card>
          <Card className="card-shadow border-border/70 p-5">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-100 text-amber-700">
                <AlertTriangle className="h-5 w-5" />
              </div>
              <div>
                <div className="mono text-2xl font-semibold">{stats ? stats.low_stock : "—"}</div>
                <div className="text-xs text-muted-foreground">Low-stock medications</div>
              </div>
            </div>
          </Card>
          <Card className="card-shadow border-border/70 p-5">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 text-blue-700">
                <Receipt className="h-5 w-5" />
              </div>
              <div>
                <div className="mono text-2xl font-semibold">{stats ? stats.pending_invoices : "—"}</div>
                <div className="text-xs text-muted-foreground">Pending invoices</div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
