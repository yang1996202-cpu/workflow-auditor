# workflow-review

**工作流复盘与重复模式发现 — Claude Code Skill**

这个 skill 用来回答一个具体问题：

> 最近 30 天里，哪些重复手动流程值得被打包，以及应该打包成什么形式？

它不会自动创建任何东西。第一产出物永远是候选清单；只有你确认后，才会创建或扩展 1-2 个高置信度、范围窄、可验证的最小资产。

## 起源

这个 skill 来自 Codex 官方团队的一个思路：让 AI 回顾工作历史，识别重复模式，把值得沉淀的流程打包成可复用工具。

原版是 Codex 提示词，我把它移植成了 Claude Code Skill。

原文参考：[Codex「自我蒸馏」提示词进化版](https://mp.weixin.qq.com/s/SDYTJrkpzFk-QbSCJQaLuQ)（AI寒武纪）

## 安装

```bash
git clone https://github.com/yang1996202-cpu/workflow-review ~/.claude/skills/workflow-review
```

如果已经安装过：

```bash
cd ~/.claude/skills/workflow-review
git pull --ff-only
```

重启 Claude Code 后，输入 `/workflow-review`，或直接说：

- “帮我看看最近有哪些重复工作流”
- “有什么可以打包成 skill”
- “找出值得自动化的事情”
- “回顾一下我最近的工作模式”

## 安装验证

确认 skill 文件存在：

```bash
test -f ~/.claude/skills/workflow-review/SKILL.md && echo ok
```

确认 bundled scripts 可运行：

```bash
~/.claude/skills/workflow-review/scripts/detect-claude-data.sh
```

正常情况下会输出类似：

```text
CLAUDE_ROOT=/Users/you/.claude
FACETS_DIR=/Users/you/.claude/usage-data/facets
SESSION_META_DIR=/Users/you/.claude/usage-data/session-meta
REPORT_PATH=/Users/you/.claude/usage-data/report.html
FACETS_COUNT=42
SESSION_META_COUNT=57
REPORT_EXISTS=yes
PROJECTS_COUNT=120
```

## 数据来源

优先级从高到低：

1. `~/.claude/usage-data/facets/*.json`：官方 `/insights` 语义层，包含目标、摩擦、结果。
2. `~/.claude/usage-data/session-meta/*.json`：结构层，包含项目路径、首条提示、会话类型等。
3. `~/.claude/usage-data/report.html`：官方聚合报告，用来交叉验证。
4. `~/.claude/projects/**/*.jsonl`：降级审计时使用，只提取统计和首条用户提示。
5. 当前工作区 git：降级旁证。

如果没有 facets，workflow-review 默认会先要求你运行 `/insights`，不会自动降级读取原始会话。

## 输出长什么样

示例见 [examples/example-output.md](examples/example-output.md)。

候选清单至少包含：

- 重复工作流
- 支持证据和日期
- 数据源
- 频率 / 置信度
- 评分
- 推荐落点：`skill`、`command`、`subagent-workflow`、`hook`、`script`、`external-automation`、`extend-existing` 或 `skip`
- 一句话理由

## 核心约束

- 禁止把完整会话记录读入上下文，只提取统计摘要。
- 输出候选清单后暂停，等你明确确认才创建。
- 每次只创建 1-2 个高置信度、范围窄的最小资产。
- 不做全 `$HOME` 内容扫描；降级时只扫 Claude projects、当前工作区 git，或你明确授权的路径。
- 常见 token/API key 会在脚本摘要中做基础脱敏。

## 常见情况

**没有 `/insights` 数据**

先在 Claude Code 里运行 `/insights`。它会生成 `usage-data`，再重新调用 `/workflow-review`。

**我想直接继续，不跑 `/insights`**

回复“继续降级审计”。workflow-review 会改用 `projects`、当前工作区 git 和可选 legacy transcripts，但结果会标注为弱证据。

**它会不会直接创建 skill？**

不会。它必须先输出候选清单，并等你确认。

## 仓库结构

```text
workflow-review/
  SKILL.md
  scripts/
    detect-claude-data.sh
    summarize-facets.py
    summarize-session-meta.py
    summarize-projects.py
  examples/
    example-output.md
```

## 作者

杨京艺 · 前 SaaS 解决方案顾问 · 现在全职折腾 AI 工具生态
