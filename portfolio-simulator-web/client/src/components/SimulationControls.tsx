import { Gauge, UserCheck } from "lucide-react";
import { labelRisk } from "../format";
import { riskOrder } from "../simulationOptions";
import type { QuestionnaireInput, RiskLevel, RiskLevelDefinition, SimulationMode } from "../types";
import { QuestionnaireForm } from "./QuestionnaireForm";

interface SimulationControlsProps {
  levels: RiskLevelDefinition[];
  mode: SimulationMode;
  riskLevel: RiskLevel;
  questionnaire: QuestionnaireInput;
  onModeChange: (mode: SimulationMode) => void;
  onRiskLevelChange: (riskLevel: RiskLevel) => void;
  onQuestionnaireChange: <K extends keyof QuestionnaireInput>(field: K, value: QuestionnaireInput[K]) => void;
}

export function SimulationControls({
  levels,
  mode,
  riskLevel,
  questionnaire,
  onModeChange,
  onRiskLevelChange,
  onQuestionnaireChange
}: SimulationControlsProps) {
  return (
    <article className="simulationMain">
      <div className="sectionHeading">
        <div>
          <h2>Choose simulation mode</h2>
          <p>Run either questionnaire inference or manual fast select for this simulation.</p>
        </div>
        <span>Only one mode runs at a time</span>
      </div>

      <div className="modeCards" role="tablist" aria-label="Simulation mode">
        <button
          type="button"
          className={mode === "questionnaire" ? "modeCard selected" : "modeCard"}
          aria-pressed={mode === "questionnaire"}
          onClick={() => onModeChange("questionnaire")}
        >
          <UserCheck size={24} />
          <strong>Questionnaire</strong>
          <span>Infer risk level from answers</span>
        </button>
        <button
          type="button"
          className={mode === "fast" ? "modeCard selected" : "modeCard"}
          aria-pressed={mode === "fast"}
          onClick={() => onModeChange("fast")}
        >
          <Gauge size={24} />
          <strong>Fast select</strong>
          <span>Manually choose a risk band</span>
        </button>
      </div>

      {mode === "questionnaire" ? (
        <QuestionnaireForm questionnaire={questionnaire} onChange={onQuestionnaireChange} />
      ) : (
        <section className="activeModePanel" aria-label="Fast select input">
          <div className="activeModeHeader">
            <div>
              <h3>Fast select risk level</h3>
              <p>Skip questionnaire inference and choose the risk profile directly.</p>
            </div>
            <span>Manual</span>
          </div>
          <div className="segmented">
            {riskOrder.map((level) => (
              <button
                key={level}
                type="button"
                className={riskLevel === level ? "selected" : ""}
                onClick={() => onRiskLevelChange(level)}
              >
                {labelRisk(level)}
              </button>
            ))}
          </div>
          <p className="modeDescription">{levels.find((level) => level.id === riskLevel)?.description ?? "Select a risk band."}</p>
        </section>
      )}
    </article>
  );
}
