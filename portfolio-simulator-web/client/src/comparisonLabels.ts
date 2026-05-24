import type { ComparisonRow } from "./types";

export const comparisonLabels: Record<ComparisonRow["id"], string> = {
  optimizedPortfolio: "Robin portfolio",
  assignedRiskBucket: "Profile equal-weight benchmark",
  mvoFullUniverse: "Full-universe benchmark",
  egx30: "EGX30"
};

export function displayComparisonLabel(row: ComparisonRow) {
  return comparisonLabels[row.id] || row.label;
}
