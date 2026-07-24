# 阿里云百炼 Wan 2.7 图生视频接入说明

## 1. 当前方案

媒体工作台的视频生成已经从 GRS AI Veo 迁移到阿里云百炼
`wan2.7-i2v-2026-04-25`。现有页面地址和 API 路径继续保留 `/media-studio/veo`，
避免已有书签、反向代理和前端调用在升级时失效；路径名称不再代表真实供应商。

GRS AI 图生图与 RunningHub 克隆音频保持原样，本次迁移只替换视频供应商。

百炼官方参考：

- [视频模型选择与迁移建议](https://help.aliyun.com/zh/model-studio/video-generate-edit-model)
- [Wan 2.7 图生视频 API](https://help.aliyun.com/zh/model-studio/image-to-video-general-api-reference)

## 2. 已接入能力

| 能力 | 当前支持情况 |
| --- | --- |
| 模型 | `wan2.7-i2v-2026-04-25` |
| 输入 | 首帧，或首帧 + 尾帧 |
| 图片来源 | 本地上传后生成限时公网短链，或直接填写公网 URL |
| 分辨率 | `720P`、`1080P` |
| 时长 | 2–15 秒 |
| 画幅 | 跟随首帧图片比例 |
| 调用方式 | 创建异步任务后，每 12 秒由页面触发一次状态查询 |
| 本地任务记录 | Redis 保留 24 小时 |
| 供应商结果地址 | 约 24 小时有效，成功后应尽快下载 |

参考生视频、驱动音频、视频续写和结果自动转存暂未开放。参考生视频属于
`wan2.7-r2v` 的独立能力，不应把参数混入当前 I2V 请求。人物图片动作模仿已通过独立的
`wan2.2-animate-move` 工作台接入，配置与接口见
[`wan-motion-transfer-integration.md`](wan-motion-transfer-integration.md)。

## 3. 环境变量

```env
# 建议使用华北 2（北京）地域的独立视频 API Key。
DASHSCOPE_API_KEY=

# 可使用公共根地址；生产环境也可填写同地域业务空间专属域名。
# 不要填写 QWEN_BASE_URL 中的 /compatible-mode/v1 路径。
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com

# 本地上传图片时必填，必须是百炼能访问的 HTTPS 后端根地址。
VIDEO_PUBLIC_BASE_URL=https://your-domain.example.com

VIDEO_TIMEOUT_SECONDS=30
VIDEO_MOCK_MODE=false
VIDEO_IMAGE_MAX_UPLOAD_MB=20
```

如果使用业务空间专属域名，应填写：

```env
DASHSCOPE_BASE_URL=https://你的WorkspaceId.cn-beijing.maas.aliyuncs.com
```

模型、Endpoint 与 API Key 必须属于同一地域。建议为视频服务创建独立 Key，不要自动复用
`QWEN_API_KEY`，这样更方便分别统计费用、设置权限和轮换密钥。

升级期间，后端仍兼容旧 `GRSAI_PUBLIC_BASE_URL`、`GRSAI_TIMEOUT_SECONDS`、
`GRSAI_MOCK_MODE` 和 `GRSAI_IMAGE_MAX_UPLOAD_MB` 作为 `VIDEO_*` 的临时回退；新部署应改用
上面的新变量。`DASHSCOPE_API_KEY` 没有旧变量回退，必须显式配置。

## 4. 供应商请求映射

创建任务：

```text
POST {DASHSCOPE_BASE_URL}/api/v1/services/aigc/video-generation/video-synthesis
X-DashScope-Async: enable
Authorization: Bearer <DASHSCOPE_API_KEY>
```

核心请求体：

```json
{
  "model": "wan2.7-i2v-2026-04-25",
  "input": {
    "prompt": "镜头缓慢推近，演员自然转身",
    "media": [
      {"type": "first_frame", "url": "https://example.com/first.png"},
      {"type": "last_frame", "url": "https://example.com/last.png"}
    ]
  },
  "parameters": {
    "resolution": "720P",
    "duration": 5,
    "prompt_extend": true,
    "watermark": false
  }
}
```

查询任务：

```text
GET {DASHSCOPE_BASE_URL}/api/v1/tasks/{task_id}
Authorization: Bearer <DASHSCOPE_API_KEY>
```

平台会把百炼的 `PENDING`、`RUNNING`、`SUCCEEDED`、`FAILED`、`CANCELED` 和 `UNKNOWN`
映射为前端统一状态。失败响应中的 `code` 与 `message` 会展示给当前任务创建者，API Key、
供应商任务 ID 和 MinIO 对象键不会返回浏览器。

## 5. 项目接口

为兼容现有前端，路径暂不改名：

| 接口 | 用途 |
| --- | --- |
| `GET /api/media-studio/veo/options` | 查询 Wan 模型、分辨率、时长、上传限制与配置状态 |
| `POST /api/media-studio/veo/tasks` | 上传首尾帧或提交公网 URL，创建百炼异步任务 |
| `GET /api/media-studio/veo/tasks` | 查询当前账号最近 12 条视频任务 |
| `GET /api/media-studio/veo/tasks/{task_id}` | 查询一次百炼状态并返回归一化结果 |
| `GET /api/public/media-studio/veo-inputs/{token}` | 供应商限时回源图片，不进入 OpenAPI 文档 |

Wan 2.7 不接受独立画幅参数。接口仍接受旧前端可能提交的 `aspect_ratio` 字段，但新任务统一
记录为 `auto`。要生成 9:16 竖屏视频，必须上传 9:16 首帧，不能只修改页面参数。

## 6. Docker 部署更新

更新服务器 `.env` 后，需要重新创建后端容器才能读取新变量：

```bash
sudo docker compose -f docker-compose.yml -f compose.production.yml \
  up -d --no-build --force-recreate backend
```

如果本次同时发布了前端新镜像，应更新 `IMAGE_TAG`、拉取新镜像，再同时重建 backend 与
frontend。首次真实验证建议使用原创、无敏感内容的小图，选择 `720P` 和 5 秒，避免一开始
使用高成本规格。

## 7. 安全要求

- API Key 只写入服务器 `.env`，不得提交 Git、截图或发送到聊天记录。
- 已经泄露过的 Qwen、GRS AI 或百炼 Key 必须在供应商控制台撤销后重新创建。
- `VIDEO_PUBLIC_BASE_URL` 应使用 HTTPS；临时图片地址带签名、对象目录限制和过期时间。
- 失败任务是否计费以百炼控制台账单为准，生产环境应开启余额告警与调用日志审计。
