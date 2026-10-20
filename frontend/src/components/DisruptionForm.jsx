import { useState } from "react";

const DEFAULT_SUPPLIERS = JSON.stringify(
  [
    {
      name: "Apex Components",
      tier: 1,
      country: "China",
      single_source: true,
      lead_time_days: 21,
      spend_usd: 120000,
    },
    {
      name: "Baltic Metals",
      tier: 2,
      country: "Poland",
      single_source: false,
      lead_time_days: 12,
      spend_usd: 40000,
    },
    {
      name: "Deccan Plastics",
      tier: 1,
      country: "India",
      single_source: false,
      lead_time_days: 9,
      spend_usd: 60000,
    },
  ],
  null,
  2
);

const TYPES = [
  ["port_closure", "Port closure"],
  ["weather", "Weather"],
  ["tariff_change", "Tariff change"],
  ["supplier_outage", "Supplier outage"],
  ["port_congestion", "Port congestion"],
  ["demand_spike", "Demand spike"],
  ["other", "Other"],
];

export default function DisruptionForm({
  busy,
  disruption,
  canAnalyze,
  onCreate,
  onAnalyze,
}) {
  const [form, setForm] = useState({
    title: "Red Sea reroute",
    disruption_type: "port_closure",
    location: "Suez Canal",
    severity: "critical",
    delay_days: 14,
    estimated_loss_usd: 50000,
  });
  const [suppliersText, setSuppliersText] = useState(DEFAULT_SUPPLIERS);
  const [supplierError, setSupplierError] = useState("");

  const update = (key) => (event) =>
    setForm({ ...form, [key]: event.target.value });

  function submit(event) {
    event.preventDefault();
    onCreate({
      ...form,
      delay_days: Number(form.delay_days),
      estimated_loss_usd: Number(form.estimated_loss_usd),
    });
  }

  function analyze() {
    try {
      setSupplierError("");
      const raw = suppliersText.trim();
      const suppliers = raw ? JSON.parse(raw) : [];
      if (!Array.isArray(suppliers)) {
        throw new Error("Suppliers must be a JSON array");
      }
      onAnalyze(suppliers);
    } catch (e) {
      setSupplierError(e.message);
    }
  }

  return (
    <section className="card">
      <h2>1 · Report a disruption</h2>

      <form onSubmit={submit}>
        <label htmlFor="title">Title</label>
        <input id="title" value={form.title} onChange={update("title")} />

        <div className="row">
          <div>
            <label htmlFor="type">Type</label>
            <select id="type" value={form.disruption_type} onChange={update("disruption_type")}>
              {TYPES.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="severity">Severity</label>
            <select id="severity" value={form.severity} onChange={update("severity")}>
              {["low", "medium", "high", "critical"].map((level) => (
                <option key={level} value={level}>
                  {level}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="row">
          <div>
            <label htmlFor="location">Location</label>
            <input id="location" value={form.location} onChange={update("location")} />
          </div>
          <div>
            <label htmlFor="delay">Delay (days)</label>
            <input id="delay" type="number" value={form.delay_days} onChange={update("delay_days")} />
          </div>
          <div>
            <label htmlFor="loss">Est. loss (USD)</label>
            <input id="loss" type="number" value={form.estimated_loss_usd} onChange={update("estimated_loss_usd")} />
          </div>
        </div>

        <label htmlFor="suppliers">Suppliers (optional JSON — feeds the Supplier Risk agent)</label>
        <textarea
          id="suppliers"
          rows={6}
          value={suppliersText}
          onChange={(event) => setSuppliersText(event.target.value)}
        />
        {supplierError && <p className="error inline">{supplierError}</p>}

        <div className="actions">
          <button type="submit" disabled={busy}>
            Create disruption
          </button>
          <button
            type="button"
            className="ghost"
            disabled={busy || !canAnalyze}
            onClick={analyze}
          >
            Run agent analysis
          </button>
        </div>
        {disruption && (
          <p className="muted small">Disruption #{disruption.id} ready.</p>
        )}
      </form>
    </section>
  );
}
