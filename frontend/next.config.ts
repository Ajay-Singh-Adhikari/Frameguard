import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Pin the workspace root to this app, so an unrelated lockfile elsewhere on
  // the machine is not mistaken for the project root.
  turbopack: { root: __dirname },
};

export default nextConfig;
