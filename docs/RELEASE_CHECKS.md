# Alpha release checks

Checked on 17 October 2026, on Linux.

| Check | Result |
|---|---|
| Python source tests | 50 passed on Python 3.14 |
| Installed-wheel tests outside the source directory | 50 passed on Python 3.12 |
| Clean demo | 10 synthetic garments, 10 image views, 20 proposed review pairs |
| Browser search and review persistence | Passed at 1280, 390 and 320 CSS pixels |
| Browser JavaScript errors / page overflow | None in those checked workflows |
| Real FashionSigLIP CPU execution | Image/text vectors of dimension 768; part proposals returned |
| Exact and optional HNSW search | Demo self-query returned the expected item first |
| Index corruption / empty publication | Rejected; empty build preserved the active generation |
| Stale review / correction | Rejected when source snapshots changed |
| Upload and origin checks | Invalid/oversize inputs and cross-origin writes rejected |
| SQLite connection lifecycle | Retained closed connections did not accumulate descriptors |
| Ruff checks | Passed |
| Base dependency advisory scan | 17 packages checked, no known advisories returned |
| Source and package artifact scan | No runtime databases, model weights, backups or detected secrets |

The advisory scan covers the pinned base runtime, not every optional machine
learning/native dependency. It is not a security audit. The scan needed one
retry after a network timeout.

The FashionSigLIP smoke check used a synthetic illustration. Retrieval quality,
part correctness and factory times have not been independently benchmarked in
this public package.

Docker configuration is included. Docker was not available on the release
server, so the container build remains a CI check after publication. macOS,
CUDA, enterprise load, SSO and remote proxy deployments were not verified.

