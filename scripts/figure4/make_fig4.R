suppressPackageStartupMessages({library(magick); library(jsonlite); library(here)})
# Composites Figure 4 from the screenshot and panel boxes written by capture_fig4.js.
# Usage (from the repository root):  Rscript scripts/figure4/make_fig4.R
d <- here("scripts", "figure4", "capture")
b  <- fromJSON(file.path(d, "boxes.json")); S <- 2   # deviceScaleFactor
BG <- "#f5f1e6"; GAP <- 26
page <- image_read(file.path(d, "page.png"))
crop <- function(k, h = NULL) {
  r <- b[[k]]
  image_crop(page, sprintf("%dx%d+%d+%d", round(r$w * S), round((if (is.null(h)) r$h else h) * S),
                           round(r$x * S), round(r$y * S)))
}
lab <- function(img, letter)
  image_annotate(image_border(img, BG, "48x12"), letter, size = 56, weight = 700,
                 font = "Helvetica", color = "#1f1b16", location = "+4+2", gravity = "northwest")
padw <- function(img, w) image_extent(img, paste0(w, "x", image_info(img)$height), gravity = "northwest", color = BG)
padh <- function(img, h) image_extent(img, paste0(image_info(img)$width, "x", h), gravity = "northwest", color = BG)

top <- crop("topbar")
# table: heading + filters + 14 data rows -- tall enough to sit comfortably under C+D
tab  <- crop("table")
# detail panel, as captured
det  <- crop("detail")
# network: drop the canvas's rounded-corner border, trim the empty canvas around
# the graph, then re-pad with a little breathing room
cy <- crop("cy"); inf <- image_info(cy)
cy <- image_crop(cy, sprintf("%dx%d+10+10", inf$width - 20, inf$height - 20))
cy <- image_trim(cy, fuzz = 5)
cy <- image_border(image_border(cy, "#f7f2e8", "18x18"), "#cfc7b8", "2x2")
side <- crop("sidebar")

A <- lab(top, "A"); Bp <- lab(side, "B"); C <- lab(cy, "C"); D <- lab(det, "D"); E <- lab(tab, "E")

# Row 1 (right side): C beside D, top-aligned to the taller of the two.
row1h <- max(image_info(C)$height, image_info(D)$height)
row1  <- image_append(c(padh(C, row1h), image_blank(GAP, row1h, BG), padh(D, row1h)))
# Row 2 (right side): the table, spanning the same width as row 1 -- pads with
# background on the right rather than stretching, so text stays crisp.
row1w <- image_info(row1)$width
row2  <- padw(E, max(row1w, image_info(E)$width))
row1  <- padw(row1, image_info(row2)$width)

rightblock <- image_append(c(row1, image_blank(image_info(row1)$width, GAP, BG), row2), stack = TRUE)

# Sidebar (B) sits to the left of the whole right block; whichever column is
# taller sets the row height, so blank space is minimised on both sides.
totalh <- max(image_info(Bp)$height, image_info(rightblock)$height)
body <- image_append(c(padh(Bp, totalh), image_blank(GAP, totalh, BG), padh(rightblock, totalh)))

fig <- image_append(c(padw(A, image_info(body)$width), image_blank(image_info(body)$width, GAP, BG), body), stack = TRUE)
image_write(image_border(fig, BG, "24x24"), here("figures/paper_figures/fig4.png"), format = "png", density = 300)
print(image_info(image_read(here("figures/paper_figures/fig4.png"))))
