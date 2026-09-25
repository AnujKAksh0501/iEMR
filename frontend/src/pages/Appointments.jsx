import CrudModule from "@/components/CrudModule";
import { Badge } from "@/components/ui/badge";

const statusColor = { Scheduled: "bg-blue-100 text-blue-800", Completed: "bg-emerald-100 text-emerald-800", Cancelled: "bg-red-100 text-red-800", "No-show": "bg-amber-100 text-amber-800" };

export default function Appointments() {
  return (
    <CrudModule
      title="Appointments"
      subtitle="Scheduling across your clinic"
      endpoint="appointments"
      testid="appointments"
      columns={[
        { key: "patient", label: "Patient" },
        { key: "doctor", label: "Doctor" },
        { key: "date", label: "Date" },
        { key: "time", label: "Time" },
        { key: "reason", label: "Reason" },
        { key: "status", label: "Status" },
      ]}
      renderCell={(c, it) =>
        c.key === "status"
          ? <Badge className={`${statusColor[it.status] || "bg-muted text-foreground"} border-0`}>{it.status || "Scheduled"}</Badge>
          : (it[c.key] ?? "—")
      }
      fields={[
        { key: "patient", label: "Patient", type: "patient" },
        { key: "doctor", label: "Doctor" },
        { key: "date", label: "Date", type: "date" },
        { key: "time", label: "Time", type: "time" },
        { key: "reason", label: "Reason", type: "textarea" },
        { key: "status", label: "Status", type: "select", options: ["Scheduled", "Completed", "Cancelled", "No-show"] },
      ]}
    />
  );
}
