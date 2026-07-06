import Link from 'next/link';
import { ChevronDown } from 'lucide-react';

const navItems = [
  { label: '产品', href: '#modules', hasMenu: true },
  { label: '解决方案', href: '#solutions', hasMenu: true },
  { label: '界面预览', href: '#preview' },
  { label: '资源文档', href: '/docs', hasMenu: true },
];

export function MarketingHeader() {
  return (
    <header className="marketingHeader simpleMarketingHeader">
      <Link className="brand" href="/" aria-label="SynLive 首页">
        <span className="brandMark">S</span>
        <span>
          <strong>SynLive</strong>
          <small>AI Digital Human Live</small>
        </span>
      </Link>
      <nav className="marketingNav" aria-label="官网导航">
        {navItems.map((item) => (
          <Link key={item.href} href={item.href}>
            {item.label}
            {item.hasMenu ? <ChevronDown aria-hidden="true" size={14} strokeWidth={2.2} /> : null}
          </Link>
        ))}
      </nav>
      <div className="headerActions">
        <Link className="solidButton" href="/app">
          进入控制台
        </Link>
      </div>
    </header>
  );
}
