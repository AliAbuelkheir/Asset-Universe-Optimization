import { comparisonLabels, displayComparisonLabel } from "./comparisonLabels";
import type { ComparisonRow, MonthlyReturnPoint } from "./types";

export const returnSeries = [
  { key: "optimizedPortfolio", label: comparisonLabels.optimizedPortfolio, color: "#31f30a" },
  { key: "profileEqualWeight", label: comparisonLabels.profileEqualWeight, color: "#0ea5e9" },
  { key: "optimizerFullUniverse", label: comparisonLabels.optimizerFullUniverse, color: "#159947" },
  { key: "fullUniverseEqualWeight", label: comparisonLabels.fullUniverseEqualWeight, color: "#f59e0b" },
  { key: "mvoFilteredUniverse", label: comparisonLabels.mvoFilteredUniverse, color: "#292929" },
  { key: "mvoFullUniverse", label: comparisonLabels.mvoFullUniverse, color: "#7f7f7f" },
  { key: "egx30", label: comparisonLabels.egx30, color: "#b8b8b8" }
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
    (series) => showOptimizer || (series.key !== "optimizedPortfolio" && series.key !== "optimizerFullUniverse")
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
