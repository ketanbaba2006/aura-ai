import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  turbopack: {},
  productionBrowserSourceMaps: false,
  webpack: (config, { dev, isServer }) => {
    if (!dev && !isServer) {
      const WebpackObfuscator = require("webpack-obfuscator");
      config.plugins.push(
        new WebpackObfuscator(
          {
            rotateStringArray: true,
            compact: true,
            controlFlowFlattening: true,
            controlFlowFlatteningThreshold: 0.5,
            stringArrayEncoding: ["base64"],
            splitStrings: true,
          },
          []
        )
      );
    }
    return config;
  },
};

export default nextConfig;

