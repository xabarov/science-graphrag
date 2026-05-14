import { useCallback, useMemo } from "react";

import { extractOpenStructuredQuestion, extractResearchPlanStreamHint } from "../session/askStreamArtifacts.js";

/**
 * Derived research plan + structured-question payloads from normalized answer / history / stream.
 */
export function useAskPanelStreamArtifacts({
  t,
  normalized,
  history,
  streamEvents,
  performAgentSubmit,
}) {
  const researchPlanForPanel = useMemo(() => {
    const rm =
      normalized && typeof normalized === "object" && normalized.run_metadata && typeof normalized.run_metadata === "object"
        ? normalized.run_metadata
        : null;
    if (rm?.research_plan && typeof rm.research_plan === "object") return rm.research_plan;
    const h0 = history[0];
    const hrm = h0?.details?.run_metadata;
    if (hrm && typeof hrm === "object" && hrm.research_plan && typeof hrm.research_plan === "object") return hrm.research_plan;
    return null;
  }, [normalized, history]);

  const researchPlanStreamHint = useMemo(() => extractResearchPlanStreamHint(streamEvents), [streamEvents]);

  const openStructuredQuestion = useMemo(() => {
    const head = history[0];
    const d = head?.details;
    const fromEvents = Array.isArray(d?.stream_events) ? extractOpenStructuredQuestion(d.stream_events) : null;
    if (fromEvents) return fromEvents;
    if (d?.open_structured_question && typeof d.open_structured_question === "object") {
      const rq = d.open_structured_question;
      if (Array.isArray(rq.questions) && rq.questions.length && String(rq.request_id || "").trim()) {
        return rq;
      }
    }
    return null;
  }, [history]);

  const onStructuredAnswersSubmit = useCallback(
    async (payload) => {
      const rid = String(payload?.request_id || "").trim();
      const answers = Array.isArray(payload?.answers) ? payload.answers : [];
      if (!rid || !answers.length) return;
      await performAgentSubmit(t("askPanel.userQuestion.continuePlaceholder"), {
        userStructuredAnswer: { request_id: rid, answers },
      });
    },
    [performAgentSubmit, t],
  );

  return {
    researchPlanForPanel,
    researchPlanStreamHint,
    openStructuredQuestion,
    onStructuredAnswersSubmit,
  };
}
