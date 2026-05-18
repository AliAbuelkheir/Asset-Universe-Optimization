export type RiskLevel = "low" | "medium" | "high";

export type SimulationMode = "questionnaire" | "fast";
export type SimulatorMode = "single" | "monthly_rebalance";

export interface MonthOption {
  month: string;
  split: "validation" | "test";
  assetCount: number;
}

export interface RiskLevelDefinition {
  id: RiskLevel;
  label: string;
  minRankPct: number;
  maxRankPct: number;
  description: string;
}

export interface QuestionnaireInput {
  gender: "Male" | "Female";
  age: number;
  Duration: "Less than 1 year" | "1-3 years" | "3-5 years" | "More than 5 years";
  Invest_Monitor: "Monthly" | "Weekly" | "Daily";
  Expect: "10%-20%" | "20%-30%" | "30%-40%";
  Objective: "Risk" | "Returns" | "Growth" | "Income";
  Purpose: "Wealth Creation" | "Savings for Future" | "Returns" | "Income";
  "What are your savings objectives?": "Health Care" | "Retirement Plan" | "Education";
}

export interface QuestionnaireInference {
  riskClass: 0 | 1 | 2;
  riskLabel: "Conservative" | "Moderate" | "Aggressive";
  riskLevel: RiskLevel;
  probabilities: Partial<Record<"Conservative" | "Moderate" | "Aggressive", number>>;
  riskScore: number;
}

export interface MonthlyReturnPoint {
  month: string;
  split: "validation" | "test";
  optimizedPortfolio: number;
  optimizedRawUniverse: number;
  assignedRiskBucket: number;
  egx30: number;
}

export interface PerformanceMetrics {
  cumulativeReturn: number;
  annualizedVolatility: number;
  sharpe: number | null;
  sortino: number | null;
  maxDrawdown: number;
  bestMonth: number;
  worstMonth: number;
  ratioNotes: {
    sharpe: string;
    sortino: string;
  };
}

export interface ComparisonRow {
  id: "optimizedPortfolio" | "optimizedRawUniverse" | "assignedRiskBucket" | "egx30";
  label: string;
  metrics: PerformanceMetrics;
}

export interface PipelineAsset {
  assetId: string;
  assetName: string;
  assetGroup: string;
  selectedByFilter: boolean;
  equalWeight: number | null;
  optimizedWeight: number | null;
}

export interface SimulationPipeline {
  activeUniverse: PipelineAsset[];
  selectedAssets: PipelineAsset[];
  activeUniverseCount: number;
  selectedAssetCount: number;
  optimizerWeightSum: number;
  optimizerDecisionDate: string;
}

export interface RebalanceTimelinePoint {
  month: string;
  split: "validation" | "test";
  optimizerDecisionDate: string;
  startingValue: number;
  monthlyReturn: number;
  endingValue: number;
  activeUniverseCount: number;
  selectedAssetCount: number;
  optimizerWeightSum: number;
  selectedAssets: PipelineAsset[];
}

export interface SimulationReport {
  simulationId: string;
  month: string;
  riskLevel: RiskLevel;
  simulatorMode: SimulatorMode;
  split: "validation" | "test";
  durationMonths: number;
  requestedDurationMonths?: number | null;
  chartIntervals: Array<{
    label: string;
    daysSincePrevious: number;
  }>;
  thesisSafeSummary: string;
  optimizerMode: "external_model";
  monthlyReturns: MonthlyReturnPoint[];
  comparison: ComparisonRow[];
  pipeline: SimulationPipeline;
  rebalanceTimeline: RebalanceTimelinePoint[];
  questionnaireInference?: QuestionnaireInference | null;
}
