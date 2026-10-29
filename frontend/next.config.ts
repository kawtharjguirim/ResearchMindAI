import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Produces a self-contained server in .next/standalone for a small Docker image.
  output: "standalone",
};

export default nextConfig;
