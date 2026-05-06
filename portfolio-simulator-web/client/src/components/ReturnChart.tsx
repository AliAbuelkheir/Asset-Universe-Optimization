import { percent } from "../format";
import type { MonthlyReturnPoint, SimulationReport } from "../types";

const SERIES = [
  { key: "optimizedPortfolio", label: "Optimizer", color: "#0f766e" },
  { key: "assignedRiskBucket", label: "Risk bucket", color: "#d97706" },
  { key: "allEqualWeight", label: "All equal", color: "#475569" },
  { key: "egx30", label: "EGX30", color: "#2563eb" }
] as const;

type SeriesKey = (typeof SERIES)[number]["key"];

function cumulative(values: number[]) {
  let current = 1;
  const curve = [0];
  values.forEach((value) => {
    current *= 1 + value;
    curve.push(current - 1);
  });
  return curve;
}

export function ReturnChart({
  points,
  intervals,
  showOptimizer
}: {
  points: MonthlyReturnPoint[];
  intervals: SimulationReport["chartIntervals"];
  showOptimizer: boolean;
}) {
  const width = 860;
  const height = 330;
  const padding = { top: 22, right: 24, bottom: 104, left: 58 };
  const visibleSeries = SERIES.filter((series) => showOptimizer || series.key !== "optimizedPortfolio");
  const allSeries = visibleSeries.map((series) => ({
    ...series,
    values: cumulative(points.map((point) => Number(point[series.key as SeriesKey] ?? 0)))
  }));
  const values = allSeries.flatMap((series) => series.values);
  const min = Math.min(-0.05, ...values);
  const max = Math.max(0.05, ...values);
  const span = max - min || 1;
  const pointCount = points.length + 1;
  const xStep = pointCount > 1 ? (width - padding.left - padding.right) / (pointCount - 1) : 0;

  const toY = (value: number) =>
    height - padding.bottom - ((value - min) / span) * (height - padding.top - padding.bottom);
  const toX = (index: number) => padding.left + index * xStep;
  const yTicks = [min, min + span / 2, max];
  const labels = intervals.length > 0 ? intervals : [{ label: "Start", daysSincePrevious: 0 }];
  const labelStep = labels.length > 8 ? Math.ceil(labels.length / 8) : 1;

  return (
    <div className="chartWrap" aria-label="Cumulative return comparison chart">
      <svg viewBox={`0 0 ${width} ${height}`} role="img">
        <text x={16} y={height / 2} className="axisTitle" transform={`rotate(-90 16 ${height / 2})`}>
          Cumulative return
        </text>
        <text x={width / 2} y={height - 22} className="axisTitle" textAnchor="middle">
          Simulation month and days since previous point
        </text>
        <line x1={padding.left} x2={width - padding.right} y1={toY(0)} y2={toY(0)} className="axisLine" />
        {[0, 0.25, 0.5, 0.75, 1].map((ratio) => (
          <line
            key={ratio}
            x1={padding.left}
            x2={width - padding.right}
            y1={padding.top + ratio * (height - padding.top - padding.bottom)}
            y2={padding.top + ratio * (height - padding.top - padding.bottom)}
            className="gridLine"
          />
        ))}
        {yTicks.map((tick) => (
          <text key={tick} x={padding.left - 8} y={toY(tick) + 4} className="tickLabel" textAnchor="end">
            {percent(tick, 0)}
          </text>
        ))}
        {labels.map((item, index) => (
          <g key={`${item.label}-${index}`}>
            <line x1={toX(index)} x2={toX(index)} y1={height - padding.bottom} y2={height - padding.bottom + 5} className="axisLine" />
            {(index === 0 || index === labels.length - 1 || index % labelStep === 0) && (
              <>
                <text x={toX(index)} y={height - padding.bottom + 19} className="tickLabel" textAnchor="middle">
                  {item.label}
                </text>
                <text x={toX(index)} y={height - padding.bottom + 34} className="intervalLabel" textAnchor="middle">
                  {index === 0 ? "0 days" : `${item.daysSincePrevious} days`}
                </text>
              </>
            )}
          </g>
        ))}
        {allSeries.map((series) => {
          const path = series.values
            .map((value, index) => `${index === 0 ? "M" : "L"} ${toX(index)} ${toY(value)}`)
            .join(" ");
          return <path key={series.key} d={path} fill="none" stroke={series.color} strokeWidth="3" strokeLinecap="round" />;
        })}
      </svg>
      <div className="legend">
        {visibleSeries.map((series) => (
          <span key={series.key}><i style={{ background: series.color }} />{series.label}</span>
        ))}
      </div>
      {labels.length > 8 && (
        <p className="chartHint">Some x-axis labels are hidden to prevent crowding. The monthly table below lists every plotted point.</p>
      )}
    </div>
  );
}
