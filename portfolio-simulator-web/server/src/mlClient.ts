import axios from "axios";
import { config } from "./config.js";

export const mlClient = axios.create({
  baseURL: config.mlServiceUrl,
  timeout: config.requestTimeoutMs
});

export async function getMlHealth() {
  const response = await mlClient.get("/health");
  return response.data;
}

export async function getMonths() {
  const response = await mlClient.get("/months");
  return response.data;
}

export async function getRiskLevels() {
  const response = await mlClient.get("/risk-levels");
  return response.data;
}

export async function runFastSimulation(payload: { month: string; riskLevel: string; durationMonths?: number | null }) {
  const response = await mlClient.post("/simulations/fast", payload);
  return response.data;
}

export async function runQuestionnaireSimulation(payload: unknown) {
  const response = await mlClient.post("/simulations/questionnaire", payload);
  return response.data;
}
