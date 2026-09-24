-- Renders text marked as revised, [text]{.rev}, in colour: the journal asks for changes to be
-- highlighted with coloured text. Word output uses the "Revised" character style from
-- revised-reference.docx, so the colour is a real style that can be changed in one place.
local COLOR = "1F4E9E"

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
    el.attributes["custom-style"] = "Revised"
    return el
  elseif FORMAT:match("html") then
    el.attributes["style"] = "color:#" .. COLOR
    return el
  end
  return el.content
end
