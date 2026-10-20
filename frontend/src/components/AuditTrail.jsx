const stamp = (iso) => (iso || "").replace("T", " ").slice(0, 19);

export default function AuditTrail({ items }) {
  return (
    <section className="card">
      <h2>5 · Audit trail</h2>
      {items.length === 0 ? (
        <p className="empty">No events yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Event</th>
              <th>Actor</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {items.map((entry) => (
              <tr key={entry.id}>
                <td className="muted">{stamp(entry.created_at)}</td>
                <td>{entry.event_type}</td>
                <td>{entry.actor}</td>
                <td className="muted">{JSON.stringify(entry.details)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
