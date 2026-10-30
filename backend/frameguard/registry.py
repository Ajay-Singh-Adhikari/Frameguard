"""Pick the anchor backend (local ledger vs. on-chain) from config."""
from __future__ import annotations

from typing import Optional, Protocol

from .config import Config
from .ledger import LocalLedger
from .util import FrameGuardError


class Registry(Protocol):
    def register(self, anchor: dict) -> dict: ...
    def get(self, video_id: str) -> Optional[dict]: ...
    def log_verification(self, video_id: str, root_matched: bool, actor: str = "") -> None: ...


def build_registry(config: Config) -> Registry:
    if config.anchor_backend == "chain":
        if not (config.rpc_url and config.contract_address and config.private_key):
            raise FrameGuardError(
                "anchor_backend=chain needs FRAMEGUARD_RPC_URL, "
                "FRAMEGUARD_CONTRACT_ADDRESS and FRAMEGUARD_PRIVATE_KEY"
            )
        from .chain import ChainRegistry  # imported lazily so web3 stays optional

        return ChainRegistry(
            config.rpc_url, config.contract_address, config.private_key, config.chain_id
        )
    return LocalLedger(config.ledger_path)
