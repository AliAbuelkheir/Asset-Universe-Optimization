export type RiskLevel = "low" | "medium" | "high";

export type SimulationMode = "questionnaire" | "fast";
export type SimulatorMode = "single" | "monthly_rebalance";

export interface MonthOption {
  month: string;
  assetCount: number;
}

export interface RiskLevelDefinition {
  id: RiskLevel;
  label: string;
  minRankPct: number;
  maxRankPct: number;
  description: string;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  ppoRootExists: boolean;
  predictionsAvailable: boolean;
  dailyMarketAvailable: boolean;
  monthlyPanelAvailable: boolean;
  questionnaireModelAvailable: boolean;
  optimizerMode: "external_model" | "unavailable";
  optimizerRuntimeAvailable: boolean;
}

export interface QuestionnaireInput {
  age: number;
  Gender_Score: 0 | 1;
  Stock_Score: 0 | 1;
  Duration_Score: 1 | 2 | 3 | 4;
  Expect_Score: 1 | 2 | 3;
  Monitor_Score: 1 | 2 | 3;
  Objective_Score: 1 | 2 | 3;
  Avenue_Score: 1 | 2 | 3 | 4;
  Factor_Returns: boolean;
  Factor_Risk: boolean;
  "Purpose_Savings for Future": boolean;
  "Purpose_Wealth Creation": boolean;
  "What are your savings objectives?_Health Care": boolean;
  "What are your savings objectives?_Retirement Plan": boolean;
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
  optimizedPortfolio: number;
  profileEqualWeight: number;
  optimizerFullUniverse: number;
  fullUniverseEqualWeight: number;
  mvoFilteredUniverse: number;
  mvoFullUniverse: number;
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
  id:
    | "optimizedPortfolio"
    | "profileEqualWeight"
    | "optimizerFullUniverse"
    | "fullUniverseEqualWeight"
    | "mvoFilteredUniverse"
    | "mvoFullUniverse"
    | "egx30";
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
