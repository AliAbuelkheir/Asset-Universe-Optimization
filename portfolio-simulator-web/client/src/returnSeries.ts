import { comparisonLabels, displayComparisonLabel } from "./comparisonLabels";
import type { ComparisonRow, MonthlyReturnPoint } from "./types";

export const returnSeries = [
  { key: "optimizedPortfolio", label: comparisonLabels.optimizedPortfolio, color: "#2563EB" },
  { key: "assignedRiskBucket", label: comparisonLabels.assignedRiskBucket, color: "#7C3AED" },
  { key: "mvoFullUniverse", label: comparisonLabels.mvoFullUniverse, color: "#F97316" },
  { key: "egx30", label: comparisonLabels.egx30, color: "#0891B2" }
] as const;

export type ReturnSeriesKey = (typeof returnSeries)[number]["key"];

export function visibleReturnSeries(showOptimizer: boolean, comparison?: ComparisonRow[]) {
  const seriesByKey = new Map(returnSeries.map((series) => [series.key, series]));
  const orderedSeries = comparison === undefined
    ? returnSeries
    : comparison.flatMap((row) => {
      const series = seriesByKey.get(row.id);
      return series ? [{ ...series, label: displayComparisonLabel(row) }] : [];
    });

  return orderedSeries.filter(
    (series) => showOptimizer || (series.key !== "optimizedPortfolio" && series.key !== "mvoFullUniverse")
  );
}

export function cumulativeReturns(points: MonthlyReturnPoint[], key: ReturnSeriesKey) {
  let current = 1;
  return points.map((point) => {
    const monthlyReturn = Number(point[key]);
    if (!Number.isFinite(monthlyReturn)) {
      throw new Error(`Missing monthly return series value for ${key} in ${point.month}.`);
    }
    current *= 1 + monthlyReturn;
    return {
      monthlyReturn,
      cumulativeReturn: current - 1
    };
  });
}
