import type { ComparisonRow } from "./types";

export const comparisonLabels: Record<ComparisonRow["id"], string> = {
  optimizedPortfolio: "Selected bucket + external weights",
  assignedRiskBucket: "Equal-weight selected assets",
  mvoFullUniverse: "Full-universe MVO",
  egx30: "EGX30"
};

export function displayComparisonLabel(row: ComparisonRow) {
  return comparisonLabels[row.id] || row.label;
}
