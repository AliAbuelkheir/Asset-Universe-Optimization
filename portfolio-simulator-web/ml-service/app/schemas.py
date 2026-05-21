from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RiskLevel = Literal["low", "medium", "high"]
SimulatorMode = Literal["single", "monthly_rebalance"]
MAX_DURATION_MONTHS = 48


class FastSimulationRequest(BaseModel):
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    riskLevel: RiskLevel
    durationMonths: int | None = Field(default=None, ge=1, le=MAX_DURATION_MONTHS)
    simulatorMode: SimulatorMode = "single"


class QuestionnaireInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    gender: Literal["Male", "Female"]
    age: int = Field(ge=18, le=70)
    Duration: Literal["Less than 1 year", "1-3 years", "3-5 years", "More than 5 years"]
    Invest_Monitor: Literal["Monthly", "Weekly", "Daily"]
    Expect: Literal["10%-20%", "20%-30%", "30%-40%"]
    Objective: Literal["Risk", "Returns", "Growth", "Income"]
    Purpose: Literal["Wealth Creation", "Savings for Future", "Returns", "Income"]
    savings_objective: Literal["Health Care", "Retirement Plan", "Education"] = Field(
        alias="What are your savings objectives?"
    )


class QuestionnaireSimulationRequest(BaseModel):
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    durationMonths: int | None = Field(default=None, ge=1, le=MAX_DURATION_MONTHS)
    simulatorMode: SimulatorMode = "single"
    questionnaire: QuestionnaireInput


class MonthOption(BaseModel):
    month: str
    split: Literal["validation", "test"]
    assetCount: int


class RiskLevelDefinition(BaseModel):
    id: RiskLevel
    label: str
    minRankPct: float
    maxRankPct: float
    description: str


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    ppoRootExists: bool
    predictionsAvailable: bool
    dailyMarketAvailable: bool
    monthlyPanelAvailable: bool
    questionnaireModelAvailable: bool
    optimizerMode: Literal["external_model", "unavailable"]
    optimizerRuntimeAvailable: bool


class QuestionnaireInference(BaseModel):
    riskClass: Literal[0, 1, 2]
    riskLabel: Literal["Conservative", "Moderate", "Aggressive"]
    riskLevel: RiskLevel
    probabilities: dict[str, float]
    riskScore: float


class ChartInterval(BaseModel):
    label: str
    daysSincePrevious: int


class MonthlyReturnPoint(BaseModel):
    month: str
    split: Literal["validation", "test"]
    optimizedPortfolio: float
    mvoFullUniverse: float
    assignedRiskBucket: float
    egx30: float


class RatioNotes(BaseModel):
    sharpe: str
    sortino: str


class PerformanceMetrics(BaseModel):
    cumulativeReturn: float
    annualizedVolatility: float
    sharpe: float | None
    sortino: float | None
    maxDrawdown: float
    bestMonth: float
    worstMonth: float
    ratioNotes: RatioNotes


class ComparisonRow(BaseModel):
    id: Literal["optimizedPortfolio", "mvoFullUniverse", "assignedRiskBucket", "egx30"]
    label: str
    metrics: PerformanceMetrics


class PipelineAsset(BaseModel):
    assetId: str
    assetName: str
    assetGroup: str
    selectedByFilter: bool
    equalWeight: float | None = None
    optimizedWeight: float | None = None


class SimulationPipeline(BaseModel):
    activeUniverse: list[PipelineAsset]
    selectedAssets: list[PipelineAsset]
    activeUniverseCount: int
    selectedAssetCount: int
    optimizerWeightSum: float
    optimizerDecisionDate: str


class RebalanceTimelinePoint(BaseModel):
    month: str
    split: Literal["validation", "test"]
    optimizerDecisionDate: str
    startingValue: float
    monthlyReturn: float
    endingValue: float
    activeUniverseCount: int
    selectedAssetCount: int
    optimizerWeightSum: float
    selectedAssets: list[PipelineAsset]


class SimulationReport(BaseModel):
    simulationId: str
    month: str
    riskLevel: RiskLevel
    simulatorMode: SimulatorMode
    split: Literal["validation", "test"]
    durationMonths: int
    requestedDurationMonths: int | None
    chartIntervals: list[ChartInterval]
    thesisSafeSummary: str
    optimizerMode: Literal["external_model"]
    monthlyReturns: list[MonthlyReturnPoint]
    comparison: list[ComparisonRow]
    pipeline: SimulationPipeline
    rebalanceTimeline: list[RebalanceTimelinePoint]
    questionnaireInference: QuestionnaireInference | None = None
