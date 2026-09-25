import CrudModule from "@/components/CrudModule";
import { Badge } from "@/components/ui/badge";

export default function Patients() {
  return (
    <CrudModule
      title="Patients"
      subtitle="Complete patient records and demographics"
      endpoint="patients"
      testid="patients"
      columns={[
        { key: "name", label: "Name" },
        { key: "gender", label: "Gender" },
        { key: "age", label: "Age" },
        { key: "phone", label: "Phone" },
        { key: "blood_group", label: "Blood" },
        { key: "condition", label: "Condition" },
      ]}
      renderCell={(c, it) =>
        c.key === "blood_group" && it.blood_group
          ? <Badge variant="outline" className="mono">{it.blood_group}</Badge>
          : (it[c.key] ?? "—")
      }
      fields={[
        { key: "name", label: "Full name" },
        { key: "gender", label: "Gender", type: "select", options: ["Male", "Female", "Other"] },
        { key: "age", label: "Age", type: "number" },
        { key: "phone", label: "Phone" },
        { key: "email", label: "Email" },
        { key: "blood_group", label: "Blood group", type: "select", options: ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"] },
        { key: "address", label: "Address", type: "textarea" },
        { key: "condition", label: "Primary condition / notes", type: "textarea" },
      ]}
    />
  );
}
