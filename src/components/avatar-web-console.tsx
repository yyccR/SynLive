'use client';

// 浏览器内 3D 数字人 demo(TalkingHead.js + HeadAudio)—— 独立于主控台的第三条渲染路径。
//
// 与 unreal / livetalking 的关系:本页不碰 session / /say / renderer_client,后端零改动。
// verbatim 链路:Azure TTS(复用 /api/v1/tts/synthesize)合 mp3 → 前端 decodeAudioData →
// head.speakAudio({audio}) 播放 → 音频经 TalkingHead.audioSpeechGainNode → HeadAudio worklet
// 实时出 Oculus viseme → 驱动 GLB 口型。中文口型靠 HeadAudio(英语 MFCC 模型,能动嘴但不完美)。
//
// 形象可切换(顶部下拉):均为标准 ARKit52 + Oculus15 viseme morph 命名,TalkingHead 通用兼容,
// 换模型零适配。默认 Avaturn 写实向(比原 RPM 卡通示例更接近真人);brunette 留作对照。
// 注意:浏览器 GLB 路径天花板是「次世代半写实」,做不到 UE MetaHuman 级写实(那是 /app/live 的活)。
//
// 模块加载:talkinghead.mjs / dynamicbones.mjs 里的 three bare import 已就地改写为 CDN 绝对
// URL(见 public/vendor/talkinghead/,升级 vendor 后需重新 sed —— 见本目录 README),且内部用
// import.meta.url 解析 playback-worklet.js,故必须以「浏览器原生 ESM」加载(webpackIgnore),
// 不能进 webpack 打包。因此无需 importmap(动态注入的 importmap 在 Next 已执行 module script
// 后会被浏览器忽略,导致 bare 'three' 无法解析)。

import { useCallback, useEffect, useRef, useState } from 'react';
import { Loader2, Video, Volume2 } from 'lucide-react';
import { api, type ReadyInfo } from '@/lib/api';

type AvatarState = 'idle' | 'loading' | 'ready' | 'failed';

// 可切换的数字人形象。morph 命名都是标准 ARKit+Oculus,TalkingHead 通用。
// voice / hz 与形象性别匹配(男模型→云希男声,hz 偏低;女模型→晓晓,hz 偏高),
// hz 即 HeadAudio 的 speakerMeanHz,需对齐 TTS 音色声道共振,口型才准。
// 三个均为各平台「示例/演示」授权,商用前需替换为自有或商用授权形象。
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AvatarOption = { id: string; name: string; url: string; body: 'M' | 'F'; voice: string; hz: number };
const AVATARS: AvatarOption[] = [
  { id: 'avaturn', name: '写实·Avaturn(男)', url: '/vendor/talkinghead/avatars/avaturn.glb', body: 'M', voice: 'zh-CN-YunxiNeural', hz: 140 },
  { id: 'avatarsdk', name: '写实·AvatarSDK(男)', url: '/vendor/talkinghead/avatars/avatarsdk.glb', body: 'M', voice: 'zh-CN-YunxiNeural', hz: 140 },
  { id: 'brunette', name: '卡通·RPM(女·原)', url: '/vendor/talkinghead/avatars/brunette.glb', body: 'F', voice: 'zh-CN-XiaoxiaoNeural', hz: 220 },
];
const DEFAULT_AVATAR = AVATARS[0];

// 运行时 dynamic import:用 new Function 包一层,打包器(Turbopack/webpack)的静态分析看不到
// import(),不会在构建期尝试解析 '/vendor/...' 路径(webpackIgnore 在 Turbopack 下不可靠)。
// vendor 是浏览器原生 ESM,three 的 import 已改写为 CDN 绝对 URL,运行时按 URL 直接加载。
// eslint-disable-next-line @typescript-eslint/no-implied-eval, no-new-func, @typescript-eslint/no-explicit-any
const dynImport = new Function('u', 'return import(u)') as (u: string) => Promise<any>;

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyHead = any;

function StatusLight({ label, ok, warn, hint }: { label: string; ok: boolean; warn?: boolean; hint?: string }) {
  const cls = warn ? 'liveLight warn' : ok ? 'liveLight ok' : 'liveLight off';
  return (
    <span className={cls} title={hint}>
      <i />
      {label}
    </span>
  );
}

export function AvatarWebConsole() {
  const [ready, setReady] = useState<ReadyInfo | null>(null);
  const [avatarState, setAvatarState] = useState<AvatarState>('idle');
  const [avatarErr, setAvatarErr] = useState('');
  const [avatarChoice, setAvatarChoice] = useState(DEFAULT_AVATAR.id);
  const [text, setText] = useState('欢迎来到直播间,今天为大家介绍我们的新品。');
  const [busy, setBusy] = useState(false);
  const [info, setInfo] = useState('');
  const [err, setErr] = useState('');

  const containerRef = useRef<HTMLDivElement | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const headRef = useRef<AnyHead>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  // 模块类缓存:首次 dynImport 后复用,热切换形象时不重复加载
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const headModRef = useRef<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const audioModRef = useRef<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const headAudioRef = useRef<any>(null);

  const selectedAvatar = AVATARS.find((a) => a.id === avatarChoice) ?? DEFAULT_AVATAR;

  const loadReady = useCallback(async () => {
    try {
      setReady(await api.ready());
    } catch {
      setReady(null);
    }
  }, []);

  useEffect(() => {
    loadReady();
    return () => {
      // 卸载时停掉动画循环、释放音频图
      try {
        headAudioRef.current?.disconnect?.();
      } catch {
        /* ignore */
      }
      try {
        headRef.current?.stop?.();
      } catch {
        /* ignore */
      }
    };
  }, [loadReady]);

  // 首次按需 dynImport vendor 模块(TalkingHead / HeadAudio 类),后续热切换复用。
  const loadModules = async () => {
    if (!headModRef.current) headModRef.current = await dynImport('/vendor/talkinghead/talkinghead.mjs');
    if (!audioModRef.current) audioModRef.current = await dynImport('/vendor/talkinghead/headaudio.mjs');
    return { TalkingHead: headModRef.current.TalkingHead, HeadAudio: audioModRef.current.HeadAudio };
  };

  // 装配 HeadAudio:音频→viseme 实时驱动口型。hz 对齐当前 TTS 音色,男声低/女声高。
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const assembleHeadAudio = async (head: any, hz: number, HeadAudio: any) => {
    try {
      headAudioRef.current?.disconnect?.();
    } catch {
      /* 旧的断不掉就算了,AudioNode 一般可 disconnect */
    }
    await head.audioCtx.audioWorklet.addModule('/vendor/talkinghead/headworklet.mjs');
    const headaudio = new HeadAudio(head.audioCtx, {
      parameterData: { vadGateActiveDb: -40, vadGateInactiveDb: -60, speakerMeanHz: hz },
    });
    await headaudio.loadModel('/vendor/talkinghead/model-en-mixed.bin');
    // 从 TalkingHead 语音增益节点 tap 音频 → HeadAudio 实时分析出 viseme
    head.audioSpeechGainNode.connect(headaudio);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    headaudio.onvalue = (key: string, value: number) => {
      Object.assign(head.mtAvatar[key], { newvalue: value, needsUpdate: true });
    };
    head.opt.update = headaudio.update.bind(headaudio);
    headAudioRef.current = headaudio;
  };

  // (重新)构建一个 TalkingHead 实例并挂载指定形象 + 装配 HeadAudio。
  // 首次连接和热切换形象都走这里:完全重建,无 HeadAudio 残留,最可靠。
  const bootAvatar = async (av: AvatarOption) => {
    const { TalkingHead, HeadAudio } = await loadModules();

    try {
      headRef.current?.stop?.();
    } catch {
      /* ignore */
    }

    // AudioWorklet(HeadAudio 口型 + TalkingHead 音频播放)是 secure-context-only API:
    // 必须用 https 或 localhost 访问。从 http+IP 打开时 audioCtx.audioWorklet 为 undefined。
    if (!window.isSecureContext) {
      throw new Error(
        '需要 secure context(https 或 localhost)才能用 AudioWorklet。请改用 https://10.2.42.21:3000 访问(首次有证书警告,点「高级→继续」即可),或在服务器本机用 http://localhost:3000。',
      );
    }

    // AudioContext 在用户手势(点击)内创建,避免 autoplay 暂停
    const head = new TalkingHead(containerRef.current, {
      lipsyncModules: [], // 不用内置文本口型(无中文);口型由 HeadAudio 实时驱动
      mixerGainSpeech: 2,
      cameraView: 'upper',
    });
    headRef.current = head;
    audioCtxRef.current = head.audioCtx;

    await head.showAvatar({
      url: av.url,
      body: av.body,
      avatarMood: 'neutral',
      lipsyncLang: 'en', // HeadAudio 不依赖语言模块,仅占位
    });

    await assembleHeadAudio(head, av.hz, HeadAudio);
  };

  const connect = async () => {
    if (avatarState === 'loading' || avatarState === 'ready') return;
    setAvatarState('loading');
    setAvatarErr('');
    try {
      await bootAvatar(selectedAvatar);
      setAvatarState('ready');
    } catch (e) {
      setAvatarState('failed');
      setAvatarErr(e instanceof Error ? e.message : String(e));
    }
  };

  // 顶部下拉切换形象:已连接就热重建(换脸+换匹配音色),未连接只更新选择,下次连接生效。
  const onAvatarChange = async (id: string) => {
    setAvatarChoice(id);
    if (avatarState !== 'ready') return;
    const av = AVATARS.find((a) => a.id === id) ?? DEFAULT_AVATAR;
    setAvatarState('loading');
    setAvatarErr('');
    try {
      await bootAvatar(av);
      setAvatarState('ready');
    } catch (e) {
      setAvatarState('failed');
      setAvatarErr(e instanceof Error ? e.message : String(e));
    }
  };

  const speak = async () => {
    const head = headRef.current;
    if (!head) return;
    setBusy(true);
    setErr('');
    setInfo('');
    try {
      // 1) Azure TTS 合成 mp3(复用后端,零改动),音色跟随当前形象性别
      const { url, latencyMs } = await api.synthesize({ text, lang: 'zh', voice: selectedAvatar.voice });
      // 2) 解码成 AudioBuffer
      const res = await fetch(url);
      const arr = await res.arrayBuffer();
      const audioCtx = audioCtxRef.current;
      if (!audioCtx) throw new Error('音频上下文未初始化');
      if (audioCtx.state === 'suspended') await audioCtx.resume();
      const audioBuffer = await audioCtx.decodeAudioData(arr);
      // 3) 播放 → 经 audioSpeechGainNode → HeadAudio 驱动口型
      head.speakAudio({ audio: audioBuffer });
      setInfo(`已发送给数字人 · TTS ${latencyMs}ms · ${audioBuffer.duration.toFixed(1)}s`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const avatarReady = avatarState === 'ready';
  const avatarLoading = avatarState === 'loading';

  return (
    <div className="liveConsole">
      {/* 状态栏 */}
      <div className="liveStatusbar">
        <div className="liveStatusLeft">
          <Video size={18} />
          <div>
            <strong>浏览器数字人(TalkingHead.js)</strong>
            <small>前端 3D 渲染 · 不占服务器 · 与 UE/LiveTalking 主链路并存</small>
          </div>
        </div>
        <div className="liveLights">
          <StatusLight label="TTS 合成" ok={!!ready?.azure_configured} hint="Azure TTS(mp3 → 前端驱动)" />
          <StatusLight
            label="数字人渲染"
            ok={avatarReady}
            warn={!avatarReady}
            hint={
              avatarReady
                ? 'TalkingHead + HeadAudio 已就绪'
                : avatarState === 'failed'
                  ? avatarErr
                  : '点击下方「连接数字人」加载 3D 模型'
            }
          />
        </div>
      </div>

      <div className="liveGrid">
        <section className="livePanel">
          <header className="livePanelHead">
            <Volume2 size={16} />
            <span>数字人预览 · 文本播报</span>
            {/* 形象选择:实时切换 GLB 模型 + 联动匹配音色。loading 时禁用避免并发重建。 */}
            <select
              value={avatarChoice}
              onChange={(e) => onAvatarChange(e.target.value)}
              disabled={avatarLoading}
              title="切换数字人形象(已连接会热重载)"
              style={{
                marginLeft: 'auto',
                background: 'rgba(255,255,255,0.04)',
                color: '#e6edf3',
                border: '1px solid rgba(255,255,255,0.14)',
                borderRadius: 8,
                padding: '4px 8px',
                fontSize: 13,
                cursor: avatarLoading ? 'wait' : 'pointer',
              }}
            >
              {AVATARS.map((a) => (
                <option key={a.id} value={a.id} style={{ color: '#111' }}>
                  {a.name}
                </option>
              ))}
            </select>
          </header>

          <div className="liveStage">
            {/* TalkingHead 把 three.js 的 <canvas> 挂进这个容器 */}
            <div
              ref={containerRef}
              style={{
                position: 'absolute',
                inset: 0,
                width: '100%',
                height: '100%',
                borderRadius: '20px',
                overflow: 'hidden',
                visibility: avatarReady ? 'visible' : 'hidden',
                zIndex: 1,
              }}
            />
            {!avatarReady && (
              <button
                className="primaryCta"
                onClick={connect}
                disabled={avatarLoading}
                style={{ zIndex: 2 }}
              >
                {avatarLoading ? <Loader2 size={16} className="spin" /> : <Video size={16} />}
                {avatarLoading ? '加载中…' : avatarState === 'failed' ? '重连数字人' : '▶ 连接数字人'}
              </button>
            )}
            <div className="liveStageCaption">
              {avatarReady
                ? `${selectedAvatar.name} 已就绪 · 输入文本让它开口`
                : avatarLoading
                  ? '正在加载 3D 模型与音频引擎…'
                  : avatarState === 'failed'
                    ? '加载失败'
                    : '点击连接加载模型'}
            </div>
            {(!avatarReady || avatarErr) && (
              <div className="liveStageNote">
                画面由浏览器内 three.js 实时渲染(TalkingHead),口型由 Azure TTS 音频经 HeadAudio 实时分析驱动。
                {!ready?.azure_configured ? ' ⚠ 后端 Azure TTS 未配置,播报会失败。' : ''}
                {avatarErr && <span style={{ color: '#ff5c5c' }}> · {avatarErr}</span>}
              </div>
            )}
          </div>

          <div className="liveField">
            <label>播报文本</label>
            <textarea
              rows={3}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="输入要让数字人说的话"
            />
            <div className="liveControls">
              <button
                className="primaryCta"
                onClick={speak}
                disabled={busy || !text.trim() || !avatarReady}
                title={!avatarReady ? '请先连接数字人' : ''}
              >
                {busy ? <Loader2 size={16} className="spin" /> : <Volume2 size={16} />}
                让数字人说
              </button>
            </div>
            {info && (
              <div className="liveAudioRow">
                <span className="latencyChip">{info}</span>
              </div>
            )}
            {err && <div className="liveErr">{err}</div>}
          </div>
        </section>

        <section className="livePanel">
          <header className="livePanelHead">
            <span>说明 · 已知限制</span>
          </header>
          <div className="liveField" style={{ lineHeight: 1.7 }}>
            <p>
              <strong>这条路径是什么:</strong>
              <br />
              浏览器内 three.js 渲染的 3D 数字人(met4citizen/TalkingHead),音视频都在本地,不占服务器 GPU。
              与 UE5 MetaHuman 主链路、LiveTalking 2D 降级路径三者并存,互不影响(.env 的 RENDERER_BACKEND 不用改)。
            </p>
            <p>
              <strong>形象怎么换:</strong>
              <br />
              顶部下拉切换。三个模型 morph 命名都是标准 ARKit52 + Oculus15 viseme,TalkingHead 通用兼容;
              切换时连同 TTS 音色、HeadAudio 共振基准(speakerMeanHz)一起联动,口型才不跑偏。
              默认「写实·Avaturn」比原 RPM 卡通示例更接近真人。
            </p>
            <p>
              <strong>口型怎么来:</strong>
              <br />
              verbatim —— 复用 SynLive 后端 Azure TTS 合成的精确 mp3,前端解码后驱动口型。
              口型由 HeadAudio(AudioWorklet)实时分析音频出 Oculus viseme,不依赖文本/时间戳,所以中文也能动嘴。
            </p>
            <p>
              <strong>已知限制(POC):</strong>
            </p>
            <ul style={{ margin: '0 0 0 1.2em', padding: 0 }}>
              <li>浏览器 GLB 路径天花板是「次世代半写实」,做不到 UE MetaHuman 级写实(那是 /app/live + UE 工程的活)。</li>
              <li>HeadAudio 预训练模型是英语 MFCC,中文口型能动但不完美;后续可升级后端 Azure Speech SDK 出精确 viseme。</li>
              <li>三个 GLB 均为各平台「示例/演示」模型(非商用授权),商用/公开前需替换为自有或商用授权形象。</li>
            </ul>
          </div>
        </section>
      </div>
    </div>
  );
}
