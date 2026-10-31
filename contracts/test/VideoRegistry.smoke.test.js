const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("VideoRegistry", function () {
  const root = "0x" + "11".repeat(32);
  const metaHash = "0x" + "22".repeat(32);

  async function deploy() {
    const Factory = await ethers.getContractFactory("VideoRegistry");
    const registry = await Factory.deploy();
    await registry.waitForDeployment();
    return registry;
  }

  const videoCid = "bafybevideo";
  const manifestCid = "bafybemanifest";

  it("registers a video (with CIDs) and reads it back", async function () {
    const registry = await deploy();
    await registry.registerVideo("vid_1", root, 900, 30, metaHash, videoCid, manifestCid);

    const [merkleRoot, frameCount, fps, metadataHash, vCid, mCid, , , exists] =
      await registry.getVideo("vid_1");
    expect(merkleRoot).to.equal(root);
    expect(frameCount).to.equal(900n);
    expect(fps).to.equal(30n);
    expect(metadataHash).to.equal(metaHash);
    expect(vCid).to.equal(videoCid);
    expect(mCid).to.equal(manifestCid);
    expect(exists).to.equal(true);
    expect(await registry.getVideoCount()).to.equal(1n);
  });

  it("rejects a duplicate video id", async function () {
    const registry = await deploy();
    await registry.registerVideo("vid_1", root, 900, 30, metaHash, videoCid, manifestCid);
    await expect(
      registry.registerVideo("vid_1", root, 900, 30, metaHash, videoCid, manifestCid)
    ).to.be.revertedWith("Video already registered");
  });

  it("rejects an empty merkle root", async function () {
    const registry = await deploy();
    await expect(
      registry.registerVideo("vid_2", ethers.ZeroHash, 1, 30, metaHash, "", "")
    ).to.be.revertedWith("Empty merkle root");
  });

  it("appends an append-only verification log", async function () {
    const registry = await deploy();
    await registry.registerVideo("vid_1", root, 900, 30, metaHash, videoCid, manifestCid);
    await registry.logVerification("vid_1", true);
    await registry.logVerification("vid_1", false);

    expect(await registry.getVerificationCount("vid_1")).to.equal(2n);
    const [, matched] = await registry.getVerification("vid_1", 0);
    expect(matched).to.equal(true);
  });
});
