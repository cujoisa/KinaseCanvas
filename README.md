# KinaseCanvas

KinaseCanvas integrates the Cantley Atlases (Ser/Thr + Tyr) and curated kinase–substrate interactions. It includes the supporting data inputs, derived
network summaries, Quarto viewers, and analysis R Markdown used to generate the
figures and JSON payloads.

## Contents

- `data/` – Cantley Atlas CSVs, kinetic reference tables, and supporting XLSX files.
- `figures/paper_figures/` – Exported manuscript-ready figures (PNG/PDF).
- `results/` – CSV exports powering the interactive network viewers.
- `src/` – Quarto and R Markdown sources for the data integration and viewers.

## Reproducing the analysis

1. Install packages recorded in `renv.lock` using `renv::restore()`.
2. Knit `src/generate_kinase_substrate_graph_tyrosine_updated.Rmd` to rebuild the
   integrated dataset and figures.
3. Render the Quarto documents under `src/` to regenerate the HTML network viewers.
