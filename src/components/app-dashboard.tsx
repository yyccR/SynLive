import Link from 'next/link';
import { ArrowRight, BellRing, CalendarClock, CircleAlert, Radio, Sparkles } from 'lucide-react';
import { moduleEntries, recentTasks, statusCards } from '@/lib/product';
import { ModuleIcon } from '@/components/icons';

export function AppDashboard() {
  return (
    <div className="workspacePage">
      <section className="workspaceHero">
        <div>
          <span className="sectionKicker">WORKSPACE</span>
          <h1>今天从这里开始搭建数字人直播间。</h1>
          <p>选择一个模块进入，或从最近任务继续。当前是静态原型，后续会接入真实后端和实时状态。</p>
        </div>
        <div className="workspaceActions">
          <Link className="primaryCta" href="/app/live">
            创建直播 <ArrowRight size={18} />
          </Link>
          <Link className="secondaryCta light" href="/app/scripts">
            上传脚本
          </Link>
        </div>
      </section>

      <section className="statusGrid" aria-label="系统状态">
        {statusCards.map((card) => (
          <article className={`statusCard ${card.tone}`} key={card.label}>
            <span>{card.label}</span>
            <strong>{card.value}</strong>
            <p>{card.detail}</p>
          </article>
        ))}
      </section>

      <section className="workspaceMainGrid">
        <div className="launcherPanel">
          <div className="panelHeader">
            <div>
              <span className="sectionKicker">LAUNCHER</span>
              <h2>功能模块入口</h2>
            </div>
            <span className="panelBadge">8 个模块</span>
          </div>
          <div className="launcherGrid">
            {moduleEntries.map((entry) => (
              <Link className="launcherCard" href={entry.href} key={entry.slug}>
                <ModuleIcon slug={entry.slug} />
                <strong>{entry.title}</strong>
                <p>{entry.description}</p>
                <span>{entry.action} →</span>
              </Link>
            ))}
          </div>
        </div>

        <aside className="opsPanel">
          <div className="opsCard broadcastCard">
            <div className="opsHeader">
              <Radio size={18} />
              <span>直播预备室</span>
            </div>
            <strong>电商新品专场</strong>
            <p>18 个脚本节点、3 个平台、1 个风险规则待确认。</p>
            <div className="readinessList">
              <span><Sparkles size={15} /> 数字人已选择</span>
              <span><CalendarClock size={15} /> 脚本待预演</span>
              <span><CircleAlert size={15} /> 视频号待授权</span>
            </div>
            <Link href="/app/live">进入预备室</Link>
          </div>
          <div className="opsCard">
            <div className="opsHeader">
              <BellRing size={18} />
              <span>最近任务</span>
            </div>
            <div className="taskList">
              {recentTasks.map((task) => (
                <article key={task.title}>
                  <strong>{task.title}</strong>
                  <p>{task.meta}</p>
                  <span>{task.state}</span>
                </article>
              ))}
            </div>
          </div>
        </aside>
      </section>
    </div>
  );
}
