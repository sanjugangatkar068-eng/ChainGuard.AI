export default function OrchestratorCard({ info, busy, result, onRun }) {
  return (
    <section className="card">
      <h2>Orchestrator</h2>

      {info ? (
        <p className="out">
          {info.orchestrator} · mode <b>{info.mode}</b> ·{" "}
          {info.interval_seconds ? `every ${info.interval_seconds}s` : "on-demand"} ·
          alert threshold {info.alert_threshold}
          <br />
          Maintains {info.roles.length} roles:{" "}
          {info.roles.map((role) => role.name).join(", ")}
        </p>
      ) : (
        <p className="empty">Loading…</p>
      )}

      {result && (
        <p className="out">
          Cycle complete — scanned {result.scanned}, relevant {result.relevant},
          created {result.created}, escalated {result.escalated}, notified{" "}
          {result.notified} ({result.data_source}).
        </p>
      )}

      <div className="actions">
        <button type="button" disabled={busy} onClick={onRun}>
          Run autonomous cycle
        </button>
      </div>
    </section>
  );
}
