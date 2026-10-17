Project Crumble is an open-source workspace for garment photo search, design
comparisons, human review and suggested changes in Standard Minute Value.

This first alpha includes local ingestion, multiple image views, versioned
embeddings, exact/optional HNSW search, a responsive reviewer interface, structured
part corrections, evidence history, review exports and operation-based SMV ranges.

Start with the synthetic demo in README.md. Use the optional pinned FashionSigLIP
provider for image and text retrieval with your own licensed photographs.
Provide your own operation library for meaningful production-time suggestions.

Code is Apache-2.0. No retailer catalogue, private photos, private model adapters
or factory time-study data are included.

Validation: 50 tests, installed-wheel checks on Python 3.12, source checks on
Python 3.14, browser checks at three screen widths, model execution smoke check,
and a base-runtime advisory scan. See docs/RELEASE_CHECKS.md for scope and limits.

This is a pilot release. It does not claim 98% accuracy, exact total garment SMV,
enterprise SSO, distributed storage or independently validated factory results.

