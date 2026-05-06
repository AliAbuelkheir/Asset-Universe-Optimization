export type RiskLevel = "low" | "medium" | "high";

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

export interface SelectedAsset {
  assetId: string;
  assetName: string;
  assetGroup: string;
  predictedRankPct: number;
  realizedVol?: number | null;
  realizedDownsideDev?: number | null;
  realizedMaxDrawdown?: number | null;
  weight?: number;
}

export interface RealizedRiskComponents {
  realizedVol: number;
  realizedDownsideDev: number;
  realizedMaxDrawdown: number;
}

export interface MonthlyReturnPoint {
  month: string;
  optimizedPortfolio?: number;
  assignedRiskBucket: number;
  allEqualWeight: number;
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
  id: "optimizedPortfolio" | "assignedRiskBucket" | "allEqualWeight" | "egx30";
  label: string;
  metrics: PerformanceMetrics;
}

export interface RiskComponentRow {
  id: "optimizedPortfolio" | "assignedRiskBucket" | "allEqualWeight" | "egx30";
  label: string;
  components: RealizedRiskComponents;
}

export interface RawRiskComponents {
  annualizedVolatility: number;
  annualizedDownsideDeviation: number;
  maxDrawdown: number;
  observations: number;
}

export interface RawRiskComponentRow {
  id: "assignedRiskBucket" | "allEqualWeight" | "egx30";
  label: string;
  components: RawRiskComponents;
}

export interface SimulationReport {
  simulationId: string;
  month: string;
  riskLevel: RiskLevel;
  split: "validation" | "test";
  durationMonths: number;
  requestedDurationMonths?: number | null;
  chartIntervals: Array<{
    label: string;
    daysSincePrevious: number;
  }>;
  thesisSafeSummary: string;
  optimizerMode: "mock_equal_weight" | "external_model";
  selectedAssets: SelectedAsset[];
  monthlyReturns: MonthlyReturnPoint[];
  comparison: ComparisonRow[];
  riskComponents: RiskComponentRow[];
  rawRiskComponents: RawRiskComponentRow[];
  assumptions: string[];
  requiredExternalContracts: {
    riskToleranceModel: string[];
    weightOptimizerModel: string[];
  };
}
