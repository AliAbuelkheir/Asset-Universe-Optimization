import { comparisonLabels } from "./comparisonLabels";
import type { MonthlyReturnPoint } from "./types";

export const returnSeries = [
  { key: "optimizedPortfolio", label: comparisonLabels.optimizedPortfolio, color: "#2563EB" },
  { key: "optimizedRawUniverse", label: comparisonLabels.optimizedRawUniverse, color: "#F97316" },
  { key: "assignedRiskBucket", label: comparisonLabels.assignedRiskBucket, color: "#7C3AED" },
  { key: "allEqualWeight", label: comparisonLabels.allEqualWeight, color: "#64748B" },
  { key: "egx30", label: comparisonLabels.egx30, color: "#0891B2" }
] as const;

export type ReturnSeriesKey = (typeof returnSeries)[number]["key"];

export function visibleReturnSeries(showOptimizer: boolean) {
  return returnSeries.filter(
    (series) => showOptimizer || (series.key !== "optimizedPortfolio" && series.key !== "optimizedRawUniverse")
  );
}

export function cumulativeReturns(points: MonthlyReturnPoint[], key: ReturnSeriesKey) {
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
