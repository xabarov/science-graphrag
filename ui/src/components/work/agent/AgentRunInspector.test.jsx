/** @vitest-environment jsdom */
import { ThemeProvider } from "@mui/material/styles";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { normalizeQueryResponse } from "../../services/researchApi.js";
import { buildAppTheme } from "../../theme/buildAppTheme.js";
import { AgentRunInspector } from "./AgentRunInspector.jsx";

const theme = buildAppTheme("dark");

function t(key) {
  return key;
}

function renderInspector(props) {
  return render(
    <ThemeProvider theme={theme}>
      <AgentRunInspector
        t={t}
        locked={false}
        inWorkspace={false}
        workId=""
        retrievalMode="agent"
        agentToolTrace={[]}
        retrievalJsonOpen={false}
        onToggleRetrievalJson={() => {}}
        {...props}
      />
    </ThemeProvider>,
  );
}

describe("AgentRunInspector", () => {
  it("renders nothing when inspector is not offered", () => {
    const normalized = normalizeQueryResponse({
      answer: "only",
      citations: [],
      graph_context: {},
      retrieval_trace: {},
    });
    const { container } = renderInspector({ normalized, streamEvents: [] });
    expect(container.firstChild).toBeNull();
  });

  it("expands inspection region on toggle", async () => {
    const normalized = normalizeQueryResponse({
      answer: "ok",
      citations: [],
      graph_context: {},
      retrieval_trace: { hit_count: 2, citations_returned: 2 },
    });
    renderInspector({
      normalized,
      streamEvents: [{ type: "intent_classified", answer_class: "inventory", source: "h" }],
    });
    const toggle = screen.getByRole("button", { name: "chat.run.inspectToggleShowAria" });
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(toggle);
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    await waitFor(() => {
      expect(screen.getByRole("region", { name: "chat.run.inspectTitle" })).toBeTruthy();
    });
  });
});
