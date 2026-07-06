"""TTS 集中配置：Azure 凭据 + 语言/音色映射。

移植自 seo_video_generate/services/tts/config.py，唯一改动：去掉 Django 依赖，
凭据改从 app.core.config.settings 读取（AZURE_SERVICE_KEY / AZURE_SERVICE_REGION）。

短代码 → Azure locale + 音色列表，每条音色 {"id","name","gender"}，沿用 STT 的 16 种语言。
参考：https://learn.microsoft.com/azure/ai-services/speech-service/language-support?tabs=tts
"""

from __future__ import annotations

from ...core.config import settings

# Azure TTS provider 标识
AZURE_TTS = "azure_tts"

# 短代码 → Azure locale + 音色列表
AZURE_TTS_LANG_MAPPING = {
    "zh": {
        "lang": "zh-CN",
        "voices": [
            {"id": "zh-CN-XiaoxiaoNeural", "name": "晓晓（女声）", "gender": "Female"},
            {"id": "zh-CN-XiaoyiNeural", "name": "晓伊（女声）", "gender": "Female"},
            {"id": "zh-CN-YunxiNeural", "name": "云希（男声）", "gender": "Male"},
            {"id": "zh-CN-YunyangNeural", "name": "云扬（男声·新闻）", "gender": "Male"},
        ],
    },
    "tw": {
        "lang": "zh-TW",
        "voices": [
            {"id": "zh-TW-HsiaoChenNeural", "name": "曉臻（女聲）", "gender": "Female"},
            {"id": "zh-TW-YunJheNeural", "name": "雲哲（男聲）", "gender": "Male"},
        ],
    },
    "yue": {
        "lang": "yue-CN",
        "voices": [
            {"id": "yue-CN-XiaoMinNeural", "name": "曉敏（女聲）", "gender": "Female"},
            {"id": "yue-CN-YunSongNeural", "name": "雲松（男聲）", "gender": "Male"},
        ],
    },
    "en": {
        "lang": "en-US",
        "voices": [
            {"id": "en-US-JennyNeural", "name": "Jenny（Female）", "gender": "Female"},
            {"id": "en-US-AriaNeural", "name": "Aria（Female）", "gender": "Female"},
            {"id": "en-US-GuyNeural", "name": "Guy（Male）", "gender": "Male"},
            {"id": "en-US-DavisNeural", "name": "Davis（Male）", "gender": "Male"},
        ],
    },
    "ja": {
        "lang": "ja-JP",
        "voices": [
            {"id": "ja-JP-NanamiNeural", "name": "七海（女声）", "gender": "Female"},
            {"id": "ja-JP-KeitaNeural", "name": "圭太（男声）", "gender": "Male"},
        ],
    },
    "ko": {
        "lang": "ko-KR",
        "voices": [
            {"id": "ko-KR-SunHiNeural", "name": "선히（女声）", "gender": "Female"},
            {"id": "ko-KR-InJoonNeural", "name": "인준（男声）", "gender": "Male"},
        ],
    },
    "th": {
        "lang": "th-TH",
        "voices": [
            {"id": "th-TH-PremwadeeNeural", "name": "Premwadee（Female）", "gender": "Female"},
            {"id": "th-TH-NiwatNeural", "name": "Niwat（Male）", "gender": "Male"},
        ],
    },
    "es": {
        "lang": "es-ES",
        "voices": [
            {"id": "es-ES-ElviraNeural", "name": "Elvira（Female）", "gender": "Female"},
            {"id": "es-ES-AlvaroNeural", "name": "Alvaro（Male）", "gender": "Male"},
        ],
    },
    "fr": {
        "lang": "fr-FR",
        "voices": [
            {"id": "fr-FR-DeniseNeural", "name": "Denise（Female）", "gender": "Female"},
            {"id": "fr-FR-HenriNeural", "name": "Henri（Male）", "gender": "Male"},
        ],
    },
    "de": {
        "lang": "de-DE",
        "voices": [
            {"id": "de-DE-KatjaNeural", "name": "Katja（Female）", "gender": "Female"},
            {"id": "de-DE-ConradNeural", "name": "Conrad（Male）", "gender": "Male"},
        ],
    },
    "it": {
        "lang": "it-IT",
        "voices": [
            {"id": "it-IT-ElsaNeural", "name": "Elsa（Female）", "gender": "Female"},
            {"id": "it-IT-DiegoNeural", "name": "Diego（Male）", "gender": "Male"},
        ],
    },
    "pt": {
        "lang": "pt-PT",
        "voices": [
            {"id": "pt-PT-RaquelNeural", "name": "Raquel（Female）", "gender": "Female"},
            {"id": "pt-PT-DuarteNeural", "name": "Duarte（Male）", "gender": "Male"},
        ],
    },
    "ru": {
        "lang": "ru-RU",
        "voices": [
            {"id": "ru-RU-SvetlanaNeural", "name": "Светлана（Female）", "gender": "Female"},
            {"id": "ru-RU-DmitryNeural", "name": "Дмитрий（Male）", "gender": "Male"},
        ],
    },
    "ar": {
        "lang": "ar-SA",
        "voices": [
            {"id": "ar-SA-ZariyahNeural", "name": "Zariyah（Female）", "gender": "Female"},
            {"id": "ar-SA-HamedNeural", "name": "Hamed（Male）", "gender": "Male"},
        ],
    },
    "pl": {
        "lang": "pl-PL",
        "voices": [
            {"id": "pl-PL-ZofiaNeural", "name": "Zofia（Female）", "gender": "Female"},
            {"id": "pl-PL-MarekNeural", "name": "Marek（Male）", "gender": "Male"},
        ],
    },
    "ms": {
        "lang": "ms-MY",
        "voices": [
            {"id": "ms-MY-YasminNeural", "name": "Yasmin（Female）", "gender": "Female"},
            {"id": "ms-MY-OsmanNeural", "name": "Osman（Male）", "gender": "Male"},
        ],
    },
}

# 前端语言下拉用：短代码 + 中文描述
LANGUAGE_OPTIONS = [
    {"code": "zh", "label": "中文（普通话）"},
    {"code": "tw", "label": "中文（台湾）"},
    {"code": "yue", "label": "粤语"},
    {"code": "en", "label": "英语"},
    {"code": "ja", "label": "日语"},
    {"code": "ko", "label": "韩语"},
    {"code": "th", "label": "泰语"},
    {"code": "es", "label": "西班牙语"},
    {"code": "fr", "label": "法语"},
    {"code": "de", "label": "德语"},
    {"code": "it", "label": "意大利语"},
    {"code": "pt", "label": "葡萄牙语"},
    {"code": "ru", "label": "俄语"},
    {"code": "ar", "label": "阿拉伯语"},
    {"code": "pl", "label": "波兰语"},
    {"code": "ms", "label": "马来语"},
]


def get_azure_config() -> tuple[str, str]:
    """返回 (subscription_key, region)，统一从 settings 读取。"""
    return (settings.azure_service_key, settings.azure_service_region)


def get_language_config(lang_code: str) -> dict | None:
    """根据短代码返回 {lang, voices}，未命中返回 None。"""
    return AZURE_TTS_LANG_MAPPING.get(lang_code)


def default_voice(lang_code: str) -> str | None:
    """返回某语言第一个音色的 id，无该语言返回 None。"""
    cfg = get_language_config(lang_code)
    if not cfg or not cfg.get("voices"):
        return None
    return cfg["voices"][0]["id"]
