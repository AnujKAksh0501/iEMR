import { useEffect, useState } from "react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Plus, Pencil, Trash2, Search } from "lucide-react";
import { toast } from "sonner";

export function PageHeader({ title, subtitle, action }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="font-serif text-3xl text-foreground sm:text-4xl">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

function FieldInput({ field, value, onChange, patients }) {
  const common = { id: field.key, "data-testid": `field-${field.key}` };
  if (field.type === "textarea")
    return <Textarea {...common} value={value || ""} onChange={(e) => onChange(e.target.value)} />;
  if (field.type === "select")
    return (
      <Select value={value || ""} onValueChange={onChange}>
        <SelectTrigger data-testid={`field-${field.key}`}><SelectValue placeholder={`Select ${field.label}`} /></SelectTrigger>
        <SelectContent>
          {field.options.map((o) => <SelectItem key={o} value={o}>{o}</SelectItem>)}
        </SelectContent>
      </Select>
    );
  if (field.type === "patient")
    return (
      <Select value={value || ""} onValueChange={onChange}>
        <SelectTrigger data-testid={`field-${field.key}`}><SelectValue placeholder="Select patient" /></SelectTrigger>
        <SelectContent>
          {patients.map((p) => <SelectItem key={p.id} value={p.name}>{p.name}</SelectItem>)}
        </SelectContent>
      </Select>
    );
  return (
    <Input {...common} type={field.type || "text"} value={value ?? ""}
      onChange={(e) => onChange(e.target.value)} />
  );
}

export default function CrudModule({ title, subtitle, endpoint, fields, columns, renderCell, testid }) {
  const [items, setItems] = useState([]);
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({});
  const [query, setQuery] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get(`/${endpoint}`);
      setItems(r.data);
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    setLoading(false);
  };

  useEffect(() => {
    load();
    if (fields.some((f) => f.type === "patient"))
      api.get("/patients").then((r) => setPatients(r.data)).catch(() => {});
    // eslint-disable-next-line
  }, [endpoint]);

  const openNew = () => { setEditing(null); setForm({}); setOpen(true); };
  const openEdit = (item) => { setEditing(item); setForm({ ...item }); setOpen(true); };

  const save = async () => {
    try {
      if (editing) await api.put(`/${endpoint}/${editing.id}`, form);
      else await api.post(`/${endpoint}`, form);
      toast.success(editing ? "Updated" : "Created");
      setOpen(false);
      load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const remove = async (item) => {
    if (!window.confirm("Delete this record?")) return;
    try { await api.delete(`/${endpoint}/${item.id}`); toast.success("Deleted"); load(); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const filtered = items.filter((it) =>
    !query || JSON.stringify(it).toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div data-testid={`page-${testid}`}>
      <PageHeader
        title={title}
        subtitle={subtitle}
        action={
          <Button onClick={openNew} data-testid={`add-${testid}-btn`} className="rounded-full">
            <Plus className="mr-1 h-4 w-4" /> New {title.replace(/s$/, "")}
          </Button>
        }
      />

      <div className="relative mb-4 max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input data-testid={`search-${testid}`} placeholder="Search…" value={query}
          onChange={(e) => setQuery(e.target.value)} className="pl-9 bg-card" />
      </div>

      <Card className="card-shadow overflow-hidden border-border/70">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/60 text-left text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                {columns.map((c) => <th key={c.key} className="px-4 py-3 font-medium">{c.label}</th>)}
                <th className="px-4 py-3 text-right font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {loading ? (
                <tr><td colSpan={columns.length + 1} className="px-4 py-10 text-center text-muted-foreground">Loading…</td></tr>
              ) : filtered.length === 0 ? (
                <tr><td colSpan={columns.length + 1} className="px-4 py-12 text-center text-muted-foreground">No records yet. Click “New” to add one.</td></tr>
              ) : filtered.map((it) => (
                <tr key={it.id} className="hover:bg-muted/30" data-testid={`row-${testid}`}>
                  {columns.map((c) => (
                    <td key={c.key} className="px-4 py-3">
                      {renderCell ? renderCell(c, it) : (it[c.key] ?? "—")}
                    </td>
                  ))}
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-1">
                      <Button size="icon" variant="ghost" onClick={() => openEdit(it)} data-testid={`edit-${testid}-btn`}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button size="icon" variant="ghost" onClick={() => remove(it)} data-testid={`delete-${testid}-btn`}>
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="font-serif text-2xl">{editing ? "Edit" : "New"} {title.replace(/s$/, "")}</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-2">
            {fields.map((f) => (
              <div key={f.key} className="grid gap-1.5">
                <Label htmlFor={f.key}>{f.label}</Label>
                <FieldInput field={f} value={form[f.key]} patients={patients}
                  onChange={(v) => setForm((s) => ({ ...s, [f.key]: v }))} />
              </div>
            ))}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button onClick={save} data-testid={`save-${testid}-btn`}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export { Badge, DialogTrigger };
