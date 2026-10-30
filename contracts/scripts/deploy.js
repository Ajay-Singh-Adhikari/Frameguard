const fs = require("fs");
const path = require("path");
const hre = require("hardhat");

async function main() {
  const VideoRegistry = await hre.ethers.getContractFactory("VideoRegistry");
  const registry = await VideoRegistry.deploy();
  await registry.waitForDeployment();

  const address = await registry.getAddress();
  const network = hre.network.name;
  console.log(`VideoRegistry deployed to ${address} on ${network}`);

  const dir = path.join(__dirname, "..", "deployments");
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(
    path.join(dir, `${network}.json`),
    JSON.stringify({ address, network, deployedAt: new Date().toISOString() }, null, 2)
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
