const RISK_COLOR = {
  low: "#34d399",
  medium: "#fbbf24",
  high: "#f87171",
  critical: "#f87171",
};

export function riskColor(level) {
  return RISK_COLOR[level] || "#38bdf8";
}

export default function BarChart({ items }) {
  if (!items || items.length === 0) return null;

  const max = Math.max(...items.map((item) => item.value), 1);
  const rowHeight = 30;
  const labelWidth = 150;
  const barWidth = 300;
  const width = labelWidth + barWidth + 120;
  const height = items.length * rowHeight + 8;

  return (
    <svg
      className="chart"
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="xMinYMin meet"
      role="img"
    >
      {items.map((item, index) => {
        const y = index * rowHeight + 8;
        const w = Math.max(2, (item.value / max) * barWidth);
        return (
          <g key={item.label}>
            <text x="0" y={y + 13} className="chart-label">
              {item.label}
            </text>
            <rect
              x={labelWidth}
              y={y + 2}
              width={w}
              height="16"
              rx="4"
              fill={item.color || "#38bdf8"}
            />
            <text x={labelWidth + w + 8} y={y + 15} className="chart-value">
              {item.sub}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
