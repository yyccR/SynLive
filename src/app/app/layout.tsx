import { AppSidebar } from '@/components/app-sidebar';

export default function WorkspaceLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <main className="appShell">
      <AppSidebar />
      <section className="appContent">
        <header className="appTopbar">
          <div>
            <span>SynLive Console</span>
            <strong>AI 数字人直播工作台</strong>
          </div>
          <div className="topbarSignals">
            <span className="signalGood">AI 在线</span>
            <span className="signalWarn">1 项待配置</span>
          </div>
        </header>
        {children}
      </section>
    </main>
  );
}
