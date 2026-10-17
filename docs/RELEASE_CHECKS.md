# Alpha release checks

## 0.2.0a1 — local Windows and website

Checked on 17 October 2026 with native Windows Python 3.11:

- 77 tests passed, with one Linux-only file-descriptor test skipped.
- Spawned-process locking, signed session expiry, Unicode credentials,
  category-first retrieval, job recovery and stale evidence checks passed.
- The local application passed photo search, crop, saved review, history and
  long-filename layout checks at 1280, 390 and 320 pixels.
- The four-page website passed those three widths, local links/assets and
  17 interactive checks including signed SMV deltas and browser-only exports.
- Browser evidence is generated locally; no private catalogue data was used.

The CI matrix includes native Windows and Linux tests, website build checks
and the Linux container build. See the repository's Actions tab for results
on the exact release commit.

## 0.1.0a1 — original Linux baseline

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

Post-publication GitHub CI passed on Python 3.11, 3.12 and 3.14, including the
Docker image build and a demo run inside the container. Evidence:
https://github.com/sohitqwer-del/project-crumble/actions/runs/39042211624

macOS, CUDA, enterprise load, SSO and remote proxy deployments were not verified.

