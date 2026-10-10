/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@ai-companion/shared"],
  // 默认 .next；CI 里可以换目录做并行隔离构建
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
  experimental: {
    typedRoutes: true,
  },
  images: {
    remotePatterns: [
      // 用户上传 / 生成的图片可能来自这些域名，按需增删
      { protocol: "https", hostname: "**.supabase.co" },
      { protocol: "http", hostname: "localhost" },
    ],
  },
};

export default nextConfig;
