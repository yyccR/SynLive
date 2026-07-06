"""Azure 神经网络 TTS 合成核心。

移植自 seo_video_generate/services/tts/synthesizer.py（逻辑不变）：
直接走 REST 接口 https://{region}.tts.speech.microsoft.com/cognitiveservices/v1，
header 用 Ocp-Apim-Subscription-Key + X-Microsoft-OutputFormat，body 是 SSML。
凭据/语言配置来自 .config（解耦 Django 后改读 settings）。
"""

from __future__ import annotations

from xml.sax.saxutils import escape

import requests
from loguru import logger

from .config import get_azure_config, get_language_config

# 音色性别 → SSML gender 值
_GENDER_MAP = {"Female": "Female", "Male": "Male"}

# Azure 输出格式：高质量 mp3
DEFAULT_OUTPUT_FORMAT = "audio-16khz-128kbitrate-mono-mp3"


def _build_ssml(
    text: str,
    locale: str,
    voice: str,
    gender: str,
    rate_pct: int,
    pitch_pct: int,
    volume: int,
) -> str:
    """构造 SSML。语速/语调百分比来自滑块（-100~100），音量 0~100。"""
    rate = f"{rate_pct:+d}%"
    pitch = f"{pitch_pct:+d}Hz"
    vol = str(max(0, min(100, int(volume))))
    gender = _GENDER_MAP.get(gender, "Female")
    return (
        f"<speak version='1.0' xml:lang='{locale}'>"
        f"<voice xml:lang='{locale}' xml:gender='{gender}' name='{voice}'>"
        f"<prosody rate='{rate}' pitch='{pitch}' volume='{vol}'>"
        f"{escape(text)}"
        f"</prosody>"
        f"</voice>"
        f"</speak>"
    )


def synthesize(
    text: str,
    lang: str,
    voice: str,
    rate_pct: int = 0,
    pitch_pct: int = 0,
    volume: int = 50,
    output_format: str = DEFAULT_OUTPUT_FORMAT,
) -> tuple[bytes | None, str | None]:
    """调用 Azure TTS 合成语音。

    Args:
        text: 要合成的文本
        lang: 语言短代码（zh/en/...）
        voice: Azure 音色名（zh-CN-XiaoxiaoNeural）
        rate_pct: 语速百分比 -100~100（0 为正常）
        pitch_pct: 语调百分比 -100~100（0 为正常）
        volume: 音量 0~100
        output_format: Azure X-Microsoft-OutputFormat

    Returns:
        (audio_bytes, error)。成功时 error 为 None。
    """
    lang_config = get_language_config(lang)
    if not lang_config:
        return None, f"不支持的语言: {lang}"

    locale = lang_config["lang"]
    # 校验音色属于该语言，并取 gender
    gender = "Female"
    valid_voices = lang_config["voices"]
    matched = next((v for v in valid_voices if v["id"] == voice), None)
    if matched:
        gender = matched.get("gender", "Female")
    elif valid_voices:
        # 兜底：未传/传错音色，用该语言第一个
        voice = valid_voices[0]["id"]
        gender = valid_voices[0].get("gender", "Female")
    else:
        return None, f"语言 {lang} 无可用音色"

    subscription_key, region = get_azure_config()
    if not subscription_key:
        return None, "Azure TTS 未配置凭据（AZURE_SERVICE_KEY）"

    url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {
        "Ocp-Apim-Subscription-Key": subscription_key,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": output_format,
        "User-Agent": "synlive",
    }
    ssml = _build_ssml(text, locale, voice, gender, rate_pct, pitch_pct, volume)

    try:
        response = requests.post(url, data=ssml.encode("utf-8"), headers=headers, timeout=30)
    except requests.Timeout:
        logger.error(f"[Azure TTS] 请求超时: lang={lang}, voice={voice}")
        return None, "Azure TTS 请求超时"
    except Exception as exc:
        logger.error(f"[Azure TTS] 请求异常: {exc}")
        return None, f"Azure TTS 请求异常: {exc}"

    if not response.ok:
        body = response.text[:300] if response.text else ""
        logger.error(
            f"[Azure TTS] 合成失败: status={response.status_code}, "
            f"lang={lang}, voice={voice}, body={body}"
        )
        return None, f"Azure TTS 合成失败（HTTP {response.status_code}）"

    if not response.content:
        return None, "Azure TTS 返回空音频"

    logger.info(
        f"[Azure TTS] 合成成功: lang={lang}, voice={voice}, "
        f"text_len={len(text)}, bytes={len(response.content)}"
    )
    return response.content, None
