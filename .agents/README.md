# 跨工具 AI 配置（单一数据源）

本目录是 **Claude Code**、**Cursor**、**Codex** 共享的 commands 与 skills  canonical 位置。

## 结构

```
.agents/
  commands/opsx/     OpenSpec 斜杠命令（apply、new、archive …）
  skills/            OpenSpec 技能（openspec-* / SKILL.md）
```

各工具通过软链接引用：

| 链接 | 目标 |
|------|------|
| `.claude/commands` | `.agents/commands` |
| `.claude/skills` | `.agents/skills` |
| `.cursor/commands` | `.agents/commands` |
| `.cursor/skills` | `.agents/skills` |
| `.codex/commands` | `.agents/commands` |
| `.codex/skills` | `.agents/skills` |

工具专属文件保留在原处，例如 `.claude/launch.json`、`.claude/settings.local.json`。

## 初始化链接

克隆仓库后执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup-agent-links.ps1
```

项目说明见根目录 `AGENTS.md`（Codex / Cursor 直接读；Claude 通过 `CLAUDE.md` 的 `@AGENTS.md` 导入）。
