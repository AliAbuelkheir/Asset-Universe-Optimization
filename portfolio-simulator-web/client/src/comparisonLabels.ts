import type { ComparisonRow } from "./types";

export const comparisonLabels: Record<ComparisonRow["id"], string> = {
  optimizedPortfolio: "Filtered Universe with optimized weights",
  assignedRiskBucket: "Filtered Universe with equal weights",
  optimizedRawUniverse: "Full Universe with optimized weights",
  egx30: "EGX30"
};
