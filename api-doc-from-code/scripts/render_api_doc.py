#!/usr/bin/env python3
"""Render JSON API docs to Markdown."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render API docs JSON into Markdown.")
    parser.add_argument("--input", required=True, help="Input JSON path")
    parser.add_argument("--output", required=True, help="Output Markdown path")
    return parser.parse_args()


def flatten_fields(fields: List[Dict[str, object]], prefix: str = "") -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for field in fields:
        name = field.get("name", "")
        full = f"{prefix}.{name}" if prefix else name
        rows.append(
            {
                "name": full,
                "type": field.get("type", ""),
                "required": field.get("required", False),
                "description": field.get("description", ""),
            }
        )
        children = field.get("children") or []
        rows.extend(flatten_fields(children, full))
    return rows


def table_for_fields(fields: List[Dict[str, object]]) -> List[str]:
    if not fields:
        return ["(无)"]
    rows = ["| 字段 | 类型 | 必填 | 说明 |", "|---|---|---|---|"]
    for f in flatten_fields(fields):
        rows.append(
            f"| {f['name']} | {f['type']} | {'Y' if f['required'] else 'N'} | {f['description']} |"
        )
    return rows


def render(md: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# API 文档")
    lines.append("")
    lines.append("## 概览")
    lines.append(f"- 服务名: {md.get('service', '')}")
    base_url = md.get("base_url", "")
    lines.append(f"- 基础路径: {base_url or 'TODO'}")
    lines.append("- 鉴权: TODO")
    lines.append("- 联系人: TODO")
    lines.append("")

    endpoints = md.get("endpoints", [])
    lines.append("## 端点汇总")
    lines.append("| Method | Path | 摘要 |")
    lines.append("|---|---|---|")
    for ep in endpoints:
        lines.append(f"| {ep.get('method','')} | {ep.get('path','')} | {ep.get('summary','')} |")

    lines.append("")
    lines.append("## 端点详情")
    for ep in endpoints:
        lines.append("")
        lines.append(f"### {ep.get('method','')} {ep.get('path','')}")
        lines.append(f"- 摘要: {ep.get('summary','')}")
        lines.append(f"- 标签: {', '.join(ep.get('tags', [])) or 'TODO'}")
        lines.append(f"- 鉴权: {ep.get('auth') or 'TODO'}")
        lines.append("")

        request = ep.get("request") or {}
        lines.append("#### 请求")
        lines.append("路径参数:")
        lines.extend(table_for_fields(request.get("path_params", [])))
        lines.append("")
        lines.append("查询参数:")
        lines.extend(table_for_fields(request.get("query_params", [])))
        lines.append("")
        lines.append("请求头:")
        lines.extend(table_for_fields(request.get("headers", [])))
        lines.append("")

        body = request.get("body") if isinstance(request, dict) else None
        if body:
            lines.append(f"请求体 (类型: {body.get('type','') or 'TODO'}):")
            lines.extend(table_for_fields(body.get("fields", [])))
        else:
            lines.append("请求体:")
            lines.append("(无)")

        lines.append("")
        lines.append("#### 响应")
        responses = ep.get("responses", {})
        if not responses:
            lines.append("(无)")
        for status, resp in responses.items():
            lines.append(f"状态码: {status}")
            lines.append(f"返回类型: {resp.get('type','') or 'TODO'}")
            lines.extend(table_for_fields(resp.get("fields", [])))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    args = parse_args()
    data = json.loads(Path(args.input).read_text())
    Path(args.output).write_text(render(data))


if __name__ == "__main__":
    main()
