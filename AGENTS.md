# AGENTS.md — AuthMan

## 项目

FastAPI + SQLAdmin 的 token 管理服务。业务代码在 `main.py` 与 `app/`，本地数据库默认为 `data/tokens.db`，Docker 内为 `/data/tokens.db`。

## 常用命令

### 本地运行（无需 Docker，推荐）

```bash
python .agents/skills/authman-local-run/scripts/authman_ctl.py serve --port 8000
```

- 端口被占用会自动顺延，实际地址见 stderr 的 `AuthMan 启动中: http://...`。
- 首次运行自动创建 `.venv` 并安装依赖；离线可先 `prepare` 再给 `serve` 加 `--no-install`。
- agent 调用 `serve` 时请使用**后台任务方式**；终端用户直接运行，Ctrl+C 停止。

```bash
python .agents/skills/authman-local-run/scripts/authman_ctl.py prepare                    # 只准备环境，输出 JSON
python .agents/skills/authman-local-run/scripts/authman_ctl.py status --port 8000         # 健康检查，输出 JSON
python .agents/skills/authman-local-run/scripts/authman_ctl.py stop --port 8000           # 按端口停止
```

### Docker 构建（两阶段）

```bash
docker build --target deps -t authman-deps:latest .   # 仅 requirements.txt 变化时需要
docker build -t authman:latest .                       # 改代码后只跑这条
docker run -d -p 18080:8000 -v authman-data:/data authman:latest
```

## 约束

- 不要改业务代码来适配本地运行；本地与 Docker 的差异只通过 `DB_PATH` 环境变量处理。
- 服务默认监听 `0.0.0.0`（所有网卡），端口默认 8000，占用时自动顺延。`/admin` 当前是 `NoAuthBackend`，局域网内可直接访问，务必只在可信网络使用；对外暴露前先加认证或反向代理，或用 `--host` 收紧监听地址。
- `data/tokens.db` 含真实 token，禁止提交到 git。
- 本地生成的 `.venv` / `.runtime` 已由 `.dockerignore` 排除，不要改 Dockerfile 把它们打进镜像。

## Skill 入口

完整技能文档：`.agents/skills/authman-local-run/SKILL.md`。各 agent 的等价入口：

- Claude Code：`.claude/skills/authman-local-run/SKILL.md`
- WorkBuddy：`.workbuddy/skills/authman-local-run/SKILL.md`
- Cursor：`.cursor/rules/authman-local-run.mdc`
- GitHub Copilot：`.github/copilot-instructions.md`
- Windsurf：`.windsurfrules`
