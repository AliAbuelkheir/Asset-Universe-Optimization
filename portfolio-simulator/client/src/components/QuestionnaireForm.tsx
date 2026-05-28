import { useEffect, useState } from "react";
import { questionnaireOptions } from "../simulationOptions";
import type { QuestionnaireInput } from "../types";

interface QuestionnaireFormProps {
  questionnaire: QuestionnaireInput;
  onChange: <K extends keyof QuestionnaireInput>(field: K, value: QuestionnaireInput[K]) => void;
}

export function QuestionnaireForm({ questionnaire, onChange }: QuestionnaireFormProps) {
  const [ageInput, setAgeInput] = useState(String(questionnaire.age));

  useEffect(() => {
    setAgeInput(String(questionnaire.age));
  }, [questionnaire.age]);

  function renderOptions<K extends keyof QuestionnaireInput>(
    field: K,
    options: ReadonlyArray<{ label: string; value: QuestionnaireInput[K] }>
  ) {
    return (
      <div className="answerChips">
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

  return (
    <section className="activeModePanel" aria-label="Questionnaire input">
      <div className="activeModeHeader">
        <div>
          <span>Questionnaire</span>
          <h3>Questionnaire</h3>
          <p>Answers determine the profile used for the historical diagnostic.</p>
        </div>
      </div>
      <div className="questionnaireStack">
        <label className="questionItem">
          <span>How old is the investor?</span>
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
        <div className="questionItem">
          <span>What is the investor's gender?</span>
          {renderOptions("gender", questionnaireOptions.gender)}
        </div>
        <div className="questionItem">
          <span>How long does the investor expect to keep this investment?</span>
          {renderOptions("Duration", questionnaireOptions.Duration)}
        </div>
        <div className="questionItem">
          <span>How often does the investor monitor investments?</span>
          {renderOptions("Invest_Monitor", questionnaireOptions.Invest_Monitor)}
        </div>
        <div className="questionItem">
          <span>What annual return range does the investor expect?</span>
          {renderOptions("Expect", questionnaireOptions.Expect)}
        </div>
        <div className="questionItem">
          <span>What is the main investment objective?</span>
          {renderOptions("Objective", questionnaireOptions.Objective)}
        </div>
        <div className="questionItem">
          <span>What is the purpose of this investment?</span>
          {renderOptions("Purpose", questionnaireOptions.Purpose)}
        </div>
        <div className="questionItem">
          <span>What is the main savings objective?</span>
          {renderOptions("What are your savings objectives?", questionnaireOptions["What are your savings objectives?"])}
        </div>
      </div>
    </section>
  );
}
