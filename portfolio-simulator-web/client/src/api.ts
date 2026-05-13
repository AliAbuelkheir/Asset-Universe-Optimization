import type {
  MonthOption,
  QuestionnaireInput,
  RiskLevel,
  RiskLevelDefinition,
  SimulationReport
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
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
  return response.json() as Promise<T>;
}

export function fetchMonths() {
  return request<MonthOption[]>("/api/months");
}

export function fetchRiskLevels() {
  return request<RiskLevelDefinition[]>("/api/risk-levels");
}

export function runFastSimulation(month: string, riskLevel: RiskLevel, durationMonths?: number | null) {
  return request<SimulationReport>("/api/simulations/fast", {
    method: "POST",
    body: JSON.stringify({ month, riskLevel, durationMonths })
  });
}

export function runQuestionnaireSimulation(
  month: string,
  questionnaire: QuestionnaireInput,
  durationMonths?: number | null
) {
  return request<SimulationReport>("/api/simulations/questionnaire", {
    method: "POST",
    body: JSON.stringify({ month, questionnaire, durationMonths })
  });
}
