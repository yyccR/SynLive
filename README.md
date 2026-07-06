# SynLive

AI 数字人直播中控平台原型。

## 本地启动

如果你的终端没有 `pnpm`，直接使用 npm 即可：

```bash
cd /Users/yangcheng/PycharmProjects/SynLive
npm run dev
```

启动成功后打开：

```text
http://localhost:3000
```

如果 3000 端口被占用，可以换端口：

```bash
npm run dev -- --port 3001
```

然后打开：

```text
http://localhost:3001
```

## 可选：使用 Corepack 运行 pnpm

macOS 上如果 `pnpm` 提示 command not found，但有 `corepack`，可以这样运行：

```bash
corepack pnpm dev
```

也可以尝试启用 pnpm shim：

```bash
sudo corepack enable pnpm
```

启用后再运行：

```bash
pnpm dev
```

## 页面入口

- 官网首页：http://localhost:3000/
- 工作台：http://localhost:3000/app
- 直播中控：http://localhost:3000/app/live
- 数字人资产：http://localhost:3000/app/avatars
- 脚本编排：http://localhost:3000/app/scripts
- 知识库问答：http://localhost:3000/app/knowledge
- 多平台推流：http://localhost:3000/app/platforms
- 场控与风控：http://localhost:3000/app/moderation
- 数据报表：http://localhost:3000/app/reports
- 年度服务：http://localhost:3000/app/services
- 文档入口：http://localhost:3000/docs

## 校验命令

```bash
npm run typecheck
npm run build
```

## 官网视觉素材

首页使用的图片和视频素材放在：

```text
public/assets/
```

当前包含：

- `hero-live-studio-poster.png`：Hero 区静态真实感主视觉
- `product-live-control.png`：直播中控真实感预览图
- `product-script-timeline.png`：脚本时间线预览图
- `product-stream-health.png`：推流健康预览图
- `solution-commerce.png`：电商直播方案图
- `solution-education.png`：教育培训方案图
- `solution-finance.png`：金融服务方案图
- `solution-gov.png`：政企宣传方案图

如果需要重新生成辅助素材：

```bash
python3 scripts/generate_marketing_assets.py
```

注意：Hero 主视觉和 `product-live-control.png` 当前由 GPT Image 生成，辅助脚本不会覆盖它们。

## 后端 & 一键启动

后端代码与文档在 `apps/api/`（FastAPI，已接入 Azure TTS + LiteLLM/GPT + LiveTalking 客户端）。基础设施编排、数字人渲染部署在 `infra/`。

### 一键脚本

```bash
# 1) 启动后端 docker 栈（postgres/redis/qdrant/minio/srs/api），自动生成 .env
#    可选提前 export AZURE_SERVICE_KEY / LITELLM_LLM_API_KEY 自动注入密钥
./scripts/start.sh
./scripts/start.sh --with-frontend   # 顺带起 Next.js 前端 :3000

# 2) 停止（保留数据）；--purge 连数据一起清
./scripts/stop.sh

# 3) 在 GPU 机器上部署 LiveTalking（渲染节点，跨机接入）
AZURE_SPEECH_KEY=xxxx SRS_HOST=<SynLive主机IP> ./scripts/deploy-livetalking.sh
```

更多见 `apps/api/README.md` 与 `infra/livetalking/README.md`。
