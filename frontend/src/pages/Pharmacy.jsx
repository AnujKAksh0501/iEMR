import CrudModule from "@/components/CrudModule";
import { Badge } from "@/components/ui/badge";

export default function Pharmacy() {
  return (
    <CrudModule
      title="Pharmacy Inventory"
      subtitle="Stock levels, pricing and reorder alerts"
      endpoint="medications"
      testid="pharmacy"
      columns={[
        { key: "name", label: "Drug" },
        { key: "category", label: "Category" },
        { key: "stock", label: "Stock" },
        { key: "unit", label: "Unit" },
        { key: "price", label: "Price ($)" },
        { key: "expiry", label: "Expiry" },
        { key: "alert", label: "Status" },
      ]}
      renderCell={(c, it) => {
        if (c.key === "alert") {
          const low = Number(it.stock || 0) <= Number(it.reorder_level || 0);
          return <Badge className={`border-0 ${low ? "bg-red-100 text-red-800" : "bg-emerald-100 text-emerald-800"}`}>{low ? "Reorder" : "In stock"}</Badge>;
        }
        if (c.key === "stock" || c.key === "price") return <span className="mono">{it[c.key] ?? "—"}</span>;
        return it[c.key] ?? "—";
      }}
      fields={[
        { key: "name", label: "Drug name" },
        { key: "category", label: "Category", type: "select", options: ["Antibiotic", "Analgesic", "Antiviral", "Cardiac", "Vitamin", "Other"] },
        { key: "stock", label: "Stock quantity", type: "number" },
        { key: "unit", label: "Unit", type: "select", options: ["Tablets", "Capsules", "Bottles", "Vials", "Strips"] },
        { key: "reorder_level", label: "Reorder level", type: "number" },
        { key: "price", label: "Unit price ($)", type: "number" },
        { key: "expiry", label: "Expiry date", type: "date" },
        { key: "supplier", label: "Supplier" },
      ]}
    />
  );
}
