# 第三方媒体工作台接入说明

本模块把供应商配置与用户创作界面分开：教师在配置页绑定 RunningHub 工作流或 GRS AI 模型，普通用户只需要上传素材、填写提示词并查看结果。

## 页面与职责

| 页面 | 用途 | 用户需要理解的内容 |
| --- | --- | --- |
| `/media-studio` | 两个工作台入口 | 选择“克隆音频”或“图生图” |
| `/media-studio/audio-clone` | RunningHub 音色克隆 | 合成文本、参考音色、可选情绪参考 |
| `/media-studio/image-to-image` | GRS AI 图生图 | 参考图片、修改要求、画幅和尺寸 |
| `/media-studio/configuration` | 教师配置中心 | 工作流版本、节点映射、GRS AI 模型和默认参数 |

配置页只对教师开放。API Key 不保存在浏览器或数据库中，只从后端 / Worker 环境变量读取。

## 数据与存储边界

- `media_workbench_configs`：两个固定工作台的供应商、模型、工作流版本与用户输入映射。
- `media_generations`：一次媒体生成业务请求，通过 `workbench_slug` 标记来源工作台。
- `provider_task_runs`：供应商任务 ID、原始状态、轮询次数、脱敏请求快照和错误信息。
- `media_assets`：输入/输出资产；`managed` 为 MinIO 受管资产，`external` 为供应商 URL。
- `workflow_templates` / `workflow_template_versions`：RunningHub 工作流稳定标识、不可变 JSON 版本及二次配置。
- `ai_tasks`：平台统一异步任务，媒体任务类型为 `media_generation.run`。

存储策略是明确的业务约束：

- GRS AI 输入图片先存 MinIO，Worker 提交时临时编码成 data URL；Base64 不写入数据库。
- GRS AI 输出在成功后立即下载并转存 MinIO，避免供应商临时 URL 失效。
- RunningHub 输入文件由 Worker 从 MinIO 读取并上传到 RunningHub。
- RunningHub 输出按需求不转存，只保存查询结果中的外部 URL。

## 工作台配置驱动的运行链路

```text
用户输入
  -> POST /api/media-workbenches/{slug}/runs
  -> 校验工作台启用状态、素材类型与开放参数
  -> 按配置映射为 GRS AI 参数或 RunningHub nodeInfoList
  -> 写入 media_generations / provider_task_runs / ai_tasks
  -> Redis 入队
  -> Worker 提交并轮询供应商
  -> GRS AI 转存 MinIO / RunningHub 登记外部 URL
  -> 前端按 workbench_slug 轮询并展示结果
```

用户接口不会接收任意供应商参数：只有教师在 `exposed_parameter_keys` 中明确开放的字段才能从工作台提交，其他工作流参数沿用已发布版本的默认值。

## GRS AI 图生图

图生图工作台固定使用 GRS AI Unified API：

- 提交：`POST {GRSAI_BASE_URL}/v1/api/generate`
- 查询：`GET {GRSAI_BASE_URL}/v1/api/result?id={taskId}`
- 关键参数：`model`、`prompt`、`images`、`aspectRatio`、`imageSize`、`replyType`

Unified API 的 `replyType` 支持 `json`、`stream` 和 `async`。本项目固定使用
`async`：创建请求立即返回任务 ID，Worker 使用全新的 HTTP 请求轮询结果；不要把
`json` 模式返回的同步任务 ID 再交给异步结果接口，否则可能得到 `result not exist`。
GRS AI 默认每 15 秒查询一次，最多查询 400 次（约 100 分钟），成功后立即把临时结果
下载并转存 MinIO。`violation`、任务失败和结果过期都会作为明确终态落库，不再无限轮询。

当前配置页提供 `nano-banana-fast`、`nano-banana-2-lite`、`nano-banana-2` 和 `nano-banana-pro`。模型列表应随 GRS AI 公告调整，不再使用已下线的 `nano-banana`。

参考资料：

- [GRS AI Unified 生图/编辑接口](https://qmy27nhsd9.apifox.cn/452392911e0)
- [GRS AI Unified 结果查询接口](https://qmy27nhsd9.apifox.cn/452409577e0)
- [GRS AI 平台公告](https://grsai.ai/zh/dashboard/announcements)

通用底层接口 `POST /api/media-generations` 仍保留 legacy 兼容能力；面向用户的“图生图”工作台不会走旧版 `/v1/draw/nano-banana`。

## RunningHub 工作流

导入接口 `POST /api/runninghub/workflows/import` 接收 ComfyUI **API 格式** JSON。自动识别规则：

- `LoadImage`、`LoadAudio`、`LoadVideo` 识别为文件输入；
- `[nodeId, outputIndex]` 识别为连线，不暴露为运行参数；
- 字符串、数字、布尔字面量识别为可配置参数；
- `Save*` / `Preview*` 节点识别为输出；
- 标题带 `DEPRECATED` 的输出默认禁用。

导入后形成草稿版本。教师可以修改用户名称、参数类型、显示位置、必填状态与输出定义，然后保存并发布。原始 JSON 与哈希不可覆盖；工作流结构变化时应作为新版本再次导入。

JSON 用于识别节点，但 RunningHub 高级任务接口还要求平台 `workflowId`。可在导入时填写，也可通过 `PUT /api/runninghub/workflows/{template_id}` 补录。克隆音频工作台只能绑定已发布版本，并且必须完成：

1. 合成文本到一个文本参数的映射；
2. 参考音色到一个文件参数的映射；
3. 可选情绪参考到第二个文件参数的映射；
4. 需要对用户开放的高级参数勾选。

真实任务执行顺序：

1. 上传绑定文件到 `/openapi/v2/media/upload/binary`；
2. 组装 `workflowId + nodeInfoList` 并提交 `/task/openapi/create`；
3. 轮询 `/openapi/v2/query`；
4. 将 `results[].url` 保存为 `external` 媒体资产。

RunningHub 当前文件上传接口支持的音频格式为 MP3、WAV、FLAC。克隆音频工作台会在任务入队前校验扩展名，避免异步任务提交后才发现格式不受支持。Worker 不会把 MinIO 的 socket 响应直接作为 multipart 文件发送，而是分块暂存到可定位文件并核对资产记录大小，再由 httpx 计算准确的 multipart `Content-Length`；这也避免了大文件一次性读入内存。供应商接口可能使用 HTTP 200 返回非零业务 `code`，适配器会将其立即转换为失败状态，不再持续无效轮询。

参考资料：[RunningHub API 文档](https://www.runninghub.cn/runninghub-api-doc-cn/api-425749013)。

## 主要后端接口

- `GET /api/media-providers`：供应商配置状态、能力、模型和存储策略。
- `GET /api/media-workbenches`：两个工作台及配置完整度，不返回密钥。
- `GET /api/media-workbenches/{slug}`：工作台运行表单定义。
- `PUT /api/media-workbenches/{slug}/configuration`：教师保存工作台绑定。
- `POST /api/media-workbenches/{slug}/runs`：按已保存配置创建任务。
- `POST /api/media-assets/upload`：上传媒体输入到 MinIO。
- `GET /api/media-generations?workbench_slug=...`：按工作台查询当前账号结果。
- `POST /api/media-generations/{id}/refresh`：立即请求一次轮询。
- `POST /api/media-generations/{id}/cancel`：停止本地后续处理。
- `POST /api/runninghub/workflows/import`：导入并自动识别 JSON。
- `PUT /api/runninghub/workflow-versions/{id}/configuration`：二次配置草稿。
- `POST /api/runninghub/workflow-versions/{id}/publish`：发布不可变版本。

## 本地安全验证与真实模式

`.env` 使用 `MEDIA_MOCK_MODE=true` 时不会访问第三方或产生费用。Mock 仍执行数据库状态变化、Redis 调度与媒体资产写入，因此可以验证完整链路。

切换真实模式前：

1. 配置 `GRSAI_API_KEY`、`GRSAI_BASE_URL`、`RUNNINGHUB_API_KEY` 和 `RUNNINGHUB_BASE_URL`；
2. 将 `MEDIA_MOCK_MODE=false`；
3. 在教师配置页确认两个供应商显示“服务端密钥已配置”；
4. 先分别提交一条低成本任务做冒烟验证。

本项目开发期使用 SQLAlchemy `create_all` 建表，同时通过 `app_schema_migrations` 执行小范围幂等增量迁移。已有数据库启动新版后会自动为 `media_generations` 补充 `workbench_slug` 和索引，不需要删除 Docker 数据卷。正式生产部署仍建议引入 Alembic 管理后续复杂结构变更。
