# Project Crumble

An open-source workspace for garment photos, design comparisons, human review and
suggested changes in Standard Minute Value (SMV).

Status: **0.1.0a1, working alpha**. This release is for local use and retailer pilots.
It is not a validated factory time system or a managed enterprise service.
No 98% accuracy claim is made.

## Run the complete demo

Python 3.11+ on Linux or macOS:

~~~sh
git clone https://github.com/sohitqwer-del/project-crumble.git
cd project-crumble
python -m venv .venv
. .venv/bin/activate
pip install -e .
crumble --workspace work demo
crumble --workspace work serve
~~~

Open http://127.0.0.1:8765. Select **dress-a** and **dress-b**, compare them, inspect
the sleeve and pocket changes, and save a review. The demo uses original drawings,
simple image descriptors and **invented operation times**. It needs no GPU,
model download, API key, private catalogue or external service.

## Use your own garments

~~~sh
pip install -e '.[fashion]'
crumble --workspace retailer init --encoder fashion
crumble --workspace retailer import garments.jsonl --image-root ./photos --report import-results.jsonl
crumble --workspace retailer worker
crumble --workspace retailer queue --limit 100
crumble --workspace retailer serve
~~~

The fashion provider downloads a pinned public Marqo-FashionSigLIP revision.
Models and image rights are separate from the code licence. Images are copied to
a content-addressed local store. Jobs resume after interruption.

One JSON object per input line:

~~~json
{"id":"dress-001","title":"Blue square neck midi dress","brand":"Example","category":"dress","rights":"Our own photography","images":["dress-001-front.jpg","dress-001-back.jpg"]}
~~~

Only local image paths inside the selected image root are imported. There is no
built-in scraper. Supply garments and images you have permission to use.

## What is included

- Streamed CSV/JSONL ingestion, multiple views, rights and source provenance.
- Versioned embeddings, resumable jobs and atomic search index publication.
- Exact blocked search; optional FAISS HNSW for approximate retrieval.
- Photo upload/drop/paste, manual garment crop, text search and product search.
- Structured parts with stated, inferred, verified, invisible and unknown states.
- Optional visual part proposals; English title extraction as a basic fallback.
- Side-by-side design changes, part corrections, review queues and JSONL export.
- Immutable snapshots, stale-review rejection and observed style relationships.
- Operation-based SMV delta ranges with source references and reviewer decisions.

A similar image is not proof of a copied design. Observation dates do not establish
which brand designed an item first. Whole outfits can hide which garment matched.

## SMV suggestions

Crumble maps changed part values to a **user-supplied operation library**. Each
operation specifies standard minutes, quantity, machine and evidence source.
It reports the delta for mapped operations and lists unresolved changes. It does
not infer an exact garment SMV, factory efficiency or labour cost from an image.

~~~sh
crumble --workspace retailer operations your-operation-library.json
~~~

See [SMV rules](docs/SMV.md), [data format](docs/DATA.md),
[architecture](docs/ARCHITECTURE.md), [deployment](docs/DEPLOYMENT.md),
[model notes](MODEL_CARD.md), [evaluation](docs/EVALUATION.md),
[API](docs/API.md), and [contributing](CONTRIBUTING.md).

## Licence

Code and original demo generator: Apache-2.0. See [LICENSE](LICENSE),
[NOTICE](NOTICE) and [third-party components](THIRD_PARTY.md).
No retailer dataset, private review, fine-tuned weights or service credentials
are distributed.

