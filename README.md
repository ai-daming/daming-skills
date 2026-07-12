# daming-skills

大铭的个人 AI Skill 集合。

每个 skill 位于 `skills/<name>/` 目录下，包含 `SKILL.md`（Claude Code / ZCode 等 agent skill 格式）及配套资源。

## 可用 Skills

| Skill | 说明 |
|-------|------|
| [pr-analyze](skills/pr-analyze/) | 对 GitHub PR 进行全面分析，生成结构化中文报告，含数据流追踪、对抗性审查、兼容性评估。 |

## 安装

### 方式一：手动复制（最简单）

```bash
git clone https://github.com/ai-daming/daming-skills.git
# 复制需要的 skill 到你的 skills 目录（Claude Code 默认 ~/.claude/skills/）
cp -r daming-skills/skills/pr-analyze ~/.claude/skills/
```

### 方式二：软链（方便更新）

```bash
git clone https://github.com/ai-daming/daming-skills.git ~/work/daming-skills
ln -s ~/work/daming-skills/skills/pr-analyze ~/.claude/skills/pr-analyze
```

## License

MIT，见 [LICENSE](LICENSE)。
