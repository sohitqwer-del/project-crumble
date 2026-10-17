import io
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from crumble.api import create_app
from crumble.ingest import decode
from crumble.models import ProductInput
from crumble.smv import validate_library
from crumble.store import Store


def test_empty_reviewer_style_fields_and_rights():
    with pytest.raises(ValueError):
        ProductInput.model_validate({"id": "a", "title": "x", "rights": "   "})


def test_pixel_limit_blocks_image(monkeypatch):
    import crumble.ingest as module

    monkeypatch.setattr(module, "MAX_PIXELS", 100)
    b = io.BytesIO()
    Image.new("RGB", (11, 11)).save(b, "PNG")
    with pytest.raises(ValueError, match="megapixels"):
        decode(b.getvalue())


def test_oversize_request_rejected_without_success(tmp_path):
    c = TestClient(create_app(tmp_path / "w"))
    # Invalid body is not accepted even without a truthful Content-Length header.
    response = c.post(
        "/api/session", content=b" " * (21 * 1024 * 1024 + 1), headers={"Content-Type": "application/json"}
    )
    assert response.status_code in (400, 413)


def test_closed_connections_do_not_accumulate_file_handles(tmp_path):
    if not Path("/proc/self/fd").exists():
        pytest.skip("Linux descriptor test")
    store = Store(tmp_path / "w")
    before = len(os.listdir("/proc/self/fd"))
    retained = []
    for _ in range(200):
        with store.connect() as c:
            c.execute("SELECT count(*) FROM products")
            retained.append(c)
    assert len(os.listdir("/proc/self/fd")) <= before + 2
    with pytest.raises(Exception):
        retained[-1].execute("SELECT 1")


@pytest.mark.parametrize("rules", [[None], [{"field": [], "values": ["none"], "operations": []}]])
def test_malformed_rule_has_controlled_error(rules):
    with pytest.raises(ValueError):
        validate_library(
            {"version": "x", "scope": "x", "illustrative": False, "operations": [], "rules": rules}
        )
