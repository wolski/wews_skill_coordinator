# Getting a journal's real requirements

## Fetching the guidelines

Author guidelines are usually a PDF, and the fetch fails in a way that looks like success.

1. Try a web fetch of the guidelines URL first.
2. **When it returns nothing useful, download the PDF and extract it locally**: `curl -sL <url> -o guide.pdf && pdftotext -layout guide.pdf -`. A compressed PDF stream defeats naive fetchers; `-layout` keeps the tables of word limits readable.
3. Publisher article pages (`pubs.acs.org`, most Elsevier domains) return **403** to automated fetches. Europe PMC often returns navigation only. Work around by using search-result summaries for short factual points, or a PMC redirect target for an open-access paper — and label anything sourced that way as unverified.

## Verify the type name exists

Do not assume the type the user names is a real submission category.

Worked example: *Journal of Proteome Research* has **no "Application Note"**. Its actual types and limits are Article 8,000; Letter 5,500; Perspective 9,500; Communication 4,500; Review 6,000; Technical Note 4,500; Tutorial 5,000. The term "application note" for JPR papers comes from a 2015 Perspective on manuscript types (doi:10.1021/pr501318d), not from the submission system.

So: find the type list in the guidelines, quote it with the limits, and **put the choice to the author**. A call may state a routing rule — JPR's software special issue sends a novel tool to the Article and an update to a published one to the Technical Note — but the rule is guidance, not a constraint, and the author may have reasons to submit shorter. Settle it before building a word budget on it.

## Caps, and the absence of caps

Check for figure, table and reference limits. If none are stated, say so explicitly and say how you checked — "grepped all 18 pages of the extracted guidelines, no cap on figures, tables or references". An unstated absence reads like an omission; a verified one is a finding that changes how the paper is planned.

## Conditions attached to the subject matter

Special issues and subject-specific policies carry conditions the general guidelines do not. Extract them verbatim, because each is a submission gate. What to look for depends on the paper:

- **Software or tools** — working and free to editors and reviewers *at submission*, an open-source licence (often strongly recommended, sometimes required), a named public repository, documentation, installation instructions, and test data.
- **Data and resources** — deposition in a recognised repository, an accession before submission, a licence, and a persistent identifier.
- **Human or animal subjects** — ethics approval, consent statements, and reporting-guideline compliance.
- **Any subject** — reporting checklists the journal mandates, and its policy on AI use, which increasingly must be disclosed.

Check each against the project immediately. Is anything private that must be public, is the licence coherent across components, is there a release, and can a reviewer reach the material without asking the authors.

## Data deposition

Find the exact wording on where raw data must live. Publishers are increasingly explicit that an author-hosted link is not acceptable — JPR states "Providing this information on a link managed by the author(s) is not acceptable." A repository accession or a DOI is the only acceptable form, which means checking early whether the project's test data has one.

## What to write down

`JOURNAL_requirements.md`, with the source of each fact: the guidelines version and date, the special-issue call URL, and which claims came from search summaries rather than the primary text.
