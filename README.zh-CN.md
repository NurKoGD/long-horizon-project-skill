# long-horizon-project

[English](README.md) | [简体中文](README.zh-CN.md)

一个面向多个智能体的长期项目协作 Skill。它把项目状态保存到对话之外的文件中，让智能体可以用更少的上下文，在不同对话、上下文重置和不同设备之间继续开发。

本仓库是可分发的 Skill 源码包。通用 Skill 位于 `.agents/skills/`，根目录用于放置说明文档和维护材料。

## 功能

- 在 `skilluse/context/current.md` 中保存紧凑的项目 checkpoint。
- 将阶段计划、决策、日志和其他智能体辅助文件集中到 `skilluse/`。
- 恢复项目时只读取当前阶段和必要的项目文件，减少 token 消耗。
- 每个对话只处理一个阶段，不自动进入下一阶段。
- 支持把 `skilluse/` 作为独立的私有 Git 仓库。
- 记录实际 Git 状态，但不自行规定 commit 或 push 策略。
- 支持在原对话没有使用该 Skill 的情况下导入并恢复项目状态。

它不会迁移完整聊天记录、自动创建新对话、替用户选择 Git 工作流，也不能强制带有硬编码输出路径的第三方 Skill 使用 `skilluse/`。

## 仓库结构

```text
.
├── .agents/
│   └── skills/
│       └── long-horizon-project/
│           ├── SKILL.md
│           ├── agents/openai.yaml
│           ├── references/
│           ├── scripts/
│           └── templates/
├── tests/
│   └── README.md
├── CONTRIBUTING.md
├── README.md
├── README.zh-CN.md
└── .gitignore
```

当前仓库暂未包含 Codex 或 Claude Code 的生命周期 Hooks。标准 Skill 可以在支持 Agent Skills 格式的智能体中使用；后续可以添加宿主专用插件和 Hooks，而不改变通用 Skill。

## 安装

### Skills CLI

将仓库发布到 GitHub 后，可以使用：

```bash
npx skills add <owner>/long-horizon-project-skill --skill long-horizon-project -g
```

如果安装器支持 `--copy`，可以使用它来复制文件，而不是建立链接。

### Codex

Codex 会从 `~/.agents/skills/` 发现用户级 Skill。先将本仓库克隆到临时目录，再复制其中的通用 Skill：

```bash
git clone https://github.com/<owner>/long-horizon-project-skill.git /tmp/long-horizon-project-skill
mkdir -p ~/.agents/skills
cp -R /tmp/long-horizon-project-skill/.agents/skills/long-horizon-project ~/.agents/skills/
```

Windows PowerShell：

```powershell
git clone https://github.com/<owner>/long-horizon-project-skill.git "$env:TEMP\long-horizon-project-skill"
New-Item -ItemType Directory -Force "$env:USERPROFILE\.agents\skills" | Out-Null
Copy-Item -Recurse -Force `
  "$env:TEMP\long-horizon-project-skill\.agents\skills\long-horizon-project" `
  "$env:USERPROFILE\.agents\skills\long-horizon-project"
```

如果 Skill 没有立即出现，请重启智能体。Codex 中可以显式调用：

```text
$long-horizon-project
```

当前仍保留隐式触发。

### Claude Code

Claude Code 的个人 Skill 目录是 `~/.claude/skills/`：

```bash
git clone https://github.com/<owner>/long-horizon-project-skill.git /tmp/long-horizon-project-skill
mkdir -p ~/.claude/skills
cp -R /tmp/long-horizon-project-skill/.agents/skills/long-horizon-project ~/.claude/skills/
```

在 Claude Code 中调用：

```text
/long-horizon-project
```

`SKILL.md`、脚本、模板和参考文档是跨平台的；`agents/openai.yaml` 主要用于 Codex 的界面元数据。

## 在项目中使用

新项目可以在新对话中输入：

```text
$long-horizon-project

初始化或检查项目状态。只处理当前阶段，并将智能体辅助文件放在 skilluse/ 下。
```

已有项目可以输入：

```text
$long-horizon-project

从 skilluse/context/current.md 恢复项目。检查项目代码仓库和 skilluse 状态仓库，然后只继续当前阶段的 Next Action。
```

初始化项目状态目录时，`<skill-directory>` 指安装后的 Skill 目录：

```text
python "<skill-directory>/scripts/init_skilluse.py" <project-path>
```

如果需要在 `skilluse/` 不存在或为空时克隆私有状态仓库：

```text
python "<skill-directory>/scripts/init_skilluse.py" <project-path> --state-repo <private-repository-url>
```

跨对话或跨设备交接前验证状态：

```text
python "<skill-directory>/scripts/validate_skilluse.py" <project-path> --strict
```

## 项目状态目录

推荐的项目结构：

```text
project/
├── src/                 # 项目功能代码
├── tests/               # 项目测试
├── README.md            # 面向人的安装和使用说明
├── .gitignore           # 包含 /skilluse/
└── skilluse/            # 通常是独立的私有 Git 仓库
    ├── context/
    │   ├── current.md
    │   └── decisions.md
    ├── plans/phases/
    ├── logs/
    ├── artifacts/
    └── local/
```

项目交付物仍放在正常的项目目录中。可配置路径的计划、交接记录、报告、截图和日志放在 `skilluse/`。不要把密钥或机器专属绝对路径写入状态文件。

## 跨设备工作流

当项目代码公开、智能体状态需要私有保存时，使用两个仓库：

```text
公开项目仓库
私有 skilluse 仓库 -> 克隆到 project/skilluse/
```

设备 A 结束阶段时，遵循项目 README、用户指令或当前 Git Skill 的 Git 工作流，并把实际的分支、commit 和推送结果记录到 `skilluse/context/current.md`。

设备 B 拉取两个仓库后，先确认 `current.md` 记录的项目 commit 与当前项目 HEAD 一致，再修改代码。

## 开发状态

当前仓库提供可移植的 Skill 层，不安装宿主生命周期 Hooks。维护和验证方式见 `CONTRIBUTING.md`。
