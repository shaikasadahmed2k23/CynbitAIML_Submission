"""Parse unified diffs into structured files / hunks / lines."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

LANG_BY_EXT = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript", ".ts": "TypeScript",
    ".tsx": "TypeScript", ".java": "Java", ".go": "Go", ".rb": "Ruby", ".php": "PHP",
    ".sql": "SQL", ".html": "HTML", ".css": "CSS", ".md": "Markdown", ".yml": "YAML",
    ".yaml": "YAML", ".json": "JSON", ".sh": "Shell", ".toml": "TOML", ".dockerfile": "Docker",
}


@dataclass
class Line:
    kind: str  # "add" | "del" | "ctx"
    text: str
    new_no: int | None = None
    old_no: int | None = None


@dataclass
class Hunk:
    old_start: int
    new_start: int
    lines: list[Line] = field(default_factory=list)


@dataclass
class FileDiff:
    path: str
    old_path: str | None = None
    is_new: bool = False
    is_deleted: bool = False
    hunks: list[Hunk] = field(default_factory=list)

    @property
    def language(self) -> str:
        name = self.path.lower()
        if name.endswith("dockerfile") or name == "dockerfile":
            return "Docker"
        dot = name.rfind(".")
        return LANG_BY_EXT.get(name[dot:], "Other") if dot != -1 else "Other"

    @property
    def added(self) -> list[Line]:
        return [l for h in self.hunks for l in h.lines if l.kind == "add"]

    @property
    def removed(self) -> list[Line]:
        return [l for h in self.hunks for l in h.lines if l.kind == "del"]


@dataclass
class ParsedDiff:
    files: list[FileDiff]

    @property
    def added_lines(self) -> int:
        return sum(len(f.added) for f in self.files)

    @property
    def removed_lines(self) -> int:
        return sum(len(f.removed) for f in self.files)

    @property
    def languages(self) -> list[str]:
        return sorted({f.language for f in self.files if f.language != "Other"})

    def valid_lines(self) -> dict[str, set[int]]:
        """Map path -> set of new-file line numbers that exist in the diff (for anchoring comments)."""
        out: dict[str, set[int]] = {}
        for f in self.files:
            out[f.path] = {l.new_no for h in f.hunks for l in h.lines if l.new_no is not None and l.kind != "del"}
        return out

    def added_code(self) -> str:
        return "\n".join(l.text for f in self.files for l in f.added)


def _strip_prefix(p: str) -> str:
    p = p.strip()
    if p.startswith(("a/", "b/")):
        p = p[2:]
    return p


def parse_diff(text: str) -> ParsedDiff:
    files: list[FileDiff] = []
    cur: FileDiff | None = None
    hunk: Hunk | None = None
    old_no = new_no = 0
    for raw in text.splitlines():
        if raw.startswith("diff --git"):
            parts = raw.split(" ")
            path = _strip_prefix(parts[-1]) if len(parts) >= 4 else ""
            cur = FileDiff(path=path)
            files.append(cur)
            hunk = None
        elif raw.startswith("new file mode") and cur:
            cur.is_new = True
        elif raw.startswith("deleted file mode") and cur:
            cur.is_deleted = True
        elif raw.startswith("--- "):
            if cur is None:  # plain unified diff without "diff --git"
                cur = FileDiff(path="")
                files.append(cur)
            p = raw[4:].strip()
            if p == "/dev/null":
                cur.is_new = True
            else:
                cur.old_path = _strip_prefix(p)
        elif raw.startswith("+++ "):
            if cur is None:
                cur = FileDiff(path="")
                files.append(cur)
            p = raw[4:].strip()
            if p == "/dev/null":
                cur.is_deleted = True
            else:
                cur.path = _strip_prefix(p)
        else:
            m = HUNK_RE.match(raw)
            if m and cur is not None:
                old_no, new_no = int(m.group(1)), int(m.group(3))
                hunk = Hunk(old_start=old_no, new_start=new_no)
                cur.hunks.append(hunk)
            elif hunk is not None:
                if raw.startswith("+"):
                    hunk.lines.append(Line("add", raw[1:], new_no=new_no)); new_no += 1
                elif raw.startswith("-"):
                    hunk.lines.append(Line("del", raw[1:], old_no=old_no)); old_no += 1
                elif raw.startswith("\\"):
                    continue  # "\ No newline at end of file"
                else:
                    hunk.lines.append(Line("ctx", raw[1:] if raw.startswith(" ") else raw, new_no=new_no, old_no=old_no))
                    new_no += 1; old_no += 1
    return ParsedDiff(files=[f for f in files if f.path])
