# Contributing

Contributions are welcome through issues and pull requests. Keep changes small
enough to review. Explain the problem, the resulting behaviour and how it was
checked.

~~~sh
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
python -m pytest -q
ruff check crumble tests
ruff format --check crumble tests
python -m build
~~~

Use synthetic fixtures or data with explicit redistribution rights. Do not
commit production photos, source exports, reviewer identities, tokens, model
caches, trained weights or factory time-study data.

Preserve evidence states and snapshot checks. Unknown is not absent. A visual
proposal is not human verification. Do not report a similarity score as an
accuracy percentage. Model improvements need identity/image-disjoint evaluation
and a clear dataset provenance record.

Describe material dependency or licence changes in your PR. By submitting a
contribution, you agree to license your contribution under Apache-2.0 and confirm
that you have the right to contribute it. No copyright assignment is required.

For suspected vulnerabilities, follow SECURITY.md rather than opening an issue
with exploitable details or private data.

