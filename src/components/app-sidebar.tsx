'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { moduleEntries } from '@/lib/product';
import { ModuleIcon } from '@/components/icons';

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <aside className="appSidebar">
      <Link className="appBrand" href="/app">
        <span className="brandMark">S</span>
        <span>
          <strong>SynLive</strong>
          <small>工作台</small>
        </span>
      </Link>
      <nav className="appNav" aria-label="工作台导航">
        <Link className={pathname === '/app' ? 'active' : ''} href="/app">
          <span className="navIcon">⌁</span>
          总览
        </Link>
        {moduleEntries.map((entry) => (
          <Link className={pathname.startsWith(entry.href) ? 'active' : ''} href={entry.href} key={entry.slug}>
            <ModuleIcon slug={entry.slug} />
            {entry.title}
          </Link>
        ))}
      </nav>
      <div className="sidebarCard">
        <span>下一步</span>
        <strong>接入直播中控真实链路</strong>
        <p>前端静态原型完成后，优先对接 session、弹幕和播报 API。</p>
      </div>
    </aside>
  );
}
