import type { ComparisonRow } from "./types";

export const comparisonLabels: Record<ComparisonRow["id"], string> = {
  optimizedPortfolio: "Full pipeline: PPO-filtered assets + optimizer weights",
  optimizedRawUniverse: "Skip asset filter: all active assets + optimizer weights",
  assignedRiskBucket: "Skip weight optimizer: PPO-filtered assets + equal weights",
  allEqualWeight: "Skip asset filter and optimizer: all active assets + equal weights",
  egx30: "EGX30 index benchmark"
};
