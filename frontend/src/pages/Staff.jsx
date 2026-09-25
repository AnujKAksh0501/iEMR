import { useEffect, useState } from "react";
import api, { formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { PageHeader } from "@/components/CrudModule";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, Trash2, UserCog } from "lucide-react";
import { toast } from "sonner";

const ROLES = ["clinic_admin", "doctor", "nurse", "pharmacist", "lab_tech", "receptionist"];

export default function Staff() {
  const { user } = useAuth();
  const [staff, setStaff] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ role: "doctor" });
  const canManage = ["clinic_admin", "super_admin"].includes(user?.role);

  const load = () => api.get("/staff").then((r) => setStaff(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const save = async () => {
    try {
      await api.post("/staff", form);
      toast.success("Staff member added");
      setOpen(false); setForm({ role: "doctor" }); load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };
  const remove = async (id) => {
    if (!window.confirm("Remove this staff member?")) return;
    try { await api.delete(`/staff/${id}`); toast.success("Removed"); load(); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  return (
    <div data-testid="page-staff">
      <PageHeader
        title="Staff"
        subtitle="Team members and their access roles"
        action={canManage && (
          <Button onClick={() => setOpen(true)} data-testid="add-staff-btn" className="rounded-full">
            <Plus className="mr-1 h-4 w-4" /> Add Staff
          </Button>
        )}
      />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {staff.map((s) => (
          <Card key={s.id} className="card-shadow flex items-center justify-between border-border/70 p-4" data-testid="staff-card">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-full bg-primary/10 text-primary">
                <UserCog className="h-5 w-5" />
              </div>
              <div>
                <div className="font-medium">{s.name}</div>
                <div className="text-xs text-muted-foreground">{s.email}</div>
                <Badge variant="outline" className="mt-1 capitalize">{s.role?.replace("_", " ")}</Badge>
              </div>
            </div>
            {canManage && s.id !== user.id && (
              <Button size="icon" variant="ghost" onClick={() => remove(s.id)} data-testid="delete-staff-btn">
                <Trash2 className="h-4 w-4 text-destructive" />
              </Button>
            )}
          </Card>
        ))}
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader><DialogTitle className="font-serif text-2xl">Add Staff Member</DialogTitle></DialogHeader>
          <div className="grid gap-4 py-2">
            <div className="grid gap-1.5"><Label>Full name</Label>
              <Input data-testid="staff-name" value={form.name || ""} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
            <div className="grid gap-1.5"><Label>Email</Label>
              <Input data-testid="staff-email" type="email" value={form.email || ""} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
            <div className="grid gap-1.5"><Label>Temporary password</Label>
              <Input data-testid="staff-password" type="text" value={form.password || ""} onChange={(e) => setForm({ ...form, password: e.target.value })} /></div>
            <div className="grid gap-1.5"><Label>Role</Label>
              <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v })}>
                <SelectTrigger data-testid="staff-role"><SelectValue /></SelectTrigger>
                <SelectContent>{ROLES.map((r) => <SelectItem key={r} value={r} className="capitalize">{r.replace("_", " ")}</SelectItem>)}</SelectContent>
              </Select></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button onClick={save} data-testid="save-staff-btn">Add</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
