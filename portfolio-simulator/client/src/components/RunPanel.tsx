import { Play, RotateCw } from "lucide-react";
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
  const durationRequestLabel = durationMonths === null
    ? "Max window"
    : `${durationMonths} month${durationMonths === 1 ? "" : "s"}`;
  const profileLabel = mode === "questionnaire" && report?.questionnaireInference && lastRunMode === "questionnaire"
    ? report.questionnaireInference.riskLabel
    : mode === "questionnaire"
      ? "Pending"
      : labelRisk(riskLevel);
  const selectedLevel = levels.find((level) => level.id === riskLevel);

  return (
    <section className="runPanel">
      <div className="sectionHeading">
        <div>
          <span>Simulation</span>
          <h2>Run setup</h2>
        </div>
      </div>

      <label>
        <span>Start month</span>
        <select value={month} onChange={(event) => onMonthChange(event.target.value)}>
          {months.map((candidate) => (
            <option value={candidate.month} key={candidate.month}>
              {candidate.month}
            </option>
          ))}
        </select>
      </label>

      <label>
        <span>Window</span>
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
          <span>Review style</span>
          <div className="simulatorModeToggle" role="group" aria-label="Review style">
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
        <span>{mode === "questionnaire" ? "Profile from answers" : "Selected profile"}</span>
        <strong>{profileLabel}</strong>
        <p>{mode === "questionnaire" ? "Confirmed after running." : selectedLevel?.label ?? "Manual profile"}</p>
      </div>

      <button className="primaryButton" type="button" onClick={onRun} disabled={loading || months.length === 0}>
        {loading ? <RotateCw size={16} /> : <Play size={16} />}
        {loading ? "Running" : "Run simulation"}
      </button>
      <p className="runNote">{durationRequestLabel} historical diagnostic.</p>
    </section>
  );
}
