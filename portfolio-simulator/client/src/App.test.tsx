import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

const monthOptions = [{ month: "2025-03", assetCount: 36 }];
const riskLevels = [
  { id: "low", label: "Low risk", minRankPct: 0, maxRankPct: 0.4, description: "Low band" },
  { id: "medium", label: "Medium risk", minRankPct: 0.25, maxRankPct: 0.75, description: "Medium band" },
  { id: "high", label: "High risk", minRankPct: 0.6, maxRankPct: 1, description: "High band" }
];

const baseReport = {
  simulationId: "sim-fixture",
  month: "2025-03",
  simulatorMode: "single",
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
        selectedByFilter: false,
        equalWeight: null,
        optimizedWeight: null
      },
      {
        assetId: "BETA",
        assetName: "Beta Cement",
        assetGroup: "Materials",
        selectedByFilter: true,
        equalWeight: 0.5,
        optimizedWeight: 0.6
      },
      {
        assetId: "GAMA",
        assetName: "Gamma Bank",
        assetGroup: "Banks",
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
        selectedByFilter: true,
        equalWeight: 0.5,
        optimizedWeight: 0.6
      },
      {
        assetId: "GAMA",
        assetName: "Gamma Bank",
        assetGroup: "Banks",
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
  rebalanceTimeline: [
    {
      month: "2025-03",
      optimizerDecisionDate: "2025-03-01",
      startingValue: 1,
      monthlyReturn: 0.015,
      endingValue: 1.015,
      activeUniverseCount: 3,
      selectedAssetCount: 2,
      optimizerWeightSum: 1,
      selectedAssets: [
        {
          assetId: "BETA",
          assetName: "Beta Cement",
          assetGroup: "Materials",
          selectedByFilter: true,
          equalWeight: 0.5,
          optimizedWeight: 0.6
        },
        {
          assetId: "GAMA",
          assetName: "Gamma Bank",
          assetGroup: "Banks",
          selectedByFilter: true,
          equalWeight: 0.5,
          optimizedWeight: 0.4
        }
      ]
    }
  ],
  monthlyReturns: [
    {
      month: "2025-03",
      optimizedPortfolio: 0.015,
      profileEqualWeight: 0.013,
      optimizerFullUniverse: 0.014,
      fullUniverseEqualWeight: 0.012,
      mvoFilteredUniverse: 0.011,
      mvoFullUniverse: 0.012,
      egx30: 0.03
    },
    {
      month: "2025-04",
      optimizedPortfolio: -0.005,
      profileEqualWeight: -0.004,
      optimizerFullUniverse: -0.006,
      fullUniverseEqualWeight: -0.007,
      mvoFilteredUniverse: -0.009,
      mvoFullUniverse: -0.008,
      egx30: 0.02
    }
  ],
  comparison: [
    {
      id: "optimizedPortfolio",
      label: "Profile optimizer portfolio",
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
      id: "profileEqualWeight",
      label: "Profile equal weights",
      metrics: {
        cumulativeReturn: 0.009,
        annualizedVolatility: 0.07,
        sharpe: 1,
        sortino: null,
        maxDrawdown: -0.004,
        bestMonth: 0.013,
        worstMonth: -0.004,
        ratioNotes: { sharpe: "", sortino: "n/a" }
      }
    },
    {
      id: "optimizerFullUniverse",
      label: "Full-universe optimizer benchmark",
      metrics: {
        cumulativeReturn: 0.008,
        annualizedVolatility: 0.085,
        sharpe: 0.9,
        sortino: null,
        maxDrawdown: -0.006,
        bestMonth: 0.014,
        worstMonth: -0.006,
        ratioNotes: { sharpe: "", sortino: "n/a" }
      }
    },
    {
      id: "fullUniverseEqualWeight",
      label: "Full-universe equal weights",
      metrics: {
        cumulativeReturn: 0.005,
        annualizedVolatility: 0.088,
        sharpe: 0.6,
        sortino: null,
        maxDrawdown: -0.007,
        bestMonth: 0.012,
        worstMonth: -0.007,
        ratioNotes: { sharpe: "", sortino: "n/a" }
      }
    },
    {
      id: "mvoFilteredUniverse",
      label: "Profile MVO benchmark",
      metrics: {
        cumulativeReturn: 0.002,
        annualizedVolatility: 0.1,
        sharpe: null,
        sortino: null,
        maxDrawdown: -0.009,
        bestMonth: 0.011,
        worstMonth: -0.009,
        ratioNotes: { sharpe: "n/a", sortino: "n/a" }
      }
    },
    {
      id: "mvoFullUniverse",
      label: "Full-universe MVO benchmark",
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
      id: "egx30",
      label: "EGX30",
      metrics: {
        cumulativeReturn: 0.05,
        annualizedVolatility: 0.12,
        sharpe: 1.3,
        sortino: null,
        maxDrawdown: 0,
        bestMonth: 0.03,
        worstMonth: 0.02,
        ratioNotes: { sharpe: "", sortino: "n/a" }
      }
    }
  ]
};

function reportForMode(simulatorMode: "single" | "monthly_rebalance") {
  const rebalanceTimeline = simulatorMode === "monthly_rebalance"
    ? [
        baseReport.rebalanceTimeline[0],
        {
          ...baseReport.rebalanceTimeline[0],
          month: "2025-04",
          optimizerDecisionDate: "2025-04-01",
          startingValue: 1.015,
          monthlyReturn: -0.005,
          endingValue: 1.009925
        }
      ]
    : baseReport.rebalanceTimeline;
  const comparison = baseReport.comparison;
  return { ...baseReport, simulatorMode, rebalanceTimeline, comparison };
}

function latestSimulationRequest() {
  const call = [...fetchMock.mock.calls].reverse().find(([url]) => String(url).includes("/api/simulations/"));
  return JSON.parse(String((call?.[1] as RequestInit | undefined)?.body ?? "{}"));
}

let questionnaireModelAvailable = true;

const fetchMock = vi.fn((url: string, init?: RequestInit) => {
  const body = init?.body ? JSON.parse(String(init.body)) : {};
  const simulatorMode = body.simulatorMode === "single" ? "single" : "monthly_rebalance";
  if (url.endsWith("/api/health")) {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({
        status: "ok",
        ppoRootExists: true,
        predictionsAvailable: true,
        dailyMarketAvailable: true,
        monthlyPanelAvailable: true,
        questionnaireModelAvailable,
        optimizerMode: "external_model",
        optimizerRuntimeAvailable: true
      })
    });
  }
  if (url.endsWith("/api/months")) {
    return Promise.resolve({ ok: true, json: () => Promise.resolve(monthOptions) });
  }
  if (url.endsWith("/api/risk-levels")) {
    return Promise.resolve({ ok: true, json: () => Promise.resolve(riskLevels) });
  }
  if (url.endsWith("/api/simulations/fast")) {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ ...reportForMode(simulatorMode), riskLevel: "low", questionnaireInference: null })
    });
  }
  if (url.endsWith("/api/simulations/questionnaire")) {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({
        ...reportForMode(simulatorMode),
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
});

vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);

async function fastRunButton() {
  const button = within(await screen.findByLabelText("Fast select input")).getByRole("button", { name: "Run" });
  await waitFor(() => expect(button).toBeEnabled());
  return button;
}

async function questionnaireRunButton() {
  return within(await screen.findByLabelText("Questionnaire input")).getByRole("button", { name: "Run" });
}

async function runSimulation(button: HTMLElement) {
  vi.useFakeTimers();
  try {
    fireEvent.click(button);
    expect(screen.getByLabelText("Running simulation")).toBeInTheDocument();
    expect(screen.queryByLabelText("Fast select")).not.toBeInTheDocument();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
  } finally {
    vi.useRealTimers();
  }
}

describe("App", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    questionnaireModelAvailable = true;
    window.localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders the simulation workflow", async () => {
    render(<App />);
    expect(await screen.findByText("Egyptian market allocation review")).toBeInTheDocument();
    expect(screen.getByText("Quick simulation")).toBeInTheDocument();
    expect(screen.getByText("Questionnaire setup")).toBeInTheDocument();
    expect(screen.getByLabelText("Questionnaire input")).toBeInTheDocument();
    expect(screen.getByText("Fast select")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Monthly review/ })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: /Opening allocation/ })).toHaveAttribute("aria-pressed", "false");
    expect(await fastRunButton()).toBeInTheDocument();
    expect(await questionnaireRunButton()).toBeInTheDocument();
  });

  it("renders the native diagnostic header", async () => {
    render(<App />);
    expect(await screen.findByLabelText("Robin portfolio simulator")).toBeInTheDocument();
    expect(screen.getAllByText("Historical diagnostics").length).toBeGreaterThan(0);
    expect(screen.queryByRole("button", { name: /Switch to dark mode/i })).not.toBeInTheDocument();
  });

  it("runs fast mode with single allocation and renders only public report fields", async () => {
    render(<App />);
    fireEvent.click(await screen.findByText("Low"));
    fireEvent.click(screen.getByRole("button", { name: /Opening allocation/ }));
    await runSimulation(await fastRunButton());

    expect(await screen.findByText("Simulation report")).toBeInTheDocument();
    expect(screen.queryByLabelText("Fast select")).not.toBeInTheDocument();
    expect(latestSimulationRequest().simulatorMode).toBe("single");
    expect(screen.getAllByText("Allocation review").length).toBeGreaterThan(0);
    expect(screen.getByText("Holdings")).toBeInTheDocument();
    expect(screen.queryByText(/Rank \d/)).not.toBeInTheDocument();
    expect(screen.getAllByText("Profile optimizer portfolio").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Profile equal weights").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Full-universe optimizer benchmark").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Full-universe equal weights").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Profile MVO benchmark").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Full-universe MVO benchmark").length).toBeGreaterThan(0);
    expect(screen.getByText("2 holdings from 3 available assets")).toBeInTheDocument();
    expect(screen.getByText("n/a ratios:")).toBeInTheDocument();
    expect(screen.getByText(/Some ratios need more return variation/)).toBeInTheDocument();
    expect(screen.getAllByText("EGX30").length).toBeGreaterThan(0);
    expect(screen.queryByText("Selected bucket + external weights")).not.toBeInTheDocument();
    expect(screen.queryByText("Equal-weight selected assets")).not.toBeInTheDocument();
    expect(screen.queryByText("Market benchmark")).not.toBeInTheDocument();
    expect(screen.queryByText("Profile benchmark")).not.toBeInTheDocument();
    expect(screen.queryByText("Full Universe with equal weights")).not.toBeInTheDocument();
    expect(screen.getByText("Cumulative return comparison")).toBeInTheDocument();
    expect(screen.queryByText("Component-risk separation across the selected period")).not.toBeInTheDocument();
    expect(screen.queryByText("Asset-universe filter impact")).not.toBeInTheDocument();
    expect(screen.queryByText(/decision date/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/PPO/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Relative risk-rank components/)).not.toBeInTheDocument();
    expect(screen.queryByText("Selection rank")).not.toBeInTheDocument();
    expect(screen.queryByText("Predicted risk")).not.toBeInTheDocument();
    expect(screen.queryByText(/external weights/i)).not.toBeInTheDocument();
  });

  it("runs fast mode with monthly rebalance by default", async () => {
    render(<App />);
    fireEvent.click(await screen.findByText("Low"));
    await runSimulation(await fastRunButton());

    expect(await screen.findByText("Monthly allocation review")).toBeInTheDocument();
    expect(latestSimulationRequest().simulatorMode).toBe("monthly_rebalance");
    expect(screen.queryByText("Pipeline replay")).not.toBeInTheDocument();
    expect(screen.queryByText("Active universe count")).not.toBeInTheDocument();
    expect(screen.getAllByText("Profile optimizer").length).toBeGreaterThan(0);
  });

  it("updates selected-month intelligence when a rebalance month is clicked", async () => {
    render(<App />);
    await runSimulation(await fastRunButton());

    const intelligence = await screen.findByLabelText("Monthly Allocation Review");
    expect(within(intelligence).getAllByText("2025-03").length).toBeGreaterThan(0);
    expect(within(intelligence).queryByText(/Decision date/i)).not.toBeInTheDocument();

    fireEvent.click(within(intelligence).getAllByRole("button", { name: /2025-04/i })[0]);

    expect(within(intelligence).getAllByText("2025-04").length).toBeGreaterThan(0);
    expect(within(intelligence).getAllByText("-0.5%").length).toBeGreaterThan(0);
  });

  it("shows selected-month allocations and benchmark deltas", async () => {
    render(<App />);
    await runSimulation(await fastRunButton());

    const intelligence = await screen.findByLabelText("Monthly Allocation Review");
    expect(within(intelligence).getByText("Benchmark delta")).toBeInTheDocument();
    expect(within(intelligence).getByText("Top allocations")).toBeInTheDocument();
    expect(within(intelligence).getAllByText("BETA").length).toBeGreaterThan(0);
    expect(within(intelligence).getByText("vs EGX30")).toBeInTheDocument();
  });

  it("runs questionnaire simulation and displays inferred label", async () => {
    render(<App />);
    await runSimulation(await questionnaireRunButton());

    expect(await screen.findByText("Moderate profile")).toBeInTheDocument();
    expect(latestSimulationRequest().simulatorMode).toBe("monthly_rebalance");
    expect(screen.queryByText("Moderate questionnaire")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Questionnaire input")).not.toBeInTheDocument();
  });

  it("lets the age input be cleared before entering a new value", async () => {
    render(<App />);
    const ageInput = await screen.findByLabelText("What is your age?");

    fireEvent.change(ageInput, { target: { value: "" } });
    expect(ageInput).toHaveValue(null);

    fireEvent.change(ageInput, { target: { value: "42" } });
    expect(ageInput).toHaveValue(42);
  });

  it("marks a report stale when controls change after a run", async () => {
    render(<App />);
    await runSimulation(await questionnaireRunButton());
    expect(await screen.findByText("Moderate profile")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Opening allocation/ }));
    expect(screen.getByText("Controls changed after this report was generated. Run the simulation again to refresh the dashboard.")).toBeInTheDocument();
  });

  it("reopens the saved questionnaire from a generated report", async () => {
    render(<App />);
    await runSimulation(await questionnaireRunButton());
    expect(await screen.findByText("Simulation report")).toBeInTheDocument();
    expect(screen.queryByLabelText("Fast select")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "New questionnaire" }));

    expect(await screen.findByLabelText("Questionnaire input")).toBeInTheDocument();
    expect(screen.getByLabelText("Fast select")).toBeInTheDocument();
    expect(screen.getByLabelText("What is your age?")).toHaveValue(29);
    expect(screen.queryByText("Simulation report")).not.toBeInTheDocument();
  });

  it("keeps fast select usable when questionnaire inference is unavailable", async () => {
    questionnaireModelAvailable = false;
    render(<App />);

    expect(await screen.findByText("Questionnaire unavailable")).toBeInTheDocument();
    await runSimulation(await fastRunButton());

    expect(await screen.findByText("Simulation report")).toBeInTheDocument();
  });

  it("renders source-backed questionnaire answers and maps grouped one-hot choices", async () => {
    render(<App />);
    expect(await screen.findByText("What is your gender?")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Female" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Male" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Locking Period" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Education" })).toBeInTheDocument();

    fireEvent.click(within(screen.getByRole("group", { name: "What is your gender?" })).getByRole("button", { name: "Female" }));
    fireEvent.click(within(screen.getByRole("group", { name: "Do you invest in the stock market?" })).getByRole("button", { name: "No" }));
    fireEvent.click(within(screen.getByRole("group", { name: "Which factor matters most when choosing an investment?" })).getByRole("button", { name: "Risk" }));
    fireEvent.click(within(screen.getByRole("group", { name: "What is the purpose of this investment?" })).getByRole("button", { name: "Returns" }));
    fireEvent.click(within(screen.getByRole("group", { name: "What are your savings objectives?" })).getByRole("button", { name: "Education" }));
    await runSimulation(await questionnaireRunButton());

    expect(latestSimulationRequest().questionnaire).toMatchObject({
      Gender_Score: 0,
      Stock_Score: 0,
      Factor_Returns: false,
      Factor_Risk: true,
      "Purpose_Savings for Future": false,
      "Purpose_Wealth Creation": false,
      "What are your savings objectives?_Health Care": false,
      "What are your savings objectives?_Retirement Plan": false
    });
  });
});
