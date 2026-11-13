-- Renders text marked as revised, [text]{.rev}, in colour: the journal asks for changes to be
-- highlighted with coloured text. Word output uses the "Revised" character style from
-- revised-reference.docx, so the colour is a real style that can be changed in one place.
--
-- In Word a character style cannot reach everything inside a span: citation numbers, cross-references
-- and inline maths keep their own formatting. The span is therefore also bracketed by invisible
-- bookmarks ("rev_N"), which scripts/finalize_docx.py uses to colour everything between them and
-- then deletes.
local COLOR = "1F4E9E"
local MARKER_ID_BASE = 20000 -- clear of the bookmark ids Quarto/pandoc assign (in the low hundreds)
local marker_count = 0

function Span(el)
  if not el.classes:includes("rev") then
    return nil
  end
  if FORMAT:match("latex") then
    local out = pandoc.List({ pandoc.RawInline("latex", "\\textcolor[HTML]{" .. COLOR .. "}{") })
    out:extend(el.content)
    out:insert(pandoc.RawInline("latex", "}"))
    return out
  elseif FORMAT:match("docx") then
    marker_count = marker_count + 1
    local id = MARKER_ID_BASE + marker_count
    el.attributes["custom-style"] = "Revised"
    return {
      pandoc.RawInline("openxml", string.format('<w:bookmarkStart w:id="%d" w:name="rev_%d"/>', id, marker_count)),
      el,
      pandoc.RawInline("openxml", string.format('<w:bookmarkEnd w:id="%d"/>', id)),
    }
  elseif FORMAT:match("html") then
    el.attributes["style"] = "color:#" .. COLOR
    return el
  end
  return el.content
end
