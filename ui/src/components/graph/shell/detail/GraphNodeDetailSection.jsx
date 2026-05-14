import React, { useState } from "react";

import {
  CLAIM_DETAIL_KEYS_IN_TABLE,
  METHOD_DETAIL_KEYS_IN_TABLE,
  claimBodyFromProperties,
  formatClaimMetadataBlock,
  isClaimSelectedNode,
} from "./detailFormatters.js";
import GraphAggregatorSection from "./detailSections/GraphAggregatorSection.jsx";
import GraphAuthorWorksSection from "./detailSections/GraphAuthorWorksSection.jsx";
import GraphClaimSection from "./detailSections/GraphClaimSection.jsx";
import GraphDefaultNodeHeader from "./detailSections/GraphDefaultNodeHeader.jsx";
import GraphMethodSection from "./detailSections/GraphMethodSection.jsx";
import GraphNodeConnectionsSection from "./detailSections/GraphNodeConnectionsSection.jsx";
import GraphPropertiesSection from "./detailSections/GraphPropertiesSection.jsx";
import GraphRawPayloadSection from "./detailSections/GraphRawPayloadSection.jsx";
import GraphWorkMembershipSection from "./detailSections/GraphWorkMembershipSection.jsx";

/**
 * @param {{
 *   tk: import("@mui/material/styles").Theme["appTokens"],
 *   t: (k: string, opts?: object) => string,
 *   selectedNode: object,
 *   relatedEdges: Array<object>,
 *   relatedEdgeRows: Array<object>,
 *   authorAuthoredWorks: Array<object>,
 *   compact: boolean,
 *   onSelectNode?: (nodeId: string) => void,
 *   onSelectEdge?: (edgeId: string) => void,
 *   onExpandWorkspaceNeighbors?: () => void | Promise<void>,
 *   onAggregatorExpand?: (node: object, expandEndpoint: string) => void | Promise<void>,
 *   expandWorkspaceNeighborsBusy?: boolean,
 * }} props
 */
export default function GraphNodeDetailSection({
  tk,
  t,
  selectedNode,
  relatedEdges,
  relatedEdgeRows,
  authorAuthoredWorks,
  compact,
  onSelectNode,
  onSelectEdge,
  onExpandWorkspaceNeighbors,
  onAggregatorExpand,
  expandWorkspaceNeighborsBusy = false,
}) {
  const [rawOpen, setRawOpen] = useState(false);
  const rows = relatedEdgeRows.length > 0 ? relatedEdgeRows : [];

  if (!selectedNode || typeof selectedNode !== "object") return null;

  const claimNode = isClaimSelectedNode(selectedNode);
  const claimProps =
    claimNode && selectedNode?.properties && typeof selectedNode.properties === "object"
      ? /** @type {Record<string, unknown>} */ (selectedNode.properties)
      : null;
  const claimBody = claimProps ? claimBodyFromProperties(claimProps) : "";
  const claimMetadataFormatted = claimProps ? formatClaimMetadataBlock(claimProps.claim_metadata) : "";
  const isMethodNode = Boolean(selectedNode && String(selectedNode.type) === "Method");
  const methodProps =
    isMethodNode && selectedNode?.properties && typeof selectedNode.properties === "object"
      ? /** @type {Record<string, unknown>} */ (selectedNode.properties)
      : null;
  const methodMarkdownForViewer = methodProps
    ? String(methodProps.description_markdown || "").trim() ||
      String(methodProps.description_plaintext || "").trim() ||
      String(methodProps.description_short || "").trim()
    : "";
  const excludedDetailKeys = claimNode ? CLAIM_DETAIL_KEYS_IN_TABLE : isMethodNode ? METHOD_DETAIL_KEYS_IN_TABLE : new Set();
  const detailPropertyEntries = Object.entries(selectedNode?.properties || {}).filter(([k]) => !excludedDetailKeys.has(k));

  return (
    <>
      {String(selectedNode.nodeKind) === "Aggregator" ? (
        <GraphAggregatorSection
          tk={tk}
          t={t}
          selectedNode={selectedNode}
          onAggregatorExpand={onAggregatorExpand}
          expandWorkspaceNeighborsBusy={expandWorkspaceNeighborsBusy}
        />
      ) : null}
      {String(selectedNode.nodeKind) !== "Aggregator" ? <GraphDefaultNodeHeader tk={tk} t={t} selectedNode={selectedNode} /> : null}

      <GraphWorkMembershipSection
        tk={tk}
        t={t}
        selectedNode={selectedNode}
        onExpandWorkspaceNeighbors={onExpandWorkspaceNeighbors}
        expandWorkspaceNeighborsBusy={expandWorkspaceNeighborsBusy}
      />

      <GraphAuthorWorksSection
        tk={tk}
        t={t}
        selectedNode={selectedNode}
        authorAuthoredWorks={authorAuthoredWorks}
        compact={compact}
        onSelectNode={onSelectNode}
      />

      {claimNode ? (
        <GraphClaimSection
          tk={tk}
          t={t}
          claimBody={claimBody}
          claimMetadataFormatted={claimMetadataFormatted}
          compact={compact}
        />
      ) : null}

      <GraphMethodSection tk={tk} t={t} methodMarkdownForViewer={methodMarkdownForViewer} compact={compact} />

      <GraphPropertiesSection
        tk={tk}
        t={t}
        detailPropertyEntries={detailPropertyEntries}
        claimNode={claimNode}
        isMethodNode={isMethodNode}
      />

      <GraphNodeConnectionsSection tk={tk} t={t} rows={rows} relatedEdges={relatedEdges} onSelectEdge={onSelectEdge} />

      <GraphRawPayloadSection
        tk={tk}
        t={t}
        selectedNode={selectedNode}
        compact={compact}
        rawOpen={rawOpen}
        onRawOpenChange={setRawOpen}
      />
    </>
  );
}
