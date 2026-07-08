import type { NextConfig } from "next";

// Server-side only: where the Next.js dev/prod server proxies /api/* to.
// Not prefixed with NEXT_PUBLIC_ since the browser never talks to this URL directly.
const BACKEND_API_URL = (process.env.BACKEND_API_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${BACKEND_API_URL}/:path*`,
      },
    ];
  },
};

export default nextConfig;
