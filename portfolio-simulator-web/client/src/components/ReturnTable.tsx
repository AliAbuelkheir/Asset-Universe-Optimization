import { percent } from "../format";
import type { MonthlyReturnPoint, SimulationReport } from "../types";

const SERIES = [
  { key: "optimizedPortfolio", label: "Optimizer" },
  { key: "assignedRiskBucket", label: "Risk bucket" },
  { key: "allEqualWeight", label: "All equal" },
  { key: "egx30", label: "EGX30" }
] as const;

type SeriesKey = (typeof SERIES)[number]["key"];

function cumulativeRows(points: MonthlyReturnPoint[], key: SeriesKey) {
  let current = 1;
  return points.map((point) => {
    const monthlyReturn = Number(point[key] ?? 0);
    current *= 1 + monthlyReturn;
    return {
      monthlyReturn,
      cumulativeReturn: current - 1
    };
  });
}

export function ReturnTable({
  points,
  intervals,
  showOptimizer
}: {
  points: MonthlyReturnPoint[];
  intervals: SimulationReport["chartIntervals"];
  showOptimizer: boolean;
}) {
  const visibleSeries = SERIES.filter((series) => showOptimizer || series.key !== "optimizedPortfolio");
  const cumulativeByKey = Object.fromEntries(
    visibleSeries.map((series) => [series.key, cumulativeRows(points, series.key)])
  ) as Record<SeriesKey, Array<{ monthlyReturn: number; cumulativeReturn: number }>>;

  return (
    <div className="tableScroller compactTable">
      <table>
        <thead>
          <tr>
            <th>Month</th>
            <th>Days since previous point</th>
            {visibleSeries.map((series) => (
              <th key={`${series.key}-monthly`}>{series.label} monthly</th>
            ))}
            {visibleSeries.map((series) => (
              <th key={`${series.key}-cumulative`}>{series.label} cumulative</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {points.map((point, index) => (
            <tr key={point.month}>
              <td>{point.month}</td>
              <td>{intervals[index + 1]?.daysSincePrevious ?? 0} days</td>
              {visibleSeries.map((series) => (
                <td key={`${series.key}-${point.month}-monthly`}>{percent(point[series.key] ?? 0)}</td>
              ))}
              {visibleSeries.map((series) => (
                <td key={`${series.key}-${point.month}-cumulative`}>
                  {percent(cumulativeByKey[series.key][index]?.cumulativeReturn ?? 0)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
