# AuthMan 参考信息

## 服务接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/docs` | Swagger UI |
| GET | `/openapi.json` | 健康检查 / OpenAPI 描述 |
| GET | `/get` | 返回 Tokens 表全部记录 `{count, data}` |
| POST | `/refresh/{token_id}` | 手动刷新指定 token |
| GET | `/check/now` | 立即执行巡检（刷新临近过期 token） |
| GET | `/auth/{platform}` | OAuth 入口：无 code 时跳转授权页，带 code 时换 token 入库 |
| GET | `/admin` | SQLAdmin 后台（当前无认证） |

支持的平台 key：`baidu`、`xiaohongshu`、`qihoo`、`juliang`。

## 配置来源

- `DB_PATH`：SQLite 文件位置。本地默认 `<项目根>/data/tokens.db`，Docker 默认 `/data/tokens.db`。
- `CHECK_INTERVAL_MINUTES = 10`：巡检周期。
- `REFRESH_AHEAD_HOURS = 2`：提前刷新窗口。
- `ADMIN_SECRET` / `ADMIN_TITLE` / `ADMIN_BASE_URL`：后台配置，当前 hardcoded 在 `app/config.py`。

## 请求回调参数差异

- 百度：`authCode`、`userId`、`appId`、`timestamp`、`signature`。
- 小红书：`auth_code`，`state` 作为 `appId`。
- 360 / qihoo：`state` 作为 `appId`，额外从数据库取 `userName`、`password`。
- 巨量 / juliang：`app_id`，`state` 不用。
- 通用：`code`、`state`、`error`、`error_description`。

## 故障排查

- **端口被占用**：`serve` 自动从请求端口起顺延 50 个；也可显式换端口或用 `stop --port` 结束旧进程。
- **pip 缺包**：默认阿里云源，失败自动回退 PyPI；可 `--mirror https://pypi.org/simple`。离线时先手动装好依赖再 `--no-install`。
- **Python 版本**：建议 3.10+（项目使用了 `str | int` 类型语法）。脚本会依次尝试 `AUTHMAN_PYTHON`、`--python`、当前解释器、`py -3.12/3.11/3.10`。
- **数据库为空**：`/get` 返回 `{"count":0,"data":[]}` 属正常，需通过 `/auth/{platform}` 完成授权后写入。
- **Docker 构建**：镜像内不安装本地 `.venv`，数据库在 `/data`；本地文件不会污染镜像（见 `.dockerignore`）。
