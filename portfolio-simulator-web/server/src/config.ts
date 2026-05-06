import dotenv from "dotenv";

dotenv.config();

export const config = {
  port: Number(process.env.PORT ?? 4000),
  mlServiceUrl: process.env.ML_SERVICE_URL ?? "http://127.0.0.1:8000",
  requestTimeoutMs: Number(process.env.REQUEST_TIMEOUT_MS ?? 30000)
};

