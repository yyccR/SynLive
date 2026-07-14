# TalkingHead.js + HeadAudio 本地 vendor

本目录是浏览器内 3D 数字人 demo(`/app/avatar-web`)的静态资源,全部同源服务(<AudioWorklet / GLB 必须同源)。

## 文件清单与来源

| 文件 | 来源 | 说明 |
| --- | --- | --- |
| `talkinghead.mjs` | [met4citizen/TalkingHead](https://github.com/met4citizen/TalkingHead) `@1.7/modules/` | TalkingHead 主类(three.js) |
| `dynamicbones.mjs` | TalkingHead `@1.7/modules/` | talkinghead.mjs 的相对依赖(物理骨骼) |
| `playback-worklet.js` | TalkingHead `@1.7/modules/` | 音频播放 AudioWorklet,被 talkinghead.mjs 用 `import.meta.url` 相对加载 |
| `headaudio.mjs` | [met4citizen/HeadAudio](https://github.com/met4citizen/HeadAudio) `@main/dist/headaudio.min.mjs` | 音频→viseme worklet node(导出 `HeadAudio` 类) |
| `headworklet.mjs` | HeadAudio `@main/dist/headworklet.min.mjs` | HeadAudio 的 AudioWorklet processor(自包含) |
| `model-en-mixed.bin` | HeadAudio `@main/dist/` | 预训练 viseme 模型(英语 MFCC+Gaussian,14KB) |
| `avatars/brunette.glb` | TalkingHead `@1.7/avatars/` | Ready Player Me 示例形象(**CC BY-NC 4.0,非商用**) |

## 📦 形象 GLB 不入库（体积大）

`avatars/*.glb` 单个 5–14MB，已加进 `.gitignore` 不随仓库分发。本机跑 `/app/avatar-web` 前需把形象 GLB 放到 `avatars/`（标准 ARKit52 + Oculus15 viseme morph 命名即可，TalkingHead 通用兼容）：

- `brunette.glb` — TalkingHead [`@1.7/avatars/`](https://github.com/met4citizen/TalkingHead/tree/master/avatars)（CC BY-NC 4.0，非商用）
- `avaturn.glb` / `avatarsdk.glb` — Avaturn / AvatarSDK 各平台示例 GLB（商用前需替换为自有或商用授权形象）

## ⚠ three 的 bare import 已就地改写为 esm.sh URL

`talkinghead.mjs` / `dynamicbones.mjs` 原本 `import ... from 'three'` / `from 'three/addons/...'`(bare specifier),
浏览器原生 ESM 无法解析(无 importmap)。Next 页面加载时已执行 module script(React hydration),HTML 规范要求
importmap 必须在第一个 module script 之前 —— 动态注入的 importmap 会被浏览器忽略,故**不能**用 importmap。

直接把这些 bare import 改写成 **esm.sh** URL。**不要用 jsdelivr**:jsdelivr 的 addons(OrbitControls/GLTFLoader 等)
内部仍是 bare `from 'three'`,会再次触发同样的 `Failed to resolve module specifier "three"` 错误;
esm.sh 内部用 `/three@x/` 相对路径,自包含,真正无 bare specifier。

**升级 vendor 后必须重新执行改写**(否则 bare 'three' 无法解析):

```bash
V=public/vendor/talkinghead
sed -i "s|from 'three/addons/|from 'https://esm.sh/three@0.180.0/examples/jsm/|g" "$V/talkinghead.mjs" "$V/dynamicbones.mjs"
sed -i "s|from 'three'|from 'https://esm.sh/three@0.180.0'|g" "$V/talkinghead.mjs" "$V/dynamicbones.mjs"
```

验证:`grep -c "from 'three'" talkinghead.mjs dynamicbones.mjs` 应为 0。

## 已知限制

- `model-en-mixed.bin` 是英语训练,中文口型能动但不完美;精确中文口型需后端 Azure Speech SDK 出 viseme。
- `brunette.glb` 非商用授权,商用/公开前���替换(如 Ready Player Me 生成)。
- 加载方式:组件里 `import(/* webpackIgnore: true */ '/vendor/talkinghead/talkinghead.mjs')`(浏览器原生 ESM,不进 webpack)。
