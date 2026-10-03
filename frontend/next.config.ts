import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  skipTrailingSlashRedirect: true,
  async rewrites() {
    const backendOrigin = (process.env.DJANGO_API_ORIGIN ?? "http://127.0.0.1:8000").replace(/\/$/, "");
    return [
      {
        source: "/api/:path*",
        destination: `${backendOrigin}/api/:path*/`,
      },
    ];
  },
};

export default nextConfig;
