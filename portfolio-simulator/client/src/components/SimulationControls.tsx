import { Gauge, UserRoundCheck } from "lucide-react";
import { labelRisk } from "../format";
import { riskOrder } from "../simulationOptions";
import type { QuestionnaireInput, RiskLevel, RiskLevelDefinition, SimulationMode } from "../types";
import { QuestionnaireForm } from "./QuestionnaireForm";

interface SimulationControlsProps {
  levels: RiskLevelDefinition[];
  mode: SimulationMode;
  riskLevel: RiskLevel;
  questionnaire: QuestionnaireInput;
  questionnaireAvailable: boolean;
  onModeChange: (mode: SimulationMode) => void;
  onRiskLevelChange: (riskLevel: RiskLevel) => void;
  onQuestionnaireChange: <K extends keyof QuestionnaireInput>(field: K, value: QuestionnaireInput[K]) => void;
}

const publicRiskDescriptions: Record<RiskLevel, string> = {
  low: "Lower volatility profile for a more conservative review.",
  medium: "Balanced profile for a middle-ground historical review.",
  high: "Higher return-seeking profile with wider return swings."
};

export function SimulationControls({
  levels,
  mode,
  riskLevel,
  questionnaire,
  questionnaireAvailable,
  onModeChange,
  onRiskLevelChange,
  onQuestionnaireChange
}: SimulationControlsProps) {
  return (
    <section className="simulationMain">
      <div className="sectionHeading">
        <div>
          <span>Investor profile</span>
          <h2>Risk input</h2>
        </div>
      </div>

      <div className="modeCards" role="group" aria-label="Risk input mode">
        <button
          type="button"
          className={mode === "questionnaire" ? "modeCard selected" : "modeCard"}
          aria-pressed={mode === "questionnaire"}
          disabled={!questionnaireAvailable}
          onClick={() => onModeChange("questionnaire")}
        >
          <UserRoundCheck size={16} />
          <strong>Questionnaire</strong>
          <span>{questionnaireAvailable ? "Use profile answers" : "Unavailable"}</span>
        </button>
        <button
          type="button"
          className={mode === "fast" ? "modeCard selected" : "modeCard"}
          aria-pressed={mode === "fast"}
          onClick={() => onModeChange("fast")}
        >
          <Gauge size={16} />
          <strong>Fast select</strong>
          <span>Choose profile</span>
        </button>
      </div>

      {mode === "questionnaire" && questionnaireAvailable ? (
        <QuestionnaireForm questionnaire={questionnaire} onChange={onQuestionnaireChange} />
      ) : (
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
        </section>
      )}
    </section>
  );
}
