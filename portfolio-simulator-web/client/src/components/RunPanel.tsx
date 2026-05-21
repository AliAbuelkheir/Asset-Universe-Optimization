import { Play } from "lucide-react";
import { labelRisk } from "../format";
import { durationOptions, simulatorModeOptions } from "../simulationOptions";
import type {
  MonthOption,
  RiskLevel,
  RiskLevelDefinition,
  SimulationMode,
  SimulatorMode,
  SimulationReport
} from "../types";

interface RunPanelProps {
  months: MonthOption[];
  levels: RiskLevelDefinition[];
  mode: SimulationMode;
  month: string;
  riskLevel: RiskLevel;
  simulatorMode: SimulatorMode;
  durationMonths: number | null;
  report: SimulationReport | null;
  lastRunMode: SimulationMode | null;
  loading: boolean;
  onMonthChange: (month: string) => void;
  onSimulatorModeChange: (simulatorMode: SimulatorMode) => void;
  onDurationChange: (duration: number | null) => void;
  onRun: () => void;
}

export function RunPanel({
  months,
  levels,
  mode,
  month,
  riskLevel,
  simulatorMode,
  durationMonths,
  report,
  lastRunMode,
  loading,
  onMonthChange,
  onSimulatorModeChange,
  onDurationChange,
  onRun
}: RunPanelProps) {
  const selectedMonth = months.find((candidate) => candidate.month === month);
  const splitLabel = selectedMonth?.split === "validation" ? "Validation diagnostic" : "Test diagnostic";
  const durationRequestLabel = durationMonths === null
    ? "max available"
    : `${durationMonths} month${durationMonths === 1 ? "" : "s"}`;

  return (
    <aside className="runPanel">
      <h2>Run configuration</h2>
      <div className="runSummary">
        <span>Mode</span>
        <strong>{mode === "questionnaire" ? "Questionnaire" : "Fast select"}</strong>
      </div>
      <label>
        <span>Month</span>
        <select value={month} onChange={(event) => onMonthChange(event.target.value)}>
          {months.map((candidate) => (
            <option value={candidate.month} key={candidate.month}>
              {candidate.month} - {candidate.split} - {candidate.assetCount} assets
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>Duration</span>
        <select
          value={durationMonths ?? "max"}
          onChange={(event) => onDurationChange(event.target.value === "max" ? null : Number(event.target.value))}
        >
          {durationOptions.map((option) => (
            <option value={option.value ?? "max"} key={option.label}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
      {simulatorModeOptions.length > 1 && (
        <div className="runPanelGroup">
          <span>Simulator type</span>
          <div className="simulatorModeToggle" role="group" aria-label="Simulator type">
            {simulatorModeOptions.map((option) => (
              <button
                key={option.value}
                type="button"
                className={simulatorMode === option.value ? "selected" : ""}
                aria-pressed={simulatorMode === option.value}
                onClick={() => onSimulatorModeChange(option.value)}
              >
                <strong>{option.label}</strong>
                <small>{option.description}</small>
              </button>
            ))}
          </div>
        </div>
      )}
      <div className="riskPreview">
        <span>{mode === "questionnaire" ? "Estimated risk level" : "Selected risk level"}</span>
        <strong>
          {mode === "questionnaire" && report?.questionnaireInference && lastRunMode === "questionnaire"
            ? report.questionnaireInference.riskLabel
            : mode === "questionnaire"
              ? "Pending"
              : labelRisk(riskLevel)}
        </strong>
        <p>
          {mode === "questionnaire"
            ? "Questionnaire risk is confirmed when the simulation runs."
            : levels.find((level) => level.id === riskLevel)?.label ?? "Manual risk band"}
        </p>
      </div>
      <button className="primaryButton" type="button" onClick={onRun} disabled={loading || months.length === 0}>
        <Play size={18} />{loading ? "Running..." : "Run simulation"}
      </button>
      <p className="runNote">
        {selectedMonth
          ? `${splitLabel}: ${selectedMonth.assetCount} active assets, ${durationRequestLabel} requested.`
          : "Loading months."}
      </p>
    </aside>
  );
}
