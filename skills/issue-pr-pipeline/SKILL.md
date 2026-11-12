---
name: issue-pr-pipeline
description: 编排「Issue → Spec 准入与决策包 → Coding Agent 实现 → Review Agent 审查 → 合并」的自动交付循环。给定一个 GitHub issue，先做预检与规格分析，把需要人工拍板的业务决策一次性打包问完并生成实施契约，然后由无头 agent 按契约 TDD 实现提 PR、按 pr-analyze 协议独立审查，通过则合并、打回则返工，直到合并或触发安全阀。适用于根因可静态定位、验收可自动验证的代码类 issue；需要真机复现或业务创意类 issue 会在准入阶段被判 NOT_READY。
---

# Issue → PR 交付流水线

把一个 GitHub issue 交给三个无头 agent 接力完成：**Spec Agent**（准入 + 决策包 + 实施契约）、**Coding Agent**（TDD 实现提 PR）、**Review Agent**（pr-analyze 协议独立审查），编排者（加载本 skill 的 agent）驱动全程并在两个人工关口转交决策。

## 前置条件

1. `gh` 已登录且有目标仓库写权限；`pi`（或兼容的 headless agent CLI）已安装。
2. 本 skill 的兄弟目录存在 `grill/` 与 `pr-analyze/`（同一 daming-skills 检出内），`pr-analyze` 已配置 `config.json` 的 `report_dir`。
3. 已复制 `config.example.json` 为本目录 `config.json`（`config.json` 不随仓库发布）并填好目标仓库信息。
4. 用户已明确授权对指定 issue 运行本流水线（含授权 Coding Agent 在专属分支上 commit/push/建 PR）。

## 总流程

```
输入：GitHub Issue
   ↓
⓪ 预检（Spec Agent 先行）：
   ├─ 已随历史 PR 完成且验收满足 → 补证关闭→ 结束
   ├─ 业务已过时、场景不再适用 → not planned 关闭→ 结束
   └─ 有效 → 继续
① SPEC：深度分析（事实，agent 自己查）+ 决策审讯（grill 纪律）
   ├─ NOT_READY（要真机/业务未定/范围过大）→ 向用户报告，结束
   ├─ 有待拍板决策 → 生成决策包 →【人工关口 1】用户一次批量拍板
   └─ 生成实施契约（目标/边界/验收点/TDD 场景/非目标/决策台账）
② CODE：Coding Agent 按契约 TDD 实现，专属分支提 PR（base=主干开发分支）
③ REVIEW：Review Agent 按 pr-analyze 协议独立审查，输出 PIPELINE_VERDICT
   ├─ APPROVE → 按 merge_policy 合并 → 评论 issue → 结束 ✅
   ├─ CHANGES_REQUIRED → 审查报告作为反馈评论 issue → 回 ②（同分支同 PR 返工）
   └─ WAIT → 停机等人工（head 漂移/门禁未知/需新决策）
⓸ 安全阀：超过 max_rounds 轮未通过 → 停机等人工
```

## 人工关口（仅两个）

1. **决策包**：Spec Agent 产出后，用户跑 `run.sh answer`（逐题交互、回车采纳推荐）或一行式作答；禁止拆成多次零碎询问；用户未答前不得启动 Coding Agent。
2. **合并放行**：按 `merge_policy`——`auto-if-green`（按仓库及本次授权要求完成审查和验证后自动合并）或 `manual`（自动循环停下，维护者明确执行 `finish`）。脚本将审查结论绑定 PR、轮次和 head，合并时校验 head。强行合并必须由用户明确拍板（FORCE=1）并记录理由。

关单动作（预检的 completed / not planned 出口）需用户确认后按 `gh-issue` 协议执行，不自动关闭。

## 编排职责（加载本 skill 的 agent 必须遵守）

- **逐阶段驱动** `run.sh`（见下），每阶段之间解析输出契约、检查产物、更新状态，不盲目连跑。
- **单实例锁**：`run.sh` 自带锁文件；发现目标已在运行时报告并等待，不重复启动。
- **传递基线**：实施契约必须先落到 issue 评论，Coding/Review Agent 均以该契约 + issue 为验收基线。脚本绑定契约、决策包和答复内容；变更后须重新 spec，审查后变更须重新 review。升级前旧任务也须重新 spec 以建立绑定。
- **反馈回路**：Review Agent 的本轮报告回写 issue，打回时也是 Coding Agent 下一轮的返工输入；回写失败要报告。
- **验证范围**：默认只运行相关测试和必要的受影响批次；只有用户明确要求时才运行全量回归。按实际结果报告测试、构建、lint 和 CI，不假定所有仓库的工作流状态相同。
- **失败诚实**：任何阶段 BLOCKED/超时/输出契约缺失，如实报告并停在该阶段，不伪造进度。
- **不越权**：编排者与三个 agent 都不部署、不改生产配置；生产验收类验收点留给维护者，合并评论须注明。
- **全程留痕**：决策包、契约、开工、审查、合并和停机尽量回写 GitHub；失败时如实报告。决策包或契约回写失败时不进入下一阶段，其他回写失败保留本地证据。

## run.sh 用法

issue-ref 支持四种写法：`500`（裸号，需 config 顶层配好默认仓库）、`owner/repo#500`、`owner/repo 500`、完整 issue URL。

```bash
cd <本 skill 目录>
./run.sh spec ai-daming/mamamate#500   # 多项目推荐写法：仓库从参数解析
./run.sh answer ai-daming/mamamate#500   # 交互答题：逐题选、回车=推荐、可写意见；答完问是否继续出契约
./run.sh answer ai-daming/mamamate#500 "Q1=B;Q2=A"  # 非交互一行式（编排 agent 用）
./run.sh spec 500                      # 裸号：用 config 顶层 repo/base_branch/main_repo_path
./run.sh init <issue-ref>              # 创建 Coding Agent 专属 worktree/分支
./run.sh coding <issue-ref> [round]    # Coding Agent（不传轮次自动=打回次数+1）
./run.sh review <issue-ref> [round]    # Review Agent（不传轮次自动=当前轮）
./run.sh finish <issue-ref> [round]    # 合并 + issue 评论（轮次同上，可不传）
./run.sh loop <issue-ref>              # 全自动循环（契约就绪后）：两个人工关口自动停
./run.sh cleanup <issue-ref>           # 清理该期重量级产物（需 MERGED 记录）
./run.sh status <issue-ref>            # 查看当前状态
```

启动目录无关：脚本从自身位置与 config.json 解析一切路径，在任何目录执行都一样。

**仓库解析顺序**（带 repo 前缀时）：config 的 `repos` 映射（可指向已有本地检出并指定 base/project）→ 自动 clone 到 `work_dir/repos/<name>`（base 自动探测：有 `dev` 分支用 dev，否则用仓库默认分支）。裸号模式仅用 config 顶层三字段，适合单项目常用场景。

## 工作区布局：各 agent 在哪里干活

| Agent | 工作目录 | 说明 |
|---|---|---|
| Spec | `main_repo_path`（目标项目本地主检出） | 只读纪律；在此目录是为了自动加载项目的 agent 指引（AGENTS.md 等） |
| Coding | `work_dir/<project>/issue-<N>/wt`（专属 git worktree，分支 `agent/issue-<N>`） | 与你的主检出完全隔离；worktree 是全量检出，项目指引同样自动加载 |
| Review | `main_repo_path` + `work_dir/<project>/issue-<N>/review-worktrees/` 下的独立 detached worktree | 本次流水线专用目录；旧版 `/tmp` 工作树不自动清理 |

每期状态集中在 `work_dir/<project>/issue-<N>/`：`state.env`（PR 号/轮次/verdict）、`decision-package(.answers).md`、`contract.md`、`wt/`、`logs/`（各轮完整输出与反馈，只追加不删除）。

`<project>` 分组目录避免多项目 issue 同号冲突：优先取 config 的 `project` 字段，缺省从 `repo` 名推导（`owner/name` → `name`）。

## 磁盘卫生

每期重量级产物（KB 级证据之外的部分）：

| 产物 | 位置 | 量级 |
|---|---|---|
| Coding 专属 worktree（含构建产物、依赖） | `work_dir/<project>/issue-<N>/wt` | JVM/前端项目每期可达 GB 级 |
| Review 审查工作树 | `work_dir/<project>/issue-<N>/review-worktrees/` | 同量级 |
| 日志/契约/决策包/状态 | `work_dir/<project>/issue-<N>/` | 随运行增长，可长期保留 |

处置：

```bash
./run.sh cleanup <issue>   # 合并后清理该期重量级产物（无 MERGED 记录时拒绝，FORCE=1 可强制）
```

或配置 `"cleanup_after_merge": true`（默认 false），合并成功后自动清理；日志与契约始终保留。编排者应在交付完成后（无论是否自动清理）向用户报告磁盘占用情况。

## Agent 输出契约

| Agent | 最后一行必须是 |
|---|---|
| Spec | `SPEC_RESULT: READY` \| `DECISIONS_REQUIRED` \| `NOT_READY=<原因>` \| `CLOSE_RECOMMENDED=<completed\|not_planned>; <证据摘要>` |
| Coding | `PIPELINE_RESULT: PR=<编号>` \| `PUSHED` \| `BLOCKED=<原因>` |
| Review | `PIPELINE_VERDICT: APPROVE` \| `CHANGES_REQUIRED` \| `WAIT` |

编排者只信任这些机器行；缺失即视为该阶段失败。

## 详细协议

- 各 agent 提示词模板：`prompts/`（spec-agent.md、coding-round1.md、coding-fix.md、review-agent.md），占位符由 run.sh 注入。
- 决策包格式、契约结构、边界情况处置（预检关闭、契约缺口兜底、CI 红门归因）：见 [references/pipeline-contract.md](references/pipeline-contract.md)。

## 实测校准

本流水线在 mamamate #464 上完成过全链路实测：预检补关 #364（completed）与 #476（not planned）、两轮 A/B 返工、F3 类契约缺口由 Review Agent 抓出并经用户拍板后闭环、CI 红门归因后由用户拍板带红合并。SKILL.md 与提示词中的纪律（决策包一次性、事实不问用户、日志不可删、锁文件）均来自该实测教训，改动前先理解其原因。
