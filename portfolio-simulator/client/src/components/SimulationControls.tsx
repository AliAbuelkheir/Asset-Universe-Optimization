import { Gauge, Play, RotateCw } from "lucide-react";
import { labelRisk } from "../format";
import { riskOrder } from "../simulationOptions";
import type { RiskLevel, RiskLevelDefinition } from "../types";

interface SimulationControlsProps {
  levels: RiskLevelDefinition[];
  riskLevel: RiskLevel;
  loading: boolean;
  onRiskLevelChange: (riskLevel: RiskLevel) => void;
  onRun: () => void;
}

const publicRiskDescriptions: Record<RiskLevel, string> = {
  low: "Lower volatility profile for a more conservative review.",
  medium: "Balanced profile for a middle-ground historical review.",
  high: "Higher return-seeking profile with wider return swings."
};

export function SimulationControls({
  levels,
  riskLevel,
  loading,
  onRiskLevelChange,
  onRun
}: SimulationControlsProps) {
  return (
    <section className="simulationMain" aria-label="Fast select">
      <div className="sectionHeading">
        <div>
          <span>Fast mode</span>
          <h2>Quick simulation</h2>
        </div>
      </div>

      <section className="activeModePanel fastModePanel" aria-label="Fast select input">
        <div className="activeModeHeader">
          <div>
            <span>Fast select</span>
            <h3>Risk profile</h3>
          </div>
        </div>
        <div className="segmented" role="group" aria-label="Risk profile">
          {riskOrder.map((level) => (
            <button
              key={level}
              type="button"
              className={riskLevel === level ? "selected" : ""}
              aria-pressed={riskLevel === level}
              onClick={() => onRiskLevelChange(level)}
            >
              {labelRisk(level)}
            </button>
          ))}
        </div>
        <p className="modeDescription">{publicRiskDescriptions[riskLevel]}</p>
        <button className="primaryButton" type="button" onClick={onRun} disabled={loading || levels.length === 0}>
          {loading ? <RotateCw size={16} /> : <Play size={16} />}
          {loading ? "Running" : "Run"}
        </button>
        <p className="runNote"><Gauge size={13} />Uses the selected profile directly.</p>
      </section>
    </section>
  );
}
