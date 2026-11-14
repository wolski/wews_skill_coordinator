#!/usr/bin/env bash
# Static Bioconductor readiness checks that BiocCheck misses or runs only on the tarball.
# Usage: precheck.sh <package-dir> [<tarball>]
# Output: one line per check, FAIL (blocks submission), CHECK (reviewer may raise it), OK.
# Read-only: builds nothing, changes nothing.

set -u
pkg_dir=${1:?usage: precheck.sh <package-dir> [<tarball>]}
tarball=${2:-}
cd "$pkg_dir" || exit 2

fails=0
checks=0
ok()   { printf 'OK     %s\n' "$*"; }
fail() { printf 'FAIL   %s\n' "$*"; fails=$((fails + 1)); }
check() { printf 'CHECK  %s\n' "$*"; checks=$((checks + 1)); }

field() { awk -v f="$1" 'BEGIN{FS=": *"} $1==f {print $2; exit}' DESCRIPTION; }
mb() { awk -v b="$1" 'BEGIN{printf "%.2f MB", b/1048576}'; }

name=$(field Package)
version=$(field Version)

# DESCRIPTION ---------------------------------------------------------------
if [ "$(basename "$PWD")" = "$name" ]; then ok "folder name = Package ($name)"
else fail "folder '$(basename "$PWD")' != Package '$name' (BiocCheck ERROR)"; fi

if [[ $version =~ ^0\.99\.[0-9]+$ ]]; then ok "version $version"
else fail "version $version is not 0.99.z (new package)"; fi

grep -q '^Maintainer:' DESCRIPTION && fail "Maintainer: field next to Authors@R" || ok "no Maintainer: field"
grep -q '^Author:' DESCRIPTION && fail "Author: field; use Authors@R only" || ok "no Author: field"
grep -q '^Remotes:' DESCRIPTION && fail "Remotes: field (BiocCheck ERROR)" || ok "no Remotes: field"
grep -q 'R (>=' DESCRIPTION && ok "R version declared: $(grep -o 'R (>= *[0-9.]*)' DESCRIPTION | head -1)" \
  || check "no R (>= x.y) in Depends"
grep -q '"cre"' DESCRIPTION && ! awk '/Authors@R/,/^[A-Z][A-Za-z]*:/' DESCRIPTION | grep -q 'ORCID' \
  && check "no ORCID in Authors@R (jianhong asks for it on cre)"
grep -q '"fnd"' DESCRIPTION || check "no fnd (funder) role in Authors@R (jianhong asked on #261)"

# NEWS and README -------------------------------------------------------------
news_files=$(git ls-files | grep -i -E '(^|/)NEWS(\.md|\.Rd)?$' | grep -v '^inst/NEWS.Rd$')
n_news=$(printf '%s\n' "$news_files" | grep -c .)
[ "$n_news" -gt 1 ] && fail "more than one NEWS file: $(echo $news_files)"
if [ -f NEWS.md ]; then
  top=$(grep -m1 '^#' NEWS.md)
  case "$top" in *"$version"*) ok "NEWS.md top heading matches $version" ;;
    *) fail "NEWS.md top heading '$top' does not name $version" ;; esac
else check "no NEWS.md"; fi

if [ -f README.md ] && grep -q -i -E '^#+ .*(AI use|provenance|AI assist)' README.md; then
  ok "README has an AI-use/provenance section"
else fail "README lacks an 'AI use and provenance' section (jianhong round 2, #261)"; fi

# Repository contents -----------------------------------------------------------
bad=$(git ls-files | grep -E '(\.Rproj$|\.DS_Store$|\.Rhistory$|\.RData$|\.so$|\.o$|\.dll$|\.log$)')
[ -n "$bad" ] && fail "tracked files the guidelines forbid: $(echo $bad)" || ok "no forbidden tracked files"

dev=$(git ls-files | cut -d/ -f1 | sort -u | grep -E '^(Makefile|air\.toml|\.lintr|_pkgdown\.yml|pkgdown|docs|make|\.githooks|\.github|SKILLS\.md|AGENTS\.md|CLAUDE\.md|Dockerfile|codecov\.yml|_quarto\.yml)$')
[ -n "$dev" ] && check "dev files in the repo (lshep asked to move Makefile/air.toml on #170): $(echo $dev)"

secretish=$(git ls-files | grep -E '\.(pem|key|crt|p12)$|(^|/)\.env$|shiny-server\.conf$')
[ -n "$secretish" ] && check "certificates or deployment config tracked: $(echo $secretish)"

[ -f inst/CITATION ] && {
  LC_ALL=C grep -q '[^ -~[:space:]]' inst/CITATION && fail "non-ASCII characters in inst/CITATION"
  grep -q 'packageDescription' inst/CITATION && check "inst/CITATION calls packageDescription() (warns on r-universe)"
  grep -q -i 'doi' inst/CITATION || check "inst/CITATION has no doi (BiocCheck WARNING)"
}

ls vignettes/*.html vignettes/*.R 2>/dev/null | grep -q . \
  && check "rendered files in vignettes/ (BiocCheck NOTE on a source-dir run): $(echo $(ls vignettes/*.html vignettes/*.R 2>/dev/null))"

# Sizes -------------------------------------------------------------------------
big=""
while IFS= read -r -d '' f; do
  [ -f "$f" ] || continue
  s=$(wc -c < "$f")
  [ "$s" -gt 5242880 ] && big="$big $f($(mb "$s"))"
done < <(git ls-files -z)
[ -n "$big" ] && fail "tracked files > 5 MB at HEAD:$big" || ok "no tracked file > 5 MB at HEAD"

largest=$(git ls-files -z | xargs -0 wc -c 2>/dev/null | grep -v ' total$' | sort -n | tail -1)
[ -n "$largest" ] && ok "largest tracked file: $(mb "$(echo "$largest" | awk '{print $1}')") $(echo "$largest" | awk '{print $2}')"

hist=$(git rev-list --objects HEAD | git cat-file --batch-check='%(objecttype) %(objectsize) %(rest)' \
  | awk '$1=="blob" && $2>5242880 {printf " %s(%.1f MB)", $3, $2/1048576}')
[ -n "$hist" ] && check "blobs > 5 MB in history (hook passes, repo stays large; git filter-repo to remove):$hist"
pack=$(git count-objects -vH | awk -F': ' '/size-pack/{print $2}')
ok "git pack size: $pack"

if [ -n "$tarball" ]; then
  s=$(wc -c < "$tarball")
  [ "$s" -le 10485760 ] && ok "tarball $(mb "$s") <= 10 MB" || fail "tarball $(mb "$s") > 10 MB"
  long=$(tar tzf "$tarball" | awk 'length($0) > 100' | head -3)
  [ -n "$long" ] && fail "paths > 100 bytes in tarball: $(echo $long)"
fi

# Code patterns reviewers flag ------------------------------------------------------
dots=$(grep -E '^export\([A-Za-z][A-Za-z0-9_]*\.[A-Za-z0-9_.]*\)' NAMESPACE 2>/dev/null | tr '\n' ' ')
[ -n "$dots" ] && check "exported names with '.': $dots"
grep -rqE '\.Deprecated\(|\.Defunct\(' R 2>/dev/null && fail ".Deprecated/.Defunct in R/ (remove deprecated code)"
n=$(grep -rcE 'suppress(Warnings|Messages)\(|<<-' R 2>/dev/null | awk -F: '{s+=$2} END{print s+0}')
[ "$n" -gt 0 ] && check "$n uses of suppressWarnings/suppressMessages/<<- in R/"
n=$(grep -rcE '(^|[^A-Za-z0-9_.])for *\(' R 2>/dev/null | awk -F: '{s+=$2} END{print s+0}')
[ "$n" -gt 0 ] && check "$n 'for (' matches in R/ (jianhong lists them; names ending in 'for' match too)"
n=$(grep -rcE 'download\.file|curl::|httr2?::|url\(' R 2>/dev/null | awk -F: '{s+=$2} END{print s+0}')
[ "$n" -gt 0 ] && check "$n network calls in R/ (BiocFileCache or R_user_dir caching; none in tests/vignettes)"

echo
echo "Summary: $fails FAIL, $checks CHECK. Next: make build, then BiocCheck::BiocCheck('<tarball>', \`new-package\` = TRUE)"
[ "$fails" -eq 0 ]
