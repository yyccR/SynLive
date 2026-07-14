# UE5 + MetaHuman + Pixel Streaming 部署手册（A 线，verbatim 模式）

SynLive 的 3D 数字人渲染节点，**verbatim（逐字复述）模式**：数字人原样说出 SynLive 给的文本。
本手册面向 **UE 工程侧（A 线）**：MetaHuman 跑起来 + Azure TTS 音频驱动口型 + Pixel Streaming 推流。

> 版本固定：**UE 5.5**（别用 5.6——ACE/Audio2Face 在 5.6 有已知 bug）。前端库 `@epicgames-ps/lib-pixelstreamingfrontend-ue5.5`。

---

## 0. 架构与对接契约

```
浏览器(Next.js)
  │  WebRTC(video+audio)                  ▲
  │  ← Pixel Streaming 直连 ──────────────┤  画面+语音回传
  │                                       │
  │  emitUIInteraction({type:'SayAudio', audio, text})
  │  ──── Pixel Streaming datachannel ───►│  UE 蓝图 OnPixelStreamingInputEvent
  │                                          │ ▼ RuntimeAudioImporter 解码 → audio component 播放
  │                                          │   + OVRLipSync 驱动 MetaHuman 口型
  ▼                                       MetaHuman 开口（音频也经 Pixel Streaming 回传）
SynLive FastAPI 后端   /say、/answer：Azure TTS 合成精确音频(mp3) → base64 返回前端
```

**对接契约（B 线 ↔ A 线的接口）**：SynLive 后端用 Azure TTS 合成文本的精确 mp3，base64 后经 datachannel 发：

```js
ps.emitUIInteraction({ type: 'SayAudio', audio: '<mp3 base64>', text: '同步文本' });
```

UE 侧蓝图：收 `SayAudio` → 用 **RuntimeAudioImporter** 把 base64 mp3 解码成 USoundWave → audio component 播放 → **OVRLipSync** 分析该音频驱动 MetaHuman 口型。音频同时经 Pixel Streaming 回传浏览器（用户听到）。

> **为什么 verbatim（Azure TTS + OVRLipSync）、不用 Convai**：Convai 的 `Invoke Speech` 把文本当 context 喂给它自己的 LLM 再回应——**非逐字复述**，不适合 SynLive 的精确播报/客服。Azure TTS 是标准 TTS、逐字精确，且 SynLive 后端已有。代价：UE 侧要接 OVRLipSync（口型）+ RuntimeAudioImporter（运行时解码），比 Convai 多两个插件——见 Step 2/3。

> **POC 限制**：emitUIInteraction 走文本 datachannel，单条消息有大小限制（~16KB），适合短播报；长文本后续可改 Pixel Streaming 的 audio input（mic）通道或分片。

---

## 1. 前置

- **显卡**：NVIDIA，MetaHuman + 1080p 推荐 **12–16 GB**（3090/4090/A10）。必须 NVIDIA（NVENC 硬编）。
- **UE 5.5**（Epic Launcher）。
- **插件**：
  - **MetaHuman**（MetaHuman Creator 配套）
  - **Pixel Streaming**（UE 自带）
  - **OVRLipSync**（Meta，免费）—— 音频→口型 viseme
  - **RuntimeAudioImporter**（社区，免费，github 搜 `RuntimeAudioImporter`）—— 运行时从 byte 解码音频成 USoundWave

---

## 2. Step 1 · 捏 MetaHuman 形象

1. 打开 https://metahuman.unrealengine.com 捏写实人脸 → Quixel Bridge 导入 UE 工程。
2. 工程里拖 MetaHuman 进关卡，加摄像机对准脸（Pixel Streaming 推这个画面）。

---

## 3. Step 2 · OVRLipSync 接 MetaHuman

目标：让一段音频能驱动 MetaHuman 的嘴型。

1. 启用 OVRLipSync 插件。
2. 给 MetaHuman 加 **OVRLipSync Actor Component**，绑定到 MetaHuman 的面部骨骼/morph（OVRLipSync 输出 viseme curve → 驱动嘴部）。
3. 配一个 **Audio Component**：OVRLipSync 监听它的输出做口型分析；播放音频时口型自动跟。

> OVRLipSync ↔ MetaHuman 的具体接法（viseme → MetaHuman 面部曲线/控制板映射）以 OVRLipSync 插件文档和社区 MetaHuman 集成教程为准。OVRLipSync 官方有 MetaHuman 示例。

---

## 4. Step 3 · UE 蓝图收 SayAudio（对接 B 线，关键）

目标：前端发 `{type:'SayAudio', audio, text}` → UE 蓝图解码 mp3 → 播放 → OVRLipSync 驱动口型。

1. Actor 加 **Pixel Streaming Input** 组件 → 右键 **Bind Event to On Input Event** → 自定义事件，输出 Descriptor（JSON 字符串）。
2. 事件体：
   - `Load Json from String` / `Get Json Object from String` 解析 Descriptor → 取 `type`、`audio`、`text`。
   - 判断 `type == "SayAudio"`：
     - **RuntimeAudioImporter** 的节点（如 `Audio From Bytes` / `Import Audio from Data`）把 `audio`（base64 → byte）解码成 **USoundWave**。
     - 把 USoundWave 喂给 Step 2 的 **Audio Component** 播放 → OVRLipSync 自动驱动 MetaHuman 口型。
   - 兜底 `type == "SayText"`（无音频）：可忽略，或走日志。
3. 自测：前端 console `ps.emitUIInteraction({type:'SayAudio', audio:'<base64>', text:'测试'})` → MetaHuman 开口 + 有声。

> 参考：Pixel Streaming 收 descriptor 节点链见 https://blueprintue.com/blueprint/-k0zc42y/ ；RuntimeAudioImporter 节点见其仓库 README。

---

## 5. Step 4 · Pixel Streaming 打包 + SignalingServer

1. 项目设置 → Pixel Streaming → 勾 `Use Signalling Server`（默认 :8888）。
2. 打包（Package Project）或先 Standalone Game 跑。
3. 起 SignalingServer（Epic 官方，github `EpicGames/PixelStreamingInfrastructure`）：
   ```bash
   node cirrus.js --HttpPort 8888 --StreamerPort 8889
   ```
4. 启动 UE 连信令：
   ```bash
   ./SynLiveUE.sh -RenderOffScreen -AudioMixer -PixelStreamingIP=127.0.0.1 -PixelStreamingPort=8889 -AllowPixelStreamingCommands
   ```

---

## 6. Step 5 · 并发模式 + TURN

- **单 UE 实例 + 多 viewer**（SynLive 直播场景）：一个 UE 进程推流，N 个浏览器观看。
- **不要** 每浏览器一个 UE 进程（16GB 卡只能 1 路）。
- 跨网/复杂 NAT：浏览器→SignalingServer `ws://host:8888`；WebRTC 媒体穿不过 NAT 时配 **TURN**（coturn）。

---

## 7. Step 6 · 与 SynLive 串通（填 .env）

```bash
RENDERER_BACKEND=unreal
NEXT_PUBLIC_RENDERER_BACKEND=unreal
NEXT_PUBLIC_PIXELSTREAMING_URL=ws://<ue-host>:8888
UE_RENDER_URL=    # verbatim 模式不用（驱动是 Azure 音频经前端 datachannel 发）
```

填完重启 SynLive 后端 + 前端。

---

## 8. 验证清单

- [ ] Step 2：UE 里给 Audio Component 喂一段音频 → MetaHuman 嘴动。
- [ ] Step 3：前端 emitUIInteraction SayAudio（带真 base64 mp3）→ MetaHuman 开口 + 有声。
- [ ] Step 4：浏览器开 `http://<ue-host>:8888` 看到 UE 画面。
- [ ] 串通：SynLive `/app/live` → 点「连接数字人」看到 MetaHuman → 点「让数字人说」/「提问」→ MetaHuman **逐字**开口 + 有声。
- [ ] 降级：`.env` 改 `RENDERER_BACKEND=livetalking`、`NEXT_PUBLIC_RENDERER_BACKEND=livetalking`，切回旧 2D 链路。

---

## 备注

- **为什么 verbatim**：见 Section 0（Convai Invoke Speech 非逐字；Azure TTS 逐字精确）。
- **UE 侧工程量**：比 Convai 方案多 OVRLipSync + RuntimeAudioImporter 两个插件及其集成，是 verbatim 的代价。Convai 方案（对话式、非逐字）仍可作备选（改 renderer + 蓝图回 Invoke Speech）。
- **Audio2Face 已停更**：用 OVRLipSync 替代 deprecated 的 NVIDIA Audio2Face-3D。
