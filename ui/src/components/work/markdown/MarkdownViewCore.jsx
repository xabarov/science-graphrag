import React, { useLayoutEffect, useMemo } from "react";
import Box from "@mui/material/Box";
import { useTheme } from "@mui/material/styles";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import rehypeKatex from "rehype-katex";
import rehypeSlug from "rehype-slug";
import remarkBreaks from "remark-breaks";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";

import hljsGithubDarkUrl from "highlight.js/styles/github-dark.min.css?url";
import hljsGithubLightUrl from "highlight.js/styles/github.min.css?url";
import "katex/dist/katex.min.css";

const HLJS_LINK_ID = "science-graphrag-hljs-theme";

/**
 * @param {import("../../theme/appTokensTypes.js").AppTokens} tk
 * @returns {Record<string, unknown>}
 */
export function getReaderMarkdownProseSx(tk) {
  return {
    color: tk.text.primary,
    fontSize: "0.90625rem",
    lineHeight: 1.7,
    wordBreak: "break-word",
    "& h1, & h2, & h3, & h4": {
      color: tk.text.primary,
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
    "& strong, & b": { color: tk.text.primary, fontWeight: 600 },
    "& em, & i": { color: tk.text.secondary, fontStyle: "italic" },
    "& a": { color: tk.text.accent, textDecoration: "underline" },
    "& ul, & ol": { pl: 2.5, mb: 1.25 },
    "& li": { mb: 0.35 },
    "& hr": {
      border: "none",
      borderTop: `1px solid ${tk.border.strong}`,
      my: 2,
    },
    "& blockquote": {
      borderLeft: `3px solid ${tk.accent.softBorder}`,
      pl: 1.5,
      my: 1.5,
      color: tk.text.secondary,
    },
    "& table": {
      width: "100%",
      borderCollapse: "collapse",
      fontSize: "0.8125rem",
      my: 1.5,
      tableLayout: "fixed",
    },
    "& th, & td": {
      border: `1px solid ${tk.border.strong}`,
      px: 1,
      py: 0.5,
      wordBreak: "break-word",
      overflowWrap: "anywhere",
    },
    "& th": { backgroundColor: tk.surface.subtle },
    "& pre": {
      overflow: "auto",
      maxWidth: "100%",
      p: 1.25,
      borderRadius: "6px",
      border: `1px solid ${tk.border.default}`,
      backgroundColor: tk.surface.code,
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
      backgroundColor: tk.surface.subtle,
      border: `1px solid ${tk.border.default}`,
    },
    "& pre code": {
      fontSize: "inherit",
      p: 0,
      border: "none",
      backgroundColor: "transparent",
    },
    "& .katex-display": { overflow: "auto", my: 1.5 },
  };
}

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
  if (!/^```[\w+-]*\s*$/.test(first) || last !== "```") return source;
  const inner = lines.slice(start + 1, end).join("\n");
  return inner.length ? inner : source;
}

/**
 * VL PDF dumps often indent every line with 4+ spaces. In CommonMark that turns the
 * whole document into an indented code block, so `**bold**` stays literal in <pre>.
 * Strip one uniform block of 4 leading spaces per line when every non-empty line has it.
 *
 * @param {string} source
 * @returns {string}
 */
export function stripUniformFourSpaceIndent(source) {
  if (source == null || typeof source !== "string") return "";
  const lines = source.replace(/\r\n/g, "\n").split("\n");
  const nonempty = lines.filter((l) => l.trim().length > 0);
  if (nonempty.length === 0) return source;
  if (!nonempty.every((l) => /^ {4}/.test(l))) return source;
  return lines.map((l) => (l.startsWith("    ") ? l.slice(4) : l)).join("\n");
}

/**
 * Light normalization so VL/OCR dumps render more predictably in react-markdown.
 * @param {string} source
 */
export function preprocessReaderMarkdown(source) {
  if (source == null || typeof source !== "string") return "";
  let t = source.replace(/\r\n/g, "\n").replace(/\r/g, "\n").replace(/\u00a0/g, " ");
  t = unwrapOuterMarkdownCodeFence(t);
  for (let i = 0; i < 64; i += 1) {
    const next = stripUniformFourSpaceIndent(t);
    if (next === t) break;
    t = next;
  }
  return t.trimEnd();
}

/**
 * Synchronous markdown → React tree (used inside lazy boundary and in SSR tests).
 * @param {{ markdown: string, "data-testid"?: string }} props
 */
export default function MarkdownViewCore({ markdown = "", "data-testid": dataTestId }) {
  const theme = useTheme();
  const tk = theme.appTokens;
  const proseSx = useMemo(() => getReaderMarkdownProseSx(tk), [tk]);

  useLayoutEffect(() => {
    const href = theme.palette.mode === "light" ? hljsGithubLightUrl : hljsGithubDarkUrl;
    let link = document.getElementById(HLJS_LINK_ID);
    if (!link) {
      link = document.createElement("link");
      link.id = HLJS_LINK_ID;
      link.rel = "stylesheet";
      document.head.appendChild(link);
    }
    link.href = href;
  }, [theme.palette.mode]);

  const body = preprocessReaderMarkdown(markdown);
  return (
    <Box
      className="reader-markdown"
      data-testid={dataTestId}
      sx={{
        ...proseSx,
        maxWidth: "100%",
        minWidth: 0,
        overflowX: "auto",
      }}
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
