---
name: workflow-review
description: |
  工作流复盘与重复模式发现 Skill。当用户有以下任何行为时触发：
  - "帮我分析一下最近有哪些重复工作流"
  - "看看有什么可以打包成 skill"
  - "回顾一下我最近的工作模式"
  - "找出值得自动化的事情"
  - "scan my habits / patterns"
  - "what should I automate"
  - "有什么重复做的事情"
  - "帮我审视一下最近的工作"
  - "从我的工作历史里发现规律"
  - "哪些工作值得做成 skill"
  - 讨论"重复劳动""手动流程""效率提升""工作流优化"时

  触发后，先回顾最近 30 天的工作；如果可用历史少于 30 天，就回顾全部可用历史，找出值得打包的重复性手动流程。

  第一产出物必须是候选清单，而不是直接创建资产。候选清单至少包含：重复工作流、支持证据和日期、频率/置信度、推荐落点（skill / command / subagent-workflow / hook / script / external-automation / extend-existing / skip）、以及一句话理由。

  只有在用户确认候选清单之后，才创建或扩展 1-2 个高置信度、范围窄、可验证的最小资产。

  注意：不要假定固定目录结构。先探测 Claude Code 数据根目录；常见结构是 `<claude-data-root>/projects/<sanitized-cwd>/<session-id>.jsonl`，旧数据可能在 `<claude-data-root>/transcripts/`（ses_*.jsonl 简化格式），如存在应一并扫描并标注数据来源。

  核心约束：(1) 禁止把完整会话记录读入上下文，必须用 Bash 提取统计摘要。(2) 产出候选清单后必须暂停，等用户明确确认后再创建。(3) Claude Code 用户先探测本机数据目录，再优先读取已探测到的 `usage-data/facets/*.json`（语义层，每会话一个 JSON，含目标/摩擦/结果）；其次是 session-meta 和 report.html；如果官方 usage-data 不存在，默认先要求用户自行运行官方 `/insights`，只有在用户明确确认继续降级审计后，才可退到 projects / 工作区 + git / 可选 legacy transcripts / 用户口述。Alice 等外部对话源只作旁证，不得成为主链路前提。
metadata:
  short-description: 分析工作历史，发现重复模式，打包成最小有用技能
---

# Workflow Review — 工作流复盘与重复模式发现

先回答一个问题：最近 30 天里，哪些重复手动流程值得被打包，以及应该打包成什么形式。

## 任务目标

1. 回顾最近 30 天的工作；如果可用历史少于 30 天，就回顾全部可用历史。
2. 识别那些重复、耗时、容易出错、上下文负担重，且值得被打包的手动流程。
3. 先交付候选清单，再在用户确认后创建最小有用资产。

## 第一产出物

第一产出物必须是候选清单，至少包含：

- 重复工作流
- 支持证据和日期
- 频率 / 置信度
- 推荐落点：skill、command、subagent-workflow、hook、script、external-automation、extend-existing 或 skip
- 一句话理由

没有候选清单，就不允许进入创建阶段。

## 推荐落点类型

- `skill`：适合有明确触发场景、判断规则和可复用步骤的工作流。
- `command`：适合用户手动触发、单次执行、主要靠提示词编排的动作。
- `subagent-workflow`：适合需要把搜索、比较、汇总等子任务分派给一个或多个 agent 的流程。
- `hook`：适合在 Claude Code 的固定事件点自动触发的检查、格式化、提醒或保护动作。
- `script`：适合边界明确、输入输出稳定、主要靠 shell/python/node 完成的确定性任务。
- `external-automation`：适合定时、轮询、跨系统编排，或必须脱离 Claude Code 会话独立运行的自动化。
- `extend-existing`：适合已有 skill、command、hook 或 script 已覆盖 70% 以上，只需要扩展。
- `skip`：适合证据不足、复发概率低、投入产出比差，或不适合固化的工作。

注意：`automation` 不是最终落点名。如果候选确实是“自动化”，必须继续分清是 `hook` 还是 `external-automation`。

## 证据收集

**重要：Bash 工具每次调用都是独立 shell，变量不跨调用保留。先运行 Step 0 拿到 `FACETS_DIR`、`SESSION_META_DIR`、`REPORT_PATH`、`PROJECTS_DIR`、`TRANSCRIPTS_DIR`；后续命令中的 `<facets-dir>`、`<session-meta-dir>`、`<projects-dir>`、`<transcripts-dir>` 必须替换成探测输出，禁止写死 `$HOME/.claude/...`。**

**0. 先探测路径并验证内容，不要写死**
```bash
CLAUDE_ROOT="${CLAUDE_DATA_ROOT:-${CLAUDE_CONFIG_DIR:-}}"
if [ -z "$CLAUDE_ROOT" ] || [ ! -d "$CLAUDE_ROOT" ]; then
  CLAUDE_ROOT="$(find "$HOME" -maxdepth 4 -type d -name .claude 2>/dev/null | head -1)"
fi

# 验证各目录是否存在且有内容
FACETS_DIR=""
SESSION_META_DIR=""
REPORT_PATH=""
PROJECTS_DIR=""
TRANSCRIPTS_DIR=""
FACETS_COUNT=0
SESSION_META_COUNT=0
REPORT_EXISTS="no"
REPORT_DATE=""
PROJECTS_COUNT=0
TRANSCRIPTS_COUNT=0

if [ -n "$CLAUDE_ROOT" ]; then
  [ -d "$CLAUDE_ROOT/usage-data/facets" ] && FACETS_DIR="$CLAUDE_ROOT/usage-data/facets"
  [ -d "$CLAUDE_ROOT/usage-data/session-meta" ] && SESSION_META_DIR="$CLAUDE_ROOT/usage-data/session-meta"
  [ -f "$CLAUDE_ROOT/usage-data/report.html" ] && REPORT_PATH="$CLAUDE_ROOT/usage-data/report.html"
  [ -d "$CLAUDE_ROOT/projects" ] && PROJECTS_DIR="$CLAUDE_ROOT/projects"
  [ -d "$CLAUDE_ROOT/transcripts" ] && TRANSCRIPTS_DIR="$CLAUDE_ROOT/transcripts"

  [ -n "$FACETS_DIR" ] && FACETS_COUNT=$(find "$FACETS_DIR" -maxdepth 1 -name "*.json" 2>/dev/null | wc -l | tr -d ' ')
  [ -n "$SESSION_META_DIR" ] && SESSION_META_COUNT=$(find "$SESSION_META_DIR" -maxdepth 1 -name "*.json" 2>/dev/null | wc -l | tr -d ' ')
  [ -n "$REPORT_PATH" ] && REPORT_EXISTS="yes" && REPORT_DATE=$(stat -f "%Sm" -t "%Y-%m-%d" "$REPORT_PATH" 2>/dev/null)
  [ -n "$PROJECTS_DIR" ] && PROJECTS_COUNT=$(find "$PROJECTS_DIR" -name "*.jsonl" 2>/dev/null | wc -l | tr -d ' ')
  [ -n "$TRANSCRIPTS_DIR" ] && TRANSCRIPTS_COUNT=$(find "$TRANSCRIPTS_DIR" -name "ses_*.jsonl" 2>/dev/null | wc -l | tr -d ' ')
fi

printf 'CLAUDE_ROOT=%s\nFACETS_DIR=%s\nSESSION_META_DIR=%s\nREPORT_PATH=%s\nPROJECTS_DIR=%s\nTRANSCRIPTS_DIR=%s\nFACETS_COUNT=%s\nSESSION_META_COUNT=%s\nREPORT_EXISTS=%s\nREPORT_DATE=%s\nPROJECTS_COUNT=%s\nTRANSCRIPTS_COUNT=%s\n' \
  "$CLAUDE_ROOT" "$FACETS_DIR" "$SESSION_META_DIR" "$REPORT_PATH" "$PROJECTS_DIR" "$TRANSCRIPTS_DIR" "$FACETS_COUNT" "$SESSION_META_COUNT" "$REPORT_EXISTS" "$REPORT_DATE" "$PROJECTS_COUNT" "$TRANSCRIPTS_COUNT"
```

**`<usage-data-dir>/` 完整数据架构**（仅在探测到 facets > 0 后适用）：

| 数据源 | 数量 | 核心字段 | 用途 |
|--------|------|---------|------|
| `facets/*.json` | 因人而异 | `underlying_goal`, `brief_summary`, `session_type`, `friction_counts`, `friction_detail`, `primary_success` | **语义层**，最有价值，每个会话的目标/摩擦/结果 |
| `session-meta/*.json` | 因人而异 | `project_path`, `start_time`, `duration_minutes`, `first_prompt`, `tool_counts` | **结构层**，覆盖所有会话，可与 facets 按 UUID join |
| `report.html` | 1个 | 叙述文字 | 已聚合的摘要；带日期版本（`report-YYYY-MM-DD.html`）是历史快照，内容相同 |

**1. usage-data 前置检查（新增）**

探测完成后，**必须先判断数据可用性**，再决定走哪条分支：

- **如果 `FACETS_COUNT > 0`**：→ 走主流程（A+B+C），这是最佳路径
- **如果 `FACETS_COUNT = 0`**：→ 先阻断并询问用户；默认优先官方 `/insights`，不自动降级

**当 facets 为空时，必须显式提示用户：**

> ⚠️ 未检测到官方 insights 结构化数据
>
> workflow-review 的高质量复盘优先依赖官方 `/insights` 生成的 usage-data（facets、session-meta、report.html）。
>
> 现在卡住，不是报错，而是在等这份官方数据。
> 如果没有它，也能继续，但只能做降级审计：证据会更弱，容易漏掉近期模式。
>
> 当前检测到的数据状态：
> - facets: {FACETS_COUNT} 个
> - session-meta: {SESSION_META_COUNT} 个
> - report.html: {REPORT_EXISTS}（{REPORT_DATE}）
> - projects: {PROJECTS_COUNT} 个会话文件
> - transcripts: {TRANSCRIPTS_COUNT} 个 legacy 文件
>
> 你有两个选项：
> **a) 推荐：先跑 `/insights`**
> 1. 在 Claude 里运行 `/insights`
> 2. 等它生成 usage-data
> 3. 再重新调用 workflow-review
>
> 说明：这不是“暂停后自动继续”。因为 `/insights` 会生成新数据，workflow-review 需要在新的一次调用里重新读取。
>
> **b) 继续降级审计**
> 直接回复“继续降级审计”，我就改用 projects + 工作区 git + 可选 legacy transcripts 继续，但结果会更弱。
>
> 默认不自动降级。你选 a 还是 b？

如果用户选 **a**：

- 明确告诉用户：请先运行 `/insights`，完成后重新调用 workflow-review。
- 不要再展开解释底层机制，除非用户追问“为什么不能自动继续”。
- 当前 skill 到此结束，不进入降级流程。

如果用户选 **b** 或明确回复“继续降级审计”，才继续执行降级流程。

如果用户没有明确选择 **a** 或 **b**，不要自动继续。

**2. 主流程：并行收集（facets > 0 时）**

**A. facets**（语义层，首选）
```bash
# 统计 30 天内数量（把 <facets-dir> 替换成 Step 0 输出的 FACETS_DIR）
find "<facets-dir>" -maxdepth 1 -name "*.json" -mtime -30 2>/dev/null | wc -l
# 提取 30 天内全部唯一 goal（去重后由 Claude 做语义归类；不用 uniq -c，避免措辞不同导致同类模式被打散）
find "<facets-dir>" -maxdepth 1 -name "*.json" -mtime -30 2>/dev/null | \
  xargs python3 -c "
import json, sys
for p in sys.argv[1:]:
    try: print(json.load(open(p)).get('underlying_goal','').strip())
    except: pass
" | sort -u | head -80
# 同期 session_type + brief_summary（补充语境，取最近 30 条）
find "<facets-dir>" -maxdepth 1 -name "*.json" -mtime -30 -exec stat -f "%m %N" {} + 2>/dev/null | sort -rn | head -30 | cut -d' ' -f2- | while read -r f; do
  python3 -c "import json; d=json.load(open('$f')); print(d.get('session_type','?'), '|', d.get('brief_summary','?')[:60])"
done
# 30 天内高频摩擦点（friction key 是离散枚举，uniq -c 不失真）
find "<facets-dir>" -maxdepth 1 -name "*.json" -mtime -30 2>/dev/null | while read -r f; do python3 -c "import json; d=json.load(open('$f')); [print(k) for k in d.get('friction_counts',{}).keys()]"; done | sort | uniq -c | sort -rn | head -10
```

**B. session-meta**（结构层，补充 facets 没有的会话）
- 取最近文件：`find "<session-meta-dir>" -maxdepth 1 -name "*.json" -exec stat -f "%m %N" {} + 2>/dev/null | sort -rn | head -30 | cut -d' ' -f2-`
- 提取：`python3 -c "import json; d=json.load(open('FILE')); print(d.get('project_path'), d.get('first_prompt','')[:80])"`
- 统计 session_type 分布：`find ... | while read f; do python3 -c "... d.get('session_type','?') ..."; done | sort | uniq -c | sort -rn`
- 与 facets 按 session UUID（文件名）join 可得完整画像

**C. report.html**（综合叙述，辅助验证）
- 存在且 ≤7天 → read_file 读取，忽略 `<style>`/`<script>` 标签，只看文字段落
- 超过 7 天 → 在提示中标注"report 已过期（{天数} 天前），建议先跑 `/insights` 刷新"，但继续用现有数据

**3. 降级流程：当 facets = 0 时**

**D. projects**（本地会话记录，降级时的主要数据源）
```bash
# 统计各工作目录的会话数量和最近活动时间
for dir in "<projects-dir>/"*/; do
  [ -d "$dir" ] || continue
  name=$(basename "$dir")
  count=$(find "$dir" -maxdepth 1 -name "*.jsonl" 2>/dev/null | wc -l | tr -d ' ')
  latest=$(find "$dir" -maxdepth 1 -name "*.jsonl" -exec stat -f "%Sm" -t "%Y-%m-%d" {} + 2>/dev/null | sort -r | head -1)
  size=$(du -sh "$dir" 2>/dev/null | cut -f1)
  printf "%-55s | %3d sessions | latest: %s | %s\n" "$name" "$count" "$latest" "$size"
done
```
- 最近会话首条用户提示（限最近 20 个）：
```bash
find "<projects-dir>" -name "*.jsonl" -exec stat -f "%m %N" {} + 2>/dev/null | sort -rn | head -20 | cut -d' ' -f2- | while read -r f; do
  printf '%s | ' "$(basename "$f")"
  python3 - "$f" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, 'r', encoding='utf-8') as fh:
  for line in fh:
    try:
      obj = json.loads(line)
    except Exception:
      continue
    if obj.get('type') != 'user':
      continue
    message = obj.get('message', {})
    if not isinstance(message, dict):
      continue
    content = message.get('content', [])
    if not isinstance(content, list):
      continue
    texts = [part.get('text', '') for part in content if isinstance(part, dict) and part.get('type') == 'text']
    text = ' '.join(t for t in texts if t).strip()
    if text:
      print(text[:80])
      break
PY
done
```
- 只允许提取文件名、时间、首条用户消息；**禁止整包读入 JSONL**

**E. legacy transcripts**（可选低优先补充）
- 仅当存在 `ses_*.jsonl` 时才读取，并明确标注为 legacy / 旁路旧数据，不当作 Claude Code 官方真源
- 旧格式：`find "<transcripts-dir>" -type f -name "ses_*.jsonl" 2>/dev/null | head -30`
- 提取首条用户消息和时间

**F. 工作区 + Git**（兜底，补充 Claude Code 之外的上下文）
```bash
find "$HOME" -name "*.md" -mtime -30 -not -path "*/.*" 2>/dev/null | head -20
git log --oneline --since="30 days ago" 2>/dev/null | head -20
```

**G. 用户口述**（最终兜底）
- A/B/C/D/E/F 全无或证据不足时，直接询问用户最近有哪些重复或耗时的工作

**可选旁证：外部对话源**
- 如果环境里恰好存在 Alice 等外部对话源，可以补充用来验证候选是否跨工具复发
- 这类来源只能作旁证，不得替代本地 Claude Code 数据，也不进入默认主链路

**降级路径总结**：
- **Level 1**（最佳）：facets + session-meta + report.html
- **Level 2**（降级主链路）：projects + 工作区 git
- **Level 3**（可选补充）：legacy transcripts（旁路旧数据）
- **Level 4**（最终）：用户口述

**Token 规则**：report.html 可整体读入（约 50KB）。facets/session-meta 只用 python3 单行提取。projects/transcripts 只允许 Bash 级摘要提取，禁止整包读入 JSONL。

## 筛选标准

只有同时满足以下四条，才对一个候选采取行动：
1. 至少发生两次，或明显很可能复发
2. 有稳定的输入、可重复的步骤、明确的输出或停止条件
3. 能实质提升速度、质量、一致性或可靠性
4. 未被已有 skills、脚本、别名或模板充分覆盖

## 执行流程

1. **明确回顾窗口**：默认最近 30 天；如果可用历史少于 30 天，就回顾全部可用历史。
2. **探测路径并验证数据可用性**：输出各数据源的数量和状态。
3. **判断分支**：
   - facets > 0 → 主流程（A+B+C）
  - facets = 0 → 先阻断提示用户选 a/b；只有用户明确确认“继续降级审计”，才进入降级流程（D+E+F+G）
4. **收集证据**：按当前分支的优先级并行收集，不要一上来就创建任何资产。
5. **识别模式**：寻找重复、耗时、容易出错、上下文重载的特征。
6. **交叉验证**（Claude Code 用户）：
   - 主流程：将 facets 的高频摩擦词（`friction_counts` 聚合）与 report.html 的叙述结论对比。两者都提 = 高置信度。facets 有但 report.html 未提 = report.html 生成日期之后出现的新模式。
  - 降级流程：将 projects 的高频工作目录与 git 记录 / 可选 legacy transcripts 交叉验证。至少两类来源同时出现 = 中置信度。仅一类来源 = 低置信度，需标注"证据单一"。
7. **选择落点**：在 `skill / command / subagent-workflow / hook / script / external-automation / extend-existing / skip` 之间选择，不要只写笼统的 “automation”。
8. **产出候选清单**：重复工作流、支持证据和日期、频次/置信度、推荐落点、一句话理由。**标注每个候选的数据来源**（如 [facets+report]、[projects+git]、[projects+legacy-transcripts]、[git] 等）。
9. **暂停，询问用户**："以上是候选清单。你觉得哪些需要补充、哪些需要删减、哪些优先级不对？确认之后我再动手创建。"
10. **只创建用户确认的项**：每次最多 1-2 个，narrow、practical、可追溯来源。
11. **汇报**：创建或扩展了什么、刻意跳过了什么、哪些内容需要更多证据。

## 硬性约束

- **清单后必须暂停**。没有用户明确确认，不创建任何东西。
- **禁止读取完整会话记录**。只用 Bash 预处理。
- **禁止推测性资产**。只打包有证据的。
- **诚实标红不匹配**。如果用户明显不适合某个模式（如销售背景的用户被建议纯算法 skill），直接标红。
- **标注数据来源**。每个候选必须注明证据来自哪些数据源（facets / report / projects / legacy-transcripts / git / user）。
- **外部对话源只能旁证**。Alice 等外部来源即使可用，也不能替代本地 Claude Code 数据链路。

## 降级处理

如果所有数据源都为空或证据严重不足：

> "当前证据有限。检测到以下数据源状态：
> - usage-data (facets): {count}
> - projects: {count}
> - legacy transcripts: {count}
> - git: {commits}
>
> 我可以给你一个轻量追踪模板，让你接下来一两周记录每天重复或耗时的工作，到时候我们再跑一遍审计。
> 
> 或者，如果你愿意口述最近常做的几件事，我可以基于你的描述直接产出候选清单。"

## 验证方式

本 Skill 工作正常的标志：
- 能正确响应工作流审计请求
- 能正确检测 Claude Code 数据目录和各数据源的存在性
- 当官方 usage-data 缺失时，能先阻断并要求用户在 `/insights` 与“继续降级审计”之间明确二选一
- 产出清单后不会自动创建任何内容
- 会暂停并等待用户确认
- 创建的 skill 是 narrow、practical 的，用户下次使用时能验证效果
- 降级时能正确标注数据来源和置信度差异
