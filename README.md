# daming-skills

大铭的个人 AI Skill 集合。

每个 skill 位于 `skills/<name>/` 目录下，包含 `SKILL.md`（Claude Code / ZCode 等 agent skill 格式）及配套资源。

## 可用 Skills

| Skill | 说明 |
|-------|------|
| [pr-analyze](skills/pr-analyze/) | 对 GitHub PR 进行全面分析，生成结构化中文报告，含数据流追踪、对抗性审查、兼容性评估。 |
| [challenge](skills/challenge/) | 在规划或实现前挑战问题框架，检验问题是否真实、关键假设是否成立，并寻找更高杠杆的替代方案。 |
| [grill](skills/grill/) | 用依赖感知的决策树和 frontier 逐轮消除方案中的关键决策歧义。 |

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

## License

MIT，见 [LICENSE](LICENSE)。
