import {
  AlertTriangle,
  BarChart3,
  CalendarDays,
  CheckCircle2,
  LineChart,
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

function App() {
  const [months, setMonths] = useState<MonthOption[]>([]);
  const [levels, setLevels] = useState<RiskLevelDefinition[]>([]);
  const [questionnaireAvailable, setQuestionnaireAvailable] = useState(false);
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
      document.getElementById("report")?.scrollIntoView?.({ behavior: motion, block: "start" });
    }, 100);
    return () => window.clearTimeout(timer);
  }, [report?.simulationId]);

  async function handleRunSimulation() {
    if (simulationMode === "questionnaire" && !questionnaireAvailable) {
      setError("Questionnaire profile input is unavailable for this deployment. Use fast select.");
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
      <header className="nativeTopBar">
        <a className="brandMark" href="#simulation" aria-label="Robin portfolio simulator">
          <img src="/robin-logo.png" alt="" />
          <span>Robin</span>
        </a>
        <nav className="topNav" aria-label="Workspace sections">
          <a href="#simulation"><SlidersHorizontal size={14} />Setup</a>
          <a href="#report"><BarChart3 size={14} />Report</a>
        </nav>
        <div className="topStatus" aria-label="Diagnostic mode">
          <CheckCircle2 size={14} />
          Historical diagnostics
        </div>
      </header>

      <section className="productIntro" aria-label="Simulator overview">
        <div>
          <span>Portfolio simulator</span>
          <h1>Egyptian market allocation review</h1>
        </div>
        <p>
          Select an investor profile and review historical portfolio behavior across the plotted window.
        </p>
      </section>

      <section className="simulatorFrame">
        <aside className="setupRail" id="simulation" aria-label="Simulation setup">
          <div className="railHeader">
            <span>Setup</span>
            <strong>{months.length > 0 ? "Ready" : "Loading"}</strong>
          </div>
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
        </aside>

        <section className="workspace" aria-label="Simulation results">
          <div className="workspaceHeader">
            <div>
              <span>Review surface</span>
              <h2>Historical diagnostics</h2>
            </div>
            <div className="workspaceMeta">
              <span><CalendarDays size={13} />{month}</span>
              <span><LineChart size={13} />{durationMonths === null ? "Max window" : `${durationMonths} month${durationMonths === 1 ? "" : "s"}`}</span>
            </div>
          </div>
          {error && <div className="errorBanner"><AlertTriangle size={16} />{error}</div>}
          <ReportView report={report} isStale={isReportStale} />
          {report?.simulatorMode === "monthly_rebalance" ? (
            <MonthlyRebalanceIntelligence report={report} isStale={isReportStale} />
          ) : (
            <PipelinePlayback report={report} isStale={isReportStale} />
          )}
        </section>
      </section>
    </main>
  );
}

export default App;
