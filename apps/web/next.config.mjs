/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@ai-companion/shared"],
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
