'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Loader2, Mic, Radio, Send, Sparkles, Volume2 } from 'lucide-react';
import { api, type AnswerResult, type ReadyInfo, type SessionInfo, type VoiceItem } from '@/lib/api';

interface QaItem {
  question: string;
  answer: string;
  llmMs: number;
  ttsMs: number | null;
  model: string;
}

function StatusLight({ label, ok, warn, hint }: { label: string; ok: boolean; warn?: boolean; hint?: string }) {
  const cls = warn ? 'liveLight warn' : ok ? 'liveLight ok' : 'liveLight off';
  return (
    <span className={cls} title={hint}>
      <i />
      {label}
    </span>
  );
}

export function LiveConsole() {
  const [ready, setReady] = useState<ReadyInfo | null>(null);
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [voices, setVoices] = useState<VoiceItem[]>([]);
  const [lang, setLang] = useState('zh');
  const [voice, setVoice] = useState('zh-CN-XiaoxiaoNeural');

  // 播报（TTS）
  const [broadcastText, setBroadcastText] = useState('欢迎来到直播间，今天为大家介绍我们的新品。');
  const [broadcastBusy, setBroadcastBusy] = useState(false);
  const [broadcastAudio, setBroadcastAudio] = useState<{ url: string; ms: number } | null>(null);
  const [broadcastErr, setBroadcastErr] = useState('');

  // 问答（LLM + TTS）
  const [question, setQuestion] = useState('这款产品支持七天无理由退货吗？');
  const [qaBusy, setQaBusy] = useState(false);
  const [qaResult, setQaResult] = useState<AnswerResult | null>(null);
  const [qaAudio, setQaAudio] = useState<{ url: string; ms: number } | null>(null);
  const [qaErr, setQaErr] = useState('');
  const [history, setHistory] = useState<QaItem[]>([]);

  const loadReady = useCallback(async () => {
    try {
      setReady(await api.ready());
    } catch {
      setReady(null);
    }
  }, []);

  const loadVoices = useCallback(async (l: string) => {
    try {
      const v = await api.voices(l);
      setVoices(v);
      if (v.length && !v.find((x) => x.id === voice)) setVoice(v[0].id);
    } catch {
      setVoices([]);
    }
  }, [voice]);

  const ensureSession = useCallback(async () => {
    try {
      const s = await api.createSession({ title: '前端中控测试', voice, lang });
      setSession(s);
    } catch (e) {
      setSession(null);
    }
  }, [voice, lang]);

  useEffect(() => {
    loadReady();
    loadVoices(lang);
    ensureSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onLangChange = (l: string) => {
    setLang(l);
    loadVoices(l);
  };

  const doBroadcast = async () => {
    setBroadcastBusy(true);
    setBroadcastErr('');
    setBroadcastAudio(null);
    try {
      const r = await api.synthesize({ text: broadcastText, lang, voice });
      setBroadcastAudio({ url: r.url, ms: r.latencyMs });
    } catch (e) {
      setBroadcastErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBroadcastBusy(false);
    }
  };

  const doAsk = async () => {
    if (!session) return;
    setQaBusy(true);
    setQaErr('');
    setQaResult(null);
    setQaAudio(null);
    try {
      // 1) 问答编排：LLM → TTS → LiveTalking（拿回答文本 + 各环节延迟 + 渲染状态）
      const res = await api.answer(session.id, { question, voice, lang });
      setQaResult(res);
      setHistory((h) => [
        { question: res.question, answer: res.answer, llmMs: res.llm_latency_ms, ttsMs: res.tts_latency_ms, model: res.model_id },
        ...h,
      ].slice(0, 20));
      // 2) 合成音频以便在浏览器试听（/answer 内部已合成，这里再取一次可播放 mp3）
      if (res.answer) {
        try {
          const a = await api.synthesize({ text: res.answer, lang, voice });
          setQaAudio({ url: a.url, ms: a.latencyMs });
        } catch {
          /* 音频可选，失败不阻塞 */
        }
      }
    } catch (e) {
      setQaErr(e instanceof Error ? e.message : String(e));
    } finally {
      setQaBusy(false);
    }
  };

  const avgLlm = useMemo(() => {
    if (!history.length) return 0;
    return Math.round(history.reduce((s, x) => s + x.llmMs, 0) / history.length);
  }, [history]);

  const degraded = !ready || ready.livetalking_enabled; // 本地无 GPU 时必为降级，按 livetalking 不可用展示

  return (
    <div className="liveConsole">
      {/* 状态栏 */}
      <div className="liveStatusbar">
        <div className="liveStatusLeft">
          <Radio size={18} />
          <div>
            <strong>直播中控台</strong>
            <small>
              {session ? `会话 ${session.id.slice(0, 8)}… · ${session.status}` : '正在创建会话…'}
            </small>
          </div>
        </div>
        <div className="liveLights">
          <StatusLight label="TTS 合成" ok={!!ready?.azure_configured} hint="Azure TTS" />
          <StatusLight label={`LLM ${ready?.llm_default_model_id || ''}`.trim()} ok={!!ready?.llm_configured} hint="LiteLLM 网关" />
          <StatusLight label="数字人渲染" ok={false} warn hint="需 GPU 节点(LiveTalking),当前降级" />
        </div>
      </div>

      <div className="liveGrid">
        {/* 左：预览 + 播报 */}
        <section className="livePanel">
          <header className="livePanelHead">
            <Volume2 size={16} />
            <span>数字人预览 · 文本播报</span>
          </header>

          <div className="liveStage">
            <div className="liveAvatarHalo" />
            <div className="liveAvatarFigure">
              <div className="liveAvatarHead" />
              <div className="liveAvatarBody" />
            </div>
            <div className="liveStageCaption">
              {qaBusy ? 'AI 正在思考…' : broadcastBusy ? '正在合成语音…' : '等待播报'}
            </div>
            <div className="liveStageNote">
              数字人画面渲染需 GPU 节点(LiveTalking)。当前可测：TTS 合成、LLM 问答，音频可直接试听。
            </div>
          </div>

          <div className="liveField">
            <label>播报文本</label>
            <textarea
              rows={3}
              value={broadcastText}
              onChange={(e) => setBroadcastText(e.target.value)}
              placeholder="输入要让数字人说的话"
            />
            <div className="liveControls">
              <select value={lang} onChange={(e) => onLangChange(e.target.value)}>
                <option value="zh">中文</option>
                <option value="en">英语</option>
                <option value="yue">粤语</option>
                <option value="ja">日语</option>
              </select>
              <select value={voice} onChange={(e) => setVoice(e.target.value)}>
                {voices.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name}
                  </option>
                ))}
              </select>
              <button className="primaryCta" onClick={doBroadcast} disabled={broadcastBusy || !broadcastText.trim()}>
                {broadcastBusy ? <Loader2 size={16} className="spin" /> : <Volume2 size={16} />}
                播报
              </button>
            </div>
            {broadcastAudio && (
              <div className="liveAudioRow">
                <audio controls autoPlay src={broadcastAudio.url} />
                <span className="latencyChip">TTS {broadcastAudio.ms} ms</span>
              </div>
            )}
            {broadcastErr && <div className="liveErr">{broadcastErr}</div>}
          </div>
        </section>

        {/* 右：弹幕问答 */}
        <section className="livePanel">
          <header className="livePanelHead">
            <Sparkles size={16} />
            <span>弹幕问答 · AI 自动回复</span>
          </header>

          <div className="liveField">
            <label>观众问题 / 弹幕</label>
            <textarea
              rows={3}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="观众提问，AI 会用数字人主播口吻回答"
            />
            <div className="liveControls">
              <button className="primaryCta" onClick={doAsk} disabled={qaBusy || !question.trim() || !session}>
                {qaBusy ? <Loader2 size={16} className="spin" /> : <Send size={16} />}
                提问（GPT 回答）
              </button>
            </div>
          </div>

          {qaResult && (
            <div className="qaCard">
              <div className="qaQuestion">
                <Mic size={14} /> {qaResult.question}
              </div>
              <p className="qaAnswer">{qaResult.answer}</p>
              <div className="qaMetrics">
                <span>LLM {qaResult.llm_latency_ms} ms</span>
                {qaResult.tts_latency_ms != null && <span>TTS {qaResult.tts_latency_ms} ms</span>}
                <span>{qaResult.model_id}</span>
                {qaResult.livetalking && (
                  <span className={qaResult.livetalking.degraded ? 'warn' : 'good'}>
                    数字人 {qaResult.livetalking.degraded ? '降级(无GPU)' : '已驱动'}
                  </span>
                )}
              </div>
              {qaAudio && (
                <div className="liveAudioRow">
                  <audio controls autoPlay src={qaAudio.url} />
                  <span className="latencyChip">TTS {qaAudio.ms} ms</span>
                </div>
              )}
            </div>
          )}
          {qaErr && <div className="liveErr">{qaErr}</div>}

          {history.length > 0 && (
            <div className="qaHistory">
              <header className="livePanelHead subtle">
                <span>历史 ({history.length})</span>
              </header>
              <ul>
                {history.map((it, i) => (
                  <li key={i}>
                    <div className="qaHistQ">{it.question}</div>
                    <div className="qaHistA">{it.answer}</div>
                    <div className="qaHistMeta">
                      LLM {it.llmMs}ms{it.ttsMs != null ? ` · TTS ${it.ttsMs}ms` : ''} · {it.model}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      </div>

      {/* 底部指标 */}
      <div className="liveMetrics">
        <div>
          <span>已回答</span>
          <strong>{history.length}</strong>
        </div>
        <div>
          <span>平均 LLM 延迟</span>
          <strong>{avgLlm ? `${avgLlm} ms` : '—'}</strong>
        </div>
        <div>
          <span>默认模型</span>
          <strong>{ready?.llm_default_model_id || '—'}</strong>
        </div>
        <div>
          <span>后端地址</span>
          <strong className="mono">:8000</strong>
        </div>
      </div>
    </div>
  );
}
