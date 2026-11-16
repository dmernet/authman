#!/usr/bin/env python3
"""从唯一的 skill 真相源同步出各主流 agent 的配置入口。

真相源：.agents/skills/authman-local-run/SKILL.md（Agent Skills 开放规范）
改完 skill 后运行：python scripts/sync_agent_config.py

生成 / 更新：
  .workbuddy/skills/authman-local-run/     WorkBuddy
  .claude/skills/authman-local-run/        Claude Code
  AGENTS.md                                Codex / Cursor / Copilot / Gemini CLI / Aider 等
  CLAUDE.md                                Claude Code（通过 @AGENTS.md 引入）
  .cursor/rules/authman-local-run.mdc      Cursor
  .github/copilot-instructions.md          GitHub Copilot
  .windsurfrules                           Windsurf
  dist/authman-local-run-doubao.zip        豆包工作（SKILL.md 位于 ZIP 根目录）
  dist/authman-local-run.zip               通用包（保留 authman-local-run/ 目录结构）
"""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANON = ROOT / ".agents" / "skills" / "authman-local-run"
SKILL_MD = CANON / "SKILL.md"
CTL = ".agents/skills/authman-local-run/scripts/authman_ctl.py"


def skill_body() -> str:
    """取 SKILL.md 中 frontmatter 之后的正文，保证各适配文件内容不漂移。"""
    parts = SKILL_MD.read_text(encoding="utf-8").split("---", 2)
    if len(parts) < 3:
        raise SystemExit("SKILL.md 缺少 YAML frontmatter")
    return parts[2].strip()


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    print("written  ", path.relative_to(ROOT).as_posix())


def sync_skill_copy(dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(CANON, dest)
    for cache in dest.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)
    print("synced   ", dest.relative_to(ROOT).as_posix())


def agents_md() -> str:
    return f"""# AGENTS.md — AuthMan

## 项目

FastAPI + SQLAdmin 的 token 管理服务。业务代码在 `main.py` 与 `app/`，本地数据库默认为 `data/tokens.db`，Docker 内为 `/data/tokens.db`。

## 常用命令

### 本地运行（无需 Docker，推荐）

```bash
python {CTL} serve --port 8000
```

- 端口被占用会自动顺延，实际地址见 stderr 的 `AuthMan 启动中: http://...`。
- 首次运行自动创建 `.venv` 并安装依赖；离线可先 `prepare` 再给 `serve` 加 `--no-install`。
- agent 调用 `serve` 时请使用**后台任务方式**；终端用户直接运行，Ctrl+C 停止。

```bash
python {CTL} prepare                    # 只准备环境，输出 JSON
python {CTL} status --port 8000         # 健康检查，输出 JSON
python {CTL} stop --port 8000           # 按端口停止
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
"""


def claude_md() -> str:
    return """@AGENTS.md

本仓库同时提供 Agent Skills 开放规范的技能：`.agents/skills/authman-local-run/SKILL.md`，Claude Code 会从 `.claude/skills/authman-local-run/` 自动加载。
"""


def cursor_rule(body: str) -> str:
    return f"""---
description: Run, stop or debug the AuthMan FastAPI token service locally without Docker. Use when the user asks to start AuthMan locally, check its status, or stop it.
globs: []
alwaysApply: false
---

{body}
"""


def copilot_md() -> str:
    return f"""# GitHub Copilot — AuthMan

## 本地运行（无需 Docker）

```bash
python {CTL} serve --port 8000      # agent 请用后台任务方式执行
python {CTL} status --port 8000
python {CTL} stop --port 8000
```

首次运行自动准备 `.venv` 与依赖；端口占用自动顺延，实际地址见 stderr。

## 约束

- 本地与 Docker 的差异只通过 `DB_PATH` 注入，不要改业务代码。
- `/admin` 无认证，服务默认监听 `0.0.0.0`（所有网卡），不要暴露到不可信网络。
- `data/tokens.db` 含真实 token，禁止提交。

完整技能文档见 `.agents/skills/authman-local-run/SKILL.md`，接口细节见该目录下 `references/api.md`。
"""


def windsurf_rules() -> str:
    return f"""# Windsurf Rules — AuthMan

## 本地运行（无需 Docker）

```bash
python {CTL} serve --port 8000      # 后台执行；端口占用自动顺延
python {CTL} status --port 8000
python {CTL} stop --port 8000
```

## Docker

```bash
docker build --target deps -t authman-deps:latest .
docker build -t authman:latest .
```

## 约束

- 不修改业务代码适配本地运行，差异只通过 `DB_PATH` 处理。
- `/admin` 无认证，禁止公网暴露；`data/tokens.db` 禁止提交。

完整技能文档：`.agents/skills/authman-local-run/SKILL.md`。
"""


def doubao_skill_md() -> str:
    """豆包面向中文用户，description 用中文触发词；去掉 WorkBuddy 专有字段。"""
    lines: list[str] = []
    for line in SKILL_MD.read_text(encoding="utf-8").splitlines(keepends=True):
        if line.startswith("agent_created:"):
            continue
        if line.startswith("description:"):
            lines.append(
                "description: 本地启动/调试/停止 AuthMan token 管理服务（FastAPI，无需 Docker）。"
                "当用户说「本地启动 AuthMan」「不用 Docker 运行」「调试接口」「启动服务」"
                "「查端口」「停止服务」时使用。自动创建虚拟环境、安装依赖、注入 DB_PATH，"
                "默认监听 0.0.0.0:8000，端口占用自动顺延。\n"
            )
            continue
        lines.append(line)
    return "".join(lines)


def build_doubao_package() -> None:
    """豆包工作技能包要求 SKILL.md 位于 ZIP 根目录，单独打一版。"""
    dist = ROOT / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    staging = ROOT / ".runtime" / "doubao-skill"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    (staging / "SKILL.md").write_text(doubao_skill_md(), encoding="utf-8")
    shutil.copytree(CANON / "scripts", staging / "scripts")
    shutil.copytree(CANON / "references", staging / "references")
    for cache in staging.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)
    out = dist / "authman-local-run-doubao.zip"
    if out.exists():
        out.unlink()
    shutil.make_archive(str(out.with_suffix("")), "zip", staging)
    print("packaged ", out.relative_to(ROOT).as_posix())


def build_generic_package() -> None:
    """通用分发包：整目录打成 authman-local-run/ 结构，解压到任意 agent 的 skills 目录即可。"""
    dist = ROOT / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    staging_root = ROOT / ".runtime" / "generic-skill"
    staging = staging_root / "authman-local-run"
    if staging_root.exists():
        shutil.rmtree(staging_root)
    staging.mkdir(parents=True)
    shutil.copytree(CANON, staging, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
    out = dist / "authman-local-run.zip"
    if out.exists():
        out.unlink()
    shutil.make_archive(str(out.with_suffix("")), "zip", staging_root)
    print("packaged ", out.relative_to(ROOT).as_posix())


def main() -> None:
    if not SKILL_MD.is_file():
        raise SystemExit(f"找不到真相源：{SKILL_MD}")

    # 1) 同一份 skill 复制到各 agent 的项目级发现目录
    sync_skill_copy(ROOT / ".workbuddy" / "skills" / "authman-local-run")
    sync_skill_copy(ROOT / ".claude" / "skills" / "authman-local-run")

    # 2) 不扫描 skills 目录的 agent，用项目级指令文件兜底
    body = skill_body()
    write(ROOT / "AGENTS.md", agents_md())
    write(ROOT / "CLAUDE.md", claude_md())
    write(ROOT / ".cursor" / "rules" / "authman-local-run.mdc", cursor_rule(body))
    write(ROOT / ".github" / "copilot-instructions.md", copilot_md())
    write(ROOT / ".windsurfrules", windsurf_rules())

    # 3) 豆包工作技能包：SKILL.md 必须在 ZIP 根目录
    build_doubao_package()

    # 4) 通用技能包：保留 authman-local-run/ 目录结构，供其它 agent 解压安装
    build_generic_package()

    print("完成。以后只需修改 .agents/skills/authman-local-run/ 再运行本脚本。")


if __name__ == "__main__":
    main()
