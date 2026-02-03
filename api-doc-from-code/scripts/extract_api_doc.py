#!/usr/bin/env python3
"""
Extract API endpoints from Java Spring, Python FastAPI/Flask, and Go Gin code
and emit a Markdown table.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

SPRING_METHODS = {
    "GetMapping": "GET",
    "PostMapping": "POST",
    "PutMapping": "PUT",
    "DeleteMapping": "DELETE",
    "PatchMapping": "PATCH",
}

HTTP_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract API endpoints into Markdown.")
    parser.add_argument("--root", required=True, help="Repository root path")
    parser.add_argument("--output", help="Output Markdown path (stdout if omitted)")
    parser.add_argument(
        "--frameworks",
        default="auto",
        help="Comma-separated: spring,fastapi,flask,gin,auto",
    )
    parser.add_argument(
        "--include",
        default="",
        help="Comma-separated glob patterns to include (e.g., **/*.java)",
    )
    parser.add_argument(
        "--exclude",
        default="",
        help="Comma-separated glob patterns to exclude (e.g., **/test/**)",
    )
    return parser.parse_args()


def split_csv(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def iter_files(root: Path, includes: List[str], excludes: List[str]) -> Iterable[Path]:
    if not includes:
        includes = ["**/*.java", "**/*.py", "**/*.go"]
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if includes and not any(fnmatch.fnmatch(rel, pat) for pat in includes):
            continue
        if excludes and any(fnmatch.fnmatch(rel, pat) for pat in excludes):
            continue
        yield path


def detect_frameworks(files: Iterable[Path]) -> List[str]:
    text = "\n".join(path.read_text(errors="ignore") for path in files)
    found = set()
    if "@RestController" in text or "@RequestMapping" in text:
        found.add("spring")
    if "FastAPI" in text or "@app.get" in text or "@router.get" in text:
        found.add("fastapi")
    if "Flask" in text or "@app.route" in text:
        found.add("flask")
    if "gin" in text and (".GET(" in text or ".POST(" in text):
        found.add("gin")
    return sorted(found)


def extract_spring(text: str, rel_path: str) -> List[Tuple[str, str, str, str]]:
    endpoints = []
    class_base = ""
    pending_class_mapping = ""

    lines = text.splitlines()
    for i, line in enumerate(lines):
        line_stripped = line.strip()

        if line_stripped.startswith("@RequestMapping"):
            pending_class_mapping = extract_path_from_annotation(line_stripped)

        if re.search(r"\bclass\s+\w+", line_stripped):
            class_base = pending_class_mapping
            pending_class_mapping = ""

        method = None
        path = ""
        for ann, http_method in SPRING_METHODS.items():
            if f"@{ann}" in line_stripped:
                method = http_method
                path = extract_path_from_annotation(line_stripped)
                break

        if "@RequestMapping" in line_stripped and method is None:
            path = extract_path_from_annotation(line_stripped)
            method = extract_request_method(line_stripped) or "ANY"

        if method:
            handler = find_next_method_name(lines, i + 1)
            full_path = join_paths(class_base, path)
            endpoints.append((method, full_path, handler, rel_path))

    return endpoints


def extract_path_from_annotation(line: str) -> str:
    m = re.search(r"\(\s*\"([^\"]+)\"", line)
    if m:
        return m.group(1)
    m = re.search(r"value\s*=\s*\"([^\"]+)\"", line)
    if m:
        return m.group(1)
    return ""


def extract_request_method(line: str) -> str:
    m = re.search(r"RequestMethod\.([A-Z]+)", line)
    if m:
        return m.group(1)
    return ""


def find_next_method_name(lines: List[str], start: int) -> str:
    for i in range(start, min(start + 6, len(lines))):
        m = re.search(r"\b(\w+)\s*\(", lines[i])
        if m:
            return m.group(1)
    return ""


def extract_fastapi(text: str, rel_path: str) -> List[Tuple[str, str, str, str]]:
    endpoints = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        m = re.search(r"@(\w+)\.(get|post|put|delete|patch|head|options)\(\s*\"([^\"]+)\"", line_stripped)
        if m:
            method = m.group(2).upper()
            path = m.group(3)
            handler = find_next_def(lines, i + 1)
            endpoints.append((method, path, handler, rel_path))
            continue
        m = re.search(r"@(\w+)\.api_route\(\s*\"([^\"]+)\".*methods\s*=\s*\[([^\]]+)\]", line_stripped)
        if m:
            path = m.group(2)
            methods = [item.strip().strip("'\"") for item in m.group(3).split(",")]
            handler = find_next_def(lines, i + 1)
            for method in methods:
                endpoints.append((method.upper(), path, handler, rel_path))
    return endpoints


def extract_flask(text: str, rel_path: str) -> List[Tuple[str, str, str, str]]:
    endpoints = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if "@app.route" in line_stripped or "@bp.route" in line_stripped:
            m = re.search(r"\(\s*\"([^\"]+)\"", line_stripped)
            path = m.group(1) if m else ""
            methods = ["GET"]
            m = re.search(r"methods\s*=\s*\[([^\]]+)\]", line_stripped)
            if m:
                methods = [item.strip().strip("'\"") for item in m.group(1).split(",")]
            handler = find_next_def(lines, i + 1)
            for method in methods:
                endpoints.append((method.upper(), path, handler, rel_path))
    return endpoints


def find_next_def(lines: List[str], start: int) -> str:
    for i in range(start, min(start + 6, len(lines))):
        m = re.search(r"\bdef\s+(\w+)\s*\(", lines[i])
        if m:
            return m.group(1)
    return ""


def extract_gin(text: str, rel_path: str) -> List[Tuple[str, str, str, str]]:
    endpoints = []
    group_map: Dict[str, str] = {}

    for line in text.splitlines():
        line_stripped = line.strip()
        m = re.search(r"(\w+)\s*:=\s*\w+\.Group\(\s*\"([^\"]+)\"\s*\)", line_stripped)
        if m:
            group_map[m.group(1)] = m.group(2)

        m = re.search(r"\.Group\(\s*\"([^\"]+)\"\s*\)\.([A-Z]+)\(\s*\"([^\"]+)\"", line_stripped)
        if m and m.group(2) in HTTP_METHODS:
            base = m.group(1)
            method = m.group(2)
            path = m.group(3)
            endpoints.append((method, join_paths(base, path), "", rel_path))

        m = re.search(r"(\w+)\.([A-Z]+)\(\s*\"([^\"]+)\"", line_stripped)
        if m and m.group(2) in HTTP_METHODS:
            base = group_map.get(m.group(1), "")
            method = m.group(2)
            path = m.group(3)
            endpoints.append((method, join_paths(base, path), "", rel_path))

    return endpoints


def join_paths(base: str, path: str) -> str:
    if not base:
        return path or "/"
    if not path:
        return base
    return ("/" + base.strip("/") + "/" + path.strip("/")).replace("//", "/")


def to_markdown(endpoints: List[Tuple[str, str, str, str]], title: str) -> str:
    lines = [f"# {title}", "", "| Method | Path | Handler | Source |", "|---|---|---|---|"]
    for method, path, handler, source in endpoints:
        lines.append(f"| {method} | {path or '/'} | {handler} | {source} |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    root = Path(args.root).resolve()
    includes = split_csv(args.include)
    excludes = split_csv(args.exclude)

    all_files = list(iter_files(root, includes, excludes))
    rel_map = {path: path.relative_to(root).as_posix() for path in all_files}

    frameworks = split_csv(args.frameworks)
    if args.frameworks == "auto":
        frameworks = detect_frameworks(all_files)

    endpoints: List[Tuple[str, str, str, str]] = []

    for path in all_files:
        rel = rel_map[path]
        if path.suffix == ".java" and "spring" in frameworks:
            endpoints.extend(extract_spring(path.read_text(errors="ignore"), rel))
        if path.suffix == ".py":
            text = path.read_text(errors="ignore")
            if "fastapi" in frameworks:
                endpoints.extend(extract_fastapi(text, rel))
            if "flask" in frameworks:
                endpoints.extend(extract_flask(text, rel))
        if path.suffix == ".go" and "gin" in frameworks:
            endpoints.extend(extract_gin(path.read_text(errors="ignore"), rel))

    if not endpoints:
        output = "# API Endpoints\n\nNo endpoints found."
    else:
        output = to_markdown(endpoints, "API Endpoints")

    if args.output:
        Path(args.output).write_text(output)
    else:
        print(output)


if __name__ == "__main__":
    main()
