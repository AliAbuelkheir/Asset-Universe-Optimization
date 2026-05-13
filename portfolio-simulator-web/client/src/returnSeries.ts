import type { MonthlyReturnPoint } from "./types";

export const returnSeries = [
  { key: "optimizedPortfolio", label: "Optimizer after risk filter", color: "#00A63E" },
  { key: "optimizedRawUniverse", label: "Optimizer on raw universe", color: "#FF8A00" },
  { key: "assignedRiskBucket", label: "Selected risk profile equal weight", color: "#47D16C" },
  { key: "allEqualWeight", label: "Market universe", color: "#667085" },
  { key: "egx30", label: "EGX30 index", color: "#8AA8FF" }
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
