/** @vitest-environment node */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { ASK_PANEL_ORCHESTRATION_RETURN_KEYS } from "./askPanelOrchestrationContract.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

describe("askPanelOrchestrationContract", () => {
  it("lists unique sorted keys", () => {
    const sorted = [...ASK_PANEL_ORCHESTRATION_RETURN_KEYS].sort((a, b) => a.localeCompare(b));
    expect(ASK_PANEL_ORCHESTRATION_RETURN_KEYS).toEqual(sorted);
    expect(new Set(ASK_PANEL_ORCHESTRATION_RETURN_KEYS).size).toBe(ASK_PANEL_ORCHESTRATION_RETURN_KEYS.length);
  });

  it("every AskPanel o.* accessor is covered by the canonical return key list", () => {
    const askPanelSource = readFileSync(join(__dirname, "../shell/AskPanel.jsx"), "utf8");
    const used = new Set();
    const re = /\bo\.(\w+)\b/g;
    let m = re.exec(askPanelSource);
    while (m) {
      used.add(m[1]);
      m = re.exec(askPanelSource);
    }
    expect(used.size).toBeGreaterThan(0);
    const keySet = new Set(ASK_PANEL_ORCHESTRATION_RETURN_KEYS);
    for (const k of used) {
      expect(keySet.has(k)).toBe(true);
    }
  });

  it("useAskPanelOrchestration return block includes every canonical key", () => {
    const orch = readFileSync(join(__dirname, "useAskPanelOrchestration.js"), "utf8");
    const returnIdx = orch.lastIndexOf("\n  return {");
    expect(returnIdx).toBeGreaterThan(-1);
    const tail = orch.slice(returnIdx);
    for (const k of ASK_PANEL_ORCHESTRATION_RETURN_KEYS) {
      const lineMatch = new RegExp(`^\\s{4}${k},`, "m").test(tail);
      expect(lineMatch, `missing return key: ${k}`).toBe(true);
    }
  });
});
