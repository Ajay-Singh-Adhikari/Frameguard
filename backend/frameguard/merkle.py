"""Merkle tree over per-frame SHA-256 hashes.

Design notes
------------
* Leaves are the per-frame SHA-256 digests (hex strings), in frame order.
* Internal nodes are ``SHA-256(0x01 || left || right)`` over the raw 32-byte
  digests. The ``0x01`` domain-separation prefix means an internal node can
  never be mistaken for a leaf, which blocks a class of second-preimage tricks.
* When a level has an odd number of nodes, the last node is duplicated
  (Bitcoin-style). The frame count is anchored alongside the root, so the tree
  shape is fixed and the known duplication malleability does not apply here.

Everything is ordered: frame 0 is leaf 0. That ordering is what lets a later
verification say *which* frame changed, not merely that something did.
"""
from __future__ import annotations

import hashlib
from typing import List, Tuple

from .util import FrameGuardError

# A proof step is (sibling_hash_hex, side) where side is "L" if the sibling sits
# on the left of the current node, "R" if it sits on the right.
ProofStep = Tuple[str, str]
Proof = List[ProofStep]

_NODE_PREFIX = b"\x01"


def _parent(left: str, right: str) -> str:
    return hashlib.sha256(_NODE_PREFIX + bytes.fromhex(left) + bytes.fromhex(right)).hexdigest()


def build_tree(leaves: List[str]) -> List[List[str]]:
    """Return every level of the tree, bottom-up.

    ``levels[0]`` is the leaves and ``levels[-1]`` is ``[root]``.
    """
    if not leaves:
        raise FrameGuardError("Cannot build a Merkle tree from zero frames")
    levels: List[List[str]] = [list(leaves)]
    current = list(leaves)
    while len(current) > 1:
        nxt: List[str] = []
        for i in range(0, len(current), 2):
            left = current[i]
            right = current[i + 1] if i + 1 < len(current) else current[i]  # duplicate last
            nxt.append(_parent(left, right))
        levels.append(nxt)
        current = nxt
    return levels


def merkle_root(leaves: List[str]) -> str:
    """Collapse the frame hashes into a single root hash."""
    return build_tree(leaves)[-1][0]


def merkle_proof(leaves: List[str], index: int) -> Proof:
    """Build the inclusion proof for the leaf at ``index``."""
    if not 0 <= index < len(leaves):
        raise FrameGuardError(f"Frame index {index} out of range (0..{len(leaves) - 1})")
    levels = build_tree(leaves)
    proof: Proof = []
    idx = index
    for level in levels[:-1]:  # every level except the root
        if idx % 2 == 0:
            sibling = idx + 1 if idx + 1 < len(level) else idx  # duplicated last node is its own sibling
            proof.append((level[sibling], "R"))
        else:
            proof.append((level[idx - 1], "L"))
        idx //= 2
    return proof


def verify_proof(leaf: str, proof: Proof, root: str) -> bool:
    """Check that ``leaf`` combined with ``proof`` reproduces ``root``."""
    h = leaf
    for sibling, side in proof:
        h = _parent(sibling, h) if side == "L" else _parent(h, sibling)
    return h == root
