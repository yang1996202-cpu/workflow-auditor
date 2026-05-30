# workflow-review

**工作流复盘与重复模式发现 — Claude Code Skill**

---

## 起源

这个 skill 来自 Codex 官方团队的一个思路：让 AI 回顾你的工作历史，识别重复模式，自动打包成可复用的工具。

原版是 Codex 提示词，我把它移植成了 Claude Code Skill。

原文参考：[Codex「自我蒸馏」提示词进化版](https://mp.weixin.qq.com/s/SDYTJrkpzFk-QbSCJQaLuQ)（AI寒武纪）

---

## 是什么

扫描你最近 30 天的 Claude Code 使用历史，找出重复性手动流程，输出候选清单，由你确认后再打包。

**不会自动创建任何东西。判断权在你手里。**

---

## 安装

```bash
git clone https://github.com/yang1996202-cpu/workflow-review ~/.claude/skills/workflow-review
```

重启 Claude Code，输入 `/workflow-review` 触发。

---

## 触发词

- "帮我看看最近有哪些重复工作流"
- "有什么可以打包成 skill"
- "找出值得自动化的事情"
- "回顾一下我最近的工作模式"

---

## 数据来源

优先读取 `~/.claude/usage-data/facets/*.json`（官方 `/insights` 语义层）；其次 session-meta；最后才降级到 projects/*.jsonl，降级前会先问你。

---

## 核心约束

- 禁止把完整会话记录读入上下文，只提取统计摘要
- 输出候选清单后暂停，等你明确确认才创建
- 每次只创建 1-2 个高置信度、范围窄的最小资产

---

## 作者

杨京艺 · 前 SaaS 解决方案顾问 · 现在全职折腾 AI 工具生态
