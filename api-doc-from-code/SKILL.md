---
name: api-doc-from-code
description: Generate Markdown API documentation directly from source code for Java Spring (MVC/Boot), Python (FastAPI/Flask), and Go (Gin). Use when asked to scan code to extract endpoints, HTTP methods, paths, parameters, request/response models, or to create/update API docs from controller annotations or router definitions.
---

# 从代码生成 API 文档

## 概览
通过扫描 Java Spring、Python FastAPI/Flask 和 Go Gin 代码库，提取接口路径、HTTP 方法，以及请求/响应相关信息，生成 Markdown API 文档。

## 工作流

1) 识别框架与入口
- 结合项目结构与 import 信息确认 Spring/FastAPI/Flask/Gin 的使用情况。
- 如果是混合项目，按语言/框架拆分提取计划。

2) 快速提取端点
- 先运行 `scripts/extract_api_doc.py` 生成初步端点列表。
- 仓库较大时使用 include/exclude globs 缩小范围。

3) 补全请求/响应细节
- Spring：读取方法参数与返回类型注解。
- FastAPI：读取类型注解与 Pydantic 模型。
- Flask：读取装饰器并结合代码人工推断请求/响应。
- Gin：读取 handler 签名与 struct tag。
- 参考 `references/` 下对应规则文件。

4) 产出最终 Markdown
- 以 `assets/api-doc-template.md` 为模板填充端点细节。
- 每个端点保持一致字段：方法、路径、摘要、参数、请求体、响应。

## 快捷命令

生成初步端点列表：
```bash
python3 /Users/heshixian/.codex/skills/api-doc-from-code/scripts/extract_api_doc.py \
  --root /path/to/repo \
  --output /tmp/api_endpoints.md
```

指定框架：
```bash
python3 /Users/heshixian/.codex/skills/api-doc-from-code/scripts/extract_api_doc.py \
  --root /path/to/repo \
  --frameworks spring,fastapi,gin
```

## 参考

- `references/java-spring.md`：Spring MVC/Boot 提取规则
- `references/python.md`：FastAPI/Flask 提取规则
- `references/go.md`：Gin 提取规则

## 输出要求

- 输出必须为 Markdown。
- 端点列表优先使用表格；详细信息用分节展示。
- 细节不确定时标记 TODO，避免编造。
