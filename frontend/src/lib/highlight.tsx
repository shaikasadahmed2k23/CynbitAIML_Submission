import type { ReactNode } from "react";

const KEYWORDS = new Set(
  ("def class return if else elif for while in import from as try except finally with lambda None True False and or not is pass " +
   "break continue raise yield async await function const let var new this null undefined export default require module throw " +
   "catch switch case self global public private static void int string interface type extends").split(" "),
);
const TOKEN = /(#.*$|\/\/.*$)|("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|\x60(?:[^\x60\\]|\\.)*\x60)|(\b\d[\d_.]*\b)|(\b[A-Za-z_][A-Za-z0-9_]*\b)/g;

/** Tiny single-line syntax highlighter (no dependency, good enough for review snippets). */
export function highlight(line: string): ReactNode[] {
  const out: ReactNode[] = [];
  let last = 0;
  let i = 0;
  for (const m of line.matchAll(TOKEN)) {
    const idx = m.index ?? 0;
    if (idx > last) out.push(line.slice(last, idx));
    const [txt, comment, str, num, word] = m;
    if (comment) out.push(<span key={i++} className="tok-c">{txt}</span>);
    else if (str) out.push(<span key={i++} className="tok-s">{txt}</span>);
    else if (num) out.push(<span key={i++} className="tok-n">{txt}</span>);
    else if (word && KEYWORDS.has(word)) out.push(<span key={i++} className="tok-k">{txt}</span>);
    else out.push(txt);
    last = idx + txt.length;
  }
  if (last < line.length) out.push(line.slice(last));
  return out;
}
