import type { MonthOption, RiskLevel, RiskLevelDefinition, SimulationReport } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.error ?? payload.detail ?? `Request failed with ${response.status}`);
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
