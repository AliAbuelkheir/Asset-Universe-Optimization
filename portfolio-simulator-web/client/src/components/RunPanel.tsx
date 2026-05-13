import { Play } from "lucide-react";
import { labelRisk } from "../format";
import { durationOptions } from "../simulationOptions";
import type { MonthOption, RiskLevel, RiskLevelDefinition, SimulationMode, SimulationReport } from "../types";

interface RunPanelProps {
  months: MonthOption[];
  levels: RiskLevelDefinition[];
  mode: SimulationMode;
  month: string;
  riskLevel: RiskLevel;
  durationMonths: number | null;
  report: SimulationReport | null;
  lastRunMode: SimulationMode | null;
  loading: boolean;
  onMonthChange: (month: string) => void;
  onDurationChange: (duration: number | null) => void;
  onRun: () => void;
}

export function RunPanel({
  months,
  levels,
  mode,
  month,
  riskLevel,
  durationMonths,
  report,
  lastRunMode,
  loading,
  onMonthChange,
  onDurationChange,
  onRun
}: RunPanelProps) {
  const selectedMonth = months.find((candidate) => candidate.month === month);
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
          ? `${selectedMonth.split} split, ${selectedMonth.assetCount} active assets, ${durationRequestLabel} requested.`
          : "Loading months."}
      </p>
    </aside>
  );
}
