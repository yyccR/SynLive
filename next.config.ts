import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  reactStrictMode: true,
  turbopack: {
    root: process.cwd(),
  },
  // dev 下从非 localhost(局域网 IP / 远程)打开页面时,Next 16 默认阻断跨 origin 的 dev 资源
  // (/_next/webpack-hmr 等),客户端不 hydrate → 按钮点击无响应。放行本机常用入口。
  allowedDevOrigins: ['localhost', '127.0.0.1', '10.2.42.21'],
  // dev 下前端(https://host:3000)经 Next 反代访问后端(:8000),一次解决:
  // ① https 页面 fetch http 后端的混合内容拦截;② 远程浏览器访问不到 host 的 localhost:8000;
  // ③ 跨源 CORS。前端 API_BASE 设为 ''(同源),fetch('/api/...'、'/health/...') 由这些 rewrite 转后端。
  async rewrites() {
    return [
      { source: '/health/:path*', destination: 'http://localhost:8000/health/:path*' },
      { source: '/api/:path*', destination: 'http://localhost:8000/api/:path*' },
    ];
  },
};

export default nextConfig;
