import assert from "node:assert/strict";
import test from "node:test";
import request from "supertest";
import { createApp } from "./app.js";

const dependencies = {
  getMlHealth: async () => ({
    status: "ok",
    ppoRootExists: true,
    predictionsAvailable: true,
    dailyMarketAvailable: true,
    optimizerMode: "mock_equal_weight"
  }),
  getMonths: async () => [{ month: "2025-03", split: "test", assetCount: 36 }],
  getRiskLevels: async () => [
    { id: "low", label: "Low risk", minRankPct: 0, maxRankPct: 0.4, description: "Low band" },
    { id: "medium", label: "Medium risk", minRankPct: 0.25, maxRankPct: 0.75, description: "Medium band" },
    { id: "high", label: "High risk", minRankPct: 0.6, maxRankPct: 1, description: "High band" }
  ],
  runFastSimulation: async (payload: { month: string; riskLevel: string; durationMonths?: number | null }) => ({
    simulationId: "test",
    month: payload.month,
    riskLevel: payload.riskLevel,
    durationMonths: 3,
    requestedDurationMonths: payload.durationMonths ?? null,
    chartIntervals: [],
    split: "test",
    selectedAssets: [],
    monthlyReturns: [],
    comparison: [],
    riskComponents: [],
    rawRiskComponents: [],
    assumptions: ["Fixed selected universe."],
    optimizerMode: "mock_equal_weight",
    thesisSafeSummary: "diagnostic only",
    requiredExternalContracts: { riskToleranceModel: [], weightOptimizerModel: [] }
  }),
  runQuestionnaireSimulation: async () => ({})
};

test("GET /api/months returns validation/test month options", async () => {
  const response = await request(createApp(dependencies)).get("/api/months").expect(200);
  assert.equal(response.body[0].month, "2025-03");
});

test("POST /api/simulations/fast validates risk level", async () => {
  await request(createApp(dependencies))
    .post("/api/simulations/fast")
    .send({ month: "2025-03", riskLevel: "aggressive" })
    .expect(400);
});

test("POST /api/simulations/fast returns a report for valid input", async () => {
  const response = await request(createApp(dependencies))
    .post("/api/simulations/fast")
    .send({ month: "2025-03", riskLevel: "medium" })
    .expect(200);
  assert.equal(response.body.optimizerMode, "mock_equal_weight");
  assert.deepEqual(response.body.comparison, []);
  assert.deepEqual(response.body.rawRiskComponents, []);
});

test("POST /api/simulations/fast preserves requested duration", async () => {
  const response = await request(createApp(dependencies))
    .post("/api/simulations/fast")
    .send({ month: "2025-03", riskLevel: "medium", durationMonths: 12 })
    .expect(200);
  assert.equal(response.body.requestedDurationMonths, 12);
});

test("POST /api/simulations/fast validates duration", async () => {
  await request(createApp(dependencies))
    .post("/api/simulations/fast")
    .send({ month: "2025-03", riskLevel: "medium", durationMonths: 0 })
    .expect(400);
});

test("POST /api/simulations/questionnaire remains disabled", async () => {
  await request(createApp(dependencies)).post("/api/simulations/questionnaire").send({}).expect(501);
});
