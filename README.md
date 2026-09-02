# daming-skills

大铭的个人 AI Skill 集合。

每个 skill 位于 `skills/<name>/` 目录下，包含 `SKILL.md`（Claude Code / ZCode 等 agent skill 格式）及配套资源。

## 可用 Skills

| Skill | 说明 |
|-------|------|
| [gh-issue](skills/gh-issue/) | 以仓库 Issue 证据契约为准，安全创建、更新、评论、分类、关联和关闭 GitHub Issue。 |
| [challenge](skills/challenge/) | 在规划或实现前挑战问题框架，检验问题是否真实、关键假设是否成立，并寻找更高杠杆的替代方案。 |
| [grill](skills/grill/) | 用依赖感知的决策树和 frontier 逐轮消除方案中的关键决策歧义。 |
| [impl-gate](skills/impl-gate/) | 在编码前核验 Accepted 架构是否同时覆盖算法、数据结构、失败恢复与迁移边界。 |
| [pr-analyze](skills/pr-analyze/) | 对 GitHub PR 的精确 base/head、契约、不变量、CI、历史 finding 和代码进行证据绑定审查。 |

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
