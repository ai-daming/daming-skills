# issue-pr-pipeline

把一个 GitHub issue 交给三个无头 agent 接力交付：**Spec Agent**（准入预检 + 决策包 + 实施契约）、**Coding Agent**（按契约 TDD 实现提 PR）、**Review Agent**（pr-analyze 协议独立审查），直到合并进主干开发分支。你的参与被压缩到两个动作：**拍板业务决策**、**放行合并**。

在 mamamate 仓库完成过全链路实测：预检补关历史 issue、两轮返工、CI 红门归因、自动合并、磁盘自动清理，全部按设计走通。

```
输入：GitHub issue（owner/repo#123 | URL | 裸号）
   ↓
⓪ 预检 ── 已修完 → 补证关单 ✅   业务过时 → not planned ✅   不适用 → pipeline/hold
① SPEC：事实调查（代码能查的不问你）+ 决策包（grill 纪律，每题带推荐）
   ├─ 有【问你】题 → 答题器逐题拍板（回车=推荐）
   └─ 实施契约成文（目标/边界/验收点/TDD 清单），回写 issue
② CODE：专属 worktree 按契约 TDD，提 PR（关联 issue，不自动关单）
③ REVIEW：独立工作树本地验证 + 五遍审查，绿门 = 本地验证全绿
   ├─ APPROVE → 合并 → pipeline/merged（差你验收关单）✅
   ├─ 打回 → 审查报告评论 issue → 自动返工（最多 max_rounds 轮）
   └─ 中断/存疑 → pipeline/blocked + 现场快照，等你解锁 ⛔
```

## 安装

```bash
git clone https://github.com/ai-daming/daming-skills.git
ln -s $(pwd)/daming-skills/skills/issue-pr-pipeline ~/.pi/agent/skills/issue-pr-pipeline  # 或复制
```

前置：`pi`（headless agent CLI）、`gh`（已登录）、`jq`；同仓库需有兄弟 skill `grill/` 与 `pr-analyze/`（软链整个 daming-skills 即可），`pr-analyze` 需配好 `config.json` 的 `report_dir`。

首次配置：复制 `config.example.json` 为 `config.json`：

```json
{
  "work_dir": "/your/pipeline-work",
  "agent_cli": "pi",
  "coding_model": "",                          // 可选：给 Coding Agent 指定模型
  "max_rounds": 3,                             // 返工安全阀
  "merge_policy": "auto-if-green",             // 绿门=审查通过且本地验证全绿，自动合并
  "cleanup_after_merge": true,                 // 合并后自动清 GB 级 worktree，保留 KB 级证据
  "repos": {
    "you/your-repo": { "main_repo_path": "/path/to/local/checkout", "base_branch": "dev" }
  }
}
```

`repos` 可选：配了的仓库用你的本地检出；没配的 `owner/repo#123` 自动 clone 到 `work_dir/repos/`，base 分支自动探测（有 `dev` 用 `dev`，否则默认分支）。

## 快速开始

```bash
cd <skill 目录>
./run.sh spec you/repo#500      # 预检+出决策包 → 自动进答题器 → 答完 Y 出契约
./run.sh loop you/repo#500      # 无人值守：coding→review→返工→合并，两个关口外全自动
```

睡前批量模式：`for n in 500 502 504; do ./run.sh spec you/repo#$n; done` 答完所有题，再 `for n in 500 502 504; do ./run.sh loop you/repo#$n; done` 排队过夜。

所有命令的轮次参数可省略（`review you/repo#500` 自动审当前轮）；issue 标了 `pipeline/manual` 的单会被拒绝进入（那是维护者的保留地）。

## 两个人工关口

1. **决策包**：只有真正的业务取舍会问你（grill 决策树 + frontier，一次性批量出题）。每题标档位：
   - `【问你】` 倾向某答案但拿不准（钱、身份、状态机、业务语义）——答题器停下来等你
   - `【默认过】` 事实/仓库既有模式充分支持——自动采纳推荐，但题面、判断依据完整保留，随时可推翻
   - **档位只分注意力、不分留痕**：两类题在决策包里信息量完全一致
2. **合并放行**：`auto-if-green` 绿门自动、异常挂起；`manual` 每次问你；强行合并 `FORCE=1`

## 全程留痕（历史是资产，issue 长度不是成本）

每个状态转换都回写 GitHub，带 `🤖 流水线自动生成` 徽标、内容哈希幂等：决策包、契约、开工、每轮审查结论、合并、停机快照。issue 上的 `pipeline/*` 标签是状态机（一单一标签）：

| 标签 | 含义 |
|---|---|
| `pipeline/hold` | 不适用（要真机/业务没定），原因见评论，条件变了会毕业 |
| `pipeline/manual` | 维护者保留地，机器一律跳过（人打人摘） |
| `pipeline/decisions` | 待拍板，决策包见评论 |
| `pipeline/ready` | 契约就绪，待启动开发（./run.sh loop） |
| `pipeline/queued` | 开发队列进行中 |
| `pipeline/blocked` | 中途受阻，等你解锁，现场快照见评论 |
| `pipeline/merged` | 已合并，差你验收后关单 |

## 门禁语义

绿门 = Review Agent 在精确 head 上的本地验证（测试/build/lint 全绿）。GitHub Actions 测试工作流可禁用（账单原因时建议如此，`gh api -X PUT repos/:owner/:repo/actions/workflows/<id>/disable`），checks 降级为参考信号：红了须归因（PR 引入/基线既有/基础设施/flaky），基础设施类红灯不阻塞。禁用决策会记录在合并评论里，恢复启用一条命令。

## 工作区与磁盘

| 位置 | 内容 | 量级 |
|---|---|---|
| `work_dir/<project>/issue-N/wt` | Coding 专属 worktree（跨轮复用） | GB 级 |
| `/tmp/pr-analyze-<PR>-*` | Review 独立审查工作树 | GB 级 |
| `work_dir/<project>/issue-N/{logs,contract.md,decision-package*}` | 证据与状态 | KB 级，长期保留 |

清理时机：合并成功后自动一次（`cleanup_after_merge: true`）；中途轮间不清（复审复用审查工作树更快，`max_rounds` 封顶）。手动：`./run.sh cleanup <ref>`（需 MERGED 记录，强制 FORCE=1）。

## 常见问题

- **跑着跑着静默**：`--mode json` 流式直播工具调用与正文；长时间无输出是在跑测试（gradle/vitest 不写会话）。
- **`缺失输出契约`**：agent 中途断线（网络）没写出结论行——重跑同一条命令，会话延续不丢上下文。
- **为什么没有 GitHub CI**：见「门禁语义」；本地验证比欠费红门的信号更真。
- **多项目同号冲突**：工作区按 `<project>/issue-N` 分组，不会撞。
- **改脚本安全吗**：run.sh 启动时自快照执行，运行中编辑原文件不影响在跑实例。

## 文档

- `SKILL.md`：编排协议（给驱动本流水线的 agent 读）
- `references/pipeline-contract.md`：决策包格式、契约结构、标签命名空间、边界处置
- `prompts/`：三个 agent 的提示词模板
