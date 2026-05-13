import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  SlidersHorizontal
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { fetchMonths, fetchRiskLevels, runFastSimulation, runQuestionnaireSimulation } from "./api";
import { PipelinePlayback } from "./components/PipelinePlayback";
import { ReportView } from "./components/ReportView";
import { RunPanel } from "./components/RunPanel";
import { SimulationControls } from "./components/SimulationControls";
import { defaultQuestionnaire } from "./simulationOptions";
import type {
  MonthOption,
  QuestionnaireInput,
  RiskLevel,
  RiskLevelDefinition,
  SimulationMode,
  SimulationReport
} from "./types";
import "./styles.css";

function App() {
  const [months, setMonths] = useState<MonthOption[]>([]);
  const [levels, setLevels] = useState<RiskLevelDefinition[]>([]);
  const [month, setMonth] = useState("2025-03");
  const [riskLevel, setRiskLevel] = useState<RiskLevel>("medium");
  const [durationMonths, setDurationMonths] = useState<number | null>(6);
  const [simulationMode, setSimulationMode] = useState<SimulationMode>("questionnaire");
  const [questionnaire, setQuestionnaire] = useState<QuestionnaireInput>(defaultQuestionnaire);
  const [lastRun, setLastRun] = useState<{ mode: SimulationMode; questionnaireKey?: string } | null>(null);
  const [report, setReport] = useState<SimulationReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([fetchMonths(), fetchRiskLevels()])
      .then(([monthPayload, levelPayload]) => {
        setMonths(monthPayload);
        setLevels(levelPayload);
        if (monthPayload.length > 0 && !monthPayload.some((candidate) => candidate.month === month)) {
          setMonth(monthPayload[0].month);
        }
      })
      .catch((cause: Error) => setError(cause.message));
  }, []);

  const questionnaireKey = useMemo(() => JSON.stringify(questionnaire), [questionnaire]);
  const isReportStale =
    !!report &&
    (report.month !== month ||
      lastRun?.mode !== simulationMode ||
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
      document.getElementById("pipeline-replay")?.scrollIntoView({ behavior: motion, block: "start" });
    }, 120);
    return () => window.clearTimeout(timer);
  }, [report?.simulationId]);

  async function handleRunSimulation() {
    setLoading(true);
    setError(null);
    try {
      const nextReport = simulationMode === "questionnaire"
        ? await runQuestionnaireSimulation(month, questionnaire, durationMonths)
        : await runFastSimulation(month, riskLevel, durationMonths);
      if (simulationMode === "questionnaire") {
        setRiskLevel(nextReport.riskLevel);
      }
      setLastRun({ mode: simulationMode, questionnaireKey: simulationMode === "questionnaire" ? questionnaireKey : undefined });
      setReport(nextReport);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setLoading(false);
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
              <h1>Egypt Risk-Bucket Historical Simulator</h1>
              <p>Questionnaire-guided historical diagnostics over validation and test months.</p>
            </div>
          </div>
          <div className="headerActions">
            <nav className="topNav" aria-label="Page sections">
              <a href="#simulation"><SlidersHorizontal size={16} />Simulation</a>
              <a href="#report"><BarChart3 size={16} />Report</a>
            </nav>
            <div className="statusPill"><CheckCircle2 size={16} />Historical diagnostics</div>
          </div>
        </header>

        <section className="simulationConsole" id="simulation">
          <SimulationControls
            levels={levels}
            mode={simulationMode}
            riskLevel={riskLevel}
            questionnaire={questionnaire}
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
            durationMonths={durationMonths}
            report={report}
            lastRunMode={lastRun?.mode ?? null}
            loading={loading}
            onMonthChange={setMonth}
            onDurationChange={setDurationMonths}
            onRun={handleRunSimulation}
          />
        </section>

        {error && <div className="errorBanner"><AlertTriangle size={18} />{error}</div>}
        <PipelinePlayback report={report} isStale={isReportStale} />
        <ReportView report={report} isStale={isReportStale} />
      </section>
    </main>
  );
}

export default App;
