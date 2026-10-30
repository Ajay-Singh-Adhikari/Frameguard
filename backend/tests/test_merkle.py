import hashlib

import pytest

from frameguard.merkle import merkle_proof, merkle_root, verify_proof
from frameguard.util import FrameGuardError


def h(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_single_leaf_root_is_the_leaf():
    leaf = h(b"only")
    assert merkle_root([leaf]) == leaf


def test_root_changes_when_a_frame_changes():
    leaves = [h(str(i).encode()) for i in range(4)]
    original = merkle_root(leaves)
    tampered = list(leaves)
    tampered[2] = h(b"edited")
    assert merkle_root(tampered) != original


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 7, 8, 16, 17])
def test_proofs_verify_for_every_leaf(n):
    leaves = [h(str(i).encode()) for i in range(n)]
    root = merkle_root(leaves)
    for i in range(n):
        assert verify_proof(leaves[i], merkle_proof(leaves, i), root)


def test_proof_fails_for_wrong_leaf():
    leaves = [h(str(i).encode()) for i in range(5)]
    root = merkle_root(leaves)
    assert not verify_proof(h(b"not a real frame"), merkle_proof(leaves, 2), root)


def test_empty_tree_raises():
    with pytest.raises(FrameGuardError):
        merkle_root([])
