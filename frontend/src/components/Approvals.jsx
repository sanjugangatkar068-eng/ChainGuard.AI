export default function Approvals({ items, onDecide }) {
  return (
    <section className="card">
      <h2>3 · Human-in-the-loop approvals</h2>
      {items.length === 0 ? (
        <p className="empty">No approvals yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Analysis</th>
              <th>Status</th>
              <th>Reviewer</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {items.map((approval) => (
              <tr key={approval.id}>
                <td>{approval.id}</td>
                <td>#{approval.analysis_id}</td>
                <td>
                  <span className={`pill ${approval.status}`}>
                    {approval.status}
                  </span>
                </td>
                <td>{approval.reviewer || "—"}</td>
                <td>
                  {approval.status === "pending" ? (
                    <>
                      <button
                        type="button"
                        className="ghost"
                        onClick={() => onDecide(approval.id, "approve")}
                      >
                        Approve
                      </button>
                      <button
                        type="button"
                        className="ghost"
                        onClick={() => onDecide(approval.id, "reject")}
                      >
                        Reject
                      </button>
                    </>
                  ) : (
                    <span className="muted">decided</span>
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
