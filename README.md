# Project Crumble

An open-source garment archive and visual retrieval workspace. Store your garment
photos and product records, create image embeddings, then upload a reference to
retrieve up to four closest previous styles for review.

[Website and browser demo](https://project-crumble.edp395764.chatgpt.site) ·
[Setup documentation](https://project-crumble.edp395764.chatgpt.site/docs.html)

Status: **0.2.0a1, working alpha**. This release is for local use and retailer pilots.
Search quality and deployment scale must be evaluated on your own archive.
No 98% accuracy claim is made.

## Run on Windows

Clone the repository, then run this from PowerShell in the project directory:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1
~~~

This creates a project-local virtual environment, installs dependencies, prepares
the original sample collection once, and starts http://127.0.0.1:8765.
After setup, use the same command with -SkipInstall for a faster start.
The application, website and data workspace can run on your own computer.
Remote GPU and training data access are optional; see [training setup](docs/TRAINING_SETUP.md).

## Run on Linux or macOS

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

Open http://127.0.0.1:8765 and choose **Photo search**. Upload a reference to find
the closest stored styles. The lightweight demo uses original drawings and simple
image descriptors to check the workflow; it is not the fashion model. It needs no GPU,
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

## How retrieval works

1. Import local images with garment IDs, titles, brands, categories and source rights.
2. Store working image copies and link each view to its product record in SQLite.
3. Generate an embedding for each image using the configured encoder.
4. Publish a model-specific vector index.
5. Encode an uploaded reference with the same model and rank similar vectors.
6. Return up to four distinct product records in the interface, showing the matched view.

The optional fashion encoder uses a pinned Marqo-FashionSigLIP revision and
normalised 768-value image embeddings. The index combines multiple matched
views into one result per product. Fewer eligible products produce fewer results.

An embedding is a numeric representation for visual comparison. Similarity
scores rank candidates; they are not match probabilities. Importing images
creates embeddings and an index; it does not train a new model.

## Retrieval and archive features

- CSV/JSONL import, multiple image views and source/rights metadata.
- SQLite garment records, immutable snapshots and linked working image files.
- Versioned embeddings, resumable jobs and atomic index publication.
- Exact blocked vector search; optional FAISS HNSW for approximate retrieval.
- Photo upload, drop, paste and manual crop; text search with the fashion encoder.
- Category filtering and title/brand lookup.
- Top-four result cards with the matched image and links to stored records.
- Product views, source context and existing review history.
- A public explanation site and a clearly labelled four-record sample archive.

The application searches your imported collection. There is no built-in retailer
scraper or shared global catalogue. A retrieved style is a useful reference,
not evidence of a launch date, influence or copying.

The workspace stores oriented, resized JPEG derivatives. Keep original image
files separately if you need a lossless asset archive.

See [data format](docs/DATA.md), [architecture](docs/ARCHITECTURE.md),
[deployment](docs/DEPLOYMENT.md), [model notes](MODEL_CARD.md),
[evaluation](docs/EVALUATION.md), [API](docs/API.md), and [contributing](CONTRIBUTING.md).

## Licence

Code and original demo generator: Apache-2.0. See [LICENSE](LICENSE),
[NOTICE](NOTICE) and [third-party components](THIRD_PARTY.md).
No retailer dataset, private review, fine-tuned weights or service credentials
are distributed.

