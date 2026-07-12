---
name: pr-analyze
version: 0.6.0
author: 大铭 (https://github.com/yinwm)
description: |
  Comprehensive PR analysis workflow for GitHub repositories. Use when user provides a PR number or URL and asks for analysis.
  Automatically checks PR purpose, compatibility impact, duplicate PRs, related PRs, CI status, and runs code review.
  Outputs a structured report in Chinese with actionable suggestions. Reports are saved to a configurable directory.

  TRIGGERS:
  - "帮我分析 PR #xxx" or "分析这个 PR"
  - "PR 分析" or "analyze PR"
  - "审查这个 PR" (审查时自动包含分析)
  - "查看 PR 兼容性影响"
  - "这个 PR 干什么的"
  - User provides a GitHub PR URL

  Use this skill proactively when user mentions a PR and wants to understand its scope and impact.

  CONFIGURATION:
  - "设置 PR 报告存储路径" or "修改 PR 报告存储目录" - Change report storage directory
  - First run will prompt for storage directory if not configured
compatibility: Requires `gh` CLI (GitHub CLI)
---

# PR 分析

对 GitHub PR 进行全面分析，生成结构化中文报告，并保存到本地。

## 配置管理

### 配置文件位置

```
~/.claude/skills/pr-analyze/config.json
```

### 配置结构

```json
{
  "report_dir": "/path/to/your/pr-reports"
}
```

### 检查与初始化配置

**每次运行时最先执行（Step 0）：**

```bash
cat ~/.claude/skills/pr-analyze/config.json 2>/dev/null || echo "NOT_FOUND"
```

**首次运行流程：**

1. 检查 `config.json` 是否存在
2. 如果不存在，使用 `AskUserQuestion` 询问用户：
   ```
   问题：PR 分析报告需要保存到本地，请选择存储目录：

   A) 使用默认目录：~/pr-reports
   B) 使用当前项目目录：./pr-reports
   C) 自定义路径（请输入完整路径）
   ```
3. 创建目录（如果不存在）
4. 写入配置文件

**修改配置流程：**

当用户说"修改 PR 报告存储目录"或"设置 PR 报告存储路径"时：
1. 显示当前配置
2. 使用 `AskUserQuestion` 询问新路径
3. 更新 `config.json`

## 报告文件命名

```
{report_dir}/{repo_slug}/pr-{number}-{YYYYMMDD}-{HHMMSS}.md
```

示例：
```
~/pr-reports/sipeed-picoclaw/pr-1900-20260323-071500.md
```

**命名规则：**
- `{repo_slug}`: owner/repo 转换为 owner-repo（避免路径中的斜杠）
- `{number}`: PR 编号
- `{YYYYMMDD}-{HHMMSS}`: 分析时间戳，支持多次分析同一 PR

## 输入

接受以下形式：
- PR 编号：`1900`（需要当前目录在 git 仓库中）
- PR URL：`https://github.com/owner/repo/pull/1900`
- 简写：`owner/repo#1900`

## 分析流程

### Step 0: 检查配置

**在开始任何分析之前执行。** 检查配置文件是否存在，不存在则引导用户配置。

### Step 1: 获取 PR 元数据 + diff + CI

```bash
gh pr view <PR> --repo <owner/repo> --json title,body,state,author,baseRefName,headRefName,files,additions,deletions,commits,number,mergeable,mergeStateStatus
gh pr diff <PR> --repo <owner/repo>
gh pr checks <PR> --repo <owner/repo> || gh pr view <PR> --repo <owner/repo> --json statusCheckRollup
```

将基本信息获取、diff 和 CI 检查合并为一次并行调用，减少轮次。

提取：
- 标题、描述、状态（OPEN/MERGED/CLOSED）
- 作者、目标分支、源分支
- 改动文件列表、增删行数
- 关联的 Issue（从 body 中提取 `Closes #xxx` 等）
- **Merge 状态**：
  - `mergeable`: `MERGEABLE` / `CONFLICTING` / `UNKNOWN`
  - `mergeStateStatus`: `CLEAN` / `DIRTY` / `BLOCKED` / `DRAFT` / `UNSTABLE`
- CI 检查结果

**重要**: 如果 `mergeable` 为 `CONFLICTING` 或 `mergeStateStatus` 为 `DIRTY`，必须在报告中突出显示这是阻塞性问题！

### Step 2: 读取已有评论和 reviews

**目的**：不重复已有发现，识别未覆盖的审查角度。

```bash
# Review comments（行内代码评论）
gh api repos/{owner}/{repo}/pulls/{number}/comments

# Reviews（整体 review）
gh api repos/{owner}/{repo}/pulls/{number}/reviews

# Issue comments（PR 主体评论）
gh api repos/{owner}/{repo}/issues/{number}/comments
```

**处理**：
1. 按评论者分组，提取关键发现
2. 标记已发现的问题（主审查不重复）
3. 识别未覆盖的角度（补充审查重点）
4. 记入报告"已有 Review"章节

**如果 API 返回空列表或失败**：跳过此步骤，不影响后续流程。

### Step 3: Clone PR 到临时目录

**目的**：获得完整源码，使数据流追踪和跨文件分析成为可能。

```bash
# 创建临时目录（含 PR 编号，方便识别）
TMPDIR=$(mktemp -d "/tmp/pr-analyze-${PR_NUMBER}-XXXXXXXX")

# 浅克隆仓库
git clone --depth 1 "https://github.com/${OWNER}/${REPO}.git" "$TMPDIR/repo"

# Fetch PR head ref 并 checkout
cd "$TMPDIR/repo"
git fetch origin "refs/pull/${PR_NUMBER}/head:pr-${PR_NUMBER}"
git checkout "pr-${PR_NUMBER}"
```

**后续所有代码审查步骤（Step 4）基于此目录的完整源码进行。**

**如果 clone 失败**（私有仓库权限、网络问题等）：回退到仅基于 diff 的审查模式，并在报告中注明"源码获取失败，审查基于 diff only"。

### Step 4: 代码审查

**读取 `~/.claude/skills/pr-analyze/checklist.md`。如果文件不存在，停止并报错。**

#### Step 4a: 数据流追踪

**这是最关键的新增步骤。** 从 diff 中识别数据表示变换点，用完整源码追踪每个变换的 roundtrip。

**通用步骤**：

1. **从 diff 中识别变换函数** — 找所有做格式转换的函数/方法（输入一种类型，输出另一种类型）
2. **从 diff 中识别存储操作** — 找所有写入持久化的地方（数据库、文件、缓存）
3. **用完整源码追踪完整路径** — 对每个变换点，从写入端追踪到存储层，再从存储层追踪到读出端
4. **验证 roundtrip 一致性** — 写入时存储了什么，读出时是否完整还原

**检查项**：
- 数据经变换后是否丢失字段？
- 存储操作是否静默丢弃部分输入？
- 读出时是否假设了写入时没有保证的不变量？
- 并发读写时数据是否一致？

#### Step 4b: Pass 1 — CRITICAL

按 checklist.md 中的 CRITICAL 类别逐项检查：

- 数据安全（注入、原子性、N+1）
- 并发安全（竞态、原子操作）
- 信任边界（外部输入验证、SSRF、XSS）
- 命令/代码注入
- 数据完整性（枚举值覆盖）

**数据完整性检查必须读取 diff 之外的代码**：当 diff 引入新的枚举值/状态/类型常量时，用 Grep 搜索所有引用同类值的位置，用 Read 逐一检查新值是否被处理。

#### Step 4c: Pass 2 — INFORMATIONAL

按 checklist.md 中的 INFORMATIONAL 类别逐项检查：

- 可维护性（文件长度、职责分离）
- 错误处理（静默吞错、终止条件）
- 性能（批量操作、内存泄漏）
- 兼容性（接口签名、配置默认值）
- 测试（覆盖度、边界条件）
- 范围漂移（实际改动 vs 声明意图）

#### Step 4d: 对抗性审查（独立子 agent）

**目的**：独立视角找主审查者盲区。

通过 Agent tool 启动一个独立子 agent（`subagent_type: "general-purpose"`），子 agent 没有主审查的上下文。

**子 agent prompt**：

```
你是一个对抗性代码审查员。对以下 PR 进行独立审查。

PR diff 获取方式：cd {临时目录} && git diff {base_branch}...HEAD
完整源码位置：{临时目录}

你的任务是找到主审查者可能遗漏的问题。以攻击者和混沌工程师的视角审查。

重点检查：
- 边界条件和异常路径
- 跨文件的数据一致性问题（特别是数据经过转换、存储、再读出的完整路径）
- 错误处理中被吞掉的失败
- 并发场景下的竞态条件
- 资源泄漏

对每个发现，输出：
[SEVERITY] (confidence: N/10) path/to/file:line — 描述

severity: CRITICAL / WARNING / INFORMATIONAL
confidence: 1-10

不要给出赞美或"看起来不错"的评论。只报告问题。如果没有发现，输出 "NO FINDINGS"。
```

**合并规则**：
- 去重：如果子 agent 的发现与主审查重复，保留置信度更高的那个，标注"独立确认"
- 去重后合并到主报告

**如果子 agent 失败或超时**：跳过此步骤，注明"对抗性审查不可用"。

### Step 5: 兼容性 + 范围漂移

#### 兼容性影响分析

| 维度 | 检查项 |
|------|--------|
| **前端** | UI 组件、样式、路由变化 |
| **API** | 接口签名、请求/响应格式变化 |
| **依赖** | 包管理文件变化 |
| **数据库** | Schema 迁移、数据结构变化 |
| **配置** | 环境变量、配置文件变化 |

#### 范围漂移检测

1. 从 PR 描述、commit message 中提取"声明的意图"
2. 对比 diff 实际改动与声明意图
3. 检测：
   - **范围蔓延**：改动超出了声明意图
   - **需求缺失**：声明了但没实现的部分

输出：
```
范围检查: [CLEAN / DRIFT / MISSING]
意图: {1 行声明意图}
交付: {1 行实际改动}
[如有 drift: 列出超范围改动]
[如有 missing: 列出未实现需求]
```

### Step 6: 生成报告

**1. 准备目录和文件名：**
```bash
REPO_SLUG=$(echo "$OWNER/$REPO" | tr '/' '-')
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
REPORT_FILE="${REPORT_DIR}/${REPO_SLUG}/pr-${PR_NUMBER}-${TIMESTAMP}.md"
mkdir -p "$(dirname "$REPORT_FILE")"
```

**2. 报告模板：**

```markdown
# PR #{number} 分析报告

> **仓库**: {owner}/{repo}
> **分支**: {head} → {base}
> **作者**: {author}
> **状态**: {state}
> **分析时间**: {timestamp}

---

## TL;DR

- **目的**: {1 句话概括}
- **风险**: {低/中/高} — {一句话说明}
- **决策**: {APPROVE / REQUEST CHANGES / COMMENT}
- **关键关注点**: {0-2 个，无则写"无"}

---

## 1. PR 功能说明

{1-2 句话概括 PR 的核心目的}

**关联 Issue**: #{issue_num} - {issue_title}（如有，无则删除此行）

---

## 2. 兼容性影响

| 影响维度 | 评估 | 说明 |
|---------|------|------|
| 前端 | ✅/⚠️/❌ | ... |
| API | ✅/⚠️/❌ | ... |
| 依赖 | ✅/⚠️/❌ | ... |
| 数据库 | ✅/⚠️/❌ | ... |
| 配置 | ✅/⚠️/❌ | ... |

---

## 3. 重复 PR / 关联分析

### 关联 Issue

{无 / 或列出}

### 关联 PR

| PR | 状态 | 关系 | 说明 |
|----|------|------|------|
| #{num} | 状态 | 关系 | ... |

（无关联 PR 则写"无"）

---

## 4. Merge 状态

{✅ 无冲突 / ⛔ 有冲突 / ⚠️ 状态异常}

---

## 5. CI 状态

{✅ 通过 / ❌ 失败}

---

## 6. 已有 Review

{列出已有评论中的关键发现，标注评论者。如无则写"无已有评论"。}

---

## 7. 代码审查

### 数据流追踪

{列出追踪到的数据变换点和 roundtrip 验证结果。如发现数据丢失/不一致，标注为 CRITICAL。}

### 主审查发现

- **阻塞问题（CRITICAL）**: N 个
- **警告（WARNING）**: N 个
- **建议改进（INFORMATIONAL）**: M 个

{逐条列出，每条格式：}
[CRITICAL] (confidence: 8/10) path/to/file:line — 描述
  影响: ...
  建议: ...

### 对抗性审查

{独立子 agent 的发现，或"对抗性审查不可用"}

### 范围检查

```
范围检查: CLEAN / DRIFT / MISSING
意图: ...
交付: ...
```

---

## 8. 总结

### 最终评估

{对 PR 的整体评价，是否建议合并}

### 需作者修复（blocking）

{无 / 或列出}

### 建议改进（non-blocking）

{无 / 或列出}

---

## 9. Review 操作建议

### 推荐操作

{APPROVE / REQUEST CHANGES / COMMENT}

### 可直接使用的 Review 评论

{生成一段完整的 review 评论文本，reviewer 可以直接复制粘贴到 GitHub PR review 中。根据 PR 作者语言选择英文或中文。}

### 可执行的 gh 命令

```bash
# Request changes
gh pr review {number} --repo {owner}/{repo} --request-changes --body "..."

# Approve
gh pr review {number} --repo {owner}/{repo} --approve --body "..."

# 仅评论
gh pr comment {number} --repo {owner}/{repo} --body "..."
```

---

*报告由 [大铭](https://github.com/yinwm) 的 `/pr-analyze` 生成 (v0.6.0)*
```

**4. 保存报告到文件。**

**5. 输出报告到终端（完整内容，不是文件路径）。**

**6. 输出确认：**
```
✅ 报告已保存到: {report_file_path}
```

**7. 交互式操作选项：**

报告输出后，使用 AskUserQuestion 询问用户下一步操作：

```
问题：分析完成，接下来要怎么操作？

A) 直接 approve（我会执行 gh pr approve）
B) Request changes（我会带上 blocking 问题）
C) 仅评论（不 approve/request changes）
D) 只保存报告，不操作
```

根据用户选择，直接执行对应的 gh 命令。如果用户选择 A（approve），追问是否同时 merge。

**注意：不要自动删除临时目录。** 用户可能在后续操作中需要访问克隆的完整源码（如深挖某个文件、跑测试等）。临时目录路径在报告头部已标注，用户自行决定何时清理。

---

## 配置修改

当用户请求修改报告存储目录时：

**触发短语：**
- "修改 PR 报告存储目录"
- "设置 PR 报告存储路径"
- "更改 pr-analyze 配置"

**流程：**
1. 读取当前配置并显示
2. 使用 `AskUserQuestion` 询问新路径
3. 更新 `config.json`
4. 确认修改成功

---

## 严重度校准

### 三级分类

| 级别 | 标准 | 示例 |
|------|------|------|
| CRITICAL | 运行时错误/安全漏洞/数据丢失，正常场景可触发，无安全网 | 格式转换丢失字段导致数据损坏 |
| WARNING | 异常行为，但存在安全网或影响有限 | token 估算偏低但有 retry 机制 |
| INFORMATIONAL | 设计偏好、可维护性建议 | 文件过长建议拆分 |

**判定口诀**：删除这行代码会引发 bug 且无安全网 → CRITICAL。有安全网兜底 → WARNING。"我会选择不同的做法" → INFORMATIONAL。

### 置信度标注

每个发现必须附带置信度（1-10），详见 `checklist.md`。

**发现格式**：
```
[CRITICAL] (confidence: 8/10) path/to/file:42 — 描述
  影响: ...
  建议: ...
```

---

## 注意事项

1. **CI 检查失败时**：输出警告，但不阻止分析继续
2. **无关联 Issue 时**：在对应位置写"无"，不要展开空段落
3. **大型 PR 时**：diff 可能很大，重点关注核心文件
4. **私有仓库**：确保 `gh` 已认证且有访问权限
5. **报告目录权限**：确保有写入权限，否则提示用户
6. **同一 PR 多次分析**：使用时间戳区分，不会覆盖
7. **信息密度优先**：能用一句话说清的不用一段话，能用表格的不用列表
8. **Clone 失败时**：回退到 diff-only 模式，报告中注明
9. **不自动删除临时目录**：保留克隆的完整源码供后续操作使用，路径在报告中标注
10. **已有评论优先**：不重复已有发现，专注于未覆盖的角度
