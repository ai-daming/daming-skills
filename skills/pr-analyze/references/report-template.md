# PR 分析报告模板

报告分两层：先给维护者一眼能懂的决策简报，再给可复核的技术附录。同一个事实只写一次；后文用 Finding ID、Invariant ID 或表格行号引用，不要换一种说法重复。

按实际触发条件选择下列内容，不要求机械填满所有章节。始终保留精确 base/head、最终回读、证据边界、发现、验证和下一步。复审保留旧 head、delta、关闭账本、不变量/熔断预检与范围审计结论；架构、详细审计矩阵、复现包和 GitHub 预览按需展开。仓库要求的检查即使未执行也不能省略；写“未执行”及原因，不得伪装成“不适用”。

简单 PR 可用短报告完整表达适用证据。复审的关闭状态在 B3 只记录一次，简报只提未关闭项与账本链接；不重复制作两张关闭表。人话 finding 可与 B5 技术证据合并在同一位置，其他位置引用它。

```markdown
# PR #{number} 分析报告

> **PR**: {owner/repo}#{number} — {url}
> **审查基线**: `{headRefOid}` against `{baseRefOid}`
> **身份 / 模式**: Review Agent / {first-review | re-review}
> **本轮触发**: {explicit PR | contextual 重新 review | equivalent；已重新调用 skill 并刷新 live facts}
> **源码**: {matching-local-worktree | isolated-clone | diff-only} — {path / unavailable}
> **分析时间**: {timestamp}

---

# A. 决策简报

## 结论

**建议动作**: {APPROVE | REQUEST CHANGES | COMMENT | WAIT}

{两到四句人话：这个 PR 要改变什么；正常什么场景会出错或为什么可以通过；谁会看到什么后果。不要先写内部状态码。}

- **当前 head**: `{headRefOid}`，最终回读 {未变化 | 已变化}
- **GitHub 门禁**: {draft / merge / CI / review decision 的一句话结果}
- **架构准入**: {READY 等状态 + 人话解释；不适用则写不适用}
- **熔断**: {先写人话，再附 NORMAL / DESIGN_TRIPPED / EVIDENCE_TRIPPED / RELEASED}
- **范围审计**: {NOT_REQUIRED | INCOMPLETE | COMPLETE} — {证据位置；没有逐成员证据不得写 COMPLETE}
- **已完成动作**: {分析、代码审查、本地验证、GitHub comment/review、approval、merge 中实际完成的项}

## 上轮问题关闭情况（仅 re-review）

{概括关闭数量和仍未关闭的 Finding ID，链接 B3 唯一的关闭账本；不要再复制一份表。}

## 当前发现

### F1 — [CRITICAL] <人话标题> (confidence: 9/10)

**会发生什么：** {普通语言的可观察错误。}

**举例：** {具体人物/请求/记录/重试序列。}

**为什么现在阻塞：** {影响 + 契约；若不阻塞则写“为什么是 warning”。}

**怎么才算修好：** {可观察的最小关闭条件。}

**非目标：** {不要求的架构、重构或扩展。}

{每个 finding 只在这里完整解释一次。Technical evidence 放附录 B5。}

## 下一步

- **Blocking**: {用 F1/F2 引用，不重述全文；无则写无}
- **Non-blocking**: {用 Finding ID 引用；无则写无}
- **推荐动作**: {一个明确动作，不直接执行未授权 GitHub mutation}

---

# B. 技术证据附录

## B1. PR、基线与证据边界

| 项目 | 结果 | 证据 |
|---|---|---|
| PR 状态 / draft | ... | live GitHub readback |
| Base SHA | `{baseRefOid}` | ... |
| Head SHA | `{headRefOid}` | ... |
| 最终 head 回读 | ... | timestamp + source |
| Mergeable / merge state | ... | ... |
| Required checks | ... | 不把 pending/UNSTABLE/BLOCKED/UNKNOWN 写成绿 |
| Review decision | ... | formal review 与 ordinary comment 分开 |
| Source checkout / merge base / diff check | ... | command/result |

**失败或降级步骤**: {原始错误、fallback、对置信度的影响；无则写无}

**未验证边界**: {没有运行或明确排除的事项}

## B2. 意图、架构与关联工作

**声明意图**: ...

**实际交付**: ...

### Implementation Gate

| 项目 | 结果 | 证据 |
|---|---|---|
| Architecture source | ... | immutable path/URL/revision |
| Algorithm coverage | complete / gaps / not required | ... |
| Data-structure coverage | complete / gaps / not required | ... |
| Design receipt | valid / stale / missing / not required | ... |
| Verification mode | full / delta | previous baseline, impact trace and reused evidence when applicable |
| Verdict | ... | minimum next gate |

### 关联 / 可能重复 PR

**检索或复用检查**: {输入、状态范围；re-review 复用时说明 Issue/title/body/scope/branch population 未变}

| PR | 状态 | 关系 | 判断依据 |
|---|---|---|---|
| ... | ... | ... | ... |

## B3. Closure ledger 与不变量

| Finding | 人话不变量 / ID | 契约锚点 | 原复现 | 声称修复 commit | 当前 exact-head 结果 | 状态 |
|---|---|---|---|---|---|---|
| ... | ... | ... | REPRO-ID | ... | ... | CLOSED / OPEN / PARTIAL / NOT RECHECKED |

| Invariant ID | 人话命题 | 事实所有者 | 权威成员 / 等价类 | 历史违反点 | 熔断 | 范围审计 |
|---|---|---|---|---|---|---|
| ... | ... | ... | ... | ... | ... | ... |

### 熔断记录（非 NORMAL 时）

- **触发条件**: ...
- **冻结范围**: ...
- **排除项 / 非目标**: ...
- **要求的关闭证据**: ...
- **当前解除结果**: ...

熔断不自动改变 Finding severity，也不自动成为 merge gate。

## B4. 完整性覆盖证据

**选择的审计表**: {state exits | producer-consumer/reconciliation | change-impact | evidence oracle}

`COMPLETE` 时必须在这里放逐成员矩阵，或链接到 report-adjacent durable artifact。下面这种按大类概括的摘要不能取得 COMPLETE 资格。

| Row ID | 成员 / 等价类 | Enforcement point / boundary | Exact-head 验证 | 结果 | 排除理由（如有） |
|---|---|---|---|---|---|
| A-1 | ... | path:line | test/repro/static trace | pass/fail | ... |

### 关键交互

| Interaction ID | 两个边界为何会互相影响 | 验证 | 结果 |
|---|---|---|---|
| I-1 | ... | ... | ... |

**完整性结论**: {NOT_REQUIRED | INCOMPLETE | COMPLETE} — {证据位置}

**仍未验证**: {明确成员/类/交互；无则写“无，见逐成员矩阵”，不能只写“无”}

## B5. Finding 技术证据

### F1

- **位置**: `path:line`
- **契约锚点**: ...
- **Observed fact**: ...
- **Inference**: ...
- **Current-head reproduction**: REPRO-1 / command / output
- **复审新增说明**: {new diff / previously missed / why current PR}
- **Severity reason**: {正常可达性、影响、安全网；breaker 不参与自动升级}

## B6. 验证与 evidence oracle

| 命令或 CI check | 结果 | 归因 |
|---|---|---|
| ... | pass/fail/pending/not run | PR / base / unknown |

| Claim | 真实判定公式 | 负向样例会失败 | 测量窗口 | Exact head / dirty / tool identity | 结果 |
|---|---|---|---|---|---|
| ... | ... | yes/no/not run | ... | ... | valid/invalid |

### Durable reproduction index

| Repro ID | Invariant | Exact head | Durable path | SHA-256 | Command | Exit/result | Environment caveat |
|---|---|---|---|---|---|---|---|
| REPRO-1 | ... | ... | `{report_dir}/.../artifacts/...` | ... | ... | ... | ... |

简单仓库命令可直接记录 command/result；reviewer 编写的非平凡脚本或 fixture 不得只留在 `/tmp`。

## B7. 兼容性、范围与奥卡姆

| 维度 | 评估 | 说明 |
|---|---|---|
| 前端 | ✅ / ⚠️ / ❌ / N/A | ... |
| API / 事件 / 命令 | ... | ... |
| 依赖 | ... | ... |
| 数据库 / 持久化 | ... | ... |
| 配置 / 部署 | ... | ... |

```text
范围检查: CLEAN / DRIFT / MISSING
意图: ...
交付: ...
超范围或缺失: ...
```

| 被要求或新增的概念 | 对应 AC | 生产消费者 | 删除后的行为差异 | 结论 |
|---|---|---|---|---|
| ... | ... | ... | ... | 保留 / 复用 / 删除 / follow-up |

### 未完成义务（存在相关事项时）

| 事项 / 来源 | 当前 AC 或后续关口 | 状态 | 完成证据或承接链接 | 责任及接受依据 | 复查日期 / 触发条件 | 缺口及阻塞动作 |
|---|---|---|---|---|---|---|
| ... | implementation / merge / release / closure | 已完成 / 已移交 / 明确不做 / 尚未承接 | ... | ... | ... | ... |

复用已有移交清单并链接；不要复制第二份。真正非目标/可选建议可简述排除理由。无相关义务时简述核验范围，不建空表；必要来源未读到不得称“无”。仅阻塞其实际所属关口；另建 Issue 不等于原 AC 完成。若 merge 会自动关闭关联 Issue，核对其关闭条件及本表证据。

## B8. GitHub 操作预览（仅用户请求 mutation 时）

**目标**: `{owner/repo}#{number}` at `{headRefOid}`

**动作**: COMMENT / APPROVE / REQUEST_CHANGES / MERGE

**完整正文**:

**身份：Review Agent**

{人话结论 + 每个 finding 的例子/影响/关闭条件 + 必要 technical evidence；可省略 GitHub 页面已有的行政元数据。}

**执行方式**: 本地 body file + `--body-file`；执行后回读 URL、author、state/head。

---

*报告由大铭的 `/pr-analyze` v0.14.0 生成。Copyright © 大铭 · [github.com/ai-daming](https://github.com/ai-daming)。*
```
