import {
  Activity,
  Bot,
  ChartSpline,
  ClipboardList,
  DatabaseZap,
  FileStack,
  Gauge,
  Headphones,
  RadioTower,
  ShieldCheck,
  Sparkles,
  Tv,
  Waves,
} from 'lucide-react';

const iconClass = 'icon';

export function ModuleIcon({ slug }: { slug: string }) {
  switch (slug) {
    case 'live':
      return <RadioTower className={iconClass} />;
    case 'avatars':
      return <Bot className={iconClass} />;
    case 'scripts':
      return <FileStack className={iconClass} />;
    case 'knowledge':
      return <DatabaseZap className={iconClass} />;
    case 'platforms':
      return <Waves className={iconClass} />;
    case 'moderation':
      return <ShieldCheck className={iconClass} />;
    case 'reports':
      return <ChartSpline className={iconClass} />;
    case 'services':
      return <Headphones className={iconClass} />;
    default:
      return <Sparkles className={iconClass} />;
  }
}

export function FeatureGlyph({ type }: { type: 'status' | 'screen' | 'script' | 'signal' }) {
  const icons = {
    status: Activity,
    screen: Tv,
    script: ClipboardList,
    signal: Gauge,
  } as const;
  const Icon = icons[type];
  return <Icon className={iconClass} />;
}
