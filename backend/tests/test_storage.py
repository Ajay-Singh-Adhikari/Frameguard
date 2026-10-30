import pytest

from frameguard.config import Config
from frameguard.storage import IpfsNodeStorage, PinataStorage, build_storage
from frameguard.util import FrameGuardError


def _capture():
    """A stub upload_fn that records calls and returns both response shapes."""
    calls = []

    def fn(url, headers, files, data):
        calls.append({"url": url, "headers": headers, "files": files, "data": data})
        return {"data": {"cid": "bafytest", "size": 123}, "Hash": "bafytest", "Size": "123"}

    return fn, calls


def test_build_storage_none():
    assert build_storage(Config(storage_backend="none")) is None


def test_pinata_add_bytes_returns_cid_and_url():
    fn, calls = _capture()
    store = PinataStorage("jwt-123", "https://gw/ipfs/", upload_fn=fn)
    out = store.add_bytes(b"hello", "x.bin")
    assert out["cid"] == "bafytest"
    assert out["gateway_url"] == "https://gw/ipfs/bafytest"
    assert out["backend"] == "pinata"
    assert calls[0]["headers"]["Authorization"] == "Bearer jwt-123"


def test_ipfs_node_add_bytes_hits_add_endpoint():
    fn, calls = _capture()
    store = IpfsNodeStorage("http://127.0.0.1:5001", "https://gw/ipfs/", upload_fn=fn)
    out = store.add_bytes(b"hello", "x.bin")
    assert out["cid"] == "bafytest"
    assert out["gateway_url"] == "https://gw/ipfs/bafytest"
    assert "/api/v0/add" in calls[0]["url"]


def test_pinata_requires_jwt():
    with pytest.raises(FrameGuardError):
        PinataStorage("", "https://gw/ipfs/")
