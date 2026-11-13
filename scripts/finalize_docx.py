"""Finish a manuscript Word file rendered by Quarto (elsevier-docx).

Quarto's Word output lacks parts of the submitted version's front matter and leaves a few layout and
highlighting details undefined. This script edits the .docx in place, as text-level XML edits (nothing
is re-serialised), and is run on both the clean and the tracked-changes manuscript:

  Both files
    * Caption paragraphs: Quarto emits two paragraph-property blocks (in the wrong order) for every
      figure and table caption; they are merged into one schema-valid block so Word applies the
      caption style unambiguously. Table cells carry two alignments (the column's, plus a centring
      Quarto appends to every cell); the column's is kept.
    * Front matter as in the submitted PDF: affiliation letters on each author, the affiliation lines
      and the corresponding-author note, all read from the manuscript's YAML. The stale draft date
      the Word template prints is removed (the submitted PDF shows none).
    * Explicit page setup (US Letter, 1-inch margins). The template defines none, so Word would fall
      back to its own default. No line numbers are added: the journal's system stamps them itself.
    * Figures taller than MAX_IMAGE_HEIGHT_IN are scaled down so a figure and its caption fit a page.
    * Title, headings and captions use the body font and colour, as in the submitted PDF. Quarto's
      Word template sets them in a separate blue display font at 20/16/14 pt and captions in full-size
      italic; see STYLE_TYPOGRAPHY for what they become.

  Tracked-changes file only (--revised)
    * Everything inside a blue passage is coloured, including citation numbers, cross-references and
      inline maths, which a character style does not reach. The range markers that
      paper/revision-markup.lua leaves in the document are used for this and then removed.
    * The template's light-blue hyperlink colour is turned off, so that blue means "changed" and
      nothing else. Otherwise every citation number in unchanged text would be blue as well.
    * References cited only in the revised manuscript are coloured in the reference list.

Usage (from the repository root; scripts/build_word_versions.sh runs everything):
    python3 scripts/finalize_docx.py paper/K-S-Database-Resource-Paper.docx
    python3 scripts/finalize_docx.py --revised paper/K-S-Database-Resource-Paper_revised.docx
"""

import argparse
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CURRENT_QMD = REPO / "paper" / "K-S-Database-Resource-Paper.qmd"
SUBMITTED_QMD = REPO / "paper" / "submitted_reference" / "K-S-Database-Resource-Paper_R1_submitted.qmd"  # baseline, as in mark_revisions.py

REVISION_COLOR = "1F4E9E"      # must match paper/revision-markup.lua and the "Revised" style
EMU_PER_INCH = 914400
MAX_IMAGE_HEIGHT_IN = 6.9      # leaves room for a caption of about 1.5 inches on a 9-inch text block
PAGE_WIDTH_TWIPS, PAGE_HEIGHT_TWIPS, PAGE_MARGIN_TWIPS = 12240, 15840, 1440
HEADER_FOOTER_TWIPS = 720
AFFILIATION_FONT_HALF_POINTS = 18   # 9 pt

# Typography of the title, headings and captions, in half-points. The body is 12 pt (the template's
# document default). Hierarchy comes from weight and a modest size step, never from font or colour.
BODY_FONTS = ('<w:rFonts w:asciiTheme="minorHAnsi" w:eastAsiaTheme="minorHAnsi" '
              'w:hAnsiTheme="minorHAnsi" w:cstheme="minorBidi" />')
STYLE_TYPOGRAPHY = {
    "Title": dict(size=32, bold=True),
    "Heading1": dict(size=28, bold=True),
    "Heading2": dict(size=24, bold=True),
    "Heading3": dict(size=24, italic=True),
    "Caption": dict(size=20),
}

# Children of <w:rPr> that must come after <w:color> in the schema's fixed order.
RPR_AFTER_COLOR = ("spacing", "w", "kern", "position", "sz", "szCs", "highlight", "u", "effect", "bdr",
                   "shd", "fitText", "vertAlign", "rtl", "cs", "em", "lang", "eastAsianLayout", "specVanish", "oMath")
# Children of <w:pPr> in the order the schema requires (only those Quarto/pandoc emit here).
PPR_ORDER = ("pStyle", "keepNext", "keepLines", "pageBreakBefore", "widowControl", "numPr", "pBdr", "shd", "tabs",
             "spacing", "ind", "contextualSpacing", "jc", "outlineLvl", "rPr")
CROSSREF_PREFIXES = ("fig-", "sfig-", "stab-", "tbl-", "sec-", "eq-")


# ---- Manuscript metadata ----

def inlines_text(inlines):
    out = []
    for i in inlines:
        t = i["t"]
        if t == "Str":
            out.append(i["c"])
        elif t in ("Space", "SoftBreak", "LineBreak"):
            out.append(" ")
        elif "c" in i and isinstance(i["c"], list):
            out.append(inlines_text([x for x in i["c"] if isinstance(x, dict)]))
    return "".join(out)


def read_front_matter(qmd):
    """Authors (name, affiliation letters, corresponding) and affiliation lines, from the YAML."""
    raw = subprocess.run(["quarto", "pandoc", str(qmd), "-s", "-t", "json"], capture_output=True, text=True, check=True).stdout
    meta = json.loads(raw)["meta"]
    affiliations = [{k: inlines_text(v["c"]) for k, v in a["c"].items() if v["t"] == "MetaInlines"} for a in meta["affiliations"]["c"]]
    letters = {a["id"]: chr(ord("a") + n) for n, a in enumerate(affiliations)}
    authors = []
    for a in meta["author"]["c"]:
        c = a["c"]
        refs = [letters[inlines_text(r["c"]["ref"]["c"])] for r in c["affiliations"]["c"]]
        authors.append({"name": inlines_text(c["name"]["c"]), "letters": refs, "corresponding": c.get("corresponding", {}).get("c", False)})
    lines = [(letters[a["id"]], ", ".join(a[k] for k in ("name", "city", "country") if k in a)) for a in affiliations]
    return authors, lines


def cited_keys(qmd):
    text = Path(qmd).read_text(encoding="utf-8")
    body = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
    return {k for k in re.findall(r"(?<![\w.])@([A-Za-z][\w:-]*[\w])", body) if not k.startswith(CROSSREF_PREFIXES)}


# ---- XML helpers (text-level) ----

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def run(text, superscript=False, italic=False, size=None):
    props = ""
    if italic:
        props += "<w:i />"
    if size:
        props += f'<w:sz w:val="{size}" /><w:szCs w:val="{size}" />'
    if superscript:
        props += '<w:vertAlign w:val="superscript" />'
    rpr = f"<w:rPr>{props}</w:rPr>" if props else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{esc(text)}</w:t></w:r>'


def paragraph(style, runs):
    return f'<w:p><w:pPr><w:pStyle w:val="{style}" /></w:pPr>{"".join(runs)}</w:p>'


def add_color_to_rpr(inner):
    """Add (or replace) <w:color> in the inside of a <w:rPr>, keeping the schema's child order."""
    color = f'<w:color w:val="{REVISION_COLOR}" />'
    if re.search(r"<w:color\b", inner):
        return re.sub(r"<w:color\b[^>]*/>", color, inner)
    m = re.search(r"<w:(?:%s)\b" % "|".join(RPR_AFTER_COLOR), inner)
    return inner[:m.start()] + color + inner[m.start():] if m else inner + color


def colour_runs(xml):
    """Colour every text run and every maths run in a fragment of document XML."""
    def word_run(m):
        head, body = m.group(1), m.group(2)
        rpr = re.match(r"\s*<w:rPr>(.*?)</w:rPr>", body, re.S)
        if rpr:
            return head + f"<w:rPr>{add_color_to_rpr(rpr.group(1))}</w:rPr>" + body[rpr.end():] + "</w:r>"
        return head + f'<w:rPr><w:color w:val="{REVISION_COLOR}" /></w:rPr>' + body + "</w:r>"

    def math_run(m):
        head, body = m.group(1), m.group(2)
        rpr = re.search(r"<w:rPr>(.*?)</w:rPr>", body, re.S)
        if rpr:
            return head + body[:rpr.start()] + f"<w:rPr>{add_color_to_rpr(rpr.group(1))}</w:rPr>" + body[rpr.end():] + "</m:r>"
        text_at = body.find("<m:t")
        colour = f'<w:rPr><w:color w:val="{REVISION_COLOR}" /></w:rPr>'
        return head + (body[:text_at] + colour + body[text_at:] if text_at >= 0 else body + colour) + "</m:r>"

    xml = re.sub(r"(<w:r(?=[\s>])[^>]*>)(.*?)</w:r>", word_run, xml, flags=re.S)
    return re.sub(r"(<m:r(?=[\s>])[^>]*>)(.*?)</m:r>", math_run, xml, flags=re.S)


# ---- Edits ----

def edit_front_matter(doc, authors, affiliation_lines):
    """One author line with affiliation letters, then the affiliations and the corresponding-author note."""
    blocks = list(re.finditer(r'<w:p>\s*<w:pPr>\s*<w:pStyle w:val="Author" ?/>\s*</w:pPr>(.*?)</w:p>', doc, re.S))
    assert len(blocks) == len(authors), f"{len(blocks)} author paragraphs in the file, {len(authors)} in the YAML"
    for m, a in zip(blocks, authors):
        assert esc(a["name"]) in m.group(1), f"author line does not match the YAML: {a['name']}"
    for prev, nxt in zip(blocks, blocks[1:]):
        assert not doc[prev.end():nxt.start()].strip(), "author paragraphs are not contiguous"
    runs = []
    for n, a in enumerate(authors):
        marks = ",".join(a["letters"] + (["*"] if a["corresponding"] else []))
        runs += [run(("" if n == 0 else ", ") + a["name"]), run(marks, superscript=True)]
    affiliations = [paragraph("Author", [run(letter, superscript=True, italic=True, size=AFFILIATION_FONT_HALF_POINTS),
                                         run(text, italic=True, size=AFFILIATION_FONT_HALF_POINTS)]) for letter, text in affiliation_lines]
    affiliations.append(paragraph("Author", [run("*", superscript=True, italic=True, size=AFFILIATION_FONT_HALF_POINTS),
                                             run("Corresponding author", italic=True, size=AFFILIATION_FONT_HALF_POINTS)]))
    doc = doc[:blocks[0].start()] + paragraph("Author", runs) + "".join(affiliations) + doc[blocks[-1].end():]
    doc, n = re.subn(r'<w:p>\s*<w:pPr>\s*<w:pStyle w:val="Date" ?/>\s*</w:pPr>.*?</w:p>\s*', "", doc, count=1, flags=re.S)
    assert n == 1, "no Date paragraph found"
    return doc

def merge_duplicate_paragraph_properties(doc):
    """Merge adjacent <w:pPr> blocks into one, later settings winning, children in schema order."""
    merged = 0

    def merge(m):
        nonlocal merged
        children = {}
        for block in (m.group(1), m.group(2)):
            found = re.findall(r"<w:(\w+)\b[^>]*?/>", block)
            leftover = re.sub(r"<w:\w+\b[^>]*?/>", "", block).strip()
            if leftover or any(tag not in PPR_ORDER for tag in found):
                return m.group(0)          # anything unfamiliar: leave the paragraph as Quarto wrote it
            for tag, element in zip(found, re.findall(r"<w:\w+\b[^>]*?/>", block)):
                children[tag] = element
        merged += 1
        return "<w:pPr>" + "".join(children[t] for t in PPR_ORDER if t in children) + "</w:pPr>"
    doc = re.sub(r"<w:pPr>((?:(?!</w:pPr>).)*)</w:pPr>\s*<w:pPr>((?:(?!</w:pPr>).)*)</w:pPr>", merge, doc, flags=re.S)

    def dedupe(m):
        nonlocal merged
        found = re.findall(r"<w:(\w+)\b[^>]*?/>", m.group(1))
        if len(found) == len(set(found)) or re.sub(r"<w:\w+\b[^>]*?/>", "", m.group(1)).strip() or any(t not in PPR_ORDER for t in found):
            return m.group(0)
        children = {}
        for tag, element in zip(found, re.findall(r"<w:\w+\b[^>]*?/>", m.group(1))):
            children.setdefault(tag, element)      # first wins: the column's alignment, not Quarto's added centring
        merged += 1
        return "<w:pPr>" + "".join(children[t] for t in PPR_ORDER if t in children) + "</w:pPr>"
    doc = re.sub(r"<w:pPr>((?:(?!</w:pPr>).)*)</w:pPr>", dedupe, doc, flags=re.S)
    return doc, merged


def set_page_setup(doc):
    setup = (f'<w:sectPr><w:pgSz w:w="{PAGE_WIDTH_TWIPS}" w:h="{PAGE_HEIGHT_TWIPS}" />'
             f'<w:pgMar w:top="{PAGE_MARGIN_TWIPS}" w:right="{PAGE_MARGIN_TWIPS}" w:bottom="{PAGE_MARGIN_TWIPS}" '
             f'w:left="{PAGE_MARGIN_TWIPS}" w:header="{HEADER_FOOTER_TWIPS}" w:footer="{HEADER_FOOTER_TWIPS}" w:gutter="0" /></w:sectPr>')
    doc, n = re.subn(r"<w:sectPr\s*/>", setup, doc)
    assert n <= 1
    return doc


def cap_image_heights(doc):
    limit = int(MAX_IMAGE_HEIGHT_IN * EMU_PER_INCH)

    def scale(m):
        block = m.group(0)
        cy = int(re.search(r"<wp:extent cx=\"\d+\" cy=\"(\d+)\"", block).group(1))
        if cy <= limit:
            return block
        factor = limit / cy
        return re.sub(r'(<(?:wp:extent|a:ext)) cx="(\d+)" cy="(\d+)"',
                      lambda e: f'{e.group(1)} cx="{round(int(e.group(2)) * factor)}" cy="{round(int(e.group(3)) * factor)}"', block)
    return re.sub(r"<w:drawing>.*?</w:drawing>", scale, doc, flags=re.S)


def colour_marked_passages(doc):
    """Colour everything between the rev_N bookmarks, then delete the bookmarks."""
    pattern = re.compile(r'<w:bookmarkStart w:id="(\d+)" w:name="rev_\d+" ?/>(.*?)<w:bookmarkEnd w:id="\1" ?/>', re.S)
    doc, n = pattern.subn(lambda m: colour_runs(m.group(2)), doc)
    assert not re.search(r'w:name="rev_\d+"', doc), "unpaired revision marker left in the document"
    return doc, n


def colour_new_references(doc, new_keys):
    coloured = []

    def entry(m):
        key = m.group(2)
        if key not in new_keys:
            return m.group(0)
        coloured.append(key)
        return m.group(1) + colour_runs(m.group(3))
    doc = re.sub(r'(<w:bookmarkStart w:id="\d+" w:name="ref-([^"]+)" ?/>\s*)(<w:p>.*?</w:p>)', entry, doc, flags=re.S)
    return doc, sorted(coloured)


def harmonise_typography(styles):
    """Give the title, headings and captions the body font and colour (see STYLE_TYPOGRAPHY)."""
    for style_id, spec in STYLE_TYPOGRAPHY.items():
        m = re.search(rf'(<w:style [^>]*w:styleId="{style_id}"[^>]*>)(.*?)(</w:style>)', styles, re.S)
        assert m, f"style {style_id} not found"
        rpr = ("<w:rPr>" + BODY_FONTS + ("<w:b /><w:bCs />" if spec.get("bold") else "")
               + ("<w:i /><w:iCs />" if spec.get("italic") else "") + '<w:color w:val="auto" />'
               + f'<w:sz w:val="{spec["size"]}" /><w:szCs w:val="{spec["size"]}" /></w:rPr>')
        body, n = re.subn(r"<w:rPr>.*?</w:rPr>", lambda _: rpr, m.group(2), count=1, flags=re.S)
        if n == 0:
            body += rpr                      # <w:rPr> follows <w:pPr> and ends the style definition here
        styles = styles[:m.start()] + m.group(1) + body + m.group(3) + styles[m.end():]
    return styles


def neutralise_hyperlink_style(styles):
    new, n = re.subn(r'(<w:style [^>]*w:styleId="Hyperlink".*?<w:rPr>)\s*<w:color [^>]*/>', r'\1<w:color w:val="auto" />', styles, flags=re.S)
    assert n == 1, "Hyperlink style not found"
    return new


# ---- Main ----

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("docx", type=Path)
    ap.add_argument("--revised", action="store_true", help="tracked-changes manuscript: colour everything in blue passages")
    args = ap.parse_args()
    args.docx = args.docx.resolve()

    with zipfile.ZipFile(args.docx) as z:
        entries = [(i, z.read(i.filename)) for i in z.infolist()]
    parts = {i.filename: b.decode("utf-8") for i, b in entries if i.filename in ("word/document.xml", "word/styles.xml")}
    doc, styles = parts["word/document.xml"], parts["word/styles.xml"]

    authors, affiliation_lines = read_front_matter(CURRENT_QMD)
    doc, n_captions = merge_duplicate_paragraph_properties(doc)
    doc = edit_front_matter(doc, authors, affiliation_lines)
    doc = set_page_setup(doc)
    doc = cap_image_heights(doc)
    styles = harmonise_typography(styles)
    report = [f"{n_captions} paragraph-property blocks repaired"]
    if args.revised:
        doc, n_passages = colour_marked_passages(doc)
        new_keys = cited_keys(CURRENT_QMD) - cited_keys(SUBMITTED_QMD)
        doc, coloured = colour_new_references(doc, new_keys)
        styles = neutralise_hyperlink_style(styles)
        report.append(f"{n_passages} marked passages coloured throughout; {len(coloured)} new references coloured")
        missing = sorted(new_keys - set(coloured))
        assert not missing, f"new references not found in the reference list: {missing}"

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False, dir=args.docx.parent) as tmp:
        tmp_path = Path(tmp.name)
    with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as out:
        for info, data in entries:
            if info.filename == "word/document.xml":
                data = doc.encode("utf-8")
            elif info.filename == "word/styles.xml":
                data = styles.encode("utf-8")
            out.writestr(info, data)
    shutil.move(tmp_path, args.docx)
    print(f"finalized {args.docx.relative_to(REPO)}: front matter, page setup, figure sizes; " + "; ".join(report))


if __name__ == "__main__":
    main()
