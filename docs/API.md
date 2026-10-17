# API

The running server exposes its complete schema at /openapi.json and a local
documentation entry point at /docs. API and image requests use a bearer token
when CRUMBLE_TOKEN is set. Browser sign-in creates an HTTP-only session cookie.

| Route | Purpose |
|---|---|
| GET /health | Process health and version; no private data |
| GET /api/status | Counts, job states, encoder, index and operation library |
| GET /api/products | Paginated catalogue; q, category, offset, limit |
| POST /api/ingest | Multipart metadata JSON plus 1–8 files; queues embeddings |
| POST /api/search/photo | Multipart file, category, limit |
| GET /api/search/text?q=... | Text-to-image retrieval with the fashion provider |
| GET /api/products/{id}/similar | Search from a stored garment |
| GET /api/products/{id} | Current source snapshot |
| POST /api/products/{id}/infer | Unpersisted visual part proposals |
| PATCH /api/products/{id}/parts | Snapshot-bound correction with reviewer |
| GET /api/compare?a=...&b=... | Part comparison and SMV suggestion |
| POST /api/reviews | Snapshot-bound relationship and SMV review |
| GET /api/queue | Pending candidate pairs with current evidence |
| GET /api/products/{id}/history | Snapshots, corrections and reviewed relationships |
| GET /api/export | Stream review JSONL |
| GET /assets/{sha256} | Stored metadata-free JPEG derivative |

Search results include provider identity, index generation, model revision,
similarity scores and candidate-pool limitations. No calibrated confidence or
exact-match probability is returned.

For imports through the web/API, send metadata fields from docs/DATA.md but omit
images; attach the bytes as multipart files. Server-local path ingestion is CLI
only. Requests do not trigger arbitrary remote URL fetching.

Review requests contain a, b, snapshot_a, snapshot_b, relation, changed,
reviewer, note, smv_decision and smv_library_hash. Fetch the comparison immediately
before reviewing. If a source or the time library changes, refresh and recheck.

~~~sh
curl -H "Authorization: Bearer $CRUMBLE_TOKEN" \
  'http://127.0.0.1:8765/api/compare?a=dress-a&b=dress-b'
~~~

