import CrudModule from "@/components/CrudModule";
import { Badge } from "@/components/ui/badge";

const sc = { Ordered: "bg-blue-100 text-blue-800", "In progress": "bg-amber-100 text-amber-800", Completed: "bg-emerald-100 text-emerald-800" };

export default function LabTests() {
  return (
    <CrudModule
      title="Lab Tests"
      subtitle="Diagnostics orders and results"
      endpoint="labtests"
      testid="labtests"
      columns={[
        { key: "patient", label: "Patient" },
        { key: "test_name", label: "Test" },
        { key: "sample", label: "Sample" },
        { key: "date", label: "Date" },
        { key: "result", label: "Result" },
        { key: "status", label: "Status" },
      ]}
      renderCell={(c, it) =>
        c.key === "status"
          ? <Badge className={`border-0 ${sc[it.status] || "bg-muted text-foreground"}`}>{it.status || "Ordered"}</Badge>
          : (it[c.key] ?? "—")
      }
      fields={[
        { key: "patient", label: "Patient", type: "patient" },
        { key: "test_name", label: "Test name" },
        { key: "sample", label: "Sample type", type: "select", options: ["Blood", "Urine", "Swab", "Tissue", "Imaging"] },
        { key: "date", label: "Date", type: "date" },
        { key: "status", label: "Status", type: "select", options: ["Ordered", "In progress", "Completed"] },
        { key: "result", label: "Result summary", type: "textarea" },
      ]}
    />
  );
}
