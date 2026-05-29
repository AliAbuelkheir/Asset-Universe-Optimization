import type { ComparisonRow } from "./types";

export const comparisonLabels: Record<ComparisonRow["id"], string> = {
  optimizedPortfolio: "Profile optimizer portfolio",
  profileEqualWeight: "Profile equal weights",
  optimizerFullUniverse: "Full-universe optimizer benchmark",
  fullUniverseEqualWeight: "Full-universe equal weights",
  mvoFilteredUniverse: "Profile MVO benchmark",
  mvoFullUniverse: "Full-universe MVO benchmark",
  egx30: "EGX30"
};

export function displayComparisonLabel(row: ComparisonRow) {
  return comparisonLabels[row.id] || row.label;
}
