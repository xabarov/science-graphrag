import React from "react";
import Box from "@mui/material/Box";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import rehypeKatex from "rehype-katex";
import rehypeSlug from "rehype-slug";
import remarkBreaks from "remark-breaks";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";

import "highlight.js/styles/github-dark.min.css";
import "katex/dist/katex.min.css";

/**
 * VL models often wrap the full extraction in one fenced block (```markdown … ```).
 * react-markdown then emits a single <pre><code>, so **bold** stays literal.
 *
 * @param {string} source
 * @returns {string}
 */
export function unwrapOuterMarkdownCodeFence(source) {
  if (source == null || typeof source !== "string") return "";
  const normalized = source.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  const lines = normalized.split("\n");
  let start = 0;
  let end = lines.length - 1;
  while (start < lines.length && lines[start].trim() === "") start += 1;
  while (end >= start && lines[end].trim() === "") end -= 1;
  if (end <= start) return source;
  const first = lines[start].trim().replace(/^\uFEFF/, "");
  const last = lines[end].trim();
  if (!/^```[\w+-]*$/.test(first) || last !== "```") return source;
  const inner = lines.slice(start + 1, end).join("\n");
  return inner.length ? inner : source;
}

/**
 * Light normalization so VL/OCR dumps render more predictably in react-markdown.
 * @param {string} source
 */
export function preprocessReaderMarkdown(source) {
  if (source == null || typeof source !== "string") return "";
  let t = source.replace(/\r\n/g, "\n").replace(/\r/g, "\n").replace(/\u00a0/g, " ");
  t = unwrapOuterMarkdownCodeFence(t);
  return t.trimEnd();
}

/** @type {Record<string, unknown>} */
export const readerMarkdownProseSx = {
  color: "rgba(255,255,255,0.88)",
  fontSize: "0.90625rem",
  lineHeight: 1.7,
  wordBreak: "break-word",
  "& h1, & h2, & h3, & h4": {
    color: "rgba(255,255,255,0.94)",
    fontWeight: 600,
    letterSpacing: "-0.02em",
    mt: 2,
    mb: 1,
    scrollMarginTop: "1rem",
  },
  "& h1": { fontSize: "1.35rem", lineHeight: 1.25 },
  "& h2": { fontSize: "1.15rem", lineHeight: 1.3 },
  "& h3": { fontSize: "1.02rem", lineHeight: 1.35 },
  "& h4": { fontSize: "0.95rem", lineHeight: 1.4 },
  "& h1:first-of-type, & h2:first-of-type, & h3:first-of-type": { mt: 0 },
  "& p": { mb: 1.1 },
  "& strong, & b": { color: "rgba(255,255,255,0.95)", fontWeight: 600 },
  "& em, & i": { color: "rgba(255,255,255,0.82)", fontStyle: "italic" },
  "& a": { color: "rgba(129,140,248,0.95)", textDecoration: "underline" },
  "& ul, & ol": { pl: 2.5, mb: 1.25 },
  "& li": { mb: 0.35 },
  "& hr": {
    border: "none",
    borderTop: "1px solid rgba(255,255,255,0.1)",
    my: 2,
  },
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
  const body = preprocessReaderMarkdown(markdown);
  return (
    <Box
      className="reader-markdown"
      data-testid={dataTestId}
      sx={readerMarkdownProseSx}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath, remarkBreaks]}
        rehypePlugins={[rehypeSlug, rehypeKatex, rehypeHighlight]}
      >
        {body}
      </ReactMarkdown>
    </Box>
  );
}
