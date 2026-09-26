import { Link } from "react-router-dom";
import { Activity } from "lucide-react";

function LegalShell({ title, children }) {
  return (
    <div className="min-h-screen bg-background">
      <header className="mx-auto flex max-w-3xl items-center justify-between px-6 py-5">
        <Link to="/" className="flex items-center gap-2">
          <Activity className="h-6 w-6 text-primary" /><span className="font-serif text-2xl text-primary">MediCore</span>
        </Link>
        <Link to="/" className="text-sm text-muted-foreground hover:text-primary">Home</Link>
      </header>
      <main className="mx-auto max-w-3xl px-6 py-8">
        <h1 className="font-serif text-4xl">{title}</h1>
        <p className="mt-2 text-sm text-muted-foreground">Last updated: June 2026 · Template — have counsel review before commercial use.</p>
        <div className="prose mt-6 space-y-4 text-sm leading-relaxed text-foreground">{children}</div>
      </main>
    </div>
  );
}

export function Terms() {
  return (
    <LegalShell title="Terms of Service">
      <p>These Terms govern your use of the MediCore platform ("Service"). By creating an account you agree to them.</p>
      <h3 className="font-serif text-xl">1. Use of Service</h3>
      <p>The Service is provided to licensed healthcare organizations for managing clinical and administrative workflows. You are responsible for the accuracy of data you enter and for maintaining the confidentiality of your credentials.</p>
      <h3 className="font-serif text-xl">2. Clinical Disclaimer</h3>
      <p>MediCore, including its AI assistant, is informational decision-support only and is not a medical device. It does not provide medical advice, diagnosis, or treatment. Licensed clinicians remain solely responsible for all clinical decisions.</p>
      <h3 className="font-serif text-xl">3. Data & Compliance</h3>
      <p>You are the data controller for patient data in your workspace. You must obtain all necessary patient consents and execute Business Associate Agreements (BAAs) with relevant sub-processors before processing protected health information.</p>
      <h3 className="font-serif text-xl">4. Subscriptions & Billing</h3>
      <p>Paid plans are billed via Stripe. Fees are non-refundable except as required by law. Plan limits apply as described on the Subscription page.</p>
      <h3 className="font-serif text-xl">5. Liability</h3>
      <p>The Service is provided "as is". To the maximum extent permitted by law, MediCore is not liable for indirect or consequential damages.</p>
    </LegalShell>
  );
}

export function Privacy() {
  return (
    <LegalShell title="Privacy Policy">
      <p>This Policy explains how MediCore handles data on behalf of clinics using the Service.</p>
      <h3 className="font-serif text-xl">1. Data We Process</h3>
      <p>Account data (staff names, emails, roles) and clinic-entered records (patients, appointments, prescriptions, labs, invoices). Each clinic's data is logically isolated by tenant.</p>
      <h3 className="font-serif text-xl">2. How Data Is Used</h3>
      <p>To provide the Service: authentication, clinical workflows, notifications you enable, and payments. We do not sell personal data.</p>
      <h3 className="font-serif text-xl">3. Sub-processors</h3>
      <p>We may use Stripe (payments), and any email/WhatsApp/AI provider you connect. You control these integrations and their keys.</p>
      <h3 className="font-serif text-xl">4. Security & Auditing</h3>
      <p>Access is role-based, passwords are hashed (bcrypt), and administrative and clinical actions are recorded in an audit trail available to clinic admins.</p>
      <h3 className="font-serif text-xl">5. Your Rights</h3>
      <p>Clinic admins can export all workspace data and erase individual patient records (right to access and erasure) from within the app.</p>
    </LegalShell>
  );
}
