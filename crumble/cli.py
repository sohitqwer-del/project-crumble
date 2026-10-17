# SPDX-License-Identifier: Apache-2.0
import argparse
import json
import os
import sys
import time
from pathlib import Path

from .embeddings import Encoder
from .settings import initialise
from .store import Store
from .util import atomic, canonical


def main(argv=None):
    parser = argparse.ArgumentParser(prog="crumble", description="Project Crumble garment intelligence")
    parser.add_argument(
        "--workspace", default="work", help="Data directory; never commit it to source control"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--encoder", choices=["demo", "fashion"], default="demo")
    init.add_argument("--device", default="cpu")
    sub.add_parser("demo", help="Create synthetic garments and a working index in an empty workspace")
    imp = sub.add_parser("import", help="Stream local JSONL or CSV imports")
    imp.add_argument("manifest")
    imp.add_argument("--image-root", required=True)
    imp.add_argument("--report", required=True, help="Per-row import result JSONL")
    worker = sub.add_parser("worker")
    worker.add_argument("--batch-size", type=int, default=8)
    worker.add_argument("--max-jobs", type=int)
    worker.add_argument("--retry", action="store_true")
    worker.add_argument("--watch", action="store_true")
    worker.add_argument("--index-backend", choices=["exact", "hnsw"], default="exact")
    index = sub.add_parser("index")
    index.add_argument("--backend", choices=["exact", "hnsw"], default="exact")
    queue = sub.add_parser("queue")
    queue.add_argument("--limit", type=int, default=100)
    lib = sub.add_parser("operations", help="Validate and install a versioned SMV operation library")
    lib.add_argument("path")
    sub.add_parser("status")
    serve = sub.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    try:
        store = Store(args.workspace)
        if args.command == "init":
            value = initialise(store, args.encoder, args.device)
            print(json.dumps(value, indent=2))
            return
        settings = initialise(store)
        if args.command == "serve":
            if (
                args.host not in ("127.0.0.1", "localhost", "::1")
                and len(os.environ.get("CRUMBLE_TOKEN", "")) < 32
            ):
                raise ValueError("Remote binding requires CRUMBLE_TOKEN of at least 32 characters")
            import uvicorn

            from .api import create_app

            uvicorn.run(create_app(store.root), host=args.host, port=args.port, proxy_headers=False)
            return
        if args.command == "operations":
            from .smv import validate_library

            data = validate_library(json.loads(Path(args.path).read_text()))
            atomic(store.root / "operations.json", canonical(data).encode())
            print(json.dumps({"installed": data["version"]}))
            return
        if args.command == "status":
            print(json.dumps(store.summary(), indent=2))
            return
        encoder = Encoder(settings["encoder"], settings["device"])
        from .jobs import enqueue, work
        from .retrieval import Search, build

        if args.command == "import":
            from .ingest import import_file

            result = import_file(store, args.manifest, args.image_root, args.report)
            enqueue(store, encoder)
            print(json.dumps(result))
            if result["error"]:
                raise SystemExit(1)
        elif args.command == "demo":
            from .demo import make
            from .queue import populate

            result = make(store)
            work(store, encoder)
            build(store, encoder)
            result["review_queue"] = populate(store, Search(store, encoder), 10)
            print(json.dumps(result))
        elif args.command == "worker":
            while True:
                result = work(store, encoder, args.batch_size, args.max_jobs, args.retry)
                if result["completed"]:
                    result["index"] = build(store, encoder, args.index_backend)
                print(json.dumps(result), flush=True)
                if not args.watch:
                    break
                args.retry = False
                time.sleep(10)
        elif args.command == "index":
            print(json.dumps(build(store, encoder, args.backend)))
        elif args.command == "queue":
            if not 1 <= args.limit <= 100000:
                raise ValueError("limit must be between 1 and 100000")
            from .queue import populate

            print(json.dumps(populate(store, Search(store, encoder), args.limit)))
    except (ValueError, OSError, ImportError) as exc:
        print(type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
