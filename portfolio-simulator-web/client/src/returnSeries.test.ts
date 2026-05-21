import { describe, expect, it } from "vitest";
import { visibleReturnSeries } from "./returnSeries";
import type { ComparisonRow } from "./types";

const metrics: ComparisonRow["metrics"] = {
  cumulativeReturn: 0,
  annualizedVolatility: 0,
  sharpe: null,
  sortino: null,
  maxDrawdown: 0,
  bestMonth: 0,
  worstMonth: 0,
  ratioNotes: {
    sharpe: "n/a",
    sortino: "n/a"
  }
};

describe("visibleReturnSeries", () => {
  it("uses API comparison rows as the visible benchmark order", () => {
    const comparison: ComparisonRow[] = [
      { id: "optimizedPortfolio", label: "Selected bucket with external weights", metrics },
      { id: "assignedRiskBucket", label: "Filtered universe equal weight", metrics },
      { id: "mvoFullUniverse", label: "Full-universe MVO", metrics },
      { id: "egx30", label: "EGX30", metrics }
    ];

    expect(visibleReturnSeries(true, comparison).map((series) => series.key)).toEqual([
      "optimizedPortfolio",
      "assignedRiskBucket",
      "mvoFullUniverse",
      "egx30"
    ]);
  });

  it("does not invent default series when the API provides an empty comparison list", () => {
    expect(visibleReturnSeries(true, []).map((series) => series.key)).toEqual([]);
  });
});
