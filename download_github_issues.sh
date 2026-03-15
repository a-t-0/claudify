#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# download_github_issues.sh
#
# Fetches all open issues + comments + labels + milestone as JSON array
# Uses fields known to avoid the "Projects (classic)" warning in 2026
# Always overwrites issues0.json
#
# Usage: ./download_github_issues.sh <owner/repo>
#   e.g. ./download_github_issues.sh a-t-0/hledger-preprocessor
#
# Requires:
#   - gh CLI installed
#   - GH_TOKEN or GITHUB_TOKEN exported with repo scope
#     (for private repos, a classic PAT with "repo" scope works)
#
# If not authenticated, run:
#   export GH_TOKEN=ghp_YourTokenHere
# ------------------------------------------------------------------------------

set -euo pipefail

# --- Argument parsing ---------------------------------------------------------
if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <owner/repo>"
    echo "  e.g. $0 a-t-0/hledger-preprocessor"
    exit 1
fi

REPO="$1"
OUTPUT_FILE="issues0.json"
LIMIT=100

# --- Check gh CLI is installed ------------------------------------------------
if ! command -v gh &>/dev/null; then
    echo "Error: gh CLI is not installed."
    echo "Install it: https://cli.github.com/"
    exit 1
fi

# --- Check authentication token is set ---------------------------------------
if [[ -z "${GH_TOKEN:-}" && -z "${GITHUB_TOKEN:-}" ]]; then
    # gh might still be authenticated via `gh auth login` — check that
    if ! gh auth status &>/dev/null; then
        echo "Error: No GitHub token found."
        echo ""
        echo "For private repos, export a PAT with 'repo' scope:"
        echo ""
        echo "  export GH_TOKEN=ghp_YourTokenHere"
        echo ""
        echo "Then re-run: $0 $REPO"
        echo ""
        echo "To create a token: https://github.com/settings/tokens/new?scopes=repo"
        exit 1
    fi
fi

# --- Validate the token works and the repo is accessible ----------------------
echo "Checking access to $REPO..."
if ! gh repo view "$REPO" --json nameWithOwner -q .nameWithOwner &>/dev/null; then
    echo "Error: Cannot access repository '$REPO'."
    echo ""
    echo "Possible causes:"
    echo "  - The repository does not exist"
    echo "  - Your token lacks 'repo' scope (needed for private repos)"
    echo "  - The token has expired"
    echo ""
    echo "Check your token:"
    echo "  gh auth status"
    echo ""
    echo "Set a valid token:"
    echo "  export GH_TOKEN=ghp_YourTokenHere"
    exit 1
fi

echo "Repository: $REPO (accessible)"
echo "Fetching up to $LIMIT open issues..."

REPO_FLAG=(--repo "$REPO")

mapfile -t numbers < <(
    gh issue list --state open --limit "$LIMIT" --json number -q '.[].number' "${REPO_FLAG[@]}" 2>/dev/null
)

if ((${#numbers[@]} == 0)); then
    echo "[]" > "$OUTPUT_FILE"
    echo "No open issues → saved empty array to $OUTPUT_FILE"
    exit 0
fi

echo "Found ${#numbers[@]} open issues. Fetching clean JSON..."

# Collect clean JSON objects
json_lines=()
for num in "${numbers[@]}"; do
    echo "  Fetching #$num"

    # Extended but safe field list (milestone + labels added)
    clean_output=$(gh issue view "$num" \
        --json number,title,state,body,author,createdAt,updatedAt,url,comments,labels,milestone \
        "${REPO_FLAG[@]}" 2>&1 \
        | grep -v -i -E 'projects.*classic|sunset-notice|being deprecated' \
        || true)

    if [[ -n "$clean_output" ]] && echo "$clean_output" | jq . >/dev/null 2>&1; then
        json_lines+=("$clean_output")
    else
        echo "  Warning: #$num output invalid or empty – skipping" >&2
    fi
done

# Build array and save
if ((${#json_lines[@]} > 0)); then
    printf '%s\n' "${json_lines[@]}" | jq -s . > "$OUTPUT_FILE"
else
    echo "[]" > "$OUTPUT_FILE"
fi

echo
echo "Done. Processed ${#numbers[@]} issues → saved to $OUTPUT_FILE"
echo "File size: $(du -h "$OUTPUT_FILE" | cut -f1)"
echo
echo "Quick test commands:"
echo "  jq length $OUTPUT_FILE                  # count issues"
echo "  jq '.[0] | {number, title, labels: (.labels | map(.name)), milestone: .milestone.title?, comments_count: (.comments | length)}' $OUTPUT_FILE"
echo "  jq '.[].title' $OUTPUT_FILE | head -n 5"
echo "  jq '.[0].labels | map(.name)' $OUTPUT_FILE   # show labels of first issue"
echo "  jq '.[].milestone | select(. != null) | .title' $OUTPUT_FILE | sort | uniq -c   # count issues per milestone"
