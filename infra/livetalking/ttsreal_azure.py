"""Azure TTS for LiveTalking（REST 版，与 SynLive 后端同一把 key / 同一套接口）。

为什么有这个文件：codewithgpu 镜像 vjo1Y6NJ3N 的 ttsreal.py 只支持 edgetts /
gpt-sovits / xtts，没有自带 azure 插件；而 edgetts 因微软封 TrustedClientToken
持续 403（点播放无声、嘴不动）。本类补上 azure：REST 合成 riff-16khz-16bit-mono-pcm
→ soundfile 读成 16kHz mono float32 → 按 chunk 喂 put_audio_frame 驱动 musetalk
口型（与 EdgeTTS 同一个出口，渲染链路零改动）。

凭据：容器环境变量 AZURE_SPEECH_KEY / AZURE_TTS_REGION（deploy-livetalking.sh 已注入）。
音色：默认 zh-CN-XiaoxiaoNeural，可用 AZURE_TTS_VOICE 覆盖。

部署：本文件由 deploy-livetalking.sh 挂载到容器
/root/metahuman-stream/ttsreal_azure.py；patch-tts-azure.sh 给 musereal.py 的
tts 分支加 `--tts azure` → AzureTTS。

接口与 EdgeTTS 完全一致（只实现 txt_to_audio），其余（msgqueue / render /
process_tts / input_stream / chunk / put_audio_frame 出口）全部复用 BaseTTS。
"""

import os
import time
from io import BytesIO
from xml.sax.saxutils import escape

import requests
import soundfile as sf
import numpy as np

from ttsreal import BaseTTS

# riff-16khz-16bit-mono-pcm = WAV 16kHz 16bit mono，soundfile 原生可读，
# 且采样率正好等于 musetalk 要求的 16000（BaseTTS.sample_rate），无需重采样。
_OUTPUT_FORMAT = "riff-16khz-16bit-mono-pcm"


class AzureTTS(BaseTTS):
    def txt_to_audio(self, msg):
        text = msg
        key = os.environ.get("AZURE_SPEECH_KEY") or os.environ.get("AZURE_SERVICE_KEY")
        region = (
            os.environ.get("AZURE_TTS_REGION")
            or os.environ.get("AZURE_SERVICE_REGION")
            or "eastasia"
        )
        voice = os.environ.get("AZURE_TTS_VOICE") or "zh-CN-XiaoxiaoNeural"
        # zh-CN-XiaoxiaoNeural -> zh-CN；yue-CN-XiaoMinNeural -> yue-CN
        locale = "-".join(voice.split("-")[:-1]) or "zh-CN"

        if not key:
            # 凭据缺失：打日志跳过本次，不抛（保持 /human 主链路不崩）
            print("[AzureTTS] AZURE_SPEECH_KEY 未设置，跳过本次合成")
            return

        ssml = (
            f"<speak version='1.0' xml:lang='{locale}'>"
            f"<voice name='{voice}'>"
            f"<prosody volume='50'>{escape(text)}</prosody>"
            f"</voice></speak>"
        )
        url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
        headers = {
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": _OUTPUT_FORMAT,
            "User-Agent": "livetalking",
        }

        t = time.time()
        try:
            resp = requests.post(
                url, data=ssml.encode("utf-8"), headers=headers, timeout=30
            )
        except Exception as exc:  # 网络异常：跳过本次，不让合成线程崩
            print(f"[AzureTTS] 请求异常: {exc}")
            return

        if not resp.ok or not resp.content:
            body = resp.text[:200] if resp.text else ""
            print(f"[AzureTTS] 合成失败 status={resp.status_code} body={body}")
            return

        # 与 EdgeTTS.txt_to_audio 同款切块出口（riff-16khz 一般已是 16000，无需重采样）
        stream, sample_rate = sf.read(BytesIO(resp.content))
        print(f"[INFO]tts audio stream {sample_rate}: {stream.shape}")
        stream = stream.astype(np.float32)
        if stream.ndim > 1:
            print(f"[WARN] audio has {stream.shape[1]} channels, only use the first.")
            stream = stream[:, 0]
        if sample_rate != self.sample_rate and stream.shape[0] > 0:
            import resampy  # 仅在罕见需要重采样��才导入

            print(
                f"[WARN] audio sample rate is {sample_rate}, "
                f"resampling into {self.sample_rate}."
            )
            stream = resampy.resample(
                x=stream, sr_orig=sample_rate, sr_new=self.sample_rate
            )

        print(f"-------azure tts time:{time.time()-t:.4f}s bytes={len(resp.content)}")

        streamlen = stream.shape[0]
        idx = 0
        while streamlen >= self.chunk:
            self.parent.put_audio_frame(stream[idx : idx + self.chunk])
            streamlen -= self.chunk
            idx += self.chunk
