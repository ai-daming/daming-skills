# daming-skills

大铭的个人 AI Skill 集合。

每个 skill 位于 `skills/<name>/` 目录下，包含 `SKILL.md`（Claude Code / ZCode 等 agent skill 格式）及配套资源。

## 可用 Skills

| Skill | 说明 |
|-------|------|
| [issue-gate](skills/issue-gate/) | 按未解决的问题路由到所需门禁，复用已有证据与授权，不固定串行执行全部 Skills。 |
| [gh-issue](skills/gh-issue/) | 以仓库 Issue 证据契约为准，安全创建、更新、评论、分类、关联和关闭 GitHub Issue。 |
| [challenge](skills/challenge/) | 在规划或实现前挑战问题框架，检验问题是否真实、关键假设是否成立，并寻找更高杠杆的替代方案。 |
| [grill](skills/grill/) | 用依赖感知的决策树和 frontier 逐轮消除方案中的关键决策歧义。 |
| [impl-gate](skills/impl-gate/) | 在编码前核验 Accepted 架构是否同时覆盖算法、数据结构、失败恢复与迁移边界。 |
| [pr-analyze](skills/pr-analyze/) | 对 GitHub PR 的精确 base/head、契约、不变量、CI、历史 finding 和代码进行证据绑定审查。 |

## 使用边界

- 问题前提不明用 `challenge`；存在用户拥有的重大取舍用 `grill`；实现准入用 `impl-gate`。不知道下一步用哪个时，让 `issue-gate` 路由。
- `impl-gate` 区分完整核验和基于旧设计证据的增量核验。新 HEAD 要重新核验，但不自动要求重做设计或重复接受未变的决定。
- `pr-analyze` 审查当前代码；复审重新运行旧复现、检查新增 diff 和受影响不变量。设计就绪不能替代代码 review。
- Issue 写入用 `gh-issue`，PR 评论/review/merge 用 `pr-analyze`。同一目标、正文和动作已有明确授权时不重复确认；新设计接受、实现、提交、push、合并、部署各自需要相应授权。

移交检查自动随三个入口执行：`impl-gate` 检查设计前置步骤，`pr-analyze` 判断遗留义务影响哪个关口，`gh-issue` 在关闭前核验承接。已移交必须同时有可定位的工作和完成标准、已确认的责任、有人维护的待办清单及复查日期/触发条件；现有发布任务中的必做步骤也可承接，不要求重复建 Issue。关键词仅辅助发现，不能替代语义核验；当前 AC 未完成也不能靠另立任务关闭。

## 安装

### 方式一：手动复制（最简单）

```bash
git clone https://github.com/ai-daming/daming-skills.git
# 以 challenge 为例；其他 skill 替换目录名即可
cp -r daming-skills/skills/challenge ~/.codex/skills/   # Codex
cp -r daming-skills/skills/challenge ~/.claude/skills/ # Claude Code
```

### 方式二：软链（方便更新）

```bash
git clone https://github.com/ai-daming/daming-skills.git ~/work/daming-skills
ln -s ~/work/daming-skills/skills/challenge ~/.codex/skills/challenge
```

`pr-analyze` 首次使用前，将 `skills/pr-analyze/config.example.json` 复制为同目录的 `config.json`，并把 `report_dir` 改成实际的绝对路径。本机 `config.json` 不随仓库发布。

## License

MIT，见 [LICENSE](LICENSE)。
