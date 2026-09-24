"""Build the tracked-changes manuscript for resubmission.

Compares the current manuscript with the version originally submitted and writes a copy of the
current manuscript in which every added or changed passage is wrapped as [text]{.rev}. The Lua
filter paper/revision-markup.lua renders those passages in colour in the PDF, Word and HTML outputs.

Sentences that were lightly edited (for example, a changed number) are marked word by word;
sentences that were rewritten or are new are marked whole. Deleted text is not shown.

Usage (from the repository root):
    python3 scripts/mark_revisions.py
    quarto render paper/K-S-Database-Resource-Paper_revised.qmd --to elsevier-pdf
    quarto render paper/K-S-Database-Resource-Paper_revised.qmd --to elsevier-docx
"""

import difflib
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SUBMITTED = REPO / "paper" / "submitted_reference" / "K-S-Database-Resource-Paper_submitted.qmd"
CURRENT = REPO / "paper" / "K-S-Database-Resource-Paper.qmd"
OUTPUT = REPO / "paper" / "K-S-Database-Resource-Paper_revised.qmd"

# A changed sentence is marked word by word only if it still closely resembles a submitted
# sentence and most of its words are unchanged; otherwise the whole sentence is marked.
WORD_LEVEL_MIN_SIMILARITY = 0.6
WORD_LEVEL_MAX_CHANGED_FRACTION = 0.5

REVISION_NOTE = "*Text added or changed in this revision is shown in blue.*"

ABBREVIATIONS = ("e.g.", "i.e.", "et al.", "vs.", "Fig.", "cf.", "approx.", "St.")
LIST_ITEM = re.compile(r"^(\s*(?:\d+\.|[-*])\s+)(.*)$")
HEADING = re.compile(r"^(#+\s+)(.*)$")
TOKEN = re.compile(r"\[@[^\]]*\]|\$[^$]*\$|\S+")


# ---- Text normalisation ----

def normalise(text):
    """Comparison form: ignores emphasis markers, escapes, quote and dash styles."""
    t = text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    t = re.sub(r"—|–|--", "-", t)
    t = re.sub(r"\\(?=[^A-Za-z])", "", t)          # markdown escapes such as \- \[ \~
    t = t.replace("**", "").replace("*", "")
    return re.sub(r"\s+", " ", t).strip()


def balanced(s):
    """True if wrapping s in a span cannot break the surrounding markdown."""
    if s.count("[") != s.count("]") or s.count("(") != s.count(")") or s.count("{") != s.count("}"):
        return False
    if s.count("**") % 2 or s.replace("**", "").count("*") % 2:
        return False
    if s.count("$") % 2 or s.count("`") % 2:
        return False
    return not s.rstrip().endswith("\\")


def split_sentences(text):
    """Sentence units, merged where needed so that each unit is balanced markdown."""
    pieces, start = [], 0
    for m in re.finditer(r"(?<=[.!?])\s+(?=[A-Z\[*\"“(0-9@])", text):
        before = text[:m.start()]
        if any(before.endswith(a) for a in ABBREVIATIONS):
            continue
        pieces.append(text[start:m.start()])
        start = m.end()
    pieces.append(text[start:])
    units, buf = [], ""
    for p in pieces:
        buf = p if not buf else buf + " " + p
        if balanced(buf):
            units.append(buf)
            buf = ""
    if buf:
        units.append(buf)
    return units


# ---- Walking the manuscript ----

def body_of(qmd):
    m = re.match(r"^---\n.*?\n---\n", qmd, re.S)
    return qmd[:m.end()], qmd[m.end():]


def figure_parts(line):
    """Split '![caption](path){attrs}' into (prefix, caption, suffix), matching nested brackets."""
    depth = 0
    for i, ch in enumerate(line[1:], start=1):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return line[:2], line[2:i], line[i:]
    return None


def walk(body, on_text, on_table_row):
    """Apply on_text to every prose unit (paragraph, list item, heading, caption) and
    on_table_row to every table row, returning the rebuilt body."""
    out = []
    for block in re.split(r"(\n\s*\n)", body):
        if not block.strip() or re.fullmatch(r"\n\s*\n", block):
            out.append(block)
            continue
        new_lines = []
        for line in block.split("\n"):
            s = line.strip()
            if not s or s.startswith(":::") or s.startswith("\\") or re.fullmatch(r"\|[\s:|-]+\|", s):
                new_lines.append(line)
            elif s.startswith("|"):
                new_lines.append(on_table_row(line))
            elif s.startswith("!["):
                parts = figure_parts(line)
                new_lines.append(line if parts is None else parts[0] + on_text(parts[1]) + parts[2])
            elif HEADING.match(line):
                pre, text = HEADING.match(line).groups()
                new_lines.append(pre + on_text(text, whole=True))
            elif LIST_ITEM.match(line):
                pre, text = LIST_ITEM.match(line).groups()
                new_lines.append(pre + on_text(text))
            else:
                new_lines.append(on_text(line))
        out.append("\n".join(new_lines))
    return "".join(out)


# ---- Marking ----

def wrap(s):
    lead = s[: len(s) - len(s.lstrip())]
    trail = s[len(s.rstrip()):]
    core = s.strip()
    return f"{lead}[{core}]{{.rev}}{trail}" if core else s


class Marker:
    def __init__(self, submitted_body):
        self.units, self.rows = [], set()

        def collect(text, whole=False):
            for u in ([text] if whole else split_sentences(text)):
                if normalise(u):
                    self.units.append(normalise(u))
            return text

        def collect_row(line):
            self.rows.add(normalise(line))
            return line

        walk(submitted_body, collect, collect_row)
        self.unit_set = set(self.units)
        self.marked_words = 0
        self.total_words = 0

    def best_match(self, norm):
        best, best_ratio = None, 0.0
        for cand in self.units:
            sm = difflib.SequenceMatcher(None, norm.split(), cand.split(), autojunk=False)
            if sm.real_quick_ratio() <= best_ratio or sm.quick_ratio() <= best_ratio:
                continue
            r = sm.ratio()
            if r > best_ratio:
                best, best_ratio = cand, r
        return best, best_ratio

    def mark_unit(self, unit):
        norm = normalise(unit)
        n_words = len(norm.split())
        self.total_words += n_words
        if not norm or norm in self.unit_set:
            return unit
        match, ratio = self.best_match(norm)
        if match is not None and ratio >= WORD_LEVEL_MIN_SIMILARITY:
            marked = self.mark_words(unit, match)
            if marked is not None:
                return marked
        self.marked_words += n_words
        return wrap(unit)

    def mark_words(self, unit, match):
        toks = list(TOKEN.finditer(unit))
        cur = [normalise(t.group()) for t in toks]
        sm = difflib.SequenceMatcher(None, cur, match.split(), autojunk=False)
        # a = current tokens, b = submitted: words only in the current text are "delete" or "replace"
        runs = [(i1, i2) for tag, i1, i2, _, _ in sm.get_opcodes() if tag in ("replace", "delete")]
        changed = sum(i2 - i1 for i1, i2 in runs)
        if changed / max(len(toks), 1) > WORD_LEVEL_MAX_CHANGED_FRACTION:
            return None
        pieces, pos = [], 0
        for i1, i2 in runs:
            a, b = toks[i1].start(), toks[i2 - 1].end()
            if not balanced(unit[a:b]):
                return None
            pieces += [unit[pos:a], wrap(unit[a:b])]
            pos = b
        pieces.append(unit[pos:])
        self.marked_words += changed
        return "".join(pieces)

    def mark_text(self, text, whole=False):
        if whole:
            return self.mark_unit(text)
        return " ".join(self.mark_unit(u) for u in split_sentences(text))

    def mark_row(self, line):
        if normalise(line) in self.rows:
            return line
        cells = line.strip().strip("|").split("|")
        self.marked_words += sum(len(c.split()) for c in cells)
        return "| " + " | ".join(wrap(c.strip()) for c in cells) + " |"


def add_markup_options(yaml):
    """Point the revised document at the colour filter and the Word style template."""
    y = yaml.replace("  elsevier-docx: \n", "  elsevier-docx:\n", 1)
    y = y.replace("  elsevier-docx:\n", "  elsevier-docx:\n    reference-doc: revised-reference.docx\n", 1)
    assert "revised-reference.docx" in y, "could not find the elsevier-docx format block"
    return y.replace("\n---\n", "\nfilters:\n  - revision-markup.lua\n---\n", 1) if y.endswith("\n---\n") else y


def main():
    _, submitted_body = body_of(SUBMITTED.read_text(encoding="utf-8"))
    yaml, current_body = body_of(CURRENT.read_text(encoding="utf-8"))
    marker = Marker(submitted_body)
    revised = walk(current_body, marker.mark_text, marker.mark_row)
    revised = revised.replace("# Abstract", REVISION_NOTE + "\n\n# Abstract", 1)
    OUTPUT.write_text(add_markup_options(yaml) + revised, encoding="utf-8")
    pct = 100 * marker.marked_words / max(marker.total_words, 1)
    print(f"wrote {OUTPUT.relative_to(REPO)}: {revised.count('{.rev}')} marked passages, "
          f"~{pct:.0f}% of words marked as added or changed")


if __name__ == "__main__":
    main()
