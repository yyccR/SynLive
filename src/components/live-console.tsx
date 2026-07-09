'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Loader2, Mic, Radio, Send, Sparkles, Video, Volume2 } from 'lucide-react';
import {
  api,
  LIVETALKING_URL,
  offerLiveTalking,
  pingLiveTalking,
  type AnswerResult,
  type ReadyInfo,
  type SessionInfo,
} from '@/lib/api';

type AvatarState = 'idle' | 'connecting' | 'connected' | 'failed';

interface QaItem {
  question: string;
  answer: string;
  llmMs: number;
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

// aiortc 不支持 trickle ICE，offer SDP 必须带全候选才能让 LiveTalking 应答后连通。
// 等 ICE 收集完成，最多等 timeoutMs（无 STUN 时仅 host 候选，通常瞬时完成）。
function waitIceGather(pc: RTCPeerConnection, timeoutMs = 2500): Promise<void> {
  return new Promise((resolve) => {
    if (pc.iceGatheringState === 'complete') return resolve();
    let done = false;
    const finish = () => {
      if (done) return;
      done = true;
      pc.removeEventListener('icegatheringstatechange', check);
      resolve();
    };
    const check = () => {
      if (pc.iceGatheringState === 'complete') finish();
    };
    pc.addEventListener('icegatheringstatechange', check);
    setTimeout(finish, timeoutMs);
  });
}

export function LiveConsole() {
  const [ready, setReady] = useState<ReadyInfo | null>(null);
  const [session, setSession] = useState<SessionInfo | null>(null);

  // 数字人 WebRTC 连接
  const [avatarState, setAvatarState] = useState<AvatarState>('idle');
  const [avatarErr, setAvatarErr] = useState('');
  const [ltReachable, setLtReachable] = useState<boolean | null>(null);
  const pcRef = useRef<RTCPeerConnection | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  // 播报（让数字人开口）
  const [broadcastText, setBroadcastText] = useState('欢迎来到直播间，今天为大家介绍我们的新品。');
  const [broadcastBusy, setBroadcastBusy] = useState(false);
  const [broadcastInfo, setBroadcastInfo] = useState('');
  const [broadcastErr, setBroadcastErr] = useState('');

  // 问答（LLM → 数字人开口）
  const [question, setQuestion] = useState('这款产品支持七天无理由退货吗？');
  const [qaBusy, setQaBusy] = useState(false);
  const [qaResult, setQaResult] = useState<AnswerResult | null>(null);
  const [qaErr, setQaErr] = useState('');
  const [history, setHistory] = useState<QaItem[]>([]);

  const loadReady = useCallback(async () => {
    try {
      setReady(await api.ready());
    } catch {
      setReady(null);
    }
  }, []);

  const ensureSession = useCallback(async () => {
    try {
      setSession(await api.createSession({ title: '前端中控测试' }));
    } catch {
      setSession(null);
    }
  }, []);

  useEffect(() => {
    loadReady();
    ensureSession();
    pingLiveTalking().then(setLtReachable);
    return () => {
      pcRef.current?.close();
      pcRef.current = null;
    };
  }, [loadReady, ensureSession]);

  const connectAvatar = async () => {
    if (avatarState === 'connecting' || avatarState === 'connected') return;
    setAvatarState('connecting');
    setAvatarErr('');
    try {
      pcRef.current?.close();
      const pc = new RTCPeerConnection();
      pcRef.current = pc;
      pc.addTransceiver('video', { direction: 'recvonly' });
      pc.addTransceiver('audio', { direction: 'recvonly' });
      pc.ontrack = (e) => {
        if (videoRef.current) {
          videoRef.current.srcObject = e.streams[0];
          // 连接由用户点击触发，已具备播放权限；音频经同一条 WebRTC 流回传
          videoRef.current.play().catch(() => {});
        }
      };
      pc.oniceconnectionstatechange = () => {
        const s = pc.iceConnectionState;
        if (s === 'connected' || s === 'completed') setAvatarState('connected');
        else if (s === 'failed') setAvatarState('failed');
      };

      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      await waitIceGather(pc); // 收集全候选，写进 offer
      const local = pc.localDescription;
      if (!local?.sdp) throw new Error('无法生成 WebRTC offer SDP');
      const ans = await offerLiveTalking(local.sdp, local.type);
      await pc.setRemoteDescription({ sdp: ans.sdp, type: ans.type as RTCSdpType });
    } catch (e) {
      setAvatarState('failed');
      setAvatarErr(e instanceof Error ? e.message : String(e));
    }
  };

  const doBroadcast = async () => {
    if (!session) return;
    setBroadcastBusy(true);
    setBroadcastErr('');
    setBroadcastInfo('');
    try {
      const r = await api.say(session.id, { text: broadcastText });
      const lt = r.livetalking;
      setBroadcastInfo(
        lt.degraded ? `数字人未驱动：${lt.detail}` : `已发送给数字人 · ${lt.latency_ms}ms`,
      );
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
    try {
      // LLM 生成回答 → 后端驱动 LiveTalking /human → 数字人开口（音视频经 WebRTC）
      const res = await api.answer(session.id, { question });
      setQaResult(res);
      setHistory((h) =>
        [
          { question: res.question, answer: res.answer, llmMs: res.llm_latency_ms, model: res.model_id },
          ...h,
        ].slice(0, 20),
      );
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

  const avatarConnected = avatarState === 'connected';
  const avatarConnecting = avatarState === 'connecting';
  const canSpeak = !!session && avatarConnected;

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
          <StatusLight label="TTS 合成" ok={!!ready?.azure_configured} hint="Azure TTS（独立试听）" />
          <StatusLight
            label={`LLM ${ready?.llm_default_model_id || ''}`.trim()}
            ok={!!ready?.llm_configured}
            hint="LiteLLM 网关"
          />
          <StatusLight
            label="数字人渲染"
            ok={avatarConnected}
            warn={!avatarConnected && ltReachable !== false}
            hint={
              avatarConnected
                ? 'LiveTalking WebRTC 已连接'
                : ltReachable === false
                  ? 'LiveTalking(8028) 不可达，请先部署'
                  : '点击下方「连接数字人」'
            }
          />
        </div>
      </div>

      <div className="liveGrid">
        {/* 左：数字人预览 + 播报 */}
        <section className="livePanel">
          <header className="livePanelHead">
            <Volume2 size={16} />
            <span>数字人预览 · 文本播报</span>
          </header>

          <div className="liveStage">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              style={{
                position: 'absolute',
                inset: 0,
                width: '100%',
                height: '100%',
                objectFit: 'contain',
                objectPosition: 'center',
                background: '#070a0e',
                borderRadius: '20px',
                visibility: avatarConnected ? 'visible' : 'hidden',
                zIndex: 1,
              }}
            />
            {!avatarConnected && (
              <button
                className="primaryCta"
                onClick={connectAvatar}
                disabled={avatarConnecting || ltReachable === false}
                style={{ zIndex: 2 }}
              >
                {avatarConnecting ? <Loader2 size={16} className="spin" /> : <Video size={16} />}
                {avatarConnecting
                  ? '连接中…'
                  : avatarState === 'failed'
                    ? '重连数字人'
                    : '▶ 连接数字人'}
              </button>
            )}
            <div className="liveStageCaption">
              {avatarConnected
                ? '数字人已连接 · 实时画面'
                : avatarConnecting
                  ? '正在建立 WebRTC…'
                  : avatarState === 'failed'
                    ? '连接失败'
                    : '点击连接拉取画面'}
            </div>
            {(!avatarConnected || avatarErr) && (
              <div className="liveStageNote">
                画面由 GPU 节点 LiveTalking(musetalk) 实时渲染、经 WebRTC 直传浏览器，开口语音也走同一条流。
                {ltReachable === false
                  ? ' ⚠ 探测不到 LiveTalking(8028)，请先在 GPU 机部署。'
                  : ` 信令地址 ${LIVETALKING_URL}`}
                {avatarErr && <span style={{ color: '#ff5c5c' }}> · {avatarErr}</span>}
              </div>
            )}
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
              <button
                className="primaryCta"
                onClick={doBroadcast}
                disabled={broadcastBusy || !broadcastText.trim() || !session}
                title={canSpeak ? '' : '请先连接数字人'}
              >
                {broadcastBusy ? <Loader2 size={16} className="spin" /> : <Volume2 size={16} />}
                让数字人说
              </button>
            </div>
            {broadcastInfo && (
              <div className="liveAudioRow">
                <span className="latencyChip">{broadcastInfo}</span>
              </div>
            )}
            {!canSpeak && broadcastText.trim() && !broadcastBusy && (
              <div className="liveErr">提示：先点上方「连接数字人」拉起画面，再播报。</div>
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
              placeholder="观众提问，AI 会用数字人主播口吻回答并开口播报"
            />
            <div className="liveControls">
              <button
                className="primaryCta"
                onClick={doAsk}
                disabled={qaBusy || !question.trim() || !session}
              >
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
                <span>{qaResult.model_id}</span>
                {qaResult.livetalking && (
                  <span className={qaResult.livetalking.degraded ? 'warn' : 'good'}>
                    数字人 {qaResult.livetalking.degraded ? '未驱动' : '已开口'}
                  </span>
                )}
              </div>
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
                      LLM {it.llmMs}ms · {it.model}
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
          <span>数字人</span>
          <strong className="mono">
            {avatarConnected ? '已连接' : avatarConnecting ? '连接中' : '未连接'}
          </strong>
        </div>
      </div>
    </div>
  );
}
