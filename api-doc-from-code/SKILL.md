---
name: api-doc-from-code
description: Generate Markdown API documentation directly from source code for Java Spring (MVC/Boot), Python (FastAPI/Flask), and Go (Gin). Use when asked to scan code to extract endpoints, HTTP methods, paths, parameters, request/response models, or to create/update API docs from controller annotations or router definitions.
---

# 从代码生成 API 文档

## 概览
通过扫描 Java Spring、Python FastAPI/Flask 和 Go Gin 代码库，提取接口路径、HTTP 方法，以及请求/响应相关信息，生成 Markdown API 文档。

## 工作流（优化版）

1) 识别框架与入口
- 结合项目结构与 import 信息确认 Spring/FastAPI/Flask/Gin 的使用情况。
- 如果是混合项目，按语言/框架拆分提取计划。

2) 扫描类文件并定位 Controller
- 扫描 `*.java`（或对应语言）类文件。
- 精确匹配 Controller（如 Spring：`@RestController`/`@Controller` + `@RequestMapping`）。
- 仅保留 Controller 中的对外接口，过滤 `interface/`、`client/`、`feign/` 等非入口定义。

3) 补全请求/响应细节（递归展开）
- Spring：
  - 读取方法参数、返回类型、`@RequestBody`/`@RequestParam`/`@PathVariable` 等注解。
  - 解析 DTO/VO/POJO 字段，并递归展开嵌套对象，直到最内层字段。
  - 处理常见集合与泛型（`List<T>`/`Map<K,V>`）与枚举。
- FastAPI：读取类型注解与 Pydantic 模型，递归展开嵌套模型字段。
- Flask：读取装饰器并结合代码人工推断请求/响应，必要时标记 TODO。
- Gin：读取 handler 签名与 struct tag，递归展开嵌套结构体。
- 参考 `references/` 下对应规则文件。

4) 产出结构化 JSON，再渲染 Markdown
- 先输出结构化 JSON（包含端点、参数、请求/响应模型与字段详情）。
- 再将 JSON 渲染为 Markdown 文档。
- 每个端点保持一致字段：方法、路径、摘要、参数、请求体、响应。
- 参数/请求体/响应体字段必须包含：字段名、类型、是否必填、说明（无说明标 TODO）。

## 依赖

Spring 解析依赖：
```bash
pip install javalang
```

## 快捷命令（按语言拆分）

Spring：生成结构化 JSON：
```bash
python3 scripts/extract_api_doc_spring.py \
  --root /path/to/repo \
  --output /tmp/api_doc.json \
  --max-depth 5
```

渲染 Markdown：
```bash
python3 scripts/render_api_doc.py \
  --input /tmp/api_doc.json \
  --output /tmp/api_doc.md
```

## 参考

- `references/java-spring.md`：Spring MVC/Boot 提取规则
- `references/python.md`：FastAPI/Flask 提取规则
- `references/go.md`：Gin 提取规则

## 输出要求

- 输出必须为 Markdown。
- 端点列表优先使用表格；详细信息用分节展示。
- 细节不确定时标记 TODO，避免编造。
 - 当存在嵌套对象时，字段列表应展开到最内层字段。
