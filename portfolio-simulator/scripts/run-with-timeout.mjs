#!/usr/bin/env node

import { spawn, spawnSync } from "node:child_process";
import { mkdirSync } from "node:fs";

const args = process.argv.slice(2);
const separatorIndex = args.indexOf("--");

if (separatorIndex === -1 || separatorIndex === args.length - 1) {
  console.error("Usage: node scripts/run-with-timeout.mjs [--timeout-ms 60000] [--mkdir path] [--shell] -- <command> [...args]");
  process.exit(2);
}

let timeoutMs = 60_000;
let shell = false;
const directories = [];

for (let index = 0; index < separatorIndex; index += 1) {
  const arg = args[index];
  if (arg === "--timeout-ms") {
    timeoutMs = Number(args[index + 1]);
    index += 1;
  } else if (arg === "--shell") {
    shell = true;
  } else if (arg === "--mkdir") {
    directories.push(args[index + 1]);
    index += 1;
  } else {
    console.error(`Unknown option: ${arg}`);
    process.exit(2);
  }
}

if (!Number.isFinite(timeoutMs) || timeoutMs <= 0) {
  console.error(`Invalid timeout: ${timeoutMs}`);
  process.exit(2);
}

const [command, ...commandArgs] = args.slice(separatorIndex + 1);
for (const directory of directories) {
  mkdirSync(directory, { recursive: true });
}
const child = spawn(command, commandArgs, {
  stdio: "inherit",
  windowsHide: true,
  shell
});

let timedOut = false;
let completed = false;

function terminateTree() {
  if (!child.pid || completed) {
    return;
  }
  if (process.platform === "win32") {
    const result = spawnSync("taskkill.exe", ["/PID", String(child.pid), "/T", "/F"], {
      stdio: "inherit",
      windowsHide: true
    });
    if (result.status !== 0) {
      child.kill("SIGKILL");
    }
  } else {
    child.kill("SIGKILL");
  }
}

const timer = setTimeout(() => {
  timedOut = true;
  console.error(`\nTimed out after ${timeoutMs}ms: ${command} ${commandArgs.join(" ")}`);
  terminateTree();
  process.exit(124);
}, timeoutMs);

child.on("error", (error) => {
  completed = true;
  clearTimeout(timer);
  console.error(`Failed to start command: ${error.message}`);
  process.exitCode = 1;
});

child.on("exit", (code, signal) => {
  completed = true;
  clearTimeout(timer);
  if (timedOut) {
    process.exitCode = 124;
  } else if (signal) {
    console.error(`Command terminated by signal ${signal}.`);
    process.exitCode = 1;
  } else {
    process.exitCode = code ?? 1;
  }
});

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => {
    terminateTree();
    process.exit(timedOut ? 124 : 1);
  });
}
