Project Crumble is an open-source workspace for garment photo search, design
comparisons, human review and suggested changes in Standard Minute Value.

Version 0.2 adds native Windows setup, a public project website and a browser
comparison demo, along with a refined reviewer interface and system fixes.

The application includes local ingestion, multiple image views, versioned
embeddings, exact/optional HNSW search, a responsive reviewer interface, structured
part corrections, evidence history, review exports and operation-based SMV ranges.

Start with the synthetic demo in README.md. Use the optional pinned FashionSigLIP
provider for image and text retrieval with your own licensed photographs.
Provide your own operation library for meaningful production-time suggestions.

Code is Apache-2.0. No retailer catalogue, private photos, private model adapters
or factory time-study data are included.

Validation: 77 native Windows tests passed with one Linux-only skip. Website and
application browser checks passed at three widths; the website also passed
17 interaction checks. Category retrieval, job/index consistency, session expiry,
snapshot-bound reviews and selected-image inference have regression coverage.
See docs/RELEASE_CHECKS.md and GitHub Actions for scope and exact-commit results.

This is a pilot release. It does not claim 98% accuracy, exact total garment SMV,
enterprise SSO, distributed storage or independently validated factory results.

