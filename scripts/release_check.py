#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Scan tracked release content. Heuristic checks supplement, not replace, review."""
import json
import re
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
paths = subprocess.check_output(["git","ls-files","-z"],cwd=root).decode().split("\0")
issues = []
patterns = [
    (re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),"private key"),
    (re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})"),"GitHub token"),
    (re.compile(r"sk-[A-Za-z0-9_-]{30,}"),"API key"),
    (re.compile(r"/(?:srv|home)/[A-Za-z0-9_.-]+/"),"private deployment reference"),
]
for name in filter(None,paths):
    p = root/name
    if p.is_symlink() or not p.is_file():
        issues.append({"file":name,"reason":"symlink or missing file"})
        continue
    if any(x in name.split("/") for x in ("local","service","work","weights",".venv",".crumble")):
        issues.append({"file":name,"reason":"private/runtime directory"})
    if p.suffix in (".sqlite",".db",".npy",".npz",".pt",".pth",".safetensors") or ".bak-" in name:
        issues.append({"file":name,"reason":"data/weights/backup artifact"})
    if p.suffix == ".sh" and b"\r" in p.read_bytes():
        issues.append({"file":name,"reason":"shell scripts require LF line endings"})
    if name == ".env" or p.stat().st_size > 2_000_000:
        issues.append({"file":name,"reason":"secret config or unexpected large file"})
    if name == "scripts/release_check.py":
        continue  # Pattern literals are the scanner, not deployed secrets.
    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        if p.suffix not in (".png",".jpg",".jpeg",".webp",".ico",".ttf",".woff2"):
            issues.append({"file":name,"reason":"unexpected binary"})
        continue
    for pattern, reason in patterns:
        if pattern.search(text):
            issues.append({"file":name,"reason":reason})
print(json.dumps({"tracked_files":len(list(filter(None,paths))),"issues":issues},indent=2))
raise SystemExit(bool(issues))

