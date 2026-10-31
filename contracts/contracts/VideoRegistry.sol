// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

/// @title VideoRegistry
/// @notice Anchors one Merkle root (over a video's per-frame SHA-256 hashes)
///         plus minimal metadata per video. Registration is a single transaction
///         regardless of video length, which keeps the cost flat. The per-frame
///         hashes, the full Merkle tree and the video itself stay off-chain.
contract VideoRegistry {
    struct VideoRecord {
        bytes32 merkleRoot;    // root of the Merkle tree over per-frame hashes
        uint256 frameCount;    // number of sampled frames (leaves)
        uint256 fps;           // sampling rate the frames were taken at
        bytes32 metadataHash;  // binds the off-chain manifest's metadata
        string videoCid;       // IPFS CID of the video (empty if not pinned)
        string manifestCid;    // IPFS CID of the off-chain manifest (empty if not pinned)
        address registrant;    // who anchored it
        uint256 timestamp;     // block time of registration
        bool exists;
    }

    struct VerificationRecord {
        address verifier;
        bool rootMatched;
        uint256 timestamp;
    }

    mapping(string => VideoRecord) public videos;
    string[] public videoIds;

    // Append-only verification log per video (who checked it and the outcome).
    mapping(string => VerificationRecord[]) public verifications;

    event VideoRegistered(
        string videoId, bytes32 merkleRoot, uint256 frameCount, address registrant, uint256 timestamp
    );
    event VideoVerified(string videoId, address verifier, bool rootMatched, uint256 timestamp);

    /// @notice Anchor a video's Merkle root and metadata. Each id can be set once.
    function registerVideo(
        string calldata videoId,
        bytes32 merkleRoot,
        uint256 frameCount,
        uint256 fps,
        bytes32 metadataHash,
        string calldata videoCid,
        string calldata manifestCid
    ) external {
        require(!videos[videoId].exists, "Video already registered");
        require(merkleRoot != bytes32(0), "Empty merkle root");

        videos[videoId] = VideoRecord({
            merkleRoot: merkleRoot,
            frameCount: frameCount,
            fps: fps,
            metadataHash: metadataHash,
            videoCid: videoCid,
            manifestCid: manifestCid,
            registrant: msg.sender,
            timestamp: block.timestamp,
            exists: true
        });
        videoIds.push(videoId);

        emit VideoRegistered(videoId, merkleRoot, frameCount, msg.sender, block.timestamp);
    }

    function getVideo(string calldata videoId)
        external
        view
        returns (bytes32, uint256, uint256, bytes32, string memory, string memory, address, uint256, bool)
    {
        VideoRecord memory v = videos[videoId];
        return (
            v.merkleRoot, v.frameCount, v.fps, v.metadataHash,
            v.videoCid, v.manifestCid, v.registrant, v.timestamp, v.exists
        );
    }

    /// @notice Record the outcome of a verification against this video's anchor.
    function logVerification(string calldata videoId, bool rootMatched) external {
        require(videos[videoId].exists, "Video not registered");
        verifications[videoId].push(
            VerificationRecord({verifier: msg.sender, rootMatched: rootMatched, timestamp: block.timestamp})
        );
        emit VideoVerified(videoId, msg.sender, rootMatched, block.timestamp);
    }

    function getVideoCount() external view returns (uint256) {
        return videoIds.length;
    }

    function getVerificationCount(string calldata videoId) external view returns (uint256) {
        return verifications[videoId].length;
    }

    function getVerification(string calldata videoId, uint256 index)
        external
        view
        returns (address, bool, uint256)
    {
        VerificationRecord memory r = verifications[videoId][index];
        return (r.verifier, r.rootMatched, r.timestamp);
    }
}
