import cors from "cors";
import express from "express";
import helmet from "helmet";
import morgan from "morgan";
import {
  getMlHealth,
  getMonths,
  getRiskLevels,
  runFastSimulation,
  runQuestionnaireSimulation
} from "./mlClient.js";

const VALID_RISK_LEVELS = new Set(["low", "medium", "high"]);

interface AppDependencies {
  getMlHealth: typeof getMlHealth;
  getMonths: typeof getMonths;
  getRiskLevels: typeof getRiskLevels;
  runFastSimulation: typeof runFastSimulation;
  runQuestionnaireSimulation: typeof runQuestionnaireSimulation;
}

const defaultDependencies: AppDependencies = {
  getMlHealth,
  getMonths,
  getRiskLevels,
  runFastSimulation,
  runQuestionnaireSimulation
};

function corsOptions() {
  const configured = process.env.CORS_ORIGINS?.split(",").map((origin) => origin.trim()).filter(Boolean) ?? [];
  if (configured.length === 0) {
    return { origin: true };
  }
  return {
    origin(origin: string | undefined, callback: (error: Error | null, allow?: boolean) => void) {
      if (!origin || configured.includes(origin)) {
        callback(null, true);
        return;
      }
      callback(new Error("Origin is not allowed by CORS."));
    }
  };
}

export function createApp(dependencies: AppDependencies = defaultDependencies) {
  const app = express();
  app.use(helmet());
  app.use(cors(corsOptions()));
  app.use(express.json({ limit: "1mb" }));
  app.use(morgan("dev"));

  app.get("/api/health", async (_request, response, next) => {
    try {
      const ml = await dependencies.getMlHealth();
      response.json({
        status: ml.status === "ok" ? "ok" : "degraded",
        express: "ok",
        mlService: ml
      });
    } catch (error) {
      next(error);
    }
  });

  app.get("/api/months", async (_request, response, next) => {
    try {
      response.json(await dependencies.getMonths());
    } catch (error) {
      next(error);
    }
  });

  app.get("/api/risk-levels", async (_request, response, next) => {
    try {
      response.json(await dependencies.getRiskLevels());
    } catch (error) {
      next(error);
    }
  });

  app.post("/api/simulations/fast", async (request, response, next) => {
    try {
      const { month, riskLevel, durationMonths } = request.body ?? {};
      if (typeof month !== "string" || !/^\d{4}-\d{2}$/.test(month)) {
        response.status(400).json({ error: "month must use YYYY-MM format." });
        return;
      }
      if (typeof riskLevel !== "string" || !VALID_RISK_LEVELS.has(riskLevel)) {
        response.status(400).json({ error: "riskLevel must be low, medium, or high." });
        return;
      }
      const parsedDuration = durationMonths === null || durationMonths === undefined ? undefined : Number(durationMonths);
      if (parsedDuration !== undefined && (!Number.isInteger(parsedDuration) || parsedDuration < 1)) {
        response.status(400).json({ error: "durationMonths must be a positive integer when provided." });
        return;
      }
      response.json(await dependencies.runFastSimulation({ month, riskLevel, durationMonths: parsedDuration }));
    } catch (error) {
      next(error);
    }
  });

  app.post("/api/simulations/questionnaire", async (request, response, next) => {
    try {
      response.status(501).json(await dependencies.runQuestionnaireSimulation(request.body));
    } catch (error) {
      response.status(501).json({
        error: "Questionnaire inference is disabled until the risk-tolerance model contract is received."
      });
    }
  });

  app.use((error: unknown, _request: express.Request, response: express.Response, _next: express.NextFunction) => {
    const status = typeof error === "object" && error !== null && "response" in error
      ? Number((error as { response?: { status?: number } }).response?.status ?? 502)
      : 500;
    const detail = typeof error === "object" && error !== null && "response" in error
      ? (error as { response?: { data?: unknown } }).response?.data
      : undefined;
    response.status(status).json({
      error: "API request failed.",
      detail: detail ?? (error instanceof Error ? error.message : String(error))
    });
  });

  return app;
}
