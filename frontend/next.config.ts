import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  skipTrailingSlashRedirect: true,
  devIndicators: false,
  allowedDevOrigins: ["127.0.0.1"],
  async rewrites() {
    const configuredBackendOrigin = process.env.DJANGO_API_ORIGIN;
    if (process.env.VERCEL && !configuredBackendOrigin) {
      throw new Error("DJANGO_API_ORIGIN must point to the deployed Django API before deploying to Vercel.");
    }
    const backendOrigin = (configuredBackendOrigin ?? "http://127.0.0.1:8000").replace(/\/$/, "");
    return [
      {
        source: "/api/:path*",
        destination: `${backendOrigin}/api/:path*/`,
      },
    ];
  },
};

export default nextConfig;
