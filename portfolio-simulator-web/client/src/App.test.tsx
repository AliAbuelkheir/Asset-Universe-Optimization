import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import App from "./App";

vi.stubGlobal("fetch", vi.fn((url: string) => {
  if (url.endsWith("/api/months")) {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve([{ month: "2025-03", split: "test", assetCount: 36 }])
    });
  }
  if (url.endsWith("/api/risk-levels")) {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve([
        { id: "low", label: "Low risk", minRankPct: 0, maxRankPct: 0.4, description: "Low band" },
        { id: "medium", label: "Medium risk", minRankPct: 0.25, maxRankPct: 0.75, description: "Medium band" },
        { id: "high", label: "High risk", minRankPct: 0.6, maxRankPct: 1, description: "High band" }
      ])
    });
  }
  if (url.endsWith("/api/simulations/fast")) {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({
        simulationId: "test",
        month: "2025-03",
        riskLevel: "low",
        split: "test",
        durationMonths: 2,
        requestedDurationMonths: 3,
        chartIntervals: [
          { label: "Start", daysSincePrevious: 0 },
          { label: "2025-03", daysSincePrevious: 31 },
          { label: "2025-04", daysSincePrevious: 30 }
        ],
        thesisSafeSummary: "Historical diagnostic only.",
        optimizerMode: "mock_equal_weight",
        selectedAssets: [
          {
            assetId: "EGX30",
            assetName: "EGX30 Index",
            assetGroup: "EquityIndex",
            predictedRankPct: 0.1,
            realizedVol: 0.2,
            realizedDownsideDev: 0.3,
            realizedMaxDrawdown: 0.4
          }
        ],
        monthlyReturns: [
          { month: "2025-03", assignedRiskBucket: 0.01, allEqualWeight: 0.02, egx30: 0.03 },
          { month: "2025-04", assignedRiskBucket: -0.01, allEqualWeight: 0.01, egx30: 0.02 }
        ],
        comparison: [
          {
            id: "assignedRiskBucket",
            label: "Assigned risk bucket equal weight",
            metrics: {
              cumulativeReturn: 0,
              annualizedVolatility: 0.1,
              sharpe: null,
              sortino: null,
              maxDrawdown: -0.01,
              bestMonth: 0.01,
              worstMonth: -0.01,
              ratioNotes: { sharpe: "n/a", sortino: "n/a" }
            }
          }
        ],
        riskComponents: [
          {
            id: "assignedRiskBucket",
            label: "Assigned risk bucket equal weight",
            components: { realizedVol: 0.2, realizedDownsideDev: 0.3, realizedMaxDrawdown: 0.4 }
          }
        ],
        rawRiskComponents: [
          {
            id: "assignedRiskBucket",
            label: "Assigned risk bucket equal weight",
            components: {
              annualizedVolatility: 0.15,
              annualizedDownsideDeviation: 0.05,
              maxDrawdown: -0.04,
              observations: 20
            }
          }
        ],
        assumptions: ["Asset selection is fixed."],
        requiredExternalContracts: { riskToleranceModel: [], weightOptimizerModel: [] }
      })
    });
  }
  return Promise.resolve({ ok: false, json: () => Promise.resolve({ error: "unknown" }) });
}) as unknown as typeof fetch);

describe("App", () => {
  it("renders the fast-mode workflow", async () => {
    render(<App />);
    expect(await screen.findByText("Egypt Risk-Bucket Historical Simulator")).toBeInTheDocument();
    expect(screen.getByText("Questionnaire model")).toBeInTheDocument();
    expect(screen.getByText("Run fast simulation")).toBeInTheDocument();
  });

  it("renders public report fields without mock optimizer or predicted risk labels", async () => {
    render(<App />);
    fireEvent.click(await screen.findByText("Low"));
    fireEvent.click(screen.getByText("Run fast simulation"));

    expect(await screen.findByText("Raw realized risk diagnostics at decision month")).toBeInTheDocument();
    expect(screen.getByText("Relative risk-rank components at decision month")).toBeInTheDocument();
    expect(screen.getByText("Selection rank")).toBeInTheDocument();
    expect(screen.queryByText("Predicted risk")).not.toBeInTheDocument();
    expect(screen.queryByText("Optimizer portfolio")).not.toBeInTheDocument();
  });
});
