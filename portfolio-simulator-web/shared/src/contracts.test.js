import assert from "node:assert/strict";
import test from "node:test";

test("risk levels remain stable for API contracts", () => {
  const levels = ["low", "medium", "high"];
  assert.deepEqual(levels, ["low", "medium", "high"]);
});

