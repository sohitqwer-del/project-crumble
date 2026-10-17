#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Run after gh authentication, source review, tests and a committed release.
set -eu
owner=sohitqwer-del
repo=project-crumble
version="v$(python -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')"
if test -z "${GH_CONFIG_DIR:-}" && test -f .crumble/github/hosts.yml; then
  GH_CONFIG_DIR="$PWD/.crumble/github"
  export GH_CONFIG_DIR
fi
test -z "$(git status --porcelain)" || { echo "Commit or resolve local changes first."; exit 1; }
python scripts/release_check.py
test "$(gh api user --jq .login)" = "$owner" || { echo "Sign in as the expected owner."; exit 1; }
if ! gh repo view "$owner/$repo" >/dev/null 2>&1; then
  gh repo create "$owner/$repo" --public --source=. --remote=origin \
    --description "Garment photo search, design changes, human review and SMV suggestions."
fi
remote="$(git remote get-url origin)"
case "$remote" in
  "https://github.com/$owner/$repo.git"|"git@github.com:$owner/$repo.git") ;;
  *) echo "Origin does not match the intended repository."; exit 1 ;;
esac
test "$(git rev-parse "$version^{commit}")" = "$(git rev-parse HEAD)" || {
  echo "Tag the reviewed release commit before publishing."; exit 1;
}
git push -u origin main
git push origin "$version"
gh release create "$version" \
  "dist/project_crumble-${version#v}-py3-none-any.whl" \
  "dist/project_crumble-${version#v}.tar.gz" \
  --verify-tag --prerelease --title "Project Crumble ${version#v}" --notes-file docs/RELEASE_NOTES.md

