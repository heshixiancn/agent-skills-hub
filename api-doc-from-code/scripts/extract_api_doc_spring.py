#!/usr/bin/env python3
"""
Extract structured API docs from Java Spring controllers and emit JSON.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

import javalang

SPRING_METHODS = {
    "GetMapping": "GET",
    "PostMapping": "POST",
    "PutMapping": "PUT",
    "DeleteMapping": "DELETE",
    "PatchMapping": "PATCH",
}

DEFAULT_EXCLUDE_DIRS = {"interface", "client", "feign"}

SCALAR_TYPES = {
    "byte",
    "short",
    "int",
    "long",
    "float",
    "double",
    "boolean",
    "char",
    "Byte",
    "Short",
    "Integer",
    "Long",
    "Float",
    "Double",
    "Boolean",
    "Character",
    "String",
    "BigDecimal",
    "BigInteger",
    "Date",
    "LocalDate",
    "LocalDateTime",
    "OffsetDateTime",
    "ZonedDateTime",
    "Instant",
    "UUID",
    "Object",
}

COLLECTION_TYPES = {
    "List",
    "Set",
    "Collection",
    "Iterable",
    "ArrayList",
    "LinkedList",
    "HashSet",
    "Page",
    "IPage",
}

MAP_TYPES = {"Map", "HashMap", "LinkedHashMap"}

REQUIRED_ANN = {"NotNull", "NotBlank", "NotEmpty"}


@dataclass
class FieldInfo:
    name: str
    type: str
    required: bool
    description: str
    children: List["FieldInfo"]


@dataclass
class ClassInfo:
    full_name: str
    package: str
    imports: Dict[str, str]
    fields: List[FieldInfo]
    is_enum: bool


@dataclass
class ControllerInfo:
    full_name: str
    package: str
    imports: Dict[str, str]
    class_base: str
    node: javalang.tree.ClassDeclaration
    doc_map: Dict[int, str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract Spring API docs into JSON.")
    parser.add_argument("--root", required=True, help="Repository root path")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--include", default="", help="Comma-separated glob patterns to include")
    parser.add_argument("--exclude", default="", help="Comma-separated glob patterns to exclude")
    parser.add_argument(
        "--exclude-dirs",
        default=",".join(sorted(DEFAULT_EXCLUDE_DIRS)),
        help="Comma-separated directory names to exclude",
    )
    parser.add_argument("--max-depth", type=int, default=5, help="Max depth for nested fields")
    return parser.parse_args()


def split_csv(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def iter_java_files(
    root: Path, includes: List[str], excludes: List[str]
) -> Iterable[Path]:
    if not includes:
        includes = ["**/*.java"]
    for path in root.rglob("*.java"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if includes and not any(fnmatch.fnmatch(rel, pat) for pat in includes):
            continue
        if excludes and any(fnmatch.fnmatch(rel, pat) for pat in excludes):
            continue
        yield path


def clean_doc(lines: List[str]) -> str:
    cleaned = []
    for line in lines:
        line = line.strip()
        line = re.sub(r"^/\*+", "", line)
        line = re.sub(r"\*+/$", "", line)
        line = re.sub(r"^\*", "", line).strip()
        if line:
            cleaned.append(line)
    return " ".join(cleaned).strip()


def map_doc_for_lines(text: str) -> Dict[int, str]:
    lines = text.splitlines()
    doc_map: Dict[int, str] = {}
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("/**"):
            j = i
            block = []
            while j < len(lines):
                block.append(lines[j])
                if "*/" in lines[j]:
                    break
                j += 1
            doc = clean_doc(block)
            k = j + 1
            while k < len(lines):
                nxt = lines[k].strip()
                if not nxt or nxt.startswith("@"):
                    k += 1
                    continue
                doc_map[k + 1] = doc
                break
            i = j + 1
            continue
        if stripped.startswith("//"):
            doc = stripped.lstrip("/").strip()
            k = i + 1
            while k < len(lines):
                nxt = lines[k].strip()
                if not nxt or nxt.startswith("@"):
                    k += 1
                    continue
                doc_map[k + 1] = doc
                break
        i += 1
    return doc_map


def import_map(tree: javalang.tree.CompilationUnit) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for imp in tree.imports:
        if imp.wildcard:
            continue
        simple = imp.path.split(".")[-1]
        mapping[simple] = imp.path
    return mapping


def type_to_str(t: Optional[javalang.tree.Type]) -> str:
    if t is None:
        return "void"
    name = t.name
    if t.dimensions:
        name += "[]" * len(t.dimensions)
    if hasattr(t, "arguments") and t.arguments:
        args = []
        for arg in t.arguments:
            if isinstance(arg, javalang.tree.TypeArgument) and arg.type:
                args.append(type_to_str(arg.type))
        if args:
            name = f"{name}<{', '.join(args)}>"
    return name


def literal_value(node) -> str:
    if node is None:
        return ""
    if isinstance(node, javalang.tree.Literal):
        return node.value.strip('"')
    if isinstance(node, javalang.tree.MemberReference):
        return node.member
    if isinstance(node, javalang.tree.ElementArrayValue):
        values = [literal_value(v) for v in node.values]
        return ",".join([v for v in values if v])
    return ""


def annotation_kv(ann: javalang.tree.Annotation) -> Dict[str, str]:
    kv: Dict[str, str] = {}
    if hasattr(ann, "element") and ann.element is not None:
        kv["value"] = literal_value(ann.element)
    if hasattr(ann, "element_pairs") and ann.element_pairs:
        for pair in ann.element_pairs:
            kv[pair.name] = literal_value(pair.value)
    return kv


def get_mapping_paths(ann: javalang.tree.Annotation) -> List[str]:
    kv = annotation_kv(ann)
    if "path" in kv and kv["path"]:
        return [p.strip() for p in kv["path"].split(",") if p.strip()]
    if "value" in kv and kv["value"]:
        return [p.strip() for p in kv["value"].split(",") if p.strip()]
    return [""]


def get_request_methods(ann: javalang.tree.Annotation) -> List[str]:
    kv = annotation_kv(ann)
    raw = kv.get("method", "")
    if raw:
        return [m.replace("RequestMethod.", "") for m in raw.split(",") if m]
    return ["ANY"]


def is_controller(ann_names: List[str]) -> bool:
    return any(name.endswith("RestController") or name.endswith("Controller") for name in ann_names)


def get_class_base(annotations: List[javalang.tree.Annotation]) -> str:
    for ann in annotations:
        if ann.name.endswith("RequestMapping"):
            paths = get_mapping_paths(ann)
            return paths[0] if paths else ""
    return ""


def find_annotation(annotations: List[javalang.tree.Annotation], name_suffix: str) -> Optional[javalang.tree.Annotation]:
    for ann in annotations:
        if ann.name.endswith(name_suffix):
            return ann
    return None


def get_field_description(
    annotations: List[javalang.tree.Annotation], doc_map: Dict[int, str], line: Optional[int]
) -> str:
    for ann in annotations:
        if ann.name.endswith("ApiModelProperty") or ann.name.endswith("Schema"):
            kv = annotation_kv(ann)
            for key in ("value", "description", "title"):
                if kv.get(key):
                    return kv[key]
    if line and line in doc_map:
        return doc_map[line]
    return "TODO"


def is_required(annotations: List[javalang.tree.Annotation]) -> bool:
    for ann in annotations:
        if ann.name in REQUIRED_ANN:
            return True
        if ann.name.endswith("ApiModelProperty") or ann.name.endswith("Schema"):
            kv = annotation_kv(ann)
            required = kv.get("required")
            if required and required.lower() == "true":
                return True
    return False


def parse_type_string(type_str: str) -> Tuple[str, List[str]]:
    if "<" not in type_str:
        return type_str, []
    base = type_str.split("<", 1)[0]
    inner = type_str.rsplit(">", 1)[0].split("<", 1)[1]
    parts = [p.strip() for p in inner.split(",") if p.strip()]
    return base, parts


def resolve_type(
    type_name: str,
    package: str,
    imports: Dict[str, str],
    simple_index: Dict[str, List[str]],
    class_index: Dict[str, ClassInfo],
) -> Optional[str]:
    if "." in type_name:
        if type_name in class_index:
            return type_name
        if package:
            candidate = f"{package}.{type_name}"
            if candidate in class_index:
                return candidate
        matches = [full for full in class_index.keys() if full.endswith(f".{type_name}")]
        if len(matches) == 1:
            return matches[0]
        return None
    if type_name in imports:
        return imports[type_name]
    candidate = f"{package}.{type_name}" if package else type_name
    if candidate in class_index:
        return candidate
    if len(simple_index.get(type_name, [])) == 1:
        return simple_index[type_name][0]
    return None


def expand_type(
    type_str: str,
    package: str,
    imports: Dict[str, str],
    class_index: Dict[str, ClassInfo],
    simple_index: Dict[str, List[str]],
    max_depth: int,
    visited: Set[str],
) -> List[FieldInfo]:
    if max_depth <= 0:
        return []
    base, args = parse_type_string(type_str)
    base = base.replace("[]", "")
    if base in SCALAR_TYPES:
        return []
    if base in COLLECTION_TYPES and args:
        return expand_type(args[-1], package, imports, class_index, simple_index, max_depth - 1, visited)
    if base in MAP_TYPES and args:
        return expand_type(args[-1], package, imports, class_index, simple_index, max_depth - 1, visited)
    full = resolve_type(base, package, imports, simple_index, class_index)
    if not full or full in visited:
        return []
    class_info = class_index.get(full)
    if not class_info or class_info.is_enum:
        return []
    next_visited = set(visited)
    next_visited.add(full)
    fields: List[FieldInfo] = []
    for field in class_info.fields:
        children = expand_type(
            field.type,
            class_info.package,
            class_info.imports,
            class_index,
            simple_index,
            max_depth - 1,
            next_visited,
        )
        fields.append(
            FieldInfo(
                name=field.name,
                type=field.type,
                required=field.required,
                description=field.description,
                children=children,
            )
        )
    return fields


def flatten_fields(fields: List[FieldInfo]) -> List[Dict[str, object]]:
    def to_dict(field: FieldInfo) -> Dict[str, object]:
        return {
            "name": field.name,
            "type": field.type,
            "required": field.required,
            "description": field.description,
            "children": [to_dict(c) for c in field.children],
        }

    return [to_dict(f) for f in fields]


def parse_java_files(
    root: Path,
    files: Iterable[Path],
    controller_paths: Set[Path],
) -> Tuple[Dict[str, ClassInfo], Dict[str, List[str]], List[ControllerInfo]]:
    class_index: Dict[str, ClassInfo] = {}
    simple_index: Dict[str, List[str]] = {}
    controllers: List[ControllerInfo] = []

    for path in files:
        text = path.read_text(errors="ignore")
        try:
            tree = javalang.parse.parse(text)
        except (javalang.parser.JavaSyntaxError, TypeError):
            continue
        package = tree.package.name if tree.package else ""
        imports = import_map(tree)
        doc_map = map_doc_for_lines(text)

        for path_nodes, node in tree.filter(javalang.tree.ClassDeclaration):
            class_path = [n.name for n in path_nodes if isinstance(n, javalang.tree.ClassDeclaration)]
            if not class_path or class_path[-1] != node.name:
                class_path.append(node.name)
            class_name = ".".join(class_path)
            full_name = f"{package}.{class_name}" if package else class_name
            ann_names = [ann.name for ann in node.annotations]
            class_base = get_class_base(node.annotations)
            is_ctrl = is_controller(ann_names)
            fields: List[FieldInfo] = []
            for field in node.fields:
                field_type = type_to_str(field.type)
                for decl in field.declarators:
                    line = field.position.line if field.position else None
                    fields.append(
                        FieldInfo(
                            name=decl.name,
                            type=field_type,
                            required=is_required(field.annotations),
                            description=get_field_description(field.annotations, doc_map, line),
                            children=[],
                        )
                    )
            class_index[full_name] = ClassInfo(
                full_name=full_name,
                package=package,
                imports=imports,
                fields=fields,
                is_enum=False,
            )
            simple_index.setdefault(node.name, []).append(full_name)
            if is_ctrl and path in controller_paths:
                controllers.append(
                    ControllerInfo(
                        full_name=full_name,
                        package=package,
                        imports=imports,
                        class_base=class_base,
                        node=node,
                        doc_map=doc_map,
                    )
                )

        for path_nodes, node in tree.filter(javalang.tree.EnumDeclaration):
            enum_path = [n.name for n in path_nodes if isinstance(n, javalang.tree.ClassDeclaration)]
            if not enum_path or enum_path[-1] != node.name:
                enum_path.append(node.name)
            enum_name = ".".join(enum_path)
            full_name = f"{package}.{enum_name}" if package else enum_name
            class_index[full_name] = ClassInfo(
                full_name=full_name,
                package=package,
                imports=imports,
                fields=[],
                is_enum=True,
            )
            simple_index.setdefault(node.name, []).append(full_name)

    return class_index, simple_index, controllers


def method_summary(method: javalang.tree.MethodDeclaration, doc_map: Dict[int, str]) -> str:
    ann = find_annotation(method.annotations, "ApiOperation") or find_annotation(method.annotations, "Operation")
    if ann:
        kv = annotation_kv(ann)
        for key in ("value", "summary", "notes"):
            if kv.get(key):
                return kv[key]
    if method.position and method.position.line in doc_map:
        return doc_map[method.position.line]
    return method.name


def join_paths(base: str, path: str) -> str:
    if not base:
        return path or "/"
    if not path:
        return base
    return ("/" + base.strip("/") + "/" + path.strip("/")).replace("//", "/")


def param_description(annotations: List[javalang.tree.Annotation]) -> str:
    ann = find_annotation(annotations, "ApiParam") or find_annotation(annotations, "Parameter")
    if ann:
        kv = annotation_kv(ann)
        for key in ("value", "name", "description"):
            if kv.get(key):
                return kv[key]
    return "TODO"


def build_endpoints(
    controllers: List[ControllerInfo],
    class_index: Dict[str, ClassInfo],
    simple_index: Dict[str, List[str]],
    max_depth: int,
) -> List[Dict[str, object]]:
    endpoints: List[Dict[str, object]] = []

    for ctrl in controllers:
        for method in ctrl.node.methods:
            mappings: List[Tuple[str, str]] = []
            for ann in method.annotations:
                if ann.name in SPRING_METHODS:
                    for p in get_mapping_paths(ann):
                        mappings.append((SPRING_METHODS[ann.name], p))
                if ann.name.endswith("RequestMapping"):
                    for m in get_request_methods(ann):
                        for p in get_mapping_paths(ann):
                            mappings.append((m, p))
            if not mappings:
                continue

            path_params: List[FieldInfo] = []
            query_params: List[FieldInfo] = []
            headers: List[FieldInfo] = []
            body_type: Optional[str] = None
            body_fields: List[FieldInfo] = []

            for param in method.parameters:
                ann_names = [a.name for a in param.annotations]
                ann_req_param = find_annotation(param.annotations, "RequestParam")
                ann_path = find_annotation(param.annotations, "PathVariable")
                ann_header = find_annotation(param.annotations, "RequestHeader")
                ann_body = find_annotation(param.annotations, "RequestBody")
                ann_model = find_annotation(param.annotations, "ModelAttribute")

                param_type = type_to_str(param.type)
                param_name = param.name
                required = is_required(param.annotations)

                if ann_req_param:
                    kv = annotation_kv(ann_req_param)
                    name = kv.get("value") or kv.get("name") or param_name
                    req = kv.get("required")
                    if req:
                        required = req.lower() == "true"
                    else:
                        required = True
                    query_params.append(
                        FieldInfo(
                            name=name,
                            type=param_type,
                            required=required,
                            description=param_description(param.annotations),
                            children=[],
                        )
                    )
                    continue
                if ann_path:
                    kv = annotation_kv(ann_path)
                    name = kv.get("value") or kv.get("name") or param_name
                    path_params.append(
                        FieldInfo(
                            name=name,
                            type=param_type,
                            required=True,
                            description=param_description(param.annotations),
                            children=[],
                        )
                    )
                    continue
                if ann_header:
                    kv = annotation_kv(ann_header)
                    name = kv.get("value") or kv.get("name") or param_name
                    req = kv.get("required")
                    if req:
                        required = req.lower() == "true"
                    else:
                        required = True
                    headers.append(
                        FieldInfo(
                            name=name,
                            type=param_type,
                            required=required,
                            description=param_description(param.annotations),
                            children=[],
                        )
                    )
                    continue
                if ann_body or ann_model or ("RequestBody" in ann_names):
                    body_type = param_type
                    body_fields = expand_type(
                        param_type,
                        ctrl.package,
                        ctrl.imports,
                        class_index,
                        simple_index,
                        max_depth,
                        set(),
                    )
                    continue

            return_type = type_to_str(method.return_type)
            if return_type.startswith("ResponseEntity"):
                _, args = parse_type_string(return_type)
                if args:
                    return_type = args[0]

            resp_fields = expand_type(
                return_type,
                ctrl.package,
                ctrl.imports,
                class_index,
                simple_index,
                max_depth,
                set(),
            )

            base_summary = method_summary(method, ctrl.doc_map)
            controller_simple = ctrl.full_name.split(".")[-1]
            summary = f"{controller_simple} - {base_summary}"

            for http_method, path in mappings:
                full_path = join_paths(ctrl.class_base, path)
                endpoints.append(
                    {
                        "method": http_method,
                        "path": full_path,
                        "summary": summary,
                        "tags": [],
                        "auth": "",
                        "handler": {
                            "class": ctrl.full_name,
                            "method": method.name,
                        },
                        "request": {
                            "path_params": flatten_fields(path_params),
                            "query_params": flatten_fields(query_params),
                            "headers": flatten_fields(headers),
                            "body": {
                                "type": body_type or "",
                                "fields": flatten_fields(body_fields),
                            }
                            if body_type
                            else None,
                        },
                        "responses": {
                            "TODO": {
                                "type": return_type,
                                "fields": flatten_fields(resp_fields),
                            }
                        },
                    }
                )

    return endpoints


def main() -> None:
    args = parse_args()
    root = Path(args.root).resolve()
    includes = split_csv(args.include)
    excludes = split_csv(args.exclude)
    exclude_dirs = {d.strip() for d in split_csv(args.exclude_dirs)}

    files = list(iter_java_files(root, includes, excludes))
    controller_paths = {
        path
        for path in files
        if not any(part in exclude_dirs for part in path.parts)
    }
    class_index, simple_index, controllers = parse_java_files(root, files, controller_paths)

    endpoints = build_endpoints(controllers, class_index, simple_index, args.max_depth)

    output = {
        "service": root.name,
        "base_url": "",
        "endpoints": endpoints,
    }

    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
