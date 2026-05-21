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
  questionnaireAvailable: boolean;
  onModeChange: (mode: SimulationMode) => void;
  onRiskLevelChange: (riskLevel: RiskLevel) => void;
  onQuestionnaireChange: <K extends keyof QuestionnaireInput>(field: K, value: QuestionnaireInput[K]) => void;
}

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
  const selectedLevel = levels.find((level) => level.id === riskLevel);
  const selectedBandWidth = selectedLevel
    ? Math.round((selectedLevel.maxRankPct - selectedLevel.minRankPct) * 100)
    : null;

  return (
    <article className="simulationMain">
      <div className="sectionHeading">
        <div>
          <h2>Choose simulation mode</h2>
          <p>Use the questionnaire or choose a risk profile directly for this simulation.</p>
        </div>
        <span>Only one mode runs at a time</span>
      </div>

      <div className="modeCards" role="group" aria-label="Simulation mode">
        <button
          type="button"
          className={mode === "questionnaire" ? "modeCard selected" : "modeCard"}
          aria-pressed={mode === "questionnaire"}
          disabled={!questionnaireAvailable}
          onClick={() => onModeChange("questionnaire")}
        >
          <UserCheck size={24} />
          <strong>Questionnaire</strong>
          <span>{questionnaireAvailable ? "Infer risk level from the contracted model" : "Unavailable in this deployment"}</span>
        </button>
        <button
          type="button"
          className={mode === "fast" ? "modeCard selected" : "modeCard"}
          aria-pressed={mode === "fast"}
          onClick={() => onModeChange("fast")}
        >
          <Gauge size={24} />
          <strong>Fast select</strong>
          <span>Choose a risk band directly</span>
        </button>
      </div>

      {mode === "questionnaire" && questionnaireAvailable ? (
        <QuestionnaireForm questionnaire={questionnaire} onChange={onQuestionnaireChange} />
      ) : (
        <section className="activeModePanel fastModePanel" aria-label="Fast select input">
          <div className="activeModeHeader">
            <div>
              <h3>Fast select risk level</h3>
              <p>Choose the risk profile directly and keep the setup compact.</p>
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
          <p className="modeDescription">{selectedLevel?.description ?? "Select a risk band."}</p>
          <div className="modeSetupSummary" aria-label="Fast select summary">
            <div>
              <span>Current band</span>
              <strong>{labelRisk(riskLevel)}</strong>
            </div>
            <div>
              <span>Universe range</span>
              <strong>{selectedBandWidth ? `${selectedBandWidth}% band` : "Selected band"}</strong>
            </div>
            <div>
              <span>Output focus</span>
              <strong>Historical diagnostics</strong>
            </div>
          </div>
        </section>
      )}
    </article>
  );
}
