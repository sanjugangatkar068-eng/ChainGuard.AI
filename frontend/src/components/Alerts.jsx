export default function Alerts({ items, onAck }) {
  return (
    <section className="card">
      <h2>4 · Escalation alerts</h2>
      {items.length === 0 ? (
        <p className="empty">No alerts yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Level</th>
              <th>Subject</th>
              <th>Channel</th>
              <th>Ack</th>
            </tr>
          </thead>
          <tbody>
            {items.map((alert) => (
              <tr key={alert.id}>
                <td>{alert.id}</td>
                <td>
                  <span className={`pill ${alert.level}`}>{alert.level}</span>
                </td>
                <td>{alert.subject}</td>
                <td>
                  {alert.channel}
                  {alert.delivered ? " ✓" : ""}
                </td>
                <td>
                  {alert.acknowledged ? (
                    <span className="muted">acked</span>
                  ) : (
                    <button
                      type="button"
                      className="ghost"
                      onClick={() => onAck(alert.id)}
                    >
                      Ack
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
