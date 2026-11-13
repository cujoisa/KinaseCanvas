"""UK-to-US spelling for the manuscript, the response letter and the cover letter.

Used two ways: to convert text (python3 scripts/us_spelling.py FILE ...), and by mark_revisions.py, which
compares texts after this conversion so that a spelling-only change is not marked as a revision.

Only whole words are changed, with their capitalisation kept. Lines of the response letter that quote the
reviewers ("> " without the italic "> *" of our own quotes) are left exactly as the reviewers wrote them,
and YAML front matter is never touched.
"""

import re
import sys
from pathlib import Path

UK_TO_US = {
    "analyse": "analyze", "analysed": "analyzed", "analysing": "analyzing",
    "apologise": "apologize", "apologised": "apologized",
    "behaviour": "behavior", "behaviours": "behaviors", "behavioural": "behavioral",
    "catalogue": "catalog", "catalogues": "catalogs", "catalogued": "cataloged", "cataloguing": "cataloging",
    "centre": "center", "centres": "centers", "centred": "centered",
    "characterise": "characterize", "characterised": "characterized", "characterising": "characterizing",
    "characterisation": "characterization",
    "colour": "color", "colours": "colors", "coloured": "colored",
    "emphasise": "emphasize", "emphasised": "emphasized",
    "favour": "favor", "favoured": "favored", "favourable": "favorable",
    "generalise": "generalize", "generalised": "generalized",
    "harmonise": "harmonize", "harmonised": "harmonized", "harmonisation": "harmonization",
    "hypothesise": "hypothesize", "hypothesised": "hypothesized",
    "labelled": "labeled", "labelling": "labeling",
    "licence": "license", "licences": "licenses",
    "localise": "localize", "localised": "localized", "localisation": "localization",
    "minimise": "minimize", "minimised": "minimized", "maximise": "maximize", "maximised": "maximized",
    "modelled": "modeled", "modelling": "modeling",
    "neighbour": "neighbor", "neighbours": "neighbors", "neighbouring": "neighboring",
    "neighbourhood": "neighborhood", "neighbourhoods": "neighborhoods",
    "normalise": "normalize", "normalised": "normalized", "normalisation": "normalization",
    "optimise": "optimize", "optimised": "optimized",
    "organise": "organize", "organised": "organized", "organisation": "organization",
    "orphanise": "orphanize",
    "orthologue": "ortholog", "orthologues": "orthologs",
    "prioritise": "prioritize", "prioritised": "prioritized", "prioritises": "prioritizes",
    "prioritising": "prioritizing", "prioritisation": "prioritization",
    "programme": "program", "programmes": "programs",
    "randomise": "randomize", "randomised": "randomized",
    "realise": "realize", "realised": "realized",
    "recognise": "recognize", "recognised": "recognized",
    "signalled": "signaled", "signalling": "signaling",
    "specialised": "specialized",
    "standardise": "standardize", "standardised": "standardized",
    "summarise": "summarize", "summarised": "summarized", "summarising": "summarizing",
    "towards": "toward",
    "utilise": "utilize", "utilised": "utilized",
    "visualise": "visualize", "visualised": "visualized",
    "visualisation": "visualization", "visualisations": "visualizations",
    "whilst": "while", "amongst": "among",
}

_WORD = re.compile(r"\b(" + "|".join(sorted(UK_TO_US, key=len, reverse=True)) + r")\b", re.IGNORECASE)


def to_us(text):
    def swap(m):
        word = m.group(0); us = UK_TO_US[word.lower()]
        if word.isupper():
            return us.upper()
        return us[0].upper() + us[1:] if word[0].isupper() else us
    return _WORD.sub(swap, text)


def convert_file(path):
    text = Path(path).read_text(encoding="utf-8")
    m = re.match(r"\A---\n.*?\n---\n", text, re.S)
    head, body = (text[:m.end()], text[m.end():]) if m else ("", text)
    lines = body.split("\n")
    is_letter = Path(path).name.startswith("Response_to_Reviewers")
    out = [line if (is_letter and line.startswith("> ") and not line.startswith("> *")) else to_us(line) for line in lines]
    new = head + "\n".join(out)
    changed = sum(a != b for a, b in zip(lines, out))
    Path(path).write_text(new, encoding="utf-8")
    return changed


if __name__ == "__main__":
    for f in sys.argv[1:]:
        print(f"{f}: {convert_file(f)} lines changed")
