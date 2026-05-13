import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

const monthOptions = [{ month: "2025-03", split: "test", assetCount: 36 }];
const riskLevels = [
  { id: "low", label: "Low risk", minRankPct: 0, maxRankPct: 0.4, description: "Low band" },
  { id: "medium", label: "Medium risk", minRankPct: 0.25, maxRankPct: 0.75, description: "Medium band" },
  { id: "high", label: "High risk", minRankPct: 0.6, maxRankPct: 1, description: "High band" }
];

const baseReport = {
  simulationId: "test",
  month: "2025-03",
  split: "test",
  durationMonths: 2,
  requestedDurationMonths: 3,
  chartIntervals: [
    { label: "Start", daysSincePrevious: 0 },
    { label: "2025-03", daysSincePrevious: 31 },
    { label: "2025-04", daysSincePrevious: 30 }
  ],
  thesisSafeSummary: "Historical diagnostic only.",
  optimizerMode: "external_model",
  pipeline: {
    activeUniverse: [
      {
        assetId: "ALFA",
        assetName: "Alpha Holding",
        assetGroup: "Financials",
        predictedRisk: 0.12,
        predictedRankPct: 0.1,
        selectedByFilter: false,
        equalWeight: null,
        optimizedWeight: null
      },
      {
        assetId: "BETA",
        assetName: "Beta Cement",
        assetGroup: "Materials",
        predictedRisk: 0.42,
        predictedRankPct: 0.48,
        selectedByFilter: true,
        equalWeight: 0.5,
        optimizedWeight: 0.6
      },
      {
        assetId: "GAMA",
        assetName: "Gamma Bank",
        assetGroup: "Banks",
        predictedRisk: 0.56,
        predictedRankPct: 0.64,
        selectedByFilter: true,
        equalWeight: 0.5,
        optimizedWeight: 0.4
      }
    ],
    selectedAssets: [
      {
        assetId: "BETA",
        assetName: "Beta Cement",
        assetGroup: "Materials",
        predictedRisk: 0.42,
        predictedRankPct: 0.48,
        selectedByFilter: true,
        equalWeight: 0.5,
        optimizedWeight: 0.6
      },
      {
        assetId: "GAMA",
        assetName: "Gamma Bank",
        assetGroup: "Banks",
        predictedRisk: 0.56,
        predictedRankPct: 0.64,
        selectedByFilter: true,
        equalWeight: 0.5,
        optimizedWeight: 0.4
      }
    ],
    activeUniverseCount: 3,
    selectedAssetCount: 2,
    optimizerWeightSum: 1,
    optimizerDecisionDate: "2025-03-01"
  },
  monthlyReturns: [
    { month: "2025-03", optimizedPortfolio: 0.015, optimizedRawUniverse: 0.012, assignedRiskBucket: 0.01, allEqualWeight: 0.02, egx30: 0.03 },
    { month: "2025-04", optimizedPortfolio: -0.005, optimizedRawUniverse: -0.008, assignedRiskBucket: -0.01, allEqualWeight: 0.01, egx30: 0.02 }
  ],
  comparison: [
    {
      id: "optimizedPortfolio",
      label: "Optimizer on selected risk bucket",
      metrics: {
        cumulativeReturn: 0.01,
        annualizedVolatility: 0.08,
        sharpe: 1.1,
        sortino: null,
        maxDrawdown: -0.005,
        bestMonth: 0.015,
        worstMonth: -0.005,
        ratioNotes: { sharpe: "", sortino: "n/a" }
      }
    },
    {
      id: "optimizedRawUniverse",
      label: "Optimizer on full active universe",
      metrics: {
        cumulativeReturn: 0.004,
        annualizedVolatility: 0.09,
        sharpe: 0.7,
        sortino: null,
        maxDrawdown: -0.008,
        bestMonth: 0.012,
        worstMonth: -0.008,
        ratioNotes: { sharpe: "", sortino: "n/a" }
      }
    },
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
  ]
};

const fetchMock = vi.fn((url: string) => {
  if (url.endsWith("/api/months")) {
    return Promise.resolve({ ok: true, json: () => Promise.resolve(monthOptions) });
  }
  if (url.endsWith("/api/risk-levels")) {
    return Promise.resolve({ ok: true, json: () => Promise.resolve(riskLevels) });
  }
  if (url.endsWith("/api/simulations/fast")) {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ ...baseReport, riskLevel: "low", questionnaireInference: null })
    });
  }
  if (url.endsWith("/api/simulations/questionnaire")) {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({
        ...baseReport,
        riskLevel: "medium",
        durationMonths: 1,
        requestedDurationMonths: 1,
        chartIntervals: [{ label: "Start", daysSincePrevious: 0 }, { label: "2025-03", daysSincePrevious: 31 }],
        monthlyReturns: [baseReport.monthlyReturns[0]],
        comparison: [],
        questionnaireInference: {
          riskClass: 1,
          riskLabel: "Moderate",
          riskLevel: "medium",
          probabilities: { Conservative: 0.1, Moderate: 0.8, Aggressive: 0.1 },
          riskScore: 10
        }
      })
    });
  }
  return Promise.resolve({ ok: false, json: () => Promise.resolve({ error: "unknown" }) });
}) as unknown as typeof fetch;

vi.stubGlobal("fetch", fetchMock);

describe("App", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the simulation workflow", async () => {
    render(<App />);
    expect(await screen.findByText("Egypt Risk-Bucket Historical Simulator")).toBeInTheDocument();
    expect(screen.getByText("Choose simulation mode")).toBeInTheDocument();
    expect(screen.getAllByText("Questionnaire").length).toBeGreaterThan(0);
    expect(screen.getByText("Fast select")).toBeInTheDocument();
    expect(screen.getByText("Run simulation")).toBeInTheDocument();
  });

  it("runs fast mode and renders only public report fields", async () => {
    render(<App />);
    fireEvent.click(await screen.findByText("Fast select"));
    fireEvent.click(await screen.findByText("Low"));
    fireEvent.click(screen.getByText("Run simulation"));

    expect(await screen.findByText("Simulation report")).toBeInTheDocument();
    expect(screen.getByText("Pipeline replay")).toBeInTheDocument();
    expect(screen.getByText("Asset universe selection")).toBeInTheDocument();
    expect(screen.getByText("Final selected-asset weights")).toBeInTheDocument();
    expect(screen.getAllByText("Full pipeline: PPO-filtered assets + optimizer weights").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Skip asset filter: all active assets + optimizer weights").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Skip weight optimizer: PPO-filtered assets + equal weights").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Skip asset filter and optimizer: all active assets + equal weights").length).toBeGreaterThan(0);
    expect(screen.getByText("Cumulative return comparison")).toBeInTheDocument();
    expect(screen.queryByText("Component-risk separation across the test period")).not.toBeInTheDocument();
    expect(screen.queryByText("Asset-universe filter impact")).not.toBeInTheDocument();
    expect(screen.queryByText("Relative risk-rank components at decision month")).not.toBeInTheDocument();
    expect(screen.queryByText("Selection rank")).not.toBeInTheDocument();
    expect(screen.queryByText("Predicted risk")).not.toBeInTheDocument();
  });

  it("runs questionnaire simulation and displays inferred label", async () => {
    render(<App />);
    fireEvent.click(await screen.findByText("Run simulation"));

    expect(await screen.findByText("Moderate questionnaire")).toBeInTheDocument();
    expect(screen.getAllByText("Medium").length).toBeGreaterThan(0);
  });

  it("lets the age input be cleared before entering a new value", async () => {
    render(<App />);
    const ageInput = await screen.findByLabelText("How old is the investor?");

    fireEvent.change(ageInput, { target: { value: "" } });
    expect(ageInput).toHaveValue(null);

    fireEvent.change(ageInput, { target: { value: "42" } });
    expect(ageInput).toHaveValue(42);
  });

  it("marks a report stale when controls change after a run", async () => {
    render(<App />);
    fireEvent.click(await screen.findByText("Run simulation"));
    expect(await screen.findByText("Moderate questionnaire")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Fast select"));
    expect(screen.getByText("Controls changed after this report was generated. Run the simulation again to refresh the dashboard.")).toBeInTheDocument();
  });
});
