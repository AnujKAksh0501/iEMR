import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import {
  LayoutDashboard, Users, CalendarDays, Pill, Package, FlaskConical,
  UserCog, Receipt, Sparkles, LogOut, Activity, Menu, X,
} from "lucide-react";
import { useState } from "react";

const NAV = [
  { to: "/app", label: "Dashboard", icon: LayoutDashboard, end: true, id: "dashboard" },
  { to: "/app/patients", label: "Patients", icon: Users, id: "patients" },
  { to: "/app/appointments", label: "Appointments", icon: CalendarDays, id: "appointments" },
  { to: "/app/prescriptions", label: "Prescriptions", icon: Pill, id: "prescriptions" },
  { to: "/app/pharmacy", label: "Pharmacy", icon: Package, id: "pharmacy" },
  { to: "/app/labtests", label: "Lab Tests", icon: FlaskConical, id: "labtests" },
  { to: "/app/staff", label: "Staff", icon: UserCog, id: "staff" },
  { to: "/app/billing", label: "Billing", icon: Receipt, id: "billing" },
  { to: "/app/assistant", label: "AI Assistant", icon: Sparkles, id: "assistant" },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const doLogout = () => { logout(); navigate("/login"); };

  const SidebarInner = () => (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 px-6 py-6">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-accent-foreground">
          <Activity className="h-5 w-5" />
        </div>
        <div className="leading-tight">
          <div className="font-serif text-xl text-primary-foreground">MediCore</div>
          <div className="text-[11px] text-primary-foreground/60 truncate max-w-[140px]">{user?.clinic_name}</div>
        </div>
      </div>
      <nav className="flex-1 space-y-1 px-3">
        {NAV.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            end={n.end}
            data-testid={`nav-${n.id}`}
            onClick={() => setOpen(false)}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-primary-foreground/15 text-primary-foreground"
                  : "text-primary-foreground/70 hover:bg-primary-foreground/10 hover:text-primary-foreground"
              }`
            }
          >
            <n.icon className="h-[18px] w-[18px]" />
            {n.label}
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-primary-foreground/10 p-3">
        <div className="mb-2 px-3 py-1">
          <div className="text-sm font-medium text-primary-foreground">{user?.name}</div>
          <div className="text-[11px] capitalize text-primary-foreground/60">{user?.role?.replace("_", " ")}</div>
        </div>
        <button
          data-testid="logout-btn"
          onClick={doLogout}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-primary-foreground/70 hover:bg-primary-foreground/10"
        >
          <LogOut className="h-[18px] w-[18px]" /> Sign out
        </button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-background">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 bg-primary lg:block">
        <SidebarInner />
      </aside>

      {open && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black/40" onClick={() => setOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-64 bg-primary">
            <button className="absolute right-3 top-4 text-primary-foreground" onClick={() => setOpen(false)}>
              <X className="h-5 w-5" />
            </button>
            <SidebarInner />
          </aside>
        </div>
      )}

      <div className="lg:pl-64">
        <header className="sticky top-0 z-30 flex items-center gap-3 border-b bg-background/80 px-4 py-3 backdrop-blur lg:px-8">
          <button className="lg:hidden" onClick={() => setOpen(true)} data-testid="menu-toggle">
            <Menu className="h-6 w-6" />
          </button>
          <div className="text-sm text-muted-foreground">
            <span className="font-serif text-lg text-foreground">{user?.clinic_name}</span>
          </div>
        </header>
        <main className="px-4 py-6 lg:px-8 lg:py-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
