# ---- Curated-site recovery by the specificity atlas, per kinase family ----
#
# How well does each atlas kinase's measured motif rank that kinase's own curated sites?
# For every curated kinase-site pair whose site the atlas scores for that kinase, we take
# the motif percentile the atlas assigns. Because a kinase's percentiles are uniform over
# all scored sites, a motif with no information about real substrates would place curated
# sites at a mean percentile of 50 and put 10% of them at or above the 90th percentile.
# The mean percentile / 100 equals the AUROC of the motif score for curated sites against
# all scored sites. The atlas motifs come from peptide libraries, not known substrates,
# so the test is not circular.
#
# Inputs (released pipeline outputs):
#   results/combined_kinase_substrate_pairs_2025.csv  curated + predicted triplets
#   results/unfiltered_cantley_dataset.csv            full atlas matrix (3.6 GB)
#   data/Comprehensive_Kinase_Simple_with_class.csv   kinase family annotation
# Outputs:
#   results/curated_site_recovery_by_kinase.csv
#   results/curated_site_recovery_by_family.csv

# ---- Setup ----
library(tidyverse)
library(here)
library(conflicted)
library(data.table)
conflicts_prefer(dplyr::filter, dplyr::select, dplyr::lag, dplyr::between)

motif_cutoff <- 90          # operating-point motif percentile
min_sites_per_kinase <- 5   # kinases with fewer scored curated sites are not summarized alone
curated_sources <- c("PhosphoSitePlus", "EPSD", "iPTMNet")

# ---- Curated kinase-site pairs ----
curated <- read_csv(here("results", "combined_kinase_substrate_pairs_2025.csv"),
                    show_col_types = FALSE) |>
  filter(Source %in% curated_sources) |>
  distinct(Kinase, Substrate_Uniprot_ID, Site)
message("Curated kinase-site triplets: ", nrow(curated))

# ---- Atlas percentiles for those pairs only ----
atlas <- fread(here("results", "unfiltered_cantley_dataset.csv"),
               select = c("Substrate_Uniprot_ID", "Kinase", "Site", "Percentile"))
atlas_kinases <- unique(atlas$Kinase)
scored <- atlas[curated, on = .(Kinase, Substrate_Uniprot_ID, Site), nomatch = NULL] |>
  as_tibble() |>
  distinct(Kinase, Substrate_Uniprot_ID, Site, .keep_all = TRUE)
rm(atlas); invisible(gc())
message("Curated triplets with an atlas kinase: ",
        sum(curated$Kinase %in% atlas_kinases),
        "; scored by the atlas for that kinase: ", nrow(scored))

# ---- Kinase families ----
families <- read_csv(here("data", "Comprehensive_Kinase_Simple_with_class.csv"),
                     show_col_types = FALSE) |>
  select(symbol_a = Gene, symbol_b = `HUGO GENE 220307...1`, Family = `Kinase Family`) |>
  pivot_longer(c(symbol_a, symbol_b), values_to = "Kinase") |>
  distinct(Kinase, Family) |>
  filter(!is.na(Kinase), !is.na(Family)) |>
  distinct(Kinase, .keep_all = TRUE)

# ---- Per-kinase and per-family recovery ----
by_kinase <- scored |>
  left_join(families, by = "Kinase") |>
  group_by(Family, Kinase) |>
  summarise(n_sites = n(),
            mean_percentile = mean(Percentile),
            pct_at_cutoff = 100 * mean(Percentile >= motif_cutoff),
            .groups = "drop") |>
  arrange(Family, desc(n_sites))

summarise_recovery <- function(d) {
  d |>
    summarise(n_kinases = n_distinct(Kinase),
              n_sites = n(),
              auroc = mean(Percentile) / 100,
              median_percentile = median(Percentile),
              pct_at_cutoff = 100 * mean(Percentile >= motif_cutoff),
              .groups = "drop")
}

scored_fam <- scored |> left_join(families, by = "Kinase")
by_family <- bind_rows(
  scored_fam |> filter(!is.na(Family)) |> group_by(Family) |> summarise_recovery(),
  scored_fam |> summarise_recovery() |> mutate(Family = "All")
) |>
  mutate(fold_over_random = pct_at_cutoff / (100 - motif_cutoff)) |>
  arrange(desc(n_sites))

# Per-kinase AUROC distribution within each family, for kinases with enough sites
kinase_auroc <- by_kinase |>
  filter(n_sites >= min_sites_per_kinase) |>
  group_by(Family) |>
  summarise(n_kinases_min_sites = n(),
            median_kinase_auroc = median(mean_percentile) / 100,
            n_kinases_auroc_gt_half = sum(mean_percentile > 50),
            .groups = "drop")
by_family <- by_family |> left_join(kinase_auroc, by = "Family")

write_csv(by_kinase, here("results", "curated_site_recovery_by_kinase.csv"))
write_csv(by_family, here("results", "curated_site_recovery_by_family.csv"))
print(by_family, width = Inf)
print(by_kinase |> filter(Family == "Atypical"), n = Inf)
