import {
  AlertTriangle,
  BarChart3,
  CalendarDays,
  CheckCircle2,
  LineChart,
  LoaderCircle,
  SlidersHorizontal,
  UserRoundCheck
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { fetchHealth, fetchMonths, fetchRiskLevels, runFastSimulation, runQuestionnaireSimulation } from "./api";
import { MonthlyRebalanceIntelligence } from "./components/MonthlyRebalanceIntelligence";
import { PipelinePlayback } from "./components/PipelinePlayback";
import { QuestionnaireForm } from "./components/QuestionnaireForm";
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

type WorkspaceView = "questionnaire" | "report";
const minimumLoadingMs = 2000;

function WorkspaceLoading({ mode }: { mode: SimulationMode }) {
  return (
    <section className="workspaceLoading t-panel-slide" data-open="true" aria-label="Running simulation" aria-live="polite">
      <div className="workspaceSpinner" aria-hidden="true">
        <LoaderCircle size={28} />
      </div>
      <h2>Running historical simulation</h2>
      <p>
        {mode === "questionnaire"
          ? "Inferring the investor profile and preparing diagnostics."
          : "Applying the selected risk profile and preparing diagnostics."}
      </p>
    </section>
  );
}

function App() {
  const [months, setMonths] = useState<MonthOption[]>([]);
  const [levels, setLevels] = useState<RiskLevelDefinition[]>([]);
  const [questionnaireAvailable, setQuestionnaireAvailable] = useState(false);
  const [initializing, setInitializing] = useState(true);
  const [month, setMonth] = useState("2025-03");
  const [riskLevel, setRiskLevel] = useState<RiskLevel>("medium");
  const [durationMonths, setDurationMonths] = useState<number | null>(6);
  const [simulatorMode, setSimulatorMode] = useState<SimulatorMode>(defaultSimulatorMode);
  const [questionnaire, setQuestionnaire] = useState<QuestionnaireInput>(defaultQuestionnaire);
  const [lastRun, setLastRun] = useState<{ mode: SimulationMode; questionnaireKey?: string } | null>(null);
  const [report, setReport] = useState<SimulationReport | null>(null);
  const [workspaceView, setWorkspaceView] = useState<WorkspaceView>("questionnaire");
  const [loadingMode, setLoadingMode] = useState<SimulationMode | null>(null);
  const [error, setError] = useState<string | null>(null);
  const runRequestId = useRef(0);
  const questionnaireScrollTimer = useRef<number | null>(null);

  useEffect(() => {
    Promise.all([fetchMonths(), fetchRiskLevels(), fetchHealth()])
      .then(([monthPayload, levelPayload, healthPayload]) => {
        setMonths(monthPayload);
        setLevels(levelPayload);
        setQuestionnaireAvailable(healthPayload.questionnaireModelAvailable);
        if (monthPayload.length > 0 && !monthPayload.some((candidate) => candidate.month === month)) {
          setMonth(monthPayload[0].month);
        }
      })
      .catch((cause: Error) => {
        setError(cause.message);
      })
      .finally(() => setInitializing(false));
  }, []);

  const questionnaireKey = useMemo(() => JSON.stringify(questionnaire), [questionnaire]);
  const isReportStale =
    !!report &&
    (report.month !== month ||
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

  useEffect(() => {
    return () => {
      if (questionnaireScrollTimer.current !== null) {
        window.clearTimeout(questionnaireScrollTimer.current);
      }
    };
  }, []);

  async function handleRunSimulation(mode: SimulationMode) {
    if (mode === "questionnaire" && !questionnaireAvailable) {
      setError("Questionnaire profile input is unavailable for this deployment. Use fast select.");
      return;
    }
    const requestId = runRequestId.current + 1;
    runRequestId.current = requestId;
    setLoadingMode(mode);
    setError(null);
    try {
      const reportRequest = mode === "questionnaire"
        ? runQuestionnaireSimulation(month, questionnaire, durationMonths, simulatorMode)
        : runFastSimulation(month, riskLevel, durationMonths, simulatorMode);
      const [nextReport] = await Promise.all([
        Promise.resolve(reportRequest),
        new Promise<void>((resolve) => window.setTimeout(resolve, minimumLoadingMs))
      ]);
      if (requestId !== runRequestId.current) {
        return;
      }
      if (mode === "questionnaire") {
        setRiskLevel(nextReport.riskLevel);
      }
      setLastRun({ mode, questionnaireKey: mode === "questionnaire" ? questionnaireKey : undefined });
      setReport(nextReport);
      setWorkspaceView("report");
    } catch (cause) {
      if (requestId === runRequestId.current) {
        setError(cause instanceof Error ? cause.message : String(cause));
      }
    } finally {
      if (requestId === runRequestId.current) {
        setLoadingMode(null);
      }
    }
  }

  function updateQuestionnaire<K extends keyof QuestionnaireInput>(field: K, value: QuestionnaireInput[K]) {
    setQuestionnaire((current) => ({ ...current, [field]: value }));
  }

  function showQuestionnaire() {
    setError(null);
    setWorkspaceView("questionnaire");
    const prefersReducedMotion = typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const motion = prefersReducedMotion ? "auto" : "smooth";
    if (questionnaireScrollTimer.current !== null) {
      window.clearTimeout(questionnaireScrollTimer.current);
    }
    questionnaireScrollTimer.current = window.setTimeout(() => {
      questionnaireScrollTimer.current = null;
      document.getElementById("questionnaire")?.scrollIntoView?.({ behavior: motion, block: "start" });
    }, 100);
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
          <a href={workspaceView === "report" ? "#report" : "#questionnaire"}>
            {workspaceView === "report" ? <BarChart3 size={14} /> : <UserRoundCheck size={14} />}
            {workspaceView === "report" ? "Report" : "Questionnaire"}
          </a>
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
        {workspaceView === "report" && report && loadingMode === null ? (
          <button className="newQuestionnaireButton" type="button" onClick={showQuestionnaire}>
            <UserRoundCheck size={15} />
            New questionnaire
          </button>
        ) : (
          <p>
            Review historical portfolio diagnostics.
          </p>
        )}
      </section>

      <section className="simulatorFrame">
        <aside className="setupRail" id="simulation" aria-label="Simulation setup">
          <div className="railHeader">
            <span>Setup</span>
            <strong>{months.length > 0 ? "Ready" : "Loading"}</strong>
          </div>
          <RunPanel
            months={months}
            month={month}
            simulatorMode={simulatorMode}
            durationMonths={durationMonths}
            onMonthChange={setMonth}
            onSimulatorModeChange={setSimulatorMode}
            onDurationChange={setDurationMonths}
          />
          {workspaceView === "questionnaire" && loadingMode === null && (
            <SimulationControls
              levels={levels}
              riskLevel={riskLevel}
              loading={false}
              onRiskLevelChange={setRiskLevel}
              onRun={() => handleRunSimulation("fast")}
            />
          )}
        </aside>

        <section className="workspace" aria-label="Simulation results">
          <div className="workspaceHeader">
            <div>
              <span>{workspaceView === "report" ? "Review surface" : "Investor profile"}</span>
              <h2>{workspaceView === "report" ? "Historical diagnostics" : "Questionnaire setup"}</h2>
            </div>
            <div className="workspaceMeta">
              <span><CalendarDays size={13} />{month}</span>
              <span><LineChart size={13} />{durationMonths === null ? "Max window" : `${durationMonths} month${durationMonths === 1 ? "" : "s"}`}</span>
            </div>
          </div>
          {error && <div className="errorBanner"><AlertTriangle size={16} />{error}</div>}
          {loadingMode !== null ? (
            <WorkspaceLoading mode={loadingMode} />
          ) : workspaceView === "questionnaire" ? (
            questionnaireAvailable ? (
              <QuestionnaireForm
                questionnaire={questionnaire}
                disabled={loadingMode !== null}
                onChange={updateQuestionnaire}
                onRun={() => handleRunSimulation("questionnaire")}
              />
            ) : (
              <section className="profileUnavailable t-panel-slide" data-open="true" id="questionnaire">
                <UserRoundCheck size={28} />
                <h2>{initializing ? "Loading questionnaire" : "Questionnaire unavailable"}</h2>
                <p>
                  {initializing
                    ? "Checking whether questionnaire inference is available for this deployment."
                    : "Use fast select on the left to run a historical diagnostic."}
                </p>
              </section>
            )
          ) : (
            <>
              <ReportView report={report} isStale={isReportStale} />
              {report?.simulatorMode === "monthly_rebalance" ? (
                <MonthlyRebalanceIntelligence report={report} isStale={isReportStale} />
              ) : (
                <PipelinePlayback report={report} isStale={isReportStale} />
              )}
            </>
          )}
        </section>
      </section>
    </main>
  );
}

export default App;
