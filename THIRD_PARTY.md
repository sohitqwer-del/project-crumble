# Third-party components

Project Crumble source is Apache-2.0. This does not relicense dependencies,
retailer images, factory standards, datasets or separately downloaded models.

## Direct runtime components

| Component | Declared upstream licence | Source |
|---|---|---|
| NumPy | BSD-3-Clause | https://github.com/numpy/numpy/blob/main/LICENSE.txt |
| Pillow | MIT-CMU | https://github.com/python-pillow/Pillow/blob/main/LICENSE |
| FastAPI | MIT | https://github.com/fastapi/fastapi/blob/master/LICENSE |
| Uvicorn | BSD-3-Clause | https://github.com/encode/uvicorn/blob/main/LICENSE.md |
| python-multipart | Apache-2.0 | https://github.com/Kludex/python-multipart/blob/master/LICENSE.txt |
| PyTorch, optional | BSD-3-Clause, with third-party notices | https://github.com/pytorch/pytorch/blob/main/LICENSE |
| OpenCLIP, optional | MIT | https://github.com/mlfoundations/open_clip/blob/main/LICENSE |
| huggingface-hub, optional | Apache-2.0 | https://github.com/huggingface/huggingface_hub/blob/main/LICENSE |
| FAISS, optional | MIT | https://github.com/facebookresearch/faiss/blob/main/LICENSE |

The release dependency inventory records installed package metadata for the
tested base environment. Dependencies retain their licence files in their
distributions. The inventory is not a legal opinion or an exhaustive review of
every optional dependency and embedded native library.

## Model

Marqo/marqo-fashionSigLIP declares Apache-2.0 in its
[model card](https://huggingface.co/Marqo/marqo-fashionSigLIP).
This integration pins revision c56244cc94f92419e8369fa71efdaf403b124ce8.
It downloads config, tokenizer files and safetensors from the model publisher.
No base weights or private fine-tuned weights are redistributed in Crumble.

The upstream model's training data is not included or relicensed here.
Evaluate its terms and suitability for your own deployment. No gated Gemma,
SAM or other private precursor dependency is required by this release.

## Images and time data

The demo generator is original project code under Apache-2.0 and creates
synthetic garment illustrations. The example times are invented and labelled
illustrative. No retailer photography, licensed print, private review or factory
time-study library is included.

A self-hosted deployment must obtain rights to its own images and operation
libraries. Rights metadata records an importer's statement; it does not establish
that the statement is legally sufficient.

