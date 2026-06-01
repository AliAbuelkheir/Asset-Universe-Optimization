import { durationOptions, simulatorModeOptions } from "../simulationOptions";
import type {
  MonthOption,
  SimulatorMode
} from "../types";

interface RunPanelProps {
  months: MonthOption[];
  month: string;
  simulatorMode: SimulatorMode;
  durationMonths: number | null;
  onMonthChange: (month: string) => void;
  onSimulatorModeChange: (simulatorMode: SimulatorMode) => void;
  onDurationChange: (duration: number | null) => void;
}

export function RunPanel({
  months,
  month,
  simulatorMode,
  durationMonths,
  onMonthChange,
  onSimulatorModeChange,
  onDurationChange
}: RunPanelProps) {
  const durationRequestLabel = durationMonths === null
    ? "Max window"
    : `${durationMonths} month${durationMonths === 1 ? "" : "s"}`;

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

      <p className="runNote">{durationRequestLabel} historical diagnostic. Applied to both run paths.</p>
    </section>
  );
}
