import CrudModule from "@/components/CrudModule";

export default function Prescriptions() {
  return (
    <CrudModule
      title="Prescriptions"
      subtitle="Medication orders and dosage instructions"
      endpoint="prescriptions"
      testid="prescriptions"
      columns={[
        { key: "patient", label: "Patient" },
        { key: "medication", label: "Medication" },
        { key: "dosage", label: "Dosage" },
        { key: "frequency", label: "Frequency" },
        { key: "duration", label: "Duration" },
        { key: "prescribed_by", label: "Prescriber" },
      ]}
      fields={[
        { key: "patient", label: "Patient", type: "patient" },
        { key: "medication", label: "Medication" },
        { key: "dosage", label: "Dosage (e.g. 500mg)" },
        { key: "frequency", label: "Frequency", type: "select", options: ["Once daily", "Twice daily", "Thrice daily", "Every 6 hours", "As needed"] },
        { key: "duration", label: "Duration (e.g. 7 days)" },
        { key: "prescribed_by", label: "Prescribed by" },
        { key: "notes", label: "Notes", type: "textarea" },
      ]}
    />
  );
}
