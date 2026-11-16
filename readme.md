# AuthMan

第三方平台 token 管理服务。用 FastAPI + SQLAdmin 管理百度、小红书、360、巨量等平台的 OAuth token：授权即入库，每 10 分钟巡检一次，临近过期或已失效的自动刷新，`/admin` 后台可查可改。

- 代码：`main.py` 与 `app/`
- 数据：本地 `data/tokens.db`，Docker 内 `/data/tokens.db`（由 `DB_PATH` 决定）
- 许可证：MIT，见 [LICENSE](LICENSE)
- 接口：`/docs` 看 Swagger，`/get` 取全量 token，`/auth/{platform}` 走 OAuth

## 在豆包安装 skill

直接下载 [`dist/authman-local-run-doubao.zip`](dist/authman-local-run-doubao.zip)，在豆包工作里上传为技能即可（`SKILL.md` 已放在 ZIP 根目录，description 为中文触发词）。

注意：技能包只含运行指南，**不含项目代码**。装好后先 clone 本仓库，再到仓库根目录执行技能里的命令；如果 skill 装在别处，用 `--repo "<仓库路径>"` 指定项目位置。

## 项目结构

```text
authman/
├── main.py                     # 入口：组装 app
├── requirements.txt
└── app/
    ├── __init__.py
    ├── config.py               # 所有常量
    ├── database.py             # engine / Base / Session 工具
    ├── models.py               # Token 模型
    ├── admin.py                # SQLAdmin 后台
    ├── platforms/
    │   ├── __init__.py         # 注册表 PLATFORM_REGISTRY
    │   ├── base.py             # BasePlatform 抽象
    │   ├── baidu.py
    │   ├── xiaohongshu.py
    │   ├── qihoo.py
    │   └── juliang.py
    ├── services/
    │   ├── __init__.py
    │   ├── tokens.py           # 刷新 / 字段抽取
    │   └── scheduler.py        # 定时巡检
    └── api/
        ├── __init__.py
        ├── public.py           # /get  /refresh/{id}  /check/now
        └── auth.py             # /auth/{platform}
```

## 本地运行（无需 Docker）

项目自带一个 agent skill，提供跨平台控制器 `scripts/authman_ctl.py`：

```bash
python .agents/skills/authman-local-run/scripts/authman_ctl.py serve --port 8000
```

- 首次运行会自动创建 `.venv`、安装依赖；数据库使用 `data/tokens.db`（由 `DB_PATH` 注入）。
- 默认监听 `0.0.0.0`（所有网卡），端口 8000，被占用时自动向上查找可用端口；启动后访问 `http://127.0.0.1:<port>/docs` 和 `/admin`。
- 其它命令：`prepare`（只装环境）、`status`（查状态）、`stop --port 8000`（停服务）。
- agent 调用 `serve` 时请使用后台任务方式。

### 跨 agent 兼容性

SKILL.md 是开放标准（`agentskills.io`），Claude Code、Codex CLI、Gemini CLI、Cursor、Windsurf、GitHub Copilot 等主流 agent 都支持这个格式。但它们**发现 skill 的目录不同**，所以同一个 skill 在仓库里放了多份入口：

| Agent | 自动发现的入口 |
|---|---|
| 通用 / Codex / Gemini CLI / 其它 | `.agents/skills/authman-local-run/` |
| Claude Code | `.claude/skills/authman-local-run/` |
| WorkBuddy | `.workbuddy/skills/authman-local-run/` |
| Cursor | `.cursor/rules/authman-local-run.mdc` |
| GitHub Copilot | `.github/copilot-instructions.md` |
| Windsurf | `.windsurfrules` |
| 其它只读 AGENTS.md 的 agent | 根目录 `AGENTS.md`（含完整命令与约束） |
| 豆包工作 | `dist/authman-local-run-doubao.zip`（上传技能包） |

**只需改一处**：编辑 `.agents/skills/authman-local-run/`，然后运行 `python scripts/sync_agent_config.py`，会自动同步到上面所有位置，避免多份内容漂移。单文件分发包在 `dist/authman-local-run.zip`，解压到目标 agent 的 skills 目录即可。

注意：Claude Code 不原生读取 `AGENTS.md`，仓库里的 `CLAUDE.md` 通过 `@AGENTS.md` 引入同一份内容。

### 豆包工作

`dist/authman-local-run-doubao.zip` 是豆包工作专用技能包：按豆包要求把 `SKILL.md` 放在 ZIP 根目录，`description` 改为中文触发词，并带上 `scripts/` 和 `references/`。在豆包开放平台创建技能时上传该 ZIP，发布范围可选「企业提供」或公开上架。

前提：脚本需要从所在目录向上找到 `main.py` + `requirements.txt` + `app/`。如果豆包在云端沙箱执行，需把项目代码一起放进它的工作目录，或用 `--repo` 指定路径，否则脚本无法定位项目根。

## Docker 构建

Dockerfile 为两阶段构建：两个阶段均基于 `python:3.14-alpine`，`deps` 阶段安装并精简依赖，`runtime` 阶段只复制依赖和代码。清理步骤放在依赖安装同一层，避免旧层占用体积。

镜像体积：原先 `python:3.14-slim` 方案最终镜像 365MB；现在 `authman:latest` 为 **212MB**（减少 42%）。可选再删掉 SQLAdmin 后台的 babel 语言包得到 **170MB**（`authman:i18n-off`，后台页面可用但国际化显示会退化）。

```bash
# 1) 依赖阶段（仅 requirements.txt 变化时重建），镜像长期保留
docker build --target deps -t authman-deps:latest .

# 2) 运行阶段（改代码后只需重跑这条，依赖层命中缓存，约 10 秒）
docker build -t authman:latest .

# 可选：极致瘦身版（再省约 42MB，后台国际化退化）
docker build --build-arg TRIM_I18N=1 -t authman:i18n-off .

# 3) 运行
docker run -d -p 18080:8000 -v authman-data:/data authman:latest
curl http://127.0.0.1:18080/get
```

`.dockerignore` 会排除本地 `.venv`、`.runtime`、`.workbuddy`、日志和测试文件，避免污染镜像。

已验证：`authman:latest` 容器内 `/get`、`/docs`、`/admin/` 均返回 200；`authman:i18n-off` 后台页面同样可访问。旧的 slim 镜像保留为 `authman:slim-backup` / `authman-deps:slim-backup`，确认无需回退后可直接删除。

## 安全提示

服务默认监听 `0.0.0.0`，且 `/admin` 目前使用 `NoAuthBackend`（不校验身份）：局域网内任何设备都能直接读改 token。只在可信网络使用；对外暴露前请先加认证或置于反向代理之后，或用 `--host 127.0.0.1` 收紧监听地址。`data/tokens.db` 含真实 token 与账号密码，已在 `.gitignore` 中排除，不要提交。
