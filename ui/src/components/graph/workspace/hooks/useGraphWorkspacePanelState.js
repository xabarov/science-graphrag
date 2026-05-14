import { useEffect, useState } from "react";

import {
  LS_EMBEDDED_LEGEND,
  LS_GRAPH_CANVAS_COLOR_BY,
  LS_GRAPH_CANVAS_COMMUNITY_HULLS,
  LS_GRAPH_CANVAS_LAYOUT_MODE,
  LS_GRAPH_STANDALONE_DETAIL_MIN_PX,
  LS_GRAPH_VIZ_MODE,
  LS_STANDALONE_DETAILS,
  LS_STANDALONE_LEGEND,
  readBoolLs,
  readGraphColorByStored,
  readGraphDetailColumnPxStored,
  readLsLayout,
  readLsMode,
} from "../graphWorkspacePanelStorage.js";

/**
 * Local UI state + localStorage persistence for the graph workspace shell.
 *
 * @param {{ standalone: boolean, focusLayout: boolean, labMode: boolean }} opts
 */
export function useGraphWorkspacePanelState({ standalone, focusLayout, labMode }) {
  const [vizMode, setVizMode] = useState(() => (standalone ? "canvas" : readLsMode()));
  const [canvasLayoutMode, setCanvasLayoutMode] = useState(() => (standalone ? "force" : readLsLayout()));
  const [detailsVisible, setDetailsVisible] = useState(() => (standalone ? readBoolLs(LS_STANDALONE_DETAILS, !focusLayout) : true));
  const [legendOpen, setLegendOpen] = useState(() =>
    standalone ? readBoolLs(LS_STANDALONE_LEGEND, !focusLayout) : readBoolLs(LS_EMBEDDED_LEGEND, true),
  );
  const [diagnosticsOpen, setDiagnosticsOpen] = useState(labMode);
  const [detailMinPx, setDetailMinPx] = useState(() => readGraphDetailColumnPxStored());
  const [localFindQuery, setLocalFindQuery] = useState("");
  const [centerCanvasNonce, setCenterCanvasNonce] = useState(0);
  const [centerCanvasNodeId, setCenterCanvasNodeId] = useState("");
  const [graphColorBy, setGraphColorBy] = useState(() => readGraphColorByStored());
  const [graphCommunityHulls, setGraphCommunityHulls] = useState(() => readBoolLs(LS_GRAPH_CANVAS_COMMUNITY_HULLS, false));

  useEffect(() => {
    if (standalone) window.localStorage.setItem(LS_GRAPH_STANDALONE_DETAIL_MIN_PX, String(detailMinPx));
  }, [standalone, detailMinPx]);
  useEffect(() => {
    if (standalone) window.localStorage.setItem(LS_STANDALONE_DETAILS, detailsVisible ? "1" : "0");
  }, [standalone, detailsVisible]);
  useEffect(() => {
    if (standalone) window.localStorage.setItem(LS_STANDALONE_LEGEND, legendOpen ? "1" : "0");
    else window.localStorage.setItem(LS_EMBEDDED_LEGEND, legendOpen ? "1" : "0");
  }, [standalone, legendOpen]);
  useEffect(() => {
    if (!standalone) window.localStorage.setItem(LS_GRAPH_VIZ_MODE, vizMode);
  }, [standalone, vizMode]);
  useEffect(() => {
    if (!standalone) window.localStorage.setItem(LS_GRAPH_CANVAS_LAYOUT_MODE, canvasLayoutMode);
  }, [standalone, canvasLayoutMode]);

  useEffect(() => {
    try {
      window.localStorage.setItem(LS_GRAPH_CANVAS_COLOR_BY, graphColorBy);
    } catch {
      /* ignore */
    }
  }, [graphColorBy]);

  useEffect(() => {
    try {
      window.localStorage.setItem(LS_GRAPH_CANVAS_COMMUNITY_HULLS, graphCommunityHulls ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [graphCommunityHulls]);

  return {
    vizMode,
    setVizMode,
    canvasLayoutMode,
    setCanvasLayoutMode,
    detailsVisible,
    setDetailsVisible,
    legendOpen,
    setLegendOpen,
    diagnosticsOpen,
    setDiagnosticsOpen,
    detailMinPx,
    setDetailMinPx,
    localFindQuery,
    setLocalFindQuery,
    centerCanvasNonce,
    setCenterCanvasNonce,
    centerCanvasNodeId,
    setCenterCanvasNodeId,
    graphColorBy,
    setGraphColorBy,
    graphCommunityHulls,
    setGraphCommunityHulls,
  };
}
