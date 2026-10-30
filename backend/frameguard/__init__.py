"""FrameGuard: frame-level video tamper detection anchored on a Merkle root.

A video is broken into frames, each frame is hashed with SHA-256, and the frame
hashes are combined into a single Merkle tree. Only the 32-byte Merkle root plus
minimal metadata is anchored (on a local hash-chained ledger by default, or on an
Ethereum contract when configured). Verification rebuilds the tree from a received
copy, compares roots, and localizes exactly which frames differ.
"""

__version__ = "0.1.0"
