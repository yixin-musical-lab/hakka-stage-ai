# GRS AI Veo 图生视频调研与接入说明

> 历史说明：GRS AI Veo 通道已停止用于当前项目。现行视频生成方案为阿里云百炼
> `wan2.7-i2v-2026-04-25`，请阅读 [Wan 2.7 图生视频接入说明](./wan-video-integration.md)。
> 本文仅用于解释旧任务和旧环境变量，不应再作为新部署配置依据。

调研日期：2026-07-23

## 1. 平台能力概览

GRS AI 是聚合式模型 API 平台，公开页面覆盖文本、识图、图像生成 / 编辑与视频生成；当前公开展示的模型族包括 GPT Image、Nano Banana / Gemini Image、Gemini 文本模型、Flux 与 Veo。平台控制台还提供：

- API Key 创建与额度管理；
- 模型列表、可用状态、积分消耗与价格示例；
- 调用日志、任务 ID、提示词、请求参数、结果与耗时查询；
- 充值、订单、积分消耗查询；
- 阿里云 OSS、腾讯云 COS、Cloudflare R2、七牛云存储库配置；
- 在线体验、旧版接口文档、公告与帮助中心。

公开资料：

- [GRS AI 首页](https://grsai.com/zh)
- [GRS AI 模型列表](https://grsai.com/zh/dashboard/models)
- [GRS AI 平台公告](https://grsai.com/zh/dashboard/announcements)
- [GRS AI Veo 文档](https://grsai.com/zh/dashboard/documents/veo)

平台在 2026-05-08 公告了统一生成接口 `/v1/api/generate`，主要解决不同图片模型端点和参数不一致的问题；Veo 页面当前仍明确使用独立视频端点，因此本项目没有把图片 Unified API 参数混入 Veo 请求。

## 2. Veo 接口契约

### 2.1 节点与鉴权

| 项目 | 当前公开值 |
| --- | --- |
| 海外节点 | `https://grsaiapi.com` |
| 国内直连节点 | `https://grsai.dakka.com.cn` |
| 鉴权 | `Authorization: Bearer <API_KEY>` |
| 请求类型 | `Content-Type: application/json` |

项目默认使用国内直连节点，但通过 `GRSAI_BASE_URL` 保持可切换。

### 2.2 创建任务

`POST /v1/video/veo`

| 字段 | 必填 | 本次接入 | 说明 |
| --- | --- | --- | --- |
| `model` | 是 | 是 | 当前参数表列出 `veo3.1-fast`、`veo3.1-pro` |
| `prompt` | 是 | 是 | 视频内容、动作、镜头和氛围描述 |
| `firstFrameUrl` | 图生视频必填 | 是 | 首帧公网地址 |
| `lastFrameUrl` | 否 | 是 | 需搭配首帧使用 |
| `urls` | 否 | 暂不开放 | Fast 最多三张参考图，不能与首尾帧混用 |
| `aspectRatio` | 否 | 是 | `16:9` 或 `9:16`，默认 `16:9` |
| `webHook` | 否 | 固定 `-1` | `-1` 表示立即返回任务 ID，由调用方轮询 |
| `shutProgress` | 否 | 固定 `true` | 关闭流式进度，本项目统一通过结果接口查询 |

GRS AI 默认采用流式响应；如果填写普通 webhook，会把进度和最终结果 POST 到回调地址。本项目不引入公网回调服务，选择官方明确支持的 `webHook="-1"` 模式。

创建响应示意：

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "id": "provider-task-id"
  }
}
```

### 2.3 查询结果

`POST /v1/draw/result`

请求：

```json
{
  "id": "provider-task-id"
}
```

核心结果字段：

| 字段 | 说明 |
| --- | --- |
| `id` | 供应商任务 ID |
| `url` | 成功视频 URL，文档标注有效约 2 小时 |
| `progress` | 0-100 |
| `status` | `running` / `succeeded` / `failed` |
| `failure_reason` | `output_moderation`、`input_moderation` 或 `error` |
| `error` | 详细失败信息 |

查询接口外层 `code=0` 表示成功，`code=-22` 表示任务不存在。生成失败时 GRS AI 文档说明会返还积分，但具体账务仍应以平台日志和积分记录为准。

## 3. 本项目的接入设计

```text
浏览器 /media-studio
  -> 登录鉴权后的 FastAPI 代理
  -> 首尾帧暂存私有 MinIO
  -> 生成两小时有效的签名回源 URL
  -> GRS AI /v1/video/veo
  -> Redis 保存当前账号的任务归属与安全元数据
  -> 页面每 12 秒调用本项目任务查询接口
  -> FastAPI 代理 /v1/draw/result
```

安全与工程边界：

- `GRSAI_API_KEY` 只存在于后端环境变量，不进入前端、Redis、数据库或响应。
- 前端只拿项目自己的任务 ID；供应商任务 ID 不返回浏览器。
- Redis 记录账号归属，其他账号即使猜到任务 ID 也得到 404。
- 上传图片只允许 JPG、PNG、WEBP，默认最大 10MB；二进制写入 MinIO，Redis 只保存对象键。
- GRS AI 回源地址使用 JWT 签名并限时，不能遍历 MinIO 其他目录。
- 视频生成发生在云端，本机不运行视频模型，不占用 RTX 3060 显存。
- 当前成功视频仍是供应商临时 URL，页面明确提醒两小时内下载；自动转存 MinIO 可作为后续独立任务。

## 4. 新增接口

| 接口 | 用途 |
| --- | --- |
| `GET /api/media-studio/veo/options` | 查询模型、画幅、上传限制与配置状态 |
| `POST /api/media-studio/veo/tasks` | 上传首尾帧或提交公网 URL，创建异步任务 |
| `GET /api/media-studio/veo/tasks` | 查询当前账号最近 12 条任务 |
| `GET /api/media-studio/veo/tasks/{task_id}` | 查询一次供应商状态并返回归一化结果 |
| `GET /api/public/media-studio/veo-inputs/{token}` | GRS AI 限时回源图片，不出现在 OpenAPI 文档 |

## 5. 环境变量

```dotenv
GRSAI_API_KEY=
GRSAI_BASE_URL=https://grsai.dakka.com.cn
GRSAI_PUBLIC_BASE_URL=https://api.example.com
GRSAI_TIMEOUT_SECONDS=30
GRSAI_MOCK_MODE=false
GRSAI_IMAGE_MAX_UPLOAD_MB=10
```

`GRSAI_PUBLIC_BASE_URL` 必须是 GRS AI 能从公网访问到的后端根地址。纯本地 `localhost` 无法被供应商回源；本地联调可开启 `GRSAI_MOCK_MODE=true`，真实低成本冒烟应在有公网 HTTPS 地址的测试环境执行。

## 6. 后续建议

1. 成功后由 Worker 立即下载视频并转存 MinIO，消除两小时临时 URL 风险。
2. 把三张参考图设计成与“首尾帧”并列的独立输入模式，避免违反供应商互斥约束。
3. 任务量增大后把主动轮询迁移到 Worker 定时扫描，页面只查询本地状态。
4. 从 Redis 短期记录升级为数据库任务表，支持长期素材库、审计与按项目归档。
5. 在真实 API Key 和低成本账号下做一条 Fast 首帧冒烟；不要在本机批量生成视频。

