/** @vitest-environment jsdom */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

import { AgentLiveStatus } from "./AgentLiveStatus.jsx";

function t(key, vars = {}) {
  let out =
    {
      "chat.run.liveStripTitle": "Live",
      "chat.stream.thinking": "Thinking…",
      "chat.stream.intent": "Intent:{{cls}}:{{src}}",
    }[key] || key;
  Object.entries(vars).forEach(([k, v]) => {
    out = out.split(`{{${k}}}`).join(String(v));
  });
  return out;
}

describe("AgentLiveStatus", () => {
  it("shows shimmer when active and no meaningful events yet", () => {
    render(<AgentLiveStatus t={t} streamEvents={[]} isActive />);
    expect(screen.getByText("Thinking…")).toBeTruthy();
  });

  it("shows last meaningful stream line when inactive", () => {
    render(
      <AgentLiveStatus
        t={t}
        streamEvents={[{ type: "intent_classified", answer_class: "inventory", source: "h" }]}
        isActive={false}
      />,
    );
    expect(screen.getByText("Intent:inventory:h")).toBeTruthy();
  });
});
