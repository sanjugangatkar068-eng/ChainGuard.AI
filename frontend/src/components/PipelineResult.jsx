import BarChart, { riskColor } from "./BarChart";

const money = (n) => "$" + Number(n).toLocaleString();

export default function PipelineResult({ result, disruption }) {
  if (!result) {
    return (
      <section className="card">
        <h2>2 · Agent pipeline output</h2>
        <p className="empty">Create a disruption, then run the analysis.</p>
      </section>
    );
  }

  const sensing = result.disruption_sensing;
  const planning = result.scenario_planning;
  const logistics = result.logistics;
  const inventory = result.inventory;
  const compliance = result.compliance_audit;
  const supplierRisk = result.supplier_risk;

  const scenarioItems = planning.scenarios.map((scenario) => ({
    label: scenario.name,
    value: scenario.delay_days,
    color: riskColor(scenario.risk),
    sub: `${scenario.delay_days} d · ${money(scenario.extra_cost_usd)}`,
  }));

  const supplierItems = supplierRisk?.suppliers.map((supplier) => ({
    label: supplier.name,
    value: supplier.spend_share_pct,
    color: riskColor(supplier.risk_level),
    sub: `${supplier.spend_share_pct}% · ${supplier.risk_level}`,
  }));

  return (
    <section className="card">
      <h2>2 · Agent pipeline output</h2>

      {result.pipeline && (
        <div className="agent">
          <h3>{result.pipeline.orchestrator}</h3>
          <p className="out">
            {result.pipeline.agents_ok} ok · {result.pipeline.agents_failed} failed ·{" "}
            {result.pipeline.agents_skipped} skipped · {result.pipeline.duration_ms} ms
            <br />
            {result.pipeline.trace
              .map((step) => `${step.agent}:${step.status}`)
              .join("  ·  ")}
          </p>
        </div>
      )}

      <div className="agent">
        <h3>1 · Disruption Sensing Agent</h3>
        <p className="out">
          Risk <span className={`pill ${sensing.risk_level}`}>{sensing.risk_level}</span>{" "}
          (score {sensing.risk_score}) · confidence {sensing.confidence} ·{" "}
          {sensing.disruption_type} at {sensing.location} · source: {sensing.source}
        </p>
      </div>

      <div className="agent">
        <h3>2 · Scenario Planning Agent</h3>
        <BarChart items={scenarioItems} />
        <table>
          <thead>
            <tr>
              <th>Option</th>
              <th>Cost</th>
              <th>Delay</th>
              <th>Risk</th>
              <th>Budget</th>
            </tr>
          </thead>
          <tbody>
            {planning.scenarios.map((scenario) => (
              <tr key={scenario.id}>
                <td>{scenario.name}</td>
                <td>{money(scenario.extra_cost_usd)}</td>
                <td>{scenario.delay_days} d</td>
                <td>
                  <span className={`pill ${scenario.risk}`}>{scenario.risk}</span>
                </td>
                <td>
                  {scenario.within_budget ? (
                    "yes"
                  ) : (
                    <span className="muted">over budget</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="out">
          Recommended: <b>{planning.recommended_scenario.name}</b>
        </p>
      </div>

      <div className="agent">
        <h3>3 · Rerouting &amp; Logistics Agent</h3>
        <div className="route">
          <span className="node">Origin</span>
          <span className="line" />
          <span className="node bad">
            {disruption?.location || "Disruption"}
          </span>
          <span className="line" />
          <span className="node">Destination</span>
          <span className="eta">revised ETA +{logistics.revised_eta_days} d</span>
        </div>
        <p className="out">
          Action: {logistics.recommended_action} · route:{" "}
          {logistics.recommended_route} · {money(logistics.estimated_cost_usd)}{" "}
          (recommendation only)
        </p>
      </div>

      <div className="agent">
        <h3>4 · Inventory Rebalancing Agent</h3>
        <p className="out">
          Reorder point {inventory.reorder_point} · projected{" "}
          {inventory.projected_inventory} · replenish{" "}
          <b>{inventory.recommended_replenishment_units}</b> units (
          {money(inventory.estimated_replenishment_cost_usd)})
        </p>
      </div>

      <div className="agent">
        <h3>5 · Compliance &amp; Audit Agent</h3>
        <p className="out">
          {compliance.flags.length ? (
            compliance.flags.map((flag) => <span key={flag}>{flag}<br /></span>)
          ) : (
            "No flags."
          )}
          Report: {compliance.report.outcome} · {compliance.report.policy}
        </p>
      </div>

      {supplierRisk && (
        <div className="agent">
          <h3>6 · Supplier Risk Agent</h3>
          <BarChart items={supplierItems} />
          <p className="out">
            Concentration risk:{" "}
            <b>{supplierRisk.concentration_risk ? "YES" : "no"}</b> · highest risk:{" "}
            {supplierRisk.highest_risk_supplier} · {supplierRisk.recommendation}
          </p>
        </div>
      )}

      <div className="agent">
        <h3>Escalation Agent</h3>
        <p className="out">
          Escalate: <b>{result.escalation.escalate ? "YES" : "no"}</b> (threshold:{" "}
          {result.escalation.threshold}) · {result.escalation.reason}
        </p>
      </div>

      <div className="agent">
        <h3>Explanation</h3>
        <p className="out">
          {result.explanation.explanation}{" "}
          <span className="muted">({result.explanation.reasoning_source})</span>
        </p>
      </div>

      <div className="agent">
        <h3>Human-in-the-loop</h3>
        <p className="out">
          {result.human_approval_required
            ? "Approval requested — see section 3."
            : "No approval required."}
          {result.alert_id ? ` · alert #${result.alert_id} raised (section 4).` : ""}
        </p>
      </div>
    </section>
  );
}
