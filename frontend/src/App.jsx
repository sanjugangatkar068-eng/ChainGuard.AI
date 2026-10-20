import { useCallback, useEffect, useState } from "react";

import { API_BASE, api } from "./api";
import Alerts from "./components/Alerts";
import Approvals from "./components/Approvals";
import AuditTrail from "./components/AuditTrail";
import DisruptionForm from "./components/DisruptionForm";
import OrchestratorCard from "./components/OrchestratorCard";
import PipelineResult from "./components/PipelineResult";
import StatCards from "./components/StatCards";

export default function App() {
  const [stats, setStats] = useState({ disruptions: 0, analyses: 0, approvals: 0 });
  const [approvals, setApprovals] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [audit, setAudit] = useState([]);
  const [result, setResult] = useState(null);
  const [disruption, setDisruption] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [orchInfo, setOrchInfo] = useState(null);
  const [cycle, setCycle] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const [dash, appr, alertPage, auditPage] = await Promise.all([
        api.dashboard(),
        api.approvals(),
        api.alerts(),
        api.audit(),
      ]);
      setStats({
        disruptions: dash.disruptions,
        analyses: dash.analyses,
        approvals: appr.total,
      });
      setApprovals(appr.items);
      setAlerts(alertPage.items);
      setAudit(auditPage.items);
    } catch (e) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    refresh();
    api.orchestrator().then(setOrchInfo).catch(() => {});
  }, [refresh]);

  async function handleRunCycle() {
    setBusy(true);
    setError("");
    try {
      setCycle(await api.runCycle());
      await refresh();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleCreate(payload) {
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const created = await api.createDisruption(payload);
      setDisruption(created);
      await refresh();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleAnalyze(suppliers) {
    if (!disruption) return;
    setBusy(true);
    setError("");
    try {
      setResult(await api.analyze({ disruption_id: disruption.id, suppliers }));
      await refresh();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleDecide(id, decision) {
    setError("");
    try {
      await api.decide(id, {
        decision,
        reviewer: "web-ui",
        comments: "from web UI",
      });
      await refresh();
    } catch (e) {
      setError(e.message);
    }
  }

  async function handleAck(id) {
    setError("");
    try {
      await api.ackAlert(id);
      await refresh();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div className="app">
      <header>
        <h1>ChainGuard AI</h1>
        <span className="tag">Agentic AI for resilient supply chains</span>
        <span className="api">API: {API_BASE}</span>
      </header>

      <main>
        <StatCards stats={stats} />

        <OrchestratorCard
          info={orchInfo}
          busy={busy}
          result={cycle}
          onRun={handleRunCycle}
        />

        {error && <div className="error">Error: {error}</div>}

        <div className="grid">
          <DisruptionForm
            busy={busy}
            disruption={disruption}
            canAnalyze={Boolean(disruption)}
            onCreate={handleCreate}
            onAnalyze={handleAnalyze}
          />
          <PipelineResult result={result} disruption={disruption} />
        </div>

        <Approvals items={approvals} onDecide={handleDecide} />
        <Alerts items={alerts} onAck={handleAck} />
        <AuditTrail items={audit} />
      </main>
    </div>
  );
}
