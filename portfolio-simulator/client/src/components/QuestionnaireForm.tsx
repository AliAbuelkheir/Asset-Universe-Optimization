import { Play } from "lucide-react";
import { useEffect, useState } from "react";
import { questionnaireOptions } from "../simulationOptions";
import type { QuestionnaireInput } from "../types";

type OneHotField =
  | "Factor_Returns"
  | "Factor_Risk"
  | "Purpose_Savings for Future"
  | "Purpose_Wealth Creation"
  | "What are your savings objectives?_Health Care"
  | "What are your savings objectives?_Retirement Plan";

interface QuestionnaireFormProps {
  questionnaire: QuestionnaireInput;
  disabled: boolean;
  onChange: <K extends keyof QuestionnaireInput>(field: K, value: QuestionnaireInput[K]) => void;
  onRun: () => void;
}

export function QuestionnaireForm({ questionnaire, disabled, onChange, onRun }: QuestionnaireFormProps) {
  const [ageInput, setAgeInput] = useState(String(questionnaire.age));

  useEffect(() => {
    setAgeInput(String(questionnaire.age));
  }, [questionnaire.age]);

  function renderOptions<K extends keyof QuestionnaireInput>(
    field: K,
    options: ReadonlyArray<{ label: string; value: QuestionnaireInput[K] }>,
    ariaLabel: string
  ) {
    return (
      <div className="answerChips" role="group" aria-label={ariaLabel}>
        {options.map((option) => (
          <button
            type="button"
            key={String(option.value)}
            className={questionnaire[field] === option.value ? "answerChip selected" : "answerChip"}
            onClick={() => onChange(field, option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>
    );
  }

  function renderMappedQuestion<K extends keyof QuestionnaireInput>(
    question: string,
    field: K,
    options: ReadonlyArray<{ label: string; value: QuestionnaireInput[K] }>
  ) {
    return (
      <div className="questionItem">
        <span>{question}</span>
        {renderOptions(field, options, question)}
      </div>
    );
  }

  function renderOneHotQuestion(
    question: string,
    fields: readonly OneHotField[],
    options: ReadonlyArray<{ label: string; field?: OneHotField }>
  ) {
    const selectedField = fields.find((field) => questionnaire[field]);
    return (
      <div className="questionItem">
        <span>{question}</span>
        <div className="answerChips" role="group" aria-label={question}>
          {options.map((option) => (
            <button
              type="button"
              key={option.field ?? "unknown-baseline"}
              className={[
                "answerChip",
                selectedField === option.field ? "selected" : ""
              ].filter(Boolean).join(" ")}
              onClick={() => fields.forEach((field) => onChange(field, field === option.field))}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <section className="questionnaireSurface t-panel-slide" data-open="true" id="questionnaire" aria-label="Questionnaire input">
      <div className="questionnaireHeader">
        <div>
          <span>Investor profile</span>
          <h3>Questionnaire</h3>
          <p>Answer the profile questions, then generate a historical diagnostic using the inferred risk level.</p>
        </div>
      </div>
      <div className="questionnaireStack">
        <label className="questionItem">
          <span>What is your age?</span>
          <input
            type="number"
            min={18}
            max={70}
            value={ageInput}
            onBlur={() => setAgeInput(String(questionnaire.age))}
            onChange={(event) => {
              const nextValue = event.target.value;
              setAgeInput(nextValue);
              if (nextValue === "") {
                return;
              }
              const nextAge = Number(nextValue);
              if (Number.isInteger(nextAge) && nextAge >= 18 && nextAge <= 70) {
                onChange("age", nextAge);
              }
            }}
          />
        </label>
        {renderMappedQuestion("What is your gender?", "Gender_Score", questionnaireOptions.Gender_Score)}
        {renderMappedQuestion("Do you invest in the stock market?", "Stock_Score", questionnaireOptions.Stock_Score)}
        {renderMappedQuestion("How long do you expect to keep this investment?", "Duration_Score", questionnaireOptions.Duration_Score)}
        {renderMappedQuestion("What annual return range do you expect?", "Expect_Score", questionnaireOptions.Expect_Score)}
        {renderMappedQuestion("How often do you monitor your investments?", "Monitor_Score", questionnaireOptions.Monitor_Score)}
        {renderMappedQuestion("What is your main investment objective?", "Objective_Score", questionnaireOptions.Objective_Score)}
        {renderMappedQuestion("Which investment avenue do you prefer?", "Avenue_Score", questionnaireOptions.Avenue_Score)}
        {renderOneHotQuestion("Which factor matters most when choosing an investment?", ["Factor_Returns", "Factor_Risk"], [
          { label: "Locking Period" },
          { label: "Returns", field: "Factor_Returns" },
          { label: "Risk", field: "Factor_Risk" }
        ])}
        {renderOneHotQuestion("What is the purpose of this investment?", ["Purpose_Savings for Future", "Purpose_Wealth Creation"], [
          { label: "Returns" },
          { label: "Savings for Future", field: "Purpose_Savings for Future" },
          { label: "Wealth Creation", field: "Purpose_Wealth Creation" }
        ])}
        {renderOneHotQuestion("What are your savings objectives?", ["What are your savings objectives?_Health Care", "What are your savings objectives?_Retirement Plan"], [
          { label: "Education" },
          { label: "Health Care", field: "What are your savings objectives?_Health Care" },
          { label: "Retirement Plan", field: "What are your savings objectives?_Retirement Plan" }
        ])}
      </div>
      <footer className="questionnaireAction">
        <div>
          <strong>Ready to generate a profile?</strong>
          <span>Your answers stay available when you return for a new simulation.</span>
        </div>
        <button className="primaryButton" type="button" onClick={onRun} disabled={disabled}>
          <Play size={16} />
          Run
        </button>
      </footer>
    </section>
  );
}
