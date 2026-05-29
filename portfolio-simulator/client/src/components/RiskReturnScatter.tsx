import { displayComparisonLabel } from "../comparisonLabels";
import { percent } from "../format";
import type { ComparisonRow } from "../types";
import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis
} from "recharts";

const COLORS: Record<string, string> = {
  optimizedPortfolio: "#31f30a",
  profileEqualWeight: "#0ea5e9",
  optimizerFullUniverse: "#159947",
  fullUniverseEqualWeight: "#f59e0b",
  mvoFilteredUniverse: "#292929",
  mvoFullUniverse: "#7f7f7f",
  egx30: "#b8b8b8"
};

export function RiskReturnScatter({ rows }: { rows: ComparisonRow[] }) {
  if (rows.length === 0) {
    return null;
  }
  const data = rows.map((row) => ({
    id: row.id,
    label: displayComparisonLabel(row),
    volatility: row.metrics.annualizedVolatility,
    cumulativeReturn: row.metrics.cumulativeReturn,
    color: COLORS[row.id] ?? "var(--ink)"
  }));

  return (
    <div className="scatterWrap" aria-label="Risk return diagnostic chart">
      <div className="rechartFrame">
        <ResponsiveContainer width="100%" height={260}>
          <ScatterChart margin={{ top: 16, right: 22, bottom: 32, left: 16 }}>
            <CartesianGrid stroke="var(--chart-grid)" />
            <XAxis
              type="number"
              dataKey="volatility"
              name="Annualized volatility"
              tickFormatter={(value) => percent(Number(value), 0)}
              tick={{ fill: "var(--chart-tick)", fontSize: 12, fontWeight: 600 }}
              tickLine={false}
              axisLine={{ stroke: "var(--chart-axis)" }}
            />
            <YAxis
              type="number"
              dataKey="cumulativeReturn"
              name="Cumulative return"
              tickFormatter={(value) => percent(Number(value), 0)}
              tick={{ fill: "var(--chart-tick)", fontSize: 12, fontWeight: 600 }}
              tickLine={false}
              axisLine={{ stroke: "var(--chart-axis)" }}
              width={52}
            />
            <ZAxis range={[42, 42]} />
            <Tooltip
              cursor={{ strokeDasharray: "4 4" }}
              formatter={(value, name) => [percent(Number(value)), name]}
              labelFormatter={(_, payload) => payload?.[0]?.payload?.label ?? ""}
              contentStyle={{
                borderRadius: 8,
                borderColor: "var(--tooltip-border)",
                background: "var(--tooltip-bg)",
                color: "var(--ink)"
              }}
            />
            {data.map((point) => (
              <Scatter
                key={point.id}
                name={point.label}
                data={[point]}
                fill={point.color}
                shape="circle"
              />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <div className="legend" aria-label="Risk return chart legend">
        {rows.map((row) => (
          <span key={row.id}>
            <i style={{ background: COLORS[row.id] ?? "var(--ink)" }} />
            {displayComparisonLabel(row)}
          </span>
        ))}
      </div>
      <p className="chartHint">Upper-left indicates higher realized return with lower volatility in this diagnostic.</p>
    </div>
  );
}
