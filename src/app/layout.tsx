import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'SynLive | AI 数字人直播中控平台',
  description: '数字人定制、AI 直播中控、脚本编排、知识库问答、多平台推流和数据复盘。',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
