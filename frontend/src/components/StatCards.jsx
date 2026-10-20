export default function StatCards({ stats }) {
  const cards = [
    { label: "Disruptions", value: stats.disruptions },
    { label: "Analyses", value: stats.analyses },
    { label: "Approvals", value: stats.approvals },
  ];

  return (
    <section className="card stats">
      {cards.map((card) => (
        <div key={card.label}>
          <b>{card.value}</b>
          <span>{card.label}</span>
        </div>
      ))}
    </section>
  );
}
