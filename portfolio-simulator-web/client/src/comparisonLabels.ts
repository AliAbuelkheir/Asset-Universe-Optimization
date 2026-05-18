import type { ComparisonRow } from "./types";

export const comparisonLabels: Record<ComparisonRow["id"], string> = {
  optimizedPortfolio: "FULL pipeline",
  assignedRiskBucket: "Filtered universe with equal weights",
  optimizedRawUniverse: "MVO on FULL Asset universe",
  egx30: "EGX30"
};
