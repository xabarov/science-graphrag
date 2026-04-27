import React from "react";

import GraphCaseInspectorPanel from "./GraphCaseInspectorPanel.jsx";
import Layer1CaseInspectorPanel from "./Layer1CaseInspectorPanel.jsx";
import Layer2CaseInspectorPanel from "./Layer2CaseInspectorPanel.jsx";

/**
 * @param {{ family: string, caseDetail: Record<string, unknown> | null, fixtureDetail: Record<string, unknown> | null, caseId: string | null }} props
 */
export function renderFamilyInspectorPanel({ family, caseDetail, fixtureDetail, caseId }) {
  const fam = (family || "layer1").toLowerCase();
  const gold = /** @type {Record<string, unknown> | undefined} */ (caseDetail?.gold)?.payload;
  const hasGraphExpectations = Boolean(gold?.graph_expectations);
  if (hasGraphExpectations) {
    return <GraphCaseInspectorPanel caseId={caseId} caseDetail={caseDetail} fixtureDetail={fixtureDetail} />;
  }
  if (fam === "layer2") {
    return <Layer2CaseInspectorPanel caseDetail={caseDetail} />;
  }
  return <Layer1CaseInspectorPanel caseDetail={caseDetail} />;
}
