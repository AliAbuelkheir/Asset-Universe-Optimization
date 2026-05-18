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
      { id: "egx30", label: "EGX30", metrics },
      { id: "optimizedRawUniverse", label: "MVO on FULL Asset universe", metrics },
      { id: "optimizedPortfolio", label: "FULL pipeline", metrics }
    ];

    expect(visibleReturnSeries(true, comparison).map((series) => series.key)).toEqual([
      "egx30",
      "optimizedRawUniverse",
      "optimizedPortfolio"
    ]);
  });
});
