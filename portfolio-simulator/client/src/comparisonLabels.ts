import type { ComparisonRow } from "./types";

export const comparisonLabels: Record<ComparisonRow["id"], string> = {
  optimizedPortfolio: "Profile optimizer portfolio",
  optimizerFullUniverse: "Full-universe optimizer benchmark",
  mvoFilteredUniverse: "Profile MVO benchmark",
  mvoFullUniverse: "Full-universe MVO benchmark",
  egx30: "EGX30"
};

export function displayComparisonLabel(row: ComparisonRow) {
  return comparisonLabels[row.id] || row.label;
}
