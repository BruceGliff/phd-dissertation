#!/usr/bin/env bash
# replace_label_R.sh
# Replaces the "R" in node labels like {$R10_{0}^{5}$} with \rho
# Only affects the R that appears right after "{$" and before a digit.

set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <file.tex>" >&2
    exit 1
fi

file="$1"

# Use perl for reliable in-place substitution with a regex that matches
# only the R inside node labels: {$R<digits>...
perl -i -pe 's/\{\$R(\d)/{\$\\rho$1/g' "$file"

echo "Done. Replaced label R with \\rho in: $file"
