# Evaluate retrieval

The evaluator checks declared group/image overlap across train, validation and
test, then reports top-1, top-10 and precision of externally supplied confident
decisions. No-match queries count against confident precision when claimed.

~~~sh
python -m crumble.evaluate_cli judged-results.jsonl
~~~

Each record includes:

~~~json
{
  "query_id": "query-001",
  "split": "test",
  "group_ids": ["declared-connected-identity-component"],
  "photo_hashes": ["all-known-query-and-positive-image-hashes"],
  "positive_ids": ["known-positive-listing"],
  "ranked_ids": ["retrieved-listing-1", "retrieved-listing-2"],
  "claimed": false,
  "label_source": "Independent reviewer or verified product identity reference"
}
~~~

Use an empty positive_ids list for a true no-match query. Deduplicate ranked
results. Include all known alias component IDs and reused image hashes.
The evaluator can reject declared leakage; it cannot discover omitted aliases.

claimed is a frozen decision from the system being measured. Crumble's default
search does not claim confident identity. Choose any threshold on validation
only, record it, then apply it unchanged to test.

The numerical 98% gate requires observed top-1 and claim precision at least .98,
at least 100 claims, claim precision Wilson lower 95% bound at least .95, and
known-match claim coverage at least .5. Passing this arithmetic gate alone does
not certify a dataset, independent labels, factory use or a production model.

Wilson intervals assume independent queries. Use a grouped bootstrap when
queries share garment identity, shoot, brand or other dependencies. Keep an
independent benchmark manifest with exact model/index hashes, gallery size,
target availability, label provenance, crop failures and no-match sampling.

