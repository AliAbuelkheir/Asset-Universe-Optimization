import type { QuestionnaireInput, RiskLevel, SimulatorMode } from "./types";

export const riskOrder: RiskLevel[] = ["low", "medium", "high"];

export const simulatorModeOptions: Array<{ label: string; value: SimulatorMode; description: string }> = [
  {
    label: "Monthly review",
    value: "monthly_rebalance",
    description: "Refresh the allocation view for each plotted month."
  },
  {
    label: "Opening allocation",
    value: "single",
    description: "Keep the opening allocation through the full window."
  }
];

export const defaultSimulatorMode: SimulatorMode = "monthly_rebalance";

export const durationOptions = [
  { label: "1 month", value: 1 },
  { label: "3 months", value: 3 },
  { label: "6 months", value: 6 },
  { label: "12 months", value: 12 },
  { label: "Max available", value: null }
] as const;

export const defaultQuestionnaire: QuestionnaireInput = {
  age: 29,
  Gender_Score: 1,
  Stock_Score: 1,
  Duration_Score: 2,
  Expect_Score: 2,
  Monitor_Score: 2,
  Objective_Score: 2,
  Avenue_Score: 3,
  Factor_Returns: true,
  Factor_Risk: false,
  "Purpose_Savings for Future": false,
  "Purpose_Wealth Creation": true,
  "What are your savings objectives?_Health Care": true,
  "What are your savings objectives?_Retirement Plan": false
};

export const questionnaireOptions = {
  Gender_Score: [
    { label: "Female", value: 0 },
    { label: "Male", value: 1 }
  ],
  Stock_Score: [
    { label: "No", value: 0 },
    { label: "Yes", value: 1 }
  ],
  Duration_Score: [
    { label: "Less than 1 year", value: 1 },
    { label: "1 to 3 years", value: 2 },
    { label: "3 to 5 years", value: 3 },
    { label: "More than 5 years", value: 4 }
  ],
  Expect_Score: [
    { label: "10% to 20%", value: 1 },
    { label: "20% to 30%", value: 2 },
    { label: "30% to 40%", value: 3 }
  ],
  Monitor_Score: [
    { label: "Monthly", value: 1 },
    { label: "Weekly", value: 2 },
    { label: "Daily", value: 3 }
  ],
  Objective_Score: [
    { label: "Income", value: 1 },
    { label: "Capital appreciation", value: 2 },
    { label: "Growth", value: 3 }
  ],
  Avenue_Score: [
    { label: "Public Provident Fund", value: 1 },
    { label: "Fixed deposits", value: 2 },
    { label: "Mutual fund", value: 3 },
    { label: "Equity", value: 4 }
  ]
} as const;
