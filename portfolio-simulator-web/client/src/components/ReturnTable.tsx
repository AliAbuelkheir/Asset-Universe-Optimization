import { percent } from "../format";
import { cumulativeReturns, visibleReturnSeries, type ReturnSeriesKey } from "../returnSeries";
import type { ComparisonRow, MonthlyReturnPoint, SimulationReport } from "../types";

export function ReturnTable({
  points,
  intervals,
  comparison,
  showOptimizer
}: {
  points: MonthlyReturnPoint[];
  intervals: SimulationReport["chartIntervals"];
  comparison: ComparisonRow[];
  showOptimizer: boolean;
}) {
  const visibleSeries = visibleReturnSeries(showOptimizer, comparison);
  const cumulativeByKey = Object.fromEntries(
    visibleSeries.map((series) => [series.key, cumulativeReturns(points, series.key)])
  ) as Record<ReturnSeriesKey, Array<{ monthlyReturn: number; cumulativeReturn: number }>>;

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
                <td key={`${series.key}-${point.month}-monthly`}>{percent(point[series.key])}</td>
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
