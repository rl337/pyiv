#!/bin/bash

# Script to trigger the Documentation workflow via GitHub API
# Usage: ./trigger-docs.sh [branch]
# Requires GITHUB_TOKEN environment variable or .github_token file

BRANCH="${1:-main}"
REPO="rl337/pyiv"
WORKFLOW="docs.yml"

# Get token from environment or file
if [ -z "$GITHUB_TOKEN" ]; then
    if [ -f ".github_token" ]; then
        GITHUB_TOKEN=$(cat .github_token)
    else
        echo "Error: GITHUB_TOKEN environment variable not set and .github_token file not found"
        echo "Set it with: export GITHUB_TOKEN=your_token"
        echo "Or create .github_token file with your token"
        exit 1
    fi
fi

echo "Triggering Documentation workflow on branch: $BRANCH"

response=$(curl -s -w "\n%{http_code}" -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "https://api.github.com/repos/$REPO/actions/workflows/$WORKFLOW/dispatches" \
  -d "{\"ref\":\"$BRANCH\"}")

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "204" ]; then
    echo "✓ Successfully triggered Documentation workflow!"
    echo "View it at: https://github.com/$REPO/actions"
else
    echo "✗ Failed to trigger workflow (HTTP $http_code)"
    echo "Response: $body"
    exit 1
fi

