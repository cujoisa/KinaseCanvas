# KinaseCanvas

Code, input data and outputs for:

> Joisa CU, McCabe IC, East MP, Peng XL, Gomez SM, Yeh JJ. *KinaseCanvas: An Integrated Resource
> for Curated and Novel Kinase-Substrate Interactions.* Submitted to *Database*.

KinaseCanvas combines curated kinase-substrate interactions (PhosphoSitePlus, EPSD and iPTMnet, as
aggregated by KiNet) with motif-based predictions from the serine/threonine and tyrosine kinome
specificity atlases (Johnson et al. 2023; Yaron-Barir et al. 2024). The predictions are filtered by
subcellular co-localization (Human Protein Atlas) and phosphosite functional score (Ochoa et al. 2020).
The released resource contains 30,280 kinase-substrate pairs: 8,364 curated and 21,916 novel predictions.

- Interactive Explorer: <https://cujoisa.github.io/KinaseCanvas/>
- Source repository: <https://github.com/cujoisa/KinaseCanvas>
- This archive: <https://doi.org/10.5281/zenodo.22941318>

## What is where

| Path | Contents |
|:-----|:---------|
| `docs/generate_kinase_substrate_graph_tyrosine_updated.Rmd` | Main pipeline. Builds the resource, the supplementary tables, Figures 1-3 and Supplementary Figure 1 |
| `docs/revision_analyses.qmd` | Threshold sensitivity, evidence-layer information content and tissue-specificity analyses; Supplementary Figure 2 |
| `docs/index.qmd` | The KinaseCanvas Explorer, rendered to the self-contained `docs/index.html` |
| `scripts/figure4/` | Screenshot capture and compositing for Figure 4 |
| `paper/` | Manuscript (`K-S-Database-Resource-Paper.qmd`) and response to reviewers |
| `refs/` | Bibliography (`references.bib`) |
| `data/` | Input data (see [Input data](#input-data)) |
| `results/` | Pipeline outputs, including the released tables |
| `figures/paper_figures/` | Manuscript figures |
| `renv.lock` | R package versions |

## Requirements

- R 4.5 with the packages in `renv.lock`, including Bioconductor (`org.Hs.eg.db`, `AnnotationDbi`,
  `Biostrings`, `clusterProfiler`, `biomaRt`) and GitHub (`IDG-Kinase/DarkKinaseTools`) packages
- Quarto 1.9 or later, for the Explorer, the revision analyses and the manuscript
- For Figure 4 only: Node.js 18 or later and Google Chrome
- Memory: the pipeline holds the full unfiltered prediction matrix (about 28 million rows) in memory.
  It was run on a machine with 256 GB of RAM; we have not measured the minimum.

The pipeline took about 13 minutes on an Apple M3 Ultra. It needs network access only to fetch
canonical UniProt sequences missing from `data/uniprot_sequences_cache.fasta`. The cache in this
archive covers every released site, so a rerun works offline.

## Reproducing the results

Run all commands from the repository root.

**1. Restore the R environment**

```r
install.packages("renv")
renv::restore()
```

**2. Run the main pipeline**

The pipeline is an R Markdown document. Its five `eval=FALSE` chunks are earlier exploratory code
and are not part of the published analysis. The quickest way to run it is to extract the live code
as a script and source it:

```sh
Rscript -e 'f <- tempfile(fileext = ".R"); knitr::purl("docs/generate_kinase_substrate_graph_tyrosine_updated.Rmd", output = f, quiet = TRUE); source(f)'
```

Knitting the document (`quarto render docs/generate_kinase_substrate_graph_tyrosine_updated.Rmd`)
runs the same code and also produces an HTML report.

The pipeline writes the following:

| Output | Description |
|:-------|:------------|
| `results/combined_kinase_substrate_pairs_2025.csv` | The released resource: one row per kinase-substrate-site, with source, motif percentile, kinase rank, promiscuity index, functional score, shared compartments, composite confidence score and flanking sequence |
| `results/combined_kinase_substrate_sites_2025.csv` | Site-level table |
| `results/unfiltered_cantley_dataset.csv` | Supplementary Table S1: the complete unfiltered prediction matrix (3.4 GB) |
| `results/subcellular_localization_mapping.csv` | Supplementary Table S2: HPA compartment assignments |
| `results/ochoa_functional_scores.csv` | Supplementary Table S3: phosphosite functional scores |
| `results/alluvial_stage_counts.csv` | Supplementary Table S4: substrate counts per filtering stage (Figure 1C) |
| `results/relaxed_tier_kinase_substrate_pairs.csv` | Relaxed motif tier (75th-90th percentile); not part of the high-confidence set |
| `results/manuscript_numbers.csv` | Headline statistics quoted in the manuscript |
| `results/filter_evidence_contingency.csv` | Joint table of the three evidence layers, used in step 3 |
| `figures/paper_figures/fig1.png`, `fig2.png`, `fig3.png`, `figS1.png` | Figures 1-3 and Supplementary Figure 1 |

The pipeline stops with an error if any of its consistency checks fail: every atlas kinase must
resolve to exactly one gene, co-localization percentages must stay at or below 100%, and the
dark-kinase share must agree between Figure 3B and `manuscript_numbers.csv`.

**3. Run the revision analyses**

```sh
quarto render docs/revision_analyses.qmd
```

This step reads the outputs of step 2. It writes Supplementary Figure 2
(`figures/paper_figures/figS2_threshold_sensitivity.png`) and the tables behind the manuscript's
"Robustness of the filtering criteria" section: `threshold_sensitivity_sweep.csv`,
`evidence_layer_entropy.csv`, `evidence_layer_mutual_information.csv`,
`evidence_layer_leave_one_out.csv`, `tissue_specificity_coverage.csv` and
`coloc_discriminative_power.csv`. It also checks that its independent re-implementation of the
filters agrees with the pipeline at the published operating point.

**4. Build the Explorer**

```sh
quarto render docs/index.qmd
```

This writes `docs/index.html`, a single self-contained file that can be opened locally or served
as a static page.

**5. Regenerate Figure 4**

```sh
cd scripts/figure4 && npm install && cd ../..
node scripts/figure4/capture_fig4.js
Rscript scripts/figure4/make_fig4.R
```

The first script opens `docs/index.html` in headless Chrome. It seeds the network with TNIK,
selects the TNIK-ORC2 interaction and records the position of each panel. The second script crops
and composites the panels into `figures/paper_figures/fig4.png`. Set `CHROME_PATH` to use a
Chromium binary other than the installed Google Chrome.

**6. Render the manuscript (optional)**

```sh
quarto render paper/K-S-Database-Resource-Paper.qmd --to elsevier-html
```

The PDF format needs a LaTeX installation.

## Figures and tables

| Item | Produced by |
|:-----|:------------|
| Figure 1 | Main pipeline (step 2). Panel A is a static schematic, `figures/paper_figures/KS resource figure.png`, drawn in BioRender with an inset captured from the Explorer |
| Figures 2 and 3; Supplementary Figure 1 | Main pipeline (step 2) |
| Figure 4 | `scripts/figure4/` (step 5) |
| Supplementary Figure 2 | `docs/revision_analyses.qmd` (step 3) |
| Supplementary Tables S1-S4; relaxed tier | Main pipeline (step 2), written to `results/` |

All numerical outputs are deterministic. The Explorer's network layout is not: the fCoSE layout
places nodes differently on each load. A regenerated Figure 4 will therefore show the same nodes,
edges and values as the published figure, but arranged differently.

## Input data

| File | Source |
|:-----|:-------|
| `data/CantleyData/CantleyAtlas.csv` | Serine/threonine kinome specificity atlas: per-kinase, per-site motif scores, percentiles and promiscuity (Johnson et al. 2023, *Nature*) |
| `data/CantleyData/CantleyTyrosine.csv` | Tyrosine kinome specificity atlas (Yaron-Barir et al. 2024, *Nature*) |
| `data/kinet_data/ksi_source_full_dataset.csv` | Curated kinase-substrate interactions from PhosphoSitePlus, EPSD and iPTMnet, downloaded from the KiNet portal (Sekar et al. 2024) |
| `data/CantleyData/subcellular_location.tsv` | Human Protein Atlas subcellular location data, downloaded 10 January 2026 |
| `data/hpa/rna_tissue_specificity.tsv` | Human Protein Atlas RNA tissue specificity, downloaded 21 August 2026 (see `data/hpa/README.md`) |
| `data/41587_2019_344_MOESM4_ESM.xlsx`, `data/41587_2019_344_MOESM5_ESM.xlsx` | Ochoa et al. 2020, *Nature Biotechnology*, Supplementary Tables: annotated phosphoproteome and phosphosite functional scores |
| `data/Comprehensive_Kinase_Simple.xlsx` | Human kinome reference table (gene symbols, UniProt accessions, Entrez IDs, families), used to resolve atlas kinase names |
| `data/uniprot_sequences_cache.fasta` | Canonical UniProt sequences for every released substrate, used to verify sites and extract flanking sequences |

Dark (understudied) kinase status comes from the `DarkKinaseTools` R package (IDG programme;
Berginski et al. 2021). Gene and protein identifiers were mapped with `org.Hs.eg.db`.

Source datasets remain subject to the terms of their original licences.

## Files not used in the manuscript

The repository also contains exploratory work that is not part of the published analysis. The
manuscript does not depend on any of it:

- `docs/build_extended_network_*.qmd`, `docs/drug_target_*.qmd`,
  `docs/combined_kinase_substrate_data_viewer_updated.qmd`, `docs/extended_kinome_network_viewer.qmd`
  and `docs/kinasecanvas_final.html`
- `data/supplementary/`, `data/hippie_current.txt` and `data/kinome_profiling_novartis_evebio_combined.fst`
- `results/extended_kinome_network*.csv`
