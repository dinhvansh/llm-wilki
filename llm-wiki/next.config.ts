import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    const apiProxyTarget = process.env.API_PROXY_TARGET ?? "http://localhost:8000/api";
    const assetProxyTarget = apiProxyTarget.replace(/\/api\/?$/, "");
    return [
      {
        source: "/backend-api/:path*",
        destination: `${apiProxyTarget}/:path*`,
      },
      {
        source: "/backend-uploads/:path*",
        destination: `${assetProxyTarget}/uploads/:path*`,
      },
    ];
  },
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**",
      },
    ],
  },
};

export default nextConfig;
