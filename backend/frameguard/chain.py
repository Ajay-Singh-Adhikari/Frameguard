"""Optional on-chain anchor backed by the Solidity ``VideoRegistry`` contract.

This is only imported/used when ``FRAMEGUARD_ANCHOR_BACKEND=chain``. It keeps the
same ``register`` / ``get`` interface as :class:`LocalLedger`, so the pipeline
does not care which one it talks to. ``web3`` is an optional dependency
(``pip install -r requirements-chain.txt``).
"""
from __future__ import annotations

from typing import Optional

from .util import FrameGuardError, utc_now_iso

# Minimal ABI matching contracts/contracts/VideoRegistry.sol
_ABI = [
    {
        "inputs": [
            {"internalType": "string", "name": "videoId", "type": "string"},
            {"internalType": "bytes32", "name": "merkleRoot", "type": "bytes32"},
            {"internalType": "uint256", "name": "frameCount", "type": "uint256"},
            {"internalType": "uint256", "name": "fps", "type": "uint256"},
            {"internalType": "bytes32", "name": "metadataHash", "type": "bytes32"},
        ],
        "name": "registerVideo",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "string", "name": "videoId", "type": "string"}],
        "name": "getVideo",
        "outputs": [
            {"internalType": "bytes32", "name": "", "type": "bytes32"},
            {"internalType": "uint256", "name": "", "type": "uint256"},
            {"internalType": "uint256", "name": "", "type": "uint256"},
            {"internalType": "bytes32", "name": "", "type": "bytes32"},
            {"internalType": "address", "name": "", "type": "address"},
            {"internalType": "uint256", "name": "", "type": "uint256"},
            {"internalType": "bool", "name": "", "type": "bool"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "string", "name": "videoId", "type": "string"},
            {"internalType": "bool", "name": "rootMatched", "type": "bool"},
        ],
        "name": "logVerification",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]


def _hex32(value: str) -> bytes:
    return bytes.fromhex(value[2:] if value.startswith("0x") else value)


class ChainRegistry:
    def __init__(self, rpc_url: str, contract_address: str, private_key: str, chain_id: Optional[int] = None):
        try:
            from web3 import Web3
            from eth_account import Account
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise FrameGuardError(
                "Chain anchor requested but web3 is not installed; run "
                "'pip install -r requirements-chain.txt'"
            ) from exc

        self._w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self._w3.is_connected():
            raise FrameGuardError(f"Could not connect to RPC at {rpc_url}")
        self._account = Account.from_key(private_key)
        self._chain_id = chain_id or self._w3.eth.chain_id
        self._contract = self._w3.eth.contract(
            address=self._w3.to_checksum_address(contract_address), abi=_ABI
        )

    def register(self, anchor: dict) -> dict:
        fn = self._contract.functions.registerVideo(
            anchor["video_id"],
            _hex32(anchor["merkle_root"]),
            int(anchor["frame_count"]),
            int(anchor["target_fps"]),
            _hex32(anchor["metadata_hash"]),
        )
        tx = fn.build_transaction({
            "from": self._account.address,
            "nonce": self._w3.eth.get_transaction_count(self._account.address),
            "chainId": self._chain_id,
        })
        signed = self._account.sign_transaction(tx)
        tx_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self._w3.eth.wait_for_transaction_receipt(tx_hash)
        return {
            **anchor,
            "backend": "chain",
            "registrant": self._account.address,
            "network": f"chain-{self._chain_id}",
            "tx_hash": receipt["transactionHash"].hex(),
            "block_number": receipt["blockNumber"],
            "registered_at": utc_now_iso(),
        }

    def get(self, video_id: str) -> Optional[dict]:
        root, frame_count, fps, metadata_hash, registrant, timestamp, exists = (
            self._contract.functions.getVideo(video_id).call()
        )
        if not exists:
            return None
        return {
            "video_id": video_id,
            "merkle_root": root.hex(),
            "frame_count": frame_count,
            "target_fps": fps,
            "metadata_hash": metadata_hash.hex(),
            "registrant": registrant,
            "timestamp": timestamp,
            "backend": "chain",
        }

    def log_verification(self, video_id: str, root_matched: bool, actor: str = "") -> None:
        fn = self._contract.functions.logVerification(video_id, bool(root_matched))
        tx = fn.build_transaction({
            "from": self._account.address,
            "nonce": self._w3.eth.get_transaction_count(self._account.address),
            "chainId": self._chain_id,
        })
        signed = self._account.sign_transaction(tx)
        self._w3.eth.send_raw_transaction(signed.raw_transaction)
