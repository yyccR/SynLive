// 后端 API 客户端（浏览器端 fetch）。
// - 本地开发：不设 NEXT_PUBLIC_API_BASE_URL → 默认 http://localhost:8000
// - 单机反代部署：构建时设 NEXT_PUBLIC_API_BASE_URL="" → 同源相对路径（经 Caddy :8018 转发）
export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

// LiveTalking WebRTC 地址：浏览器直连（LiveTalking 侧 aiohttp_cors 已对 8018 放开）。
// 默认用页面同主机名 + :8028（单机部署时 SynLive 在 :8018、LiveTalking 在 :8028）。
// 跨机/自定义时用 NEXT_PUBLIC_LIVETALKING_URL 覆盖。
const LT_HOST = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
export const LIVETALKING_URL =
  process.env.NEXT_PUBLIC_LIVETALKING_URL ?? `http://${LT_HOST}:8028`;

export interface ReadyInfo {
  status: string;
  azure_configured: boolean;
  azure_region: string;
  llm_configured: boolean;
  llm_default_model_id: string;
  livetalking_enabled: boolean;
  livetalking_url: string;
}

export interface VoiceItem {
  id: string;
  name: string;
  gender: string;
}

export interface SessionInfo {
  id: string;
  title: string;
  avatar: string | null;
  voice: string | null;
  lang: string;
  livetalking_session_id: string | null;
  status: string;
}

export interface SayResult {
  session_id: string;
  text: string;
  livetalking: LiveTalkingState;
}

export interface AnswerResult {
  session_id: string;
  question: string;
  answer: string;
  model_id: string;
  llm_latency_ms: number;
  livetalking: LiveTalkingState | null;
}

export interface LiveTalkingState {
  ok: boolean;
  degraded: boolean;
  latency_ms: number;
  url: string;
  detail: string;
}

async function jfetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

// LiveTalking WebRTC 信令：POST /offer（浏览器 → LiveTalking 直连，跨源已 CORS 放开）
export async function offerLiveTalking(
  sdp: string,
  type: string,
): Promise<{ sdp: string; type: string }> {
  const res = await fetch(`${LIVETALKING_URL}/offer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sdp, type }),
  });
  if (!res.ok) throw new Error(`LiveTalking /offer HTTP ${res.status}`);
  return (await res.json()) as { sdp: string; type: string };
}

// 探测 LiveTalking 是否可达（GET / 在该镜像返回 403，<500 即视为在跑）
export async function pingLiveTalking(): Promise<boolean> {
  try {
    const res = await fetch(`${LIVETALKING_URL}/`, { method: 'GET' });
    return res.status > 0 && res.status < 500;
  } catch {
    return false;
  }
}

export const api = {
  ready: () => jfetch<ReadyInfo>('/health/ready'),
  voices: (lang: string) =>
    jfetch<VoiceItem[]>(`/api/v1/tts/voices?lang=${encodeURIComponent(lang)}`),
  languages: () => jfetch<{ code: string; label: string }[]>('/api/v1/tts/languages'),
  createSession: (body: { title?: string; voice?: string; lang?: string }) =>
    jfetch<SessionInfo>('/api/v1/live/sessions', { method: 'POST', body: JSON.stringify(body) }),
  say: (sid: string, body: { text: string; voice?: string; lang?: string }) =>
    jfetch<SayResult>(`/api/v1/live/sessions/${sid}/say`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  answer: (
    sid: string,
    body: { question: string; voice?: string; lang?: string; context?: string },
  ) =>
    jfetch<AnswerResult>(`/api/v1/live/sessions/${sid}/answer`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  // 合成 mp3，返回可直接播放的 blob URL + TTS 延迟
  synthesize: async (body: {
    text: string;
    lang: string;
    voice: string;
  }): Promise<{ url: string; latencyMs: number; bytes: number }> => {
    const res = await fetch(`${API_BASE}/api/v1/tts/synthesize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        detail = (await res.json()).detail || detail;
      } catch {
        /* ignore */
      }
      throw new Error(detail);
    }
    const blob = await res.blob();
    return {
      url: URL.createObjectURL(blob),
      latencyMs: Number(res.headers.get('X-TTS-Latency-Ms') || 0),
      bytes: blob.size,
    };
  },
};
