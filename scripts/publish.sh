#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Run after gh authentication, source review, tests and a committed release.
set -eu
owner=sohitqwer-del
repo=project-crumble
version=v0.1.0a1
test -z "$(git status --porcelain)" || { echo "Commit or resolve local changes first."; exit 1; }
python scripts/release_check.py
test "$(gh api user --jq .login)" = "$owner" || { echo "Sign in as the expected owner."; exit 1; }
if gh repo view "$owner/$repo" >/dev/null 2>&1; then
  echo "Repository already exists. Inspect its history before publishing; nothing was overwritten."
  exit 1
fi
gh repo create "$owner/$repo" --public --source=. --remote=origin \
  --description "Garment photo search, design changes, human review and SMV suggestions."
git push -u origin main
git push origin "$version"
gh release create "$version" dist/*.whl dist/*.tar.gz \
  --verify-tag --prerelease --title "Project Crumble 0.1 alpha" --notes-file docs/RELEASE_NOTES.md

