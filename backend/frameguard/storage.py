"""Off-chain IPFS storage for the video and its manifest.

At registration the video and the manifest are content-addressed on IPFS and
their CIDs are recorded alongside the anchor — the same off-chain/on-chain split
NISHAAN uses, applied to video. Two real backends share one interface:

* ``pinata`` — upload via the Pinata pinning service (needs a JWT).
* ``ipfs``   — a local Kubo node's HTTP API (needs ``ipfs daemon``).

The HTTP call is injected (``upload_fn``) so the backends are unit-testable
without a network or an account. ``none`` (default) disables storage.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional, Protocol, Union

from .config import Config
from .util import FrameGuardError

# (url, headers, files, data) -> parsed JSON response
UploadFn = Callable[[str, dict, dict, dict], dict]


def _httpx_upload(url: str, headers: dict, files: dict, data: dict) -> dict:
    try:
        import httpx
    except ImportError as exc:  # pragma: no cover - httpx is a core dep
        raise FrameGuardError("IPFS storage needs httpx") from exc
    try:
        with httpx.Client(timeout=60) as client:
            resp = client.post(url, headers=headers, files=files, data=data)
            resp.raise_for_status()
            return resp.json()
    except FrameGuardError:
        raise
    except Exception as exc:  # network / HTTP / decode errors
        raise FrameGuardError(f"IPFS upload failed: {exc}") from exc


class Storage(Protocol):
    name: str

    def add_file(self, path: Union[str, Path], name: Optional[str] = None) -> dict: ...
    def add_bytes(self, data: bytes, name: str) -> dict: ...


class PinataStorage:
    name = "pinata"
    ENDPOINT = "https://uploads.pinata.cloud/v3/files"

    def __init__(self, jwt: Optional[str], gateway: str, upload_fn: UploadFn = _httpx_upload):
        if not jwt:
            raise FrameGuardError("pinata storage needs FRAMEGUARD_PINATA_JWT")
        self._jwt = jwt
        self._gateway = gateway
        self._upload = upload_fn

    def add_bytes(self, data: bytes, name: str) -> dict:
        headers = {"Authorization": f"Bearer {self._jwt}"}
        files = {"file": (name, data, "application/octet-stream")}
        resp = self._upload(self.ENDPOINT, headers, files, {"network": "public", "name": name})
        payload = resp.get("data") or resp
        cid = payload.get("cid") or payload.get("IpfsHash")
        if not cid:
            raise FrameGuardError(f"Pinata upload returned no CID: {resp}")
        return {"cid": cid, "size": payload.get("size"), "backend": self.name,
                "gateway_url": self._gateway + cid}

    def add_file(self, path: Union[str, Path], name: Optional[str] = None) -> dict:
        p = Path(path)
        return self.add_bytes(p.read_bytes(), name or p.name)


class IpfsNodeStorage:
    name = "ipfs"

    def __init__(self, api_url: str, gateway: str, upload_fn: UploadFn = _httpx_upload):
        self._api = api_url.rstrip("/")
        self._gateway = gateway
        self._upload = upload_fn

    def add_bytes(self, data: bytes, name: str) -> dict:
        url = f"{self._api}/api/v0/add?cid-version=1"
        files = {"file": (name, data, "application/octet-stream")}
        resp = self._upload(url, {}, files, {})
        cid = resp.get("Hash") or resp.get("cid")
        if not cid:
            raise FrameGuardError(f"IPFS node returned no CID: {resp}")
        return {"cid": cid, "size": resp.get("Size"), "backend": self.name,
                "gateway_url": self._gateway + cid}

    def add_file(self, path: Union[str, Path], name: Optional[str] = None) -> dict:
        p = Path(path)
        return self.add_bytes(p.read_bytes(), name or p.name)


def build_storage(config: Config) -> Optional[Storage]:
    backend = (config.storage_backend or "none").lower()
    if backend in ("none", "", "off", "disabled"):
        return None
    if backend == "pinata":
        return PinataStorage(config.pinata_jwt, config.ipfs_gateway)
    if backend == "ipfs":
        return IpfsNodeStorage(config.ipfs_api_url, config.ipfs_gateway)
    raise FrameGuardError(f"Unknown storage backend '{config.storage_backend}'")
