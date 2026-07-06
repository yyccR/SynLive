import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { solutionCards } from '@/lib/product';
import { ModuleIcon } from '@/components/icons';
import { MarketingHeader } from '@/components/marketing-header';

const featuredModules = [
  {
    slug: 'live',
    title: '直播中控',
    href: '/app/live',
    description: '预览、弹幕、回复、接管一屏完成。',
  },
  {
    slug: 'avatars',
    title: '数字人资产',
    href: '/app/avatars',
    description: '形象、声线、服装统一管理。',
  },
  {
    slug: 'scripts',
    title: '脚本与知识库',
    href: '/app/scripts',
    description: '文档导入，生成流程与答案。',
  },
  {
    slug: 'platforms',
    title: '多平台推流',
    href: '/app/platforms',
    description: '平台配置、状态监控、异常提醒。',
  },
];

export function MarketingHome() {
  return (
    <main className="siteShell simpleSiteShell">
      <MarketingHeader />
      <section className="landingPageFrame heroPage" aria-label="AI 数字人直播平台">
        <div className="heroSection simpleHeroSection">
          <div className="heroCopy simpleHeroCopy">
            <div className="eyebrowPill">
              <span className="liveDot" />
              AI LIVE STUDIO
            </div>
            <h1>数字人直播，<br />一站开播。</h1>
            <p className="heroLead">
              脚本、互动、推流集中在一个工作台。
            </p>
            <div className="heroActions">
              <Link className="primaryCta" href="/app">
                进入控制台 <ArrowRight size={18} />
              </Link>
              <a className="secondaryCta" href="#modules">
                查看模块
              </a>
            </div>
          </div>
          <HeroVisual />
        </div>
      </section>

      <section className="moduleSection simpleSection" id="modules" aria-labelledby="module-title">
        <div className="sectionIntro simpleIntro">
          <span className="sectionKicker">CORE</span>
          <h2 id="module-title">开播所需，集中管理。</h2>
          <p>四个入口覆盖资产、脚本、互动和推流。</p>
        </div>
        <div className="moduleGrid simpleModuleGrid">
          {featuredModules.map((entry) => (
            <Link className="moduleCard simpleModuleCard" href={entry.href} key={entry.slug}>
              <span className="moduleIconWrap">
                <ModuleIcon slug={entry.slug} />
              </span>
              <h3>{entry.title}</h3>
              <p>{entry.description}</p>
              <div className="moduleFooter">
                <span>进入模块 →</span>
              </div>
            </Link>
          ))}
        </div>
      </section>

      <section className="previewSection simpleSection" id="preview" aria-labelledby="preview-title">
        <div className="previewPanel simplePreviewPanel">
          <div>
            <span className="sectionKicker">PREVIEW</span>
            <h2 id="preview-title">工作流一眼可见。</h2>
            <p>中控、脚本、推流状态保持同步。</p>
          </div>
          <div className="previewCards imagePreviewCards">
            <MiniPreview image="/assets/product-live-control.png" title="直播中控" text="实时预览与人工接管。" />
            <MiniPreview image="/assets/product-script-timeline.png" title="脚本编排" text="文档生成直播时间线。" />
            <MiniPreview image="/assets/product-stream-health.png" title="推流健康" text="多平台状态同步监测。" />
          </div>
        </div>
      </section>

      <section className="solutionSection simpleSection" id="solutions" aria-labelledby="solution-title">
        <div className="sectionIntro simpleIntro">
          <span className="sectionKicker">SCENES</span>
          <h2 id="solution-title">适合持续讲解的场景。</h2>
        </div>
        <div className="solutionGrid simpleSolutionGrid">
          {solutionCards.map((card) => (
            <article className={`solutionCard simpleSolutionCard ${card.accent}`} key={card.title}>
              <img src={`/assets/solution-${card.accent}.png`} alt={`${card.title}方案视觉`} loading="lazy" />
              <span>{card.title}</span>
              <p>{card.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="finalCta simpleFinalCta">
        <div>
          <span className="sectionKicker">START</span>
          <h2>创建直播间，开始预演。</h2>
        </div>
        <div className="heroActions">
          <Link className="primaryCta" href="/app">
            进入工作台 <ArrowRight size={18} />
          </Link>
          <Link className="secondaryCta" href="/docs">
            查看方案文档
          </Link>
        </div>
      </section>
    </main>
  );
}

function HeroVisual() {
  return (
    <div className="heroConsole heroConsoleReal heroConsoleStatic" aria-label="真实感 AI 数字人直播中控预览">
      <img className="heroConsoleRealVideo" src="/assets/hero-live-studio-poster.png" alt="AI 数字人直播中控界面预览" />
      <div className="realHeroChrome" />
      <div className="realHeroStatus">
        <span><i /> LIVE CONTROL</span>
        <strong>推流在线</strong>
      </div>
      <div className="realHeroCaption">中控 / 互动 / 时间线</div>
    </div>
  );
}

function MiniPreview({ image, title, text }: { image: string; title: string; text: string }) {
  return (
    <article className="miniPreview imagePreview">
      <img src={image} alt={`${title}界面预览`} loading="lazy" />
      <div>
        <h3>{title}</h3>
        <p>{text}</p>
      </div>
    </article>
  );
}
