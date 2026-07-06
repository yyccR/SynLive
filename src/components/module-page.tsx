import Link from 'next/link';
import { ArrowLeft, ArrowRight, CircleDot, PlugZap } from 'lucide-react';
import { moduleDetails } from '@/lib/product';
import { ModuleIcon } from '@/components/icons';

export function ModulePage({ slug }: { slug: string }) {
  const detail = moduleDetails[slug];

  if (!detail) {
    return null;
  }

  return (
    <div className="moduleDetailPage">
      <Link className="backLink" href="/app">
        <ArrowLeft size={16} /> 返回工作台
      </Link>
      <section className="moduleDetailHero">
        <div className="moduleDetailIcon">
          <ModuleIcon slug={detail.slug} />
        </div>
        <div>
          <span className="sectionKicker">{detail.eyebrow}</span>
          <h1>{detail.headline}</h1>
          <p>{detail.description}</p>
          <div className="tagRow large">
            {detail.tags.map((tag) => (
              <span key={tag}>{tag}</span>
            ))}
          </div>
        </div>
      </section>

      <section className="moduleCanvas">
        <div className="placeholderBoard">
          <div className="boardTop">
            <span className="windowDot red" />
            <span className="windowDot amber" />
            <span className="windowDot green" />
            <strong>{detail.title} / 原型占位</strong>
          </div>
          <div className="boardGrid">
            {detail.sections.map((section, index) => (
              <article className="boardCard" key={section}>
                <CircleDot size={18} />
                <span>0{index + 1}</span>
                <p>{section}</p>
              </article>
            ))}
          </div>
          <div className="integrationStrip">
            <PlugZap size={18} />
            <span>下一阶段：接入 API、实时事件和真实数据表。</span>
          </div>
        </div>
        <aside className="moduleActionPanel">
          <span className="sectionKicker">NEXT ACTION</span>
          <h2>{detail.action}</h2>
          <p>当前页面用于确认模块信息架构。确定后会继续做真实表单、列表、状态和接口联调。</p>
          <Link className="primaryCta" href="/app">
            查看所有模块 <ArrowRight size={18} />
          </Link>
        </aside>
      </section>
    </div>
  );
}
