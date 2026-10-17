# Garment and review data

Each JSONL row or CSV row describes one garment. Required fields are id, title,
rights and images (or image_path). CSV images may be a JSON list inside a quoted
cell. JSONL is recommended for rich parts and multiple views.

| Field | Meaning |
|---|---|
| id | Stable local identifier, letters/digits/dot/hyphen/underscore, up to 100 characters |
| title | Source product title, up to 1,000 characters |
| brand | Source label, optional |
| category | Your controlled garment type, used for exact filters |
| identity_group | Optional known product family/alias group; never proof of copied design |
| source_url | Attribution reference; the application does not fetch it |
| rights | Image ownership, licence or permission reference; required |
| observed_at | Source observation date supplied by the importer |
| images | 1–8 local image filenames inside the selected image root |
| parts | Optional structured claims keyed by known field names |

Example claim:

~~~json
{
  "neckline": {
    "state": "verified",
    "values": ["square"],
    "source": "Technical pack, revision 3, page 2",
    "note": "Front construction checked"
  }
}
~~~

Supported fields: category, silhouette, neckline, sleeve_length, sleeve_shape,
length, waist, hem, closure, pockets, fabric, pattern, colour, detail, back,
seams and composition.

States: stated, inferred, verified, unknown, not_visible and conflicting.
Unknown and not_visible require empty values. A verified claim must cite its
source. "none" is an explicit absence; it is different from missing data.

## Import and update

~~~sh
crumble --workspace retailer import products.jsonl --image-root photos --report result.jsonl
crumble --workspace retailer worker --watch
~~~

The importer streams rows, validates paths (including resolved symlinks), stores
images, and writes per-row results. It exits nonzero if any row fails. Successful
rows stay committed. Reimporting retries the input without duplicating snapshots.

No arbitrary HTTP image downloading is implemented. Import a licensed local
export or implement an authorised source connector outside the web-facing path.
Do not put a customer export in the public Git repository.

## Evidence and exports

A snapshot contains source metadata, current image IDs and structured fields.
Each correction creates a new snapshot and an event with reviewer attribution.
Claims imported as "verified" reflect the importer; the software has not
independently verified them.

GET /api/export returns review JSONL with snapshot IDs, relationship, changed
parts, reviewer, note, time library and SMV suggestion. Keep names and notes
private unless the contributors explicitly agree to public redistribution.

The public release contains no real retailer photos, labelled production pairs
or model-training dataset.

