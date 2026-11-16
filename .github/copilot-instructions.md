# GitHub Copilot — AuthMan

## 本地运行（无需 Docker）

```bash
python .agents/skills/authman-local-run/scripts/authman_ctl.py serve --port 8000      # agent 请用后台任务方式执行
python .agents/skills/authman-local-run/scripts/authman_ctl.py status --port 8000
python .agents/skills/authman-local-run/scripts/authman_ctl.py stop --port 8000
```

首次运行自动准备 `.venv` 与依赖；端口占用自动顺延，实际地址见 stderr。

## 约束

- 本地与 Docker 的差异只通过 `DB_PATH` 注入，不要改业务代码。
- `/admin` 无认证，服务默认监听 `0.0.0.0`（所有网卡），不要暴露到不可信网络。
- `data/tokens.db` 含真实 token，禁止提交。

完整技能文档见 `.agents/skills/authman-local-run/SKILL.md`，接口细节见该目录下 `references/api.md`。
