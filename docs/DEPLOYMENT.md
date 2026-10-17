# Deployment

Python 3.11+ on Linux or macOS is supported by the source. Release checks use
Linux; macOS has not been tested. Windows users should use WSL2 or the container.
The worker and index builder use POSIX file locks.

## Local use

~~~sh
crumble --workspace retailer worker --watch --max-jobs 1000
crumble --workspace retailer serve
~~~

The worker embeds images and rebuilds after processing a batch. --max-jobs sets
a bounded processing/index cycle. Jobs recover after interruption. Use --retry
after correcting a failed source or dependency problem.

A workspace's provider settings are fixed at initialisation. To change encoder
or its library version, create a new workspace and reimport. No model is promoted
automatically. CPU is the default. --device cuda is an explicit opt-in at init;
plan GPU memory before using shared hardware.

## Container

Create a local .env from .env.example. Generate a random token of at least
32 characters and set CRUMBLE_TOKEN. Do not commit .env.

~~~sh
python -c "import secrets; print(secrets.token_urlsafe(32))"
docker compose build
docker compose run --rm app crumble --workspace /data demo
docker compose up
~~~

The app runs as an unprivileged user. Compose binds port 8765 to loopback.
Workspace and model-cache volumes persist separately. Set CRUMBLE_EXTRAS=fashion
or fashion,ann before building to add model dependencies. Initialise an empty
workspace with --encoder fashion instead of running the descriptor demo.

## Remote access

A non-loopback --host requires CRUMBLE_TOKEN. Put the service behind an HTTPS
reverse proxy and firewall. Set CRUMBLE_ALLOWED_HOSTS to the exact hostname.
Do not use a wildcard on the public internet.

The app does not trust forwarded headers by default. For TLS termination, use
bearer-token API clients or review proxy trust and secure-cookie configuration
before remote browser use. Do not expose an unauthenticated instance directly.

This alpha is one organisation per workspace, one embedding worker, and a
shared read/write access token. Reviewer names are attribution fields, not
verified accounts. There are no per-user roles, SSO, tenant isolation or high
availability. Rotate the token to invalidate browser sessions.

## Larger catalogues

~~~sh
pip install -e '.[fashion,ann]'
crumble --workspace retailer worker --max-jobs 1000 --index-backend hnsw --watch
~~~

Each 768-dimensional float32 vector occupies 3,072 bytes. One million image
views need about 3.1 GB for one vector matrix. SQLite, published matrices, HNSW,
image files and old index generations add overhead. HNSW loads a separate
in-memory index. Each additional view creates another vector.

This is a capacity calculation, not a benchmark. The public package has not
been load-tested at one million images. The private precursor's catalogue size
is not a scale guarantee for this standalone application.

Monitor disk capacity, query latency, failed jobs and index age. Check approximate
HNSW recall against exact search on your catalogue. Category filters operate on
the candidate shortlist; a response flags possibly limited results.

PostgreSQL, object storage, managed vector services and distributed workers are
future backends. The current code is suitable for measured pilots, not an
unqualified enterprise-scale promise.

## Backup and upgrade

For a simple consistent backup, stop the API and worker and copy the complete
workspace. Copying only crumble.sqlite while WAL writers run is not sufficient.
For online backups, use SQLite's backup API and a coordinated snapshot of the
immutable assets and index generations.

Restore to a new directory and verify search and history before switching.
The current schema is version 1. Newer schemas are refused. No destructive
automatic migration is implemented. Old index generations are retained and can
be archived during maintenance after stopping readers.

