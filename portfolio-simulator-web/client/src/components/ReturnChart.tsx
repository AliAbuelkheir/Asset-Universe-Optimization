import { percent } from "../format";
import { cumulativeReturns, visibleReturnSeries } from "../returnSeries";
import type { MonthlyReturnPoint, SimulationReport } from "../types";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

export function ReturnChart({
  points,
  intervals,
  showOptimizer
}: {
  points: MonthlyReturnPoint[];
  intervals: SimulationReport["chartIntervals"];
  showOptimizer: boolean;
}) {
  const visibleSeries = visibleReturnSeries(showOptimizer);
  const labels = intervals.length > 0 ? intervals : [{ label: "Start", daysSincePrevious: 0 }];
  const seriesValues = visibleSeries.map((series) => ({
    ...series,
    values: [0, ...cumulativeReturns(points, series.key).map((point) => point.cumulativeReturn)]
  }));
  const values = seriesValues.flatMap((series) => series.values);
  const min = Math.min(-0.05, ...values);
  const max = Math.max(0.05, ...values);
  const data = labels.map((item, index) => {
    const row: Record<string, string | number> = {
      label: index === 0 ? "Start" : item.label,
      interval: index === 0 ? "0 days" : `${item.daysSincePrevious} days`
    };
    seriesValues.forEach((series) => {
      row[series.key] = series.values[index] ?? 0;
    });
    return row;
  });

  return (
    <div className="chartWrap" aria-label="Cumulative return comparison chart">
      <div className="rechartFrame">
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={data} margin={{ top: 18, right: 26, bottom: 44, left: 18 }}>
            <CartesianGrid stroke="#e5e9f7" vertical={false} />
            <XAxis
              dataKey="label"
              tick={{ fill: "#555d87", fontSize: 12, fontWeight: 600 }}
              tickLine={false}
              axisLine={{ stroke: "#cdd5ef" }}
              interval="preserveStartEnd"
            />
            <YAxis
              domain={[min, max]}
              tickFormatter={(value) => percent(Number(value), 0)}
              tick={{ fill: "#555d87", fontSize: 12, fontWeight: 600 }}
              tickLine={false}
              axisLine={{ stroke: "#cdd5ef" }}
              width={52}
            />
            <Tooltip
              formatter={(value) => percent(Number(value))}
              labelFormatter={(_, payload) => {
                const row = payload?.[0]?.payload as { label?: string; interval?: string } | undefined;
                return row ? `${row.label} - ${row.interval}` : "";
              }}
              contentStyle={{ borderRadius: 8, borderColor: "#cdd5ef" }}
            />
            {visibleSeries.map((series, index) => (
              <Line
                key={series.key}
                type="monotone"
                dataKey={series.key}
                name={series.label}
                stroke={series.color}
                strokeWidth={index === 0 ? 4 : 3}
                strokeDasharray={index === 0 ? undefined : "7 7"}
                dot={false}
                activeDot={{ r: 5 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="legend">
        {visibleSeries.map((series) => (
          <span key={series.key}><i style={{ background: series.color }} />{series.label}</span>
        ))}
      </div>
    </div>
  );
}
