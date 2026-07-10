# Scientific Reporting Skills Repository

## Goal

Create a reusable repository of modular **LLM Skills** for generating high-quality scientific reports from computational analyses (e.g. Quarto, R Markdown, Jupyter, Nextflow reports, bioinformatics pipelines).

The repository should encode established scientific writing conventions rather than domain knowledge. Each skill should be narrowly scoped, composable, and reusable across different report generators and AI agents.

The primary target is automatic report generation within the R/Quarto ecosystem, but the skills should remain language-agnostic whenever possible.

---

# Guiding Principles

The repository should follow these principles.

* Prefer scientific accuracy over persuasive language.
* Describe observations before interpretation.
* Never exaggerate findings.
* Avoid marketing or promotional language.
* Distinguish clearly between Results, Discussion, and Conclusions.
* State uncertainty where appropriate.
* Report statistical evidence instead of subjective wording.
* Prefer precise terminology over stylistic variation.
* Use consistent nomenclature throughout a report.
* Avoid unsupported causal claims.
* Avoid anthropomorphic wording (e.g. "the PCA demonstrates...").
* Write in a style suitable for peer-reviewed scientific journals.

---

# Repository Structure

```text
scientific-reporting-skills/

README.md

skills/

    scientific-writing.md
    figure-captions.md
    tables.md
    statistical-reporting.md
    methods-writing.md
    results-writing.md
    discussion-writing.md
    conclusions.md

plots/

    volcano.md
    ma-plot.md
    pca.md
    heatmap.md
    correlation.md
    boxplot.md
    violin.md
    density.md
    histogram.md
    scatterplot.md
    roc.md
    precision-recall.md
    kaplan-meier.md
    forest-plot.md
    enrichment-dotplot.md
    gsea.md
    cnetplot.md
    network.md
    umap.md
    tsne.md
    featureplot.md
    spatial.md
    genome-browser.md
    manhattan.md
    qqplot.md

domains/

    differential-expression.md
    proteomics.md
    transcriptomics.md
    metabolomics.md
    single-cell.md
    genomics.md
    pathway-analysis.md

examples/

tests/
```

The repository should remain modular. A report generator may combine multiple skills depending on the report being produced.

---

# Skill Format

Each skill should follow a common template.

```text
Purpose

Scope

Scientific conventions

Writing rules

Required information

Recommended structure

Things to avoid

Examples

References
```

Skills should remain concise (typically one to three pages).

---

# Core Skills

## Scientific Writing

General scientific writing rules.

Topics include:

* objective language
* evidence-based statements
* uncertainty
* terminology consistency
* avoiding overstatements
* reproducibility
* reporting limitations
* distinction between observation and interpretation

---

## Figure Captions

Provide universal rules for writing captions.

The recommended structure is:

1. What is shown.
2. What the visual elements represent.
3. How the figure was generated (if relevant).
4. Statistical information.
5. Abbreviations.
6. Additional technical details only if necessary.

Captions should:

* describe the figure
* avoid interpreting biological meaning
* avoid repeating the Results text
* be understandable without reading the main text

---

## Tables

Guidelines for:

* informative titles
* footnotes
* abbreviations
* statistical notation
* formatting conventions

---

## Statistical Reporting

Define consistent reporting rules.

Include guidance for:

* sample sizes
* statistical tests
* effect sizes
* confidence intervals
* adjusted P-values
* multiple testing correction
* significance thresholds

Discourage wording such as:

* highly significant
* extremely significant
* nearly significant
* borderline significant

---

## Results Writing

Results should primarily contain observations.

Recommended structure:

Observation

↓

Supporting evidence

↓

Quantitative values

↓

Statistical evidence

↓

Reference to figure or table

Interpretation should generally be reserved for the Discussion.

---

## Discussion

Recommended structure:

Interpret findings

↓

Compare with literature

↓

Discuss limitations

↓

Suggest future work

Avoid introducing new experimental results.

---

## Methods

Describe analyses sufficiently for reproducibility.

Include:

* software
* package versions
* parameters
* statistical methods
* preprocessing
* normalization
* filtering

Avoid unnecessary implementation details.

---

# Plot-Specific Skills

Each visualization should have its own skill.

Every plot skill should define:

## Purpose

What scientific question the visualization addresses.

## Caption Template

A publication-style caption template.

## Standard Terminology

Preferred wording.

## Interpretation Guidelines

What conclusions are justified.

What conclusions are **not** justified.

## Required Statistics

Relevant statistical quantities.

## Common Mistakes

Examples of misleading or exaggerated wording.

---

# Initial Plot Library

High priority:

* Volcano plot
* PCA
* Heatmap
* UMAP
* t-SNE
* MA plot
* Boxplot
* Violin plot
* Scatter plot
* Correlation plot
* Kaplan–Meier
* ROC
* Precision–Recall
* Forest plot
* GSEA enrichment plot
* Enrichment dotplot
* Network visualization
* Manhattan plot
* Genome browser view

---

# Domain-Specific Skills

After the general skills are complete, add domain-specific guidance.

Examples:

Proteomics

* protein groups
* peptides
* PTMs
* LFQ
* TMT
* DIA

Transcriptomics

* genes
* transcripts
* counts
* normalization

Single-cell

* clustering
* annotation
* trajectory analysis

Metabolomics

* metabolite identification
* pathway analysis

Each domain should primarily define terminology and reporting conventions rather than analytical methods.

---

# Examples

Each skill should include:

Good example

Poor example

Explanation of why the preferred version is scientifically appropriate.

---

# Testing

Create small benchmark datasets.

For each skill:

* provide an input description
* generate output using an LLM
* compare against expected conventions

The tests should verify that generated reports:

* avoid overstatements
* follow scientific terminology
* include required statistical information
* produce publication-quality captions
* remain consistent across figures

---

# References

Where possible, derive conventions from established scientific reporting guidelines rather than inventing new rules.

Potential sources include:

* Bioconductor BiocStyle
* Quarto documentation
* R Markdown guidance
* EQUATOR reporting guidelines
* CONSORT
* STROBE
* PRISMA
* Nature Research reporting standards
* ACS author guidelines
* Cell Press figure guidelines

Each recommendation should be traceable to accepted scientific practice whenever possible.

---

# Long-Term Vision

The repository should become a reusable collection of scientific writing skills that can be used by:

* Quarto
* R Markdown
* Codex
* Claude Code
* Cursor
* GitHub Copilot
* OpenAI Agents
* custom reporting pipelines

Rather than embedding writing conventions inside prompts, report generators should compose a small set of reusable skills appropriate for the current analysis. This modular design makes the system easier to maintain, extend, test, and improve as scientific reporting standards evolve.
