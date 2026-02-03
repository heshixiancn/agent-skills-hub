## 🚀 Agent Skills Hub

A unified repository for developing, managing, versioning, and distributing Agent Skills, with cross-platform installation support for Codex, Cursor, Claude, and project-level integrations.

## 📌 项目定位

Agent Skills Hub 是一个 可复用 AI 技能管理仓库，用于统一管理：

✅ 开源 Skills

✅ 自定义 Skills

✅ 多平台安装适配

✅ 版本与依赖管理

✅ Skill 标准化开发规范

目标是将 Agent Skill 产品化、模块化、可发布化。

🎯 设计目标

本仓库解决以下核心问题：

问题	解决方案
Skill 分散在各项目中难复用	GitHub 统一管理
不同 AI 平台规则不一致	Adapter 统一生成
Skill 版本难维护	SemVer + Registry
Skill 安装流程混乱	标准安装脚本
Skill 难共享	开源/私有均支持
🧠 什么是 Agent Skill？

Agent Skill 是：

可复用、可安装、可版本化的 AI 能力模块

通常包含：

输入定义

输出定义

行为规范

提示词模板

平台适配产物

使用文档

🏗 仓库结构
agent-skills-hub
│
├── skills/              # 所有技能源码
│   └── <skill-id>/
│       ├── skill.yaml
│       ├── templates/
│       ├── adapters/
│       └── README.md
│
├── registry/            # 技能索引
│   └── index.json
│
├── scripts/             # 安装与校验工具
│   ├── install.py
│   └── validate_skills.py
│
├── tools/               # 通用工具
│
├── docs/                # 技术规范文档
│
└── .github/workflows/   # CI 校验

⚙️ Skill 结构规范

每个 Skill 必须包含：

📄 skill.yaml

Skill 的核心定义文件：

id: example-http-json
name: HTTP JSON Fetch Skill
version: 0.1.0
description: Fetch JSON and extract fields
inputs:
outputs:
adapters:

📄 templates/

定义各 AI 平台安装产物模板：

templates/
  ├── cursor.cursorrules.tmpl
  ├── codex.skill_prompt.md.tmpl
  ├── claude.system_prompt.md.tmpl
  └── project.skill.md.tmpl

📄 README.md

Skill 使用说明与示例。

🔌 支持的宿主平台
平台	输出类型
Cursor	.cursorrules
Codex	Skill Prompt
Claude	System Prompt
Project	工程引用文档
📦 安装 Skill
1️⃣ 校验 Skills
python scripts/validate_skills.py

2️⃣ 安装到指定平台
python scripts/install.py \
  --skill example-http-json \
  --target cursor \
  --out ./_installed


支持目标：

cursor
codex
claude
project

3️⃣ 安装结果结构
_installed/
   └── cursor/
       └── example-http-json/

📚 Skill Registry

registry/index.json 用于：

Skill 检索

Skill 发布

Skill 依赖解析

第三方 Skill 集成

🔄 Skill 生命周期
设计 → 开发 → 校验 → 发布 → 安装 → 使用 → 版本迭代

🏷 Skill 版本规范

采用 SemVer：

MAJOR.MINOR.PATCH


示例：

1.0.0  重大变更
0.3.0  新功能
0.3.1  Bug修复

🔗 开源 Skill 集成方式

支持：

Git Submodule
git submodule add <repo>

Git Subtree
git subtree add

Registry 安装（推荐）

未来支持：

skill install <skill-name>

🧩 Adapter 机制

Adapter 用于：

将统一 Skill 转换为不同 AI 平台格式

流程：

skill.yaml
   ↓
Template Render
   ↓
生成目标平台产物

🔐 安全原则

Skill 必须遵循：

不编造数据

明确输入输出

不执行隐式网络操作

必须可追溯行为

🧪 CI 校验

每次提交自动执行：

validate_skills.py


保证：

Skill 结构合法

元数据完整

模板存在

🧭 未来规划

Skill 包管理器

Skill 市场

Skill 依赖解析

Skill 测试框架

Skill 权限模型

GUI 管理工具

🤝 贡献指南

欢迎提交：

新 Skill

Adapter 支持

工具增强

文档改进

📜 License

MIT License

⭐ 为什么这个仓库重要

Agent Skills Hub 试图建立：

👉 AI 能力模块的标准化生态
👉 AI 工程的“组件化开发模式”
👉 AI 工具链统一分发标准

💡 适用场景

AI 开发团队

Agent Framework 构建

个人 AI 技能库

企业知识自动化平台
