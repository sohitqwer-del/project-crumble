# Models and evidence

## Included providers

**demo** is a 192-dimensional descriptor from an 8x8 RGB image. It is a
deterministic test fixture, not a trained fashion model. Original drawings test
installation, data flow, search, comparisons and review persistence. They do
not measure real-world retrieval.

**fashion** uses Marqo/marqo-fashionSigLIP at revision
c56244cc94f92419e8369fa71efdaf403b124ce8 through OpenCLIP. It produces normalised
768-dimensional image/text vectors. The provider identity also records the
OpenCLIP version. Weights download from the original host and are not included
in this repository. See the upstream
[model card](https://huggingface.co/Marqo/marqo-fashionSigLIP)
for the model author's training description and licence.

The public provider has not been fine-tuned on the private project's data.
Private adapters, retailer imagery, proprietary benchmarks and calibration
constants are excluded. Previous private-system results are not evidence for
this package's accuracy.

## Part extraction

English title rules preserve quoted source evidence and uncertainty.
The optional fashion provider ranks text prompts for neckline, sleeve length,
sleeve shape and pattern. A margin threshold can leave a field unknown.
These margins are not calibrated confidence scores.

Prompt rankings cannot establish hidden construction, actual fibre composition,
seam lengths, operation times or identity. Multiple garments, unusual poses,
occlusion, product styling, low resolution and plain basics are known failure
cases. The reviewer must choose the relevant garment and check each proposal.

## What has been verified

The release exercises the complete synthetic workflow and real model execution
on a synthetic image. This establishes that the implementation runs. It is not
a retail accuracy benchmark, a factory time validation or a claim of 98% accuracy.

## Evaluating your data

Keep product identities and reused images together when splitting datasets.
Detect regional aliases and exact/near image duplicates before splitting.
A product-ID-only split is insufficient. Choose model and thresholds using
training and validation only; freeze an untouched test set.

Measure both correct top-1 recovery and precision among confident decisions.
Include true no-match queries. Report coverage, sample counts, brand/category
coverage, crop failures, missing targets, confidence intervals and gallery size.
Evaluate complete photo uploads, including garment selection and indexing gaps.

A same-photo or same-outfit pair is not necessarily the same garment.
Unknown duplicate identities can also distort retrieval labels.
The application makes no confidence claims by default.

Independent multi-brand photo queries, human part annotations and factory time
studies are still needed before stronger production claims. A generic detector,
segmentation model or visual language model should enter as an optional,
versioned proposal provider with its own evaluation and licence review.

