import type { QuestionnaireInput, RiskLevel, SimulatorMode } from "./types";
import { localMonthlyRebalanceEnabled } from "./environment";

export const riskOrder: RiskLevel[] = ["low", "medium", "high"];

const localSimulatorModeOptions: Array<{ label: string; value: SimulatorMode; description: string }> = [
  {
    label: "Monthly rebalance",
    value: "monthly_rebalance",
    description: "Re-run selection and optimizer every plotted month."
  },
  {
    label: "Single allocation",
    value: "single",
    description: "Use the start-month selection and weights for the full window."
  }
];

export const simulatorModeOptions = localMonthlyRebalanceEnabled
  ? localSimulatorModeOptions
  : localSimulatorModeOptions.filter((option) => option.value === "single");

export const defaultSimulatorMode: SimulatorMode = localMonthlyRebalanceEnabled ? "monthly_rebalance" : "single";

export const durationOptions = [
  { label: "1 month", value: 1 },
  { label: "3 months", value: 3 },
  { label: "6 months", value: 6 },
  { label: "12 months", value: 12 },
  { label: "Max available", value: null }
] as const;

export const defaultQuestionnaire: QuestionnaireInput = {
  gender: "Male",
  age: 29,
  Duration: "Less than 1 year",
  Invest_Monitor: "Weekly",
  Expect: "20%-30%",
  Objective: "Growth",
  Purpose: "Wealth Creation",
  "What are your savings objectives?": "Health Care"
};

export const questionnaireOptions = {
  gender: [
    { label: "Male", value: "Male" },
    { label: "Female", value: "Female" }
  ],
  Duration: [
    { label: "Less than 1 year", value: "Less than 1 year" },
    { label: "1 to 3 years", value: "1-3 years" },
    { label: "3 to 5 years", value: "3-5 years" },
    { label: "More than 5 years", value: "More than 5 years" }
  ],
  Invest_Monitor: [
    { label: "Monthly", value: "Monthly" },
    { label: "Weekly", value: "Weekly" },
    { label: "Daily", value: "Daily" }
  ],
  Expect: [
    { label: "10% to 20%", value: "10%-20%" },
    { label: "20% to 30%", value: "20%-30%" },
    { label: "30% to 40%", value: "30%-40%" }
  ],
  Objective: [
    { label: "Reduce risk", value: "Risk" },
    { label: "Generate returns", value: "Returns" },
    { label: "Grow wealth", value: "Growth" },
    { label: "Earn income", value: "Income" }
  ],
  Purpose: [
    { label: "Wealth creation", value: "Wealth Creation" },
    { label: "Savings for the future", value: "Savings for Future" },
    { label: "Returns", value: "Returns" },
    { label: "Income", value: "Income" }
  ],
  "What are your savings objectives?": [
    { label: "Health care", value: "Health Care" },
    { label: "Retirement plan", value: "Retirement Plan" },
    { label: "Education", value: "Education" }
  ]
} as const;
