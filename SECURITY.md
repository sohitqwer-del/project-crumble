# Security

The alpha is intended for local workspaces and controlled pilots. Its shared
token grants read and write access. There is no multi-tenant or role-based access
control. Use TLS, a firewall and an organisation-owned deployment boundary.

Do not send real customer images or factory records to an untrusted instance.
Image processing is bounded by file size and pixel count. Uploads are decoded,
normalised and rewritten; original metadata is not retained. The server does
not fetch user-supplied URLs or accept local paths through the API.

Keep Python, Pillow, the web stack and optional inference libraries updated.
Check model revisions and licences before changing providers. Do not load
untrusted pickled checkpoints. The bundled fashion integration uses pinned
safetensors weights and does not enable remote Python code.

Report vulnerabilities through the repository's private security advisory form
when it is enabled. If it is unavailable, open an issue asking the maintainer
for a private contact method, without exploit details, tokens or private data.
No private reporting channel or response SLA is promised before the maintainer
has enabled one.

Only the latest alpha is supported. The project has not received an independent
security audit or penetration test.

