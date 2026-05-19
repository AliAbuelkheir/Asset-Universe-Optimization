import { percent } from "../format";
import { cumulativeReturns, visibleReturnSeries, type ReturnSeriesKey } from "../returnSeries";
import type { ComparisonRow, MonthlyReturnPoint, SimulationReport } from "../types";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

type ChartRow = Record<string, string | number>;
type TooltipPayload = Array<{
  color?: string;
  dataKey?: string | number;
  name?: string | number;
  value?: string | number;
  payload?: ChartRow;
}>;

function chartClickMonth(state: unknown) {
  if (!state || typeof state !== "object" || !("activeLabel" in state)) {
    return null;
  }
  const activeLabel = (state as { activeLabel?: string | number }).activeLabel;
  if (!activeLabel || activeLabel === "Start") {
    return null;
  }
  return String(activeLabel);
}

function ReturnTooltip({
  active,
  payload,
  label
}: {
  active?: boolean;
  payload?: TooltipPayload;
  label?: string | number;
}) {
  if (!active || !payload?.length) {
    return null;
  }

  const row = payload[0]?.payload;
  const interval = row?.interval ? String(row.interval) : "";

  return (
    <div className="returnTooltip">
      <strong>{label}</strong>
      {interval && <span>{interval}</span>}
      <div>
        {payload.map((item) => {
          const key = String(item.dataKey ?? "") as ReturnSeriesKey;
          const monthly = Number(row?.[`${key}Monthly`] ?? 0);
          return (
            <p key={key}>
              <i style={{ background: item.color }} />
              <span>{item.name}</span>
              <b>{percent(Number(item.value ?? 0))}</b>
              <em>{percent(monthly)} month</em>
            </p>
          );
        })}
      </div>
    </div>
  );
}

export function ReturnChart({
  points,
  intervals,
  comparison,
  showOptimizer,
  selectedMonth,
  onMonthSelect,
  height = 320,
  showLegend = true,
  interactive = false
}: {
  points: MonthlyReturnPoint[];
  intervals: SimulationReport["chartIntervals"];
  comparison: ComparisonRow[];
  showOptimizer: boolean;
  selectedMonth?: string | null;
  onMonthSelect?: (month: string) => void;
  height?: number;
  showLegend?: boolean;
  interactive?: boolean;
}) {
  const visibleSeries = visibleReturnSeries(showOptimizer, comparison);
  const labels = intervals.length > 0 ? intervals : [{ label: "Start", daysSincePrevious: 0 }];
  const seriesValues = visibleSeries.map((series) => ({
    ...series,
    values: [0, ...cumulativeReturns(points, series.key).map((point) => point.cumulativeReturn)],
    monthlyValues: [0, ...points.map((point) => Number(point[series.key] ?? 0))]
  }));
  const values = seriesValues.flatMap((series) => series.values);
  const min = Math.min(-0.05, ...values);
  const max = Math.max(0.05, ...values);
  const data = labels.map((item, index) => {
    const row: ChartRow = {
      label: index === 0 ? "Start" : item.label,
      interval: index === 0 ? "0 days" : `${item.daysSincePrevious} days`
    };
    seriesValues.forEach((series) => {
      row[series.key] = series.values[index] ?? 0;
      row[`${series.key}Monthly`] = series.monthlyValues[index] ?? 0;
    });
    return row;
  });
  const selectedRow = selectedMonth ? data.find((row) => row.label === selectedMonth) : undefined;

  return (
    <div className={interactive ? "chartWrap interactive" : "chartWrap"} aria-label="Cumulative return comparison chart">
      <div className="rechartFrame">
        <ResponsiveContainer width="100%" height={height}>
          <LineChart
            data={data}
            margin={{ top: 18, right: 26, bottom: 44, left: 18 }}
            onClick={(state) => {
              const month = chartClickMonth(state);
              if (month) {
                onMonthSelect?.(month);
              }
            }}
          >
            <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
            <XAxis
              dataKey="label"
              tick={{ fill: "var(--chart-tick)", fontSize: 12, fontWeight: 600 }}
              tickLine={false}
              axisLine={{ stroke: "var(--chart-axis)" }}
              interval="preserveStartEnd"
            />
            <YAxis
              domain={[min, max]}
              tickFormatter={(value) => percent(Number(value), 0)}
              tick={{ fill: "var(--chart-tick)", fontSize: 12, fontWeight: 600 }}
              tickLine={false}
              axisLine={{ stroke: "var(--chart-axis)" }}
              width={52}
            />
            <Tooltip
              content={<ReturnTooltip />}
            />
            {selectedMonth && selectedRow && (
              <ReferenceLine
                x={selectedMonth}
                stroke="var(--chart-axis)"
                strokeDasharray="4 4"
                ifOverflow="extendDomain"
              />
            )}
            {visibleSeries.map((series) => {
              const isPrimaryPipeline = series.key === "optimizedPortfolio";
              return (
              <Line
                key={series.key}
                type="monotone"
                dataKey={series.key}
                name={series.label}
                stroke={series.color}
                strokeWidth={isPrimaryPipeline ? 4 : 3}
                strokeDasharray={isPrimaryPipeline ? undefined : "7 7"}
                dot={interactive ? { r: isPrimaryPipeline ? 3 : 2.5, strokeWidth: 2, fill: "var(--surface)" } : false}
                activeDot={{ r: 5 }}
              />
              );
            })}
            {selectedMonth && selectedRow && seriesValues.map((series) => (
              <ReferenceDot
                key={`${series.key}-${selectedMonth}`}
                x={selectedMonth}
                y={Number(selectedRow[series.key] ?? 0)}
                r={series.key === "optimizedPortfolio" ? 7 : 4.5}
                fill="var(--surface)"
                stroke={series.color}
                strokeWidth={series.key === "optimizedPortfolio" ? 4 : 2.5}
                ifOverflow="extendDomain"
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      {showLegend && (
        <div className="legend">
          {visibleSeries.map((series) => (
            <span key={series.key}><i style={{ background: series.color }} />{series.label}</span>
          ))}
        </div>
      )}
    </div>
  );
}
