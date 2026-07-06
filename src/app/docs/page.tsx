import Link from 'next/link';
import { ArrowLeft, FileText } from 'lucide-react';

const docs = [
  {
    title: 'AI 数字人直播系统方案与开发计划',
    path: 'docs/digital-human-live-system-plan.md',
    text: '模块划分、API 草案、部署规划、阶段进度和风险应对。',
  },
  {
    title: '技术栈选型与 UI 对标参考',
    path: 'docs/technical-stack-and-ui-references.md',
    text: '前端、后端、AI、数字人、媒体、部署和对标官网。',
  },
  {
    title: '宣传页官网与功能模块入口规划',
    path: 'docs/landing-page-and-module-entry-plan.md',
    text: '公开官网、登录后工作台、模块入口、路由和文案规划。',
  },
];

export default function DocsPage() {
  return (
    <main className="loginPage docsPage">
      <section className="docsPanel">
        <Link className="backLink docsBack" href="/">
          <ArrowLeft size={16} /> 返回官网
        </Link>
        <span className="sectionKicker">PROJECT DOCS</span>
        <h1>方案文档</h1>
        <p>文档文件已放在项目根目录的 docs/ 目录下，当前页面作为官网文档入口占位。</p>
        <div className="docsList">
          {docs.map((doc) => (
            <article className="docCard" key={doc.path}>
              <FileText size={20} />
              <div>
                <h2>{doc.title}</h2>
                <p>{doc.text}</p>
                <code>{doc.path}</code>
              </div>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
