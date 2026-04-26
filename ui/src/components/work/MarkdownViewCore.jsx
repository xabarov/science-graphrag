import React from "react";
import Box from "@mui/material/Box";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import rehypeKatex from "rehype-katex";
import rehypeSlug from "rehype-slug";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";

import "highlight.js/styles/github-dark.min.css";
import "katex/dist/katex.min.css";

/** @type {Record<string, unknown>} */
export const readerMarkdownProseSx = {
  color: "rgba(255,255,255,0.86)",
  fontSize: "0.875rem",
  lineHeight: 1.65,
  wordBreak: "break-word",
  "& h1, & h2, & h3, & h4": {
    color: "rgba(255,255,255,0.92)",
    fontWeight: 600,
    letterSpacing: "-0.02em",
    mt: 2,
    mb: 1,
    scrollMarginTop: "1rem",
  },
  "& h1": { fontSize: "1.25rem" },
  "& h2": { fontSize: "1.1rem" },
  "& h3": { fontSize: "1rem" },
  "& p": { mb: 1.25 },
  "& a": { color: "rgba(129,140,248,0.95)", textDecoration: "underline" },
  "& ul, & ol": { pl: 2.5, mb: 1.25 },
  "& li": { mb: 0.35 },
  "& blockquote": {
    borderLeft: "3px solid rgba(99,102,241,0.45)",
    pl: 1.5,
    my: 1.5,
    color: "rgba(255,255,255,0.65)",
  },
  "& table": {
    width: "100%",
    borderCollapse: "collapse",
    fontSize: "0.8125rem",
    my: 1.5,
  },
  "& th, & td": {
    border: "1px solid rgba(255,255,255,0.1)",
    px: 1,
    py: 0.5,
  },
  "& th": { backgroundColor: "rgba(255,255,255,0.04)" },
  "& pre": {
    overflow: "auto",
    p: 1.25,
    borderRadius: "6px",
    border: "1px solid rgba(255,255,255,0.08)",
    backgroundColor: "#0a0a0a",
    fontSize: "0.75rem",
    my: 1.25,
  },
  "& code": {
    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
    fontSize: "0.8125em",
  },
  "& p code, & li code, & td code": {
    px: 0.5,
    py: 0.125,
    borderRadius: "4px",
    backgroundColor: "rgba(255,255,255,0.06)",
    border: "1px solid rgba(255,255,255,0.08)",
  },
  "& pre code": {
    fontSize: "inherit",
    p: 0,
    border: "none",
    backgroundColor: "transparent",
  },
  "& .katex-display": { overflow: "auto", my: 1.5 },
};

/**
 * Synchronous markdown → React tree (used inside lazy boundary and in SSR tests).
 * @param {{ markdown: string, "data-testid"?: string }} props
 */
export default function MarkdownViewCore({ markdown = "", "data-testid": dataTestId }) {
  return (
    <Box
      className="reader-markdown"
      data-testid={dataTestId}
      sx={readerMarkdownProseSx}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeSlug, rehypeKatex, rehypeHighlight]}
      >
        {markdown}
      </ReactMarkdown>
    </Box>
  );
}
