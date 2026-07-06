import Link from 'next/link';
import { ArrowRight } from 'lucide-react';

export default function LoginPage() {
  return (
    <main className="loginPage">
      <section className="loginCard">
        <Link className="brand centered" href="/">
          <span className="brandMark">S</span>
          <span>
            <strong>SynLive</strong>
            <small>AI Digital Human Live</small>
          </span>
        </Link>
        <span className="sectionKicker">STATIC PROTOTYPE</span>
        <h1>登录入口占位</h1>
        <p>第一版先跳过认证，点击按钮直接进入工作台。后续会接入账号、角色、权限和审计。</p>
        <Link className="primaryCta full" href="/app">
          进入工作台 <ArrowRight size={18} />
        </Link>
        <Link className="secondaryCta full" href="/">
          返回官网
        </Link>
      </section>
    </main>
  );
}
