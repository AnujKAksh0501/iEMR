import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { Toaster } from "@/components/ui/sonner";
import Landing from "@/pages/Landing";
import Auth from "@/pages/Auth";
import Layout from "@/components/Layout";
import Dashboard from "@/pages/Dashboard";
import Patients from "@/pages/Patients";
import Appointments from "@/pages/Appointments";
import Prescriptions from "@/pages/Prescriptions";
import Pharmacy from "@/pages/Pharmacy";
import LabTests from "@/pages/LabTests";
import Staff from "@/pages/Staff";
import Billing from "@/pages/Billing";
import Assistant from "@/pages/Assistant";
import Automation from "@/pages/Automation";
import Developer from "@/pages/Developer";
import Docs from "@/pages/Docs";
import PaymentSuccess from "@/pages/PaymentSuccess";
import PortalLogin from "@/pages/portal/PortalLogin";
import PortalHome from "@/pages/portal/PortalHome";

function Protected({ children }) {
  const { user } = useAuth();
  if (user === null) return <div className="min-h-screen flex items-center justify-center text-muted-foreground">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Auth mode="login" />} />
          <Route path="/register" element={<Auth mode="register" />} />
          <Route path="/app" element={<Protected><Layout /></Protected>}>
            <Route index element={<Dashboard />} />
            <Route path="patients" element={<Patients />} />
            <Route path="appointments" element={<Appointments />} />
            <Route path="prescriptions" element={<Prescriptions />} />
            <Route path="pharmacy" element={<Pharmacy />} />
            <Route path="labtests" element={<LabTests />} />
            <Route path="staff" element={<Staff />} />
            <Route path="billing" element={<Billing />} />
            <Route path="assistant" element={<Assistant />} />
            <Route path="automation" element={<Automation />} />
            <Route path="developer" element={<Developer />} />
            <Route path="docs" element={<Docs />} />
          </Route>
          <Route path="/payment/success" element={<Protected><PaymentSuccess /></Protected>} />
          <Route path="/portal/login" element={<PortalLogin />} />
          <Route path="/portal" element={<PortalHome />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </AuthProvider>
  );
}

export default App;
