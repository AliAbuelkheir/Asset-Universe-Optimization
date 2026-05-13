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
  optimizedPortfolio: "#00A63E",
  optimizedRawUniverse: "#FF8A00",
  assignedRiskBucket: "#47D16C",
  allEqualWeight: "#667085",
  egx30: "#8AA8FF"
};

const LABELS: Record<string, string> = {
  optimizedPortfolio: "Optimizer after risk filter",
  optimizedRawUniverse: "Optimizer on raw universe",
  assignedRiskBucket: "Selected risk profile equal weight",
  allEqualWeight: "Market universe",
  egx30: "EGX30 index"
};

export function RiskReturnScatter({ rows }: { rows: ComparisonRow[] }) {
  if (rows.length === 0) {
    return null;
  }
  const data = rows.map((row) => ({
    id: row.id,
    label: LABELS[row.id] ?? row.label,
    volatility: row.metrics.annualizedVolatility,
    cumulativeReturn: row.metrics.cumulativeReturn,
    color: COLORS[row.id] ?? "#151721"
  }));

  return (
    <div className="scatterWrap" aria-label="Risk return diagnostic chart">
      <div className="rechartFrame">
        <ResponsiveContainer width="100%" height={260}>
          <ScatterChart margin={{ top: 16, right: 22, bottom: 32, left: 16 }}>
            <CartesianGrid stroke="#e5e9f7" />
            <XAxis
              type="number"
              dataKey="volatility"
              name="Annualized volatility"
              tickFormatter={(value) => percent(Number(value), 0)}
              tick={{ fill: "#555d87", fontSize: 12, fontWeight: 600 }}
              tickLine={false}
              axisLine={{ stroke: "#cdd5ef" }}
            />
            <YAxis
              type="number"
              dataKey="cumulativeReturn"
              name="Cumulative return"
              tickFormatter={(value) => percent(Number(value), 0)}
              tick={{ fill: "#555d87", fontSize: 12, fontWeight: 600 }}
              tickLine={false}
              axisLine={{ stroke: "#cdd5ef" }}
              width={52}
            />
            <ZAxis range={[42, 42]} />
            <Tooltip
              cursor={{ strokeDasharray: "4 4" }}
              formatter={(value, name) => [percent(Number(value)), name]}
              labelFormatter={(_, payload) => payload?.[0]?.payload?.label ?? ""}
              contentStyle={{ borderRadius: 8, borderColor: "#cdd5ef" }}
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
            <i style={{ background: COLORS[row.id] ?? "#151721" }} />
            {LABELS[row.id] ?? row.label}
          </span>
        ))}
      </div>
      <p className="chartHint">Upper-left is better for return per volatility; this remains a secondary diagnostic.</p>
    </div>
  );
}
