import type {
  HealthResponse,
  MonthOption,
  QuestionnaireInput,
  RiskLevel,
  RiskLevelDefinition,
  SimulatorMode,
  SimulationReport
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function assertFiniteNumber(value: unknown, name: string): asserts value is number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new Error(`Invalid API response: ${name} must be a finite number.`);
  }
}

function assertString(value: unknown, name: string): asserts value is string {
  if (typeof value !== "string") {
    throw new Error(`Invalid API response: ${name} must be a string.`);
  }
}

function assertMonthlyReturnPoint(value: unknown): asserts value is SimulationReport["monthlyReturns"][number] {
  if (!isObject(value)) {
    throw new Error("Invalid API response: monthly return point must be an object.");
  }
  assertString(value.month, "monthlyReturns[].month");
  assertFiniteNumber(value.optimizedPortfolio, "monthlyReturns[].optimizedPortfolio");
  assertFiniteNumber(value.mvoFullUniverse, "monthlyReturns[].mvoFullUniverse");
  assertFiniteNumber(value.assignedRiskBucket, "monthlyReturns[].assignedRiskBucket");
  assertFiniteNumber(value.egx30, "monthlyReturns[].egx30");
}

function assertMetrics(value: unknown): asserts value is SimulationReport["comparison"][number]["metrics"] {
  if (!isObject(value)) {
    throw new Error("Invalid API response: comparison metrics must be an object.");
  }
  assertFiniteNumber(value.cumulativeReturn, "comparison[].metrics.cumulativeReturn");
  assertFiniteNumber(value.annualizedVolatility, "comparison[].metrics.annualizedVolatility");
  assertFiniteNumber(value.maxDrawdown, "comparison[].metrics.maxDrawdown");
  assertFiniteNumber(value.bestMonth, "comparison[].metrics.bestMonth");
  assertFiniteNumber(value.worstMonth, "comparison[].metrics.worstMonth");
  if (value.sharpe !== null) {
    assertFiniteNumber(value.sharpe, "comparison[].metrics.sharpe");
  }
  if (value.sortino !== null) {
    assertFiniteNumber(value.sortino, "comparison[].metrics.sortino");
  }
}

function assertComparisonRow(value: unknown): asserts value is SimulationReport["comparison"][number] {
  if (!isObject(value)) {
    throw new Error("Invalid API response: comparison row must be an object.");
  }
  if (
    value.id !== "optimizedPortfolio" &&
    value.id !== "mvoFullUniverse" &&
    value.id !== "assignedRiskBucket" &&
    value.id !== "egx30"
  ) {
    throw new Error("Invalid API response: comparison[].id is unknown.");
  }
  assertString(value.label, "comparison[].label");
  assertMetrics(value.metrics);
}

function assertSimulationReport(value: unknown): asserts value is SimulationReport {
  if (!isObject(value)) {
    throw new Error("Invalid API response: simulation report must be an object.");
  }
  if (!Array.isArray(value.monthlyReturns) || !Array.isArray(value.comparison) || !Array.isArray(value.chartIntervals)) {
    throw new Error("Invalid API response: report arrays are missing.");
  }
  value.monthlyReturns.forEach(assertMonthlyReturnPoint);
  value.comparison.forEach(assertComparisonRow);
  if (value.chartIntervals.length !== value.monthlyReturns.length + 1) {
    throw new Error("Invalid API response: chartIntervals must include Start plus one row per monthly return.");
  }
  for (const row of value.comparison) {
    for (const point of value.monthlyReturns) {
      assertFiniteNumber(point[row.id], `monthlyReturns[].${row.id}`);
    }
  }
}

function assertHealthResponse(value: unknown): asserts value is HealthResponse {
  if (!isObject(value)) {
    throw new Error("Invalid API response: health response must be an object.");
  }
  if (value.status !== "ok" && value.status !== "degraded") {
    throw new Error("Invalid API response: health status is unknown.");
  }
  if (typeof value.questionnaireModelAvailable !== "boolean") {
    throw new Error("Invalid API response: questionnaireModelAvailable must be boolean.");
  }
}

async function request<T>(path: string, init?: RequestInit, validate?: (payload: unknown) => asserts payload is T): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = payload.detail;
    const detailText = typeof detail === "string" ? detail : detail ? JSON.stringify(detail) : undefined;
    throw new Error(payload.error ?? detailText ?? `Request failed with ${response.status}`);
  }
  const payload: unknown = await response.json();
  validate?.(payload);
  return payload as T;
}

export function fetchHealth() {
  return request<HealthResponse>("/api/health", undefined, assertHealthResponse);
}

export function fetchMonths() {
  return request<MonthOption[]>("/api/months");
}

export function fetchRiskLevels() {
  return request<RiskLevelDefinition[]>("/api/risk-levels");
}

export function runFastSimulation(
  month: string,
  riskLevel: RiskLevel,
  durationMonths?: number | null,
  simulatorMode: SimulatorMode = "single"
) {
  return request<SimulationReport>("/api/simulations/fast", {
    method: "POST",
    body: JSON.stringify({ month, riskLevel, durationMonths, simulatorMode })
  }, assertSimulationReport);
}

export function runQuestionnaireSimulation(
  month: string,
  questionnaire: QuestionnaireInput,
  durationMonths?: number | null,
  simulatorMode: SimulatorMode = "single"
) {
  return request<SimulationReport>("/api/simulations/questionnaire", {
    method: "POST",
    body: JSON.stringify({ month, questionnaire, durationMonths, simulatorMode })
  }, assertSimulationReport);
}
