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
      { id: "optimizedPortfolio", label: "Profile optimizer portfolio", metrics },
      { id: "profileEqualWeight", label: "Profile equal weights", metrics },
      { id: "optimizerFullUniverse", label: "Full-universe optimizer benchmark", metrics },
      { id: "fullUniverseEqualWeight", label: "Full-universe equal weights", metrics },
      { id: "mvoFilteredUniverse", label: "Profile MVO benchmark", metrics },
      { id: "mvoFullUniverse", label: "Full-universe MVO benchmark", metrics },
      { id: "egx30", label: "EGX30", metrics }
    ];

    expect(visibleReturnSeries(true, comparison).map((series) => series.key)).toEqual([
      "optimizedPortfolio",
      "profileEqualWeight",
      "optimizerFullUniverse",
      "fullUniverseEqualWeight",
      "mvoFilteredUniverse",
      "mvoFullUniverse",
      "egx30"
    ]);
  });

  it("does not invent default series when the API provides an empty comparison list", () => {
    expect(visibleReturnSeries(true, []).map((series) => series.key)).toEqual([]);
  });
});
