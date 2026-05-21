import {
  AlertTriangle,
  BarChart3,
  Moon,
  Sun,
  SlidersHorizontal
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { fetchHealth, fetchMonths, fetchRiskLevels, runFastSimulation, runQuestionnaireSimulation } from "./api";
import { MonthlyRebalanceIntelligence } from "./components/MonthlyRebalanceIntelligence";
import { PipelinePlayback } from "./components/PipelinePlayback";
import { ReportView } from "./components/ReportView";
import { RunPanel } from "./components/RunPanel";
import { SimulationControls } from "./components/SimulationControls";
import { defaultQuestionnaire, defaultSimulatorMode } from "./simulationOptions";
import type {
  MonthOption,
  QuestionnaireInput,
  RiskLevel,
  RiskLevelDefinition,
  SimulationMode,
  SimulatorMode,
  SimulationReport
} from "./types";
import "./styles.css";

type ThemeMode = "light" | "dark";

function initialTheme(): ThemeMode {
  if (typeof window === "undefined") {
    return "light";
  }
  const storedTheme = window.localStorage.getItem("portfolio-simulator-theme");
  if (storedTheme === "light" || storedTheme === "dark") {
    return storedTheme;
  }
  return typeof window.matchMedia === "function" && window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function App() {
  const [months, setMonths] = useState<MonthOption[]>([]);
  const [levels, setLevels] = useState<RiskLevelDefinition[]>([]);
  const [questionnaireAvailable, setQuestionnaireAvailable] = useState(false);
  const [theme, setTheme] = useState<ThemeMode>(initialTheme);
  const [month, setMonth] = useState("2025-03");
  const [riskLevel, setRiskLevel] = useState<RiskLevel>("medium");
  const [durationMonths, setDurationMonths] = useState<number | null>(6);
  const [simulatorMode, setSimulatorMode] = useState<SimulatorMode>(defaultSimulatorMode);
  const [simulationMode, setSimulationMode] = useState<SimulationMode>("questionnaire");
  const [questionnaire, setQuestionnaire] = useState<QuestionnaireInput>(defaultQuestionnaire);
  const [lastRun, setLastRun] = useState<{ mode: SimulationMode; questionnaireKey?: string } | null>(null);
  const [report, setReport] = useState<SimulationReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const runRequestId = useRef(0);

  useEffect(() => {
    Promise.all([fetchMonths(), fetchRiskLevels(), fetchHealth()])
      .then(([monthPayload, levelPayload, healthPayload]) => {
        setMonths(monthPayload);
        setLevels(levelPayload);
        setQuestionnaireAvailable(healthPayload.questionnaireModelAvailable);
        if (!healthPayload.questionnaireModelAvailable) {
          setSimulationMode("fast");
        }
        if (monthPayload.length > 0 && !monthPayload.some((candidate) => candidate.month === month)) {
          setMonth(monthPayload[0].month);
        }
      })
      .catch((cause: Error) => {
        setSimulationMode("fast");
        setError(cause.message);
      });
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    window.localStorage.setItem("portfolio-simulator-theme", theme);
  }, [theme]);

  const questionnaireKey = useMemo(() => JSON.stringify(questionnaire), [questionnaire]);
  const isReportStale =
    !!report &&
    (report.month !== month ||
      lastRun?.mode !== simulationMode ||
      report.simulatorMode !== simulatorMode ||
      (lastRun?.mode === "fast" && report.riskLevel !== riskLevel) ||
      (lastRun?.mode === "questionnaire" && lastRun.questionnaireKey !== questionnaireKey) ||
      (report.requestedDurationMonths ?? null) !== durationMonths);

  useEffect(() => {
    if (!report) {
      return;
    }
    const prefersReducedMotion = typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const motion = prefersReducedMotion ? "auto" : "smooth";
    const timer = window.setTimeout(() => {
      const targetId = report.simulatorMode === "monthly_rebalance" ? "rebalance-timeline" : "pipeline-replay";
      document.getElementById(targetId)?.scrollIntoView({ behavior: motion, block: "start" });
    }, 120);
    return () => window.clearTimeout(timer);
  }, [report?.simulationId]);

  async function handleRunSimulation() {
    if (simulationMode === "questionnaire" && !questionnaireAvailable) {
      setError("Questionnaire inference is unavailable for this deployment. Use fast select.");
      return;
    }
    const requestId = runRequestId.current + 1;
    runRequestId.current = requestId;
    setLoading(true);
    setError(null);
    try {
      const nextReport = simulationMode === "questionnaire"
        ? await runQuestionnaireSimulation(month, questionnaire, durationMonths, simulatorMode)
        : await runFastSimulation(month, riskLevel, durationMonths, simulatorMode);
      if (requestId !== runRequestId.current) {
        return;
      }
      if (simulationMode === "questionnaire") {
        setRiskLevel(nextReport.riskLevel);
      }
      setLastRun({ mode: simulationMode, questionnaireKey: simulationMode === "questionnaire" ? questionnaireKey : undefined });
      setReport(nextReport);
    } catch (cause) {
      if (requestId === runRequestId.current) {
        setError(cause instanceof Error ? cause.message : String(cause));
      }
    } finally {
      if (requestId === runRequestId.current) {
        setLoading(false);
      }
    }
  }

  function updateQuestionnaire<K extends keyof QuestionnaireInput>(field: K, value: QuestionnaireInput[K]) {
    setQuestionnaire((current) => ({ ...current, [field]: value }));
  }

  return (
    <main className="appShell">
      <section className="workspace">
        <header className="topBar">
          <div className="brandBlock">
            <img src="/robin-logo.png" alt="Robin Solutions" />
            <div>
              <span>Robin Solutions</span>
              <h1>Egyptian Market Portfolio Optimization Simulator</h1>
              <p>Questionnaire-guided historical diagnostics.</p>
            </div>
          </div>
          <div className="headerActions">
            <nav className="topNav" aria-label="Page sections">
              <a href="#simulation"><SlidersHorizontal size={16} />Simulation</a>
              <a href="#report"><BarChart3 size={16} />Report</a>
            </nav>
            <button
              type="button"
              className="themeToggle"
              aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
              aria-pressed={theme === "dark"}
              onClick={() => setTheme((current) => (current === "dark" ? "light" : "dark"))}
            >
              {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
              <span>{theme === "dark" ? "Light" : "Dark"}</span>
            </button>
            {/* <div className="statusPill"><CheckCircle2 size={16} />Historical diagnostics</div> */}
          </div>
        </header>

        <section className="simulationConsole" id="simulation">
          <SimulationControls
            levels={levels}
            mode={simulationMode}
            riskLevel={riskLevel}
            questionnaire={questionnaire}
            questionnaireAvailable={questionnaireAvailable}
            onModeChange={setSimulationMode}
            onRiskLevelChange={setRiskLevel}
            onQuestionnaireChange={updateQuestionnaire}
          />
          <RunPanel
            months={months}
            levels={levels}
            mode={simulationMode}
            month={month}
            riskLevel={riskLevel}
            simulatorMode={simulatorMode}
            durationMonths={durationMonths}
            report={report}
            lastRunMode={lastRun?.mode ?? null}
            loading={loading}
            onMonthChange={setMonth}
            onSimulatorModeChange={setSimulatorMode}
            onDurationChange={setDurationMonths}
            onRun={handleRunSimulation}
          />
        </section>

        {error && <div className="errorBanner"><AlertTriangle size={18} />{error}</div>}
        {report?.simulatorMode === "monthly_rebalance" ? (
          <MonthlyRebalanceIntelligence report={report} isStale={isReportStale} />
        ) : (
          <PipelinePlayback report={report} isStale={isReportStale} />
        )}
        <ReportView report={report} isStale={isReportStale} />
      </section>
    </main>
  );
}

export default App;
