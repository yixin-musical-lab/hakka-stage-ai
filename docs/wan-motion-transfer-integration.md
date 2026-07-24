# 阿里云百炼 Wan 2.2 动作模仿接入说明

## 1. 当前方案

媒体工作台新增独立的“动作模仿”入口，固定调用阿里云百炼
`wan2.2-animate-move`。输入一张单人人物图片和一段参考动作视频，输出保留图片人物与
背景、迁移参考视频动作和表情的 720P 视频。

该能力直接调用百炼原生异步接口，不经过 RunningHub，也不与现有 Wan 2.7 图生视频的
提示词、首尾帧参数混用。

官方参考：

- [万相图生动作 API](https://help.aliyun.com/zh/model-studio/wan-animate-move-api)
- [视频生成与编辑模型选择](https://help.aliyun.com/zh/model-studio/video-generate-edit-model)
- [百炼模型计费](https://help.aliyun.com/zh/model-studio/model-pricing)

## 2. 能力与素材限制

| 项目 | 当前支持情况 |
| --- | --- |
| 模型 | `wan2.2-animate-move` |
| 输入 | 一张人物图片 + 一段参考动作视频 |
| 模式 | `wan-std` 标准模式、`wan-pro` 专业模式 |
| 输出 | 720P、MP4（H.264） |
| 图片 | JPG/JPEG/PNG/BMP/WEBP，最大 5MB，宽高 200～4096px |
| 视频 | MP4/AVI/MOV，最大 200MB，2～30 秒，宽高 200～2048px |
| 宽高比 | 图片和视频均为 1:3～3:1 |
| 状态查询 | 页面每 15 秒查询一次当前未完成任务 |
| 任务记录 | Redis 按账号隔离并保留约 24 小时 |
| 结果 | 成功后优先转存私有 MinIO，并通过鉴权接口播放或下载 |

标准模式默认选中，输出约 15fps；专业模式约 25fps。页面显示的费用只用于提交前估算，
最终价格和计费结果以百炼控制台账单为准。水印默认开启，用户可在确认素材授权后关闭。

## 3. 环境变量

动作模仿复用现有百炼视频密钥、API 根地址、公网回源地址和 Mock 开关，只增加独立的素材
与结果体积限制：

```env
# 建议使用华北 2（北京）地域的独立视频 API Key。
DASHSCOPE_API_KEY=

# 可使用公共根地址；生产环境推荐填写同地域业务空间专属域名。
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com

# 必须是百炼能够访问的 HTTPS 后端根地址，不能填写 MinIO 内网地址。
VIDEO_PUBLIC_BASE_URL=https://video.example.com

VIDEO_TIMEOUT_SECONDS=30
VIDEO_MOCK_MODE=false

MOTION_IMAGE_MAX_UPLOAD_MB=5
MOTION_VIDEO_MAX_UPLOAD_MB=200
MOTION_RESULT_MAX_DOWNLOAD_MB=500
```

业务空间专属域名示例：

```env
DASHSCOPE_BASE_URL=https://你的WorkspaceId.cn-beijing.maas.aliyuncs.com
```

`DASHSCOPE_API_KEY`、业务空间域名和模型部署地域必须一致。`VIDEO_PUBLIC_BASE_URL` 用于百炼
回源读取本地上传素材，因此真实模式下密钥和公网地址必须同时配置；纯本地联调应使用
`VIDEO_MOCK_MODE=true`，不会向供应商提交任务。

## 4. 百炼请求映射

创建任务：

```text
POST {DASHSCOPE_BASE_URL}/api/v1/services/aigc/image2video/video-synthesis
X-DashScope-Async: enable
Authorization: Bearer <DASHSCOPE_API_KEY>
Content-Type: application/json
```

核心请求体：

```json
{
  "model": "wan2.2-animate-move",
  "input": {
    "image_url": "https://video.example.com/api/public/media-studio/motion-inputs/<token>",
    "video_url": "https://video.example.com/api/public/media-studio/motion-inputs/<token>",
    "watermark": true
  },
  "parameters": {
    "check_image": true,
    "mode": "wan-std"
  }
}
```

查询任务：

```text
GET {DASHSCOPE_BASE_URL}/api/v1/tasks/{task_id}
Authorization: Bearer <DASHSCOPE_API_KEY>
```

成功响应的视频地址位于 `output.results.video_url`，该地址通常只保留 24 小时。后端在首次
读到 `SUCCEEDED` 时立即尝试流式下载并转存 MinIO；转存失败不会把已成功的生成任务改成
失败，而是保留供应商临时地址并提醒用户及时下载。

## 5. 项目接口

| 接口 | 用途 |
| --- | --- |
| `GET /api/media-studio/motion-transfer/options` | 查询模式、素材限制和服务端配置状态 |
| `POST /api/media-studio/motion-transfer/tasks` | 上传人物图片和动作视频，创建百炼异步任务 |
| `GET /api/media-studio/motion-transfer/tasks` | 查询当前账号最近 12 条任务 |
| `GET /api/media-studio/motion-transfer/tasks/{task_id}` | 查询一次百炼状态，成功后触发结果转存 |
| `GET /api/media-studio/motion-transfer/tasks/{task_id}/result` | 鉴权播放或下载结果，支持单段 HTTP Range |
| `GET /api/public/media-studio/motion-inputs/{token}` | 供百炼限时回源，不进入 OpenAPI 文档 |

创建接口使用 `multipart/form-data`，包含 `person_image`、`motion_video`、`mode`、
`watermark`、`motion_duration_seconds` 和 `rights_confirmed`。未确认人物肖像与参考视频授权时
拒绝提交。

## 6. 存储与安全边界

1. 后端先校验文件名、扩展名、浏览器媒体类型和文件大小，再把二进制流写入私有 MinIO。
2. 回源 JWT 只允许访问 `media-studio/motion-inputs/` 前缀，包含签发方、受众和两小时过期时间。
3. 百炼任务 ID、账号 ID、MinIO 对象键和密钥只保存在服务端，不进入 API 响应。
4. 任务读取先校验当前账号归属；未知任务和越权任务统一返回 404。
5. 任务完成或失败后幂等删除输入素材；结果对象建议配置 MinIO 前缀生命周期，避免长期堆积。
6. 任务记录仅保留约 24 小时，当前版本不把结果登记为永久媒体资产，重要视频应及时下载。

## 7. 验证与上线

无计费验证：

```powershell
$env:VIDEO_MOCK_MODE='true'
python -m unittest discover -s tests -v
npm run build
docker compose config --quiet
```

Mock 模式应验证人物图与视频上传、任务轮询、账号隔离、OpenAPI、Range 播放响应和页面在桌面/
移动宽度下的布局。Mock 任务不会生成真实视频，因此结果区域显示完成状态但不提供下载。

真实验证只使用一组已授权、无敏感内容的 2～3 秒素材，先选择 `wan-std`。同一个任务只轮询
结果，不能为获取状态重复创建任务。确认结果已转存和可播放后即停止测试，并在百炼控制台
核对调用日志与费用。

本机 RTX 3060 只承担前后端联调，不运行或部署 Wan 模型；批量生成与正式压力测试应在云端
服务侧完成。
