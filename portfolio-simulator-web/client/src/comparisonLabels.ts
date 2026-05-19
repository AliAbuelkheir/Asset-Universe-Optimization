import type { ComparisonRow } from "./types";

export const comparisonLabels: Record<ComparisonRow["id"], string> = {
  optimizedPortfolio: "Optimized portfolio",
  assignedRiskBucket: "Equal-weight selected assets",
  optimizedRawUniverse: "Full-universe optimized",
  egx30: "EGX30"
};

export function displayComparisonLabel(row: ComparisonRow) {
  return comparisonLabels[row.id] || row.label;
}
