# Local application, optional remote GPU

The standalone application and website run from your own GitHub checkout. An
SSH-accessible training machine is optional. The website never connects to it.

Use the local workspace for the reviewer application, data schemas, tests,
website assets and public source. Keep large model caches, licensed training
datasets and GPU jobs on the training machine when that is more practical.

## Check a training host

Use the optional read-only helper with your own connection information:

~~~powershell
.\scripts\training-doctor.ps1 -HostName training.example.com -UserName training -IdentityFile C:\Keys\training-key -PythonPath /opt/training/bin/python
~~~

The command prints Python/PyTorch/CUDA capability information. It does not start
training, download a model, read a dataset, change services or load GPU weights.
Keep host profiles and private paths in the ignored .crumble directory.

## Training and evaluation workflow

1. Export only reviews you have permission to use. Bind labels to the exact
   garment images and evidence snapshots reviewed by the annotator.
2. Keep identity components and exact/near image aliases together. Freeze
   train/validation/test splits before fitting a model.
3. Fine-tune in your authorised GPU environment. Record dataset rights,
   preprocessing, seed, dependency versions and model/checkpoint hashes.
4. Select the checkpoint and confidence threshold using validation only. Include
   independently verified no-match cases in the held-out search evaluation.
5. Bring back a versioned, approved model artifact and evaluation report.
   Change the encoder's provider identity and rebuild all affected embeddings
   and indexes together. Never silently replace weights under an old identity.

The public alpha includes the pretrained FashionSigLIP provider and evaluation
tools. A one-command general-purpose fine-tuner and automatic model promotion
are not implemented. The training host's existing private experiments are not
part of this public repository, and their results are not this package's metrics.

Before publishing any data or weights, review redistribution rights. Public
source must not contain private retailer photos, factory operation libraries,
reviewer identities, credentials or data exports. Shared GPU jobs also need a
resource budget; do not restart other users' model services.
