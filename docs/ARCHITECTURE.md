# Architecture

Crumble is a self-contained application. One workspace holds one organisation's
catalogue and review history. The web application does not read any external
catalogue database.

~~~text
Local images + metadata + rights
             |
             v
  Validate / normalise / hash
             |
       SQLite snapshots ---------> structured garment claims
             |                              |
  Immutable image files                     v
             |                      before / after comparison
     resumable job queue                    |
             |                    operation library + sources
    pinned embedding provider               |
             |                      SMV delta suggestions
     versioned vector store                  |
             |                              v
     atomic index generation -------> reviewer workspace
             |                              |
      image / text search             immutable reviews
                                            |
                                    JSONL export / evaluation
~~~

## Persistence

- SQLite WAL stores products, snapshots, assets, models, vectors, jobs, reviews,
  review candidates and correction events.
- Every image has a decoded-pixel content hash, after orientation correction and
  a maximum 2048-pixel thumbnail. Storage uses a metadata-free JPEG derivative.
  This is not a bit-preserving archive of the original upload.
- The same photo can belong to several listings or depict several garments.
  A shared image hash never establishes shared garment identity.
- Import source hashes make repeated imports idempotent. Human corrections
  survive reimporting the same source. A changed source makes a new snapshot;
  previous reviews remain available and are marked stale.
- Review writes use an immediate transaction and both snapshot IDs. A concurrent
  edit causes the stale write to fail.
- A single workspace worker lock prevents duplicate work. Interrupted jobs are
  requeued, with at most three processing attempts before an error state.

## Retrieval

Provider identity includes the model revision, provider implementation and
OpenCLIP version. A query cannot silently use another provider's index.
Vectors are normalised float32. Image views are separate search entries and
results are merged by product; declared identity groups can be merged through
the Python search interface.

Exact search reads memory-mapped vectors in blocks of 32,768 and retains the
highest-scoring candidates. HNSW is optional and approximate. Its candidates are
rescored using the stored float32 vectors. Category filtering is applied to the
candidate pool; a response flags when filtering may have limited results.

Index builds use a consistent database read transaction. They publish a new
generation with checksums, then atomically change a small pointer. A failed or
empty build preserves the previous generation. A reader holds its current files
until the next request detects a new generation. Old generations stay on disk;
archive or remove unused generations during planned maintenance.

## Parts and style history

The schema separates identity, structure, surface and construction. Unknown
parts never count as matching parts. Inferred claims produce proposed changes.
Titles support a small English rule baseline. The optional fashion model gives
uncalibrated visual proposals for four visible attributes. It does not measure
seams, hidden construction, fibre composition or factory methods.

Snapshots and reviewed relationships form an observed history. They show related
designs and recorded changes. They do not prove influence, copying or first
creation dates. A dedicated graph UI and richer pattern-piece extraction are
future work; the history API already exposes the evidence.

## Extension boundaries

Add an encoder by implementing a stable spec, dimension, images() and optional
texts() methods. Any weights or preprocessing change must change its identity.
Add extraction providers as proposals with image, model and source references.
They must not overwrite verified claims automatically.

The time engine is separate from retrieval. An engineer can replace the example
operation library without retraining the photo model. Do not turn cosine
similarity, softmax scores or operation ranges into calibrated probabilities.

