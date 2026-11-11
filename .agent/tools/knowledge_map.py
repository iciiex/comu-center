#!/usr/bin/env python3
"""Knowledge map for agents: generated code map, traceability, and the graphify graph.

Usage:
    python3 .agent/tools/knowledge_map.py            # rewrite the generated docs
    python3 .agent/tools/knowledge_map.py --check    # exit 1 when they are stale (run by tests)
    python3 .agent/tools/knowledge_map.py --graph    # also rebuild graphify-out/ (needs graphifyy)

What it produces:
    docs/agent-guide/code-map.md       routes, handlers, SQL usage, templates, tests, constants
    docs/agent-guide/traceability.md   MVP/BR/EP/OD/D ids -> code, tests, documents
    graphify-out/                      knowledge graph (only with --graph)

Design rules:
    * Standard library only for the first two modes; the application is never imported.
      Code is read with ``ast`` so no database or evidence directory is created.
    * Output is deterministic (sorted, no dates, no line numbers) so ``--check`` only fails
      when the structure of the code really changed.
    * Curated links live in ``.agent/context/traceability.json`` and are validated here:
      a symbol that no longer exists is an error, not a silent stale row.
"""

from __future__ import annotations

import argparse
import ast
import difflib
import hashlib
import json
import re
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs" / "agent-guide"
CODE_MAP = GUIDE / "code-map.md"
TRACE = GUIDE / "traceability.md"
CURATED = ROOT / ".agent" / "context" / "traceability.json"
GRAPH_OUT = ROOT / "graphify-out"
BUILD_INFO = GRAPH_OUT / "BUILD_INFO.json"
GRAPHIFY_PIN = "0.9.106"
GRAPH_TITLE = "kiloos-club"

HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
ACCESS = {"require_admin": "admin", "require_staff": "staff", "require_user": "user"}
ID_RE = re.compile(
    r"(?<![A-Za-z0-9])(MVP-\d{2}|BR-\d{3}|EP-\d{2}|OD-\d{2}|D-\d{3}|ADR-\d{4}|MS-\d{2})(?!\d)"
)
ID_ORDER = ["MVP", "BR", "EP", "OD", "D", "ADR", "MS"]
STATES = {"implemented", "partial", "demo-only", "sample", "missing"}

SQL_READ = (re.compile(r"(?<!DELETE )\bFROM\s+([a-z_]+)"), re.compile(r"\bJOIN\s+([a-z_]+)"))
SQL_WRITE = (
    ("INSERT", re.compile(r"\bINSERT\s+INTO\s+([a-z_]+)")),
    ("UPDATE", re.compile(r"\bUPDATE\s+([a-z_]+)\s+SET\b")),
    ("DELETE", re.compile(r"\bDELETE\s+FROM\s+([a-z_]+)")),
    ("DDL", re.compile(r"\bALTER\s+TABLE\s+([a-z_]+)")),
    ("DDL", re.compile(r"\bCREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-z_]+)")),
)
APPEND_ONLY = ("score_events", "point_transactions", "audit_logs")
CREATE_TABLE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-z_]+)\s*\((.*?)\n\s*\)", re.S
)
CREATE_INDEX = re.compile(
    r"CREATE\s+(UNIQUE\s+)?INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-z_]+)\s+ON\s+([a-z_]+)\s*"
    r"\(([^)]*)\)(?:\s*WHERE\s+([^;]+))?;",
    re.S,
)
ALTER_ADD = re.compile(r"ALTER\s+TABLE\s+([a-z_]+)\s+ADD\s+COLUMN\s+([a-z_]+)\s+([^;]+);")


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ----------------------------------------------------------------------------- model


@dataclass
class Sym:
    path: str
    name: str
    line: int
    end: int
    kind: str
    doc: str = ""
    reads: set[str] = field(default_factory=set)
    writes: set[str] = field(default_factory=set)
    ops: set[tuple[str, str]] = field(default_factory=set)  # (INSERT|UPDATE|DELETE|DDL, table)
    calls: set[str] = field(default_factory=set)
    errors: set[tuple[str, str]] = field(default_factory=set)
    templates: set[str] = field(default_factory=set)
    statuses: set[int] = field(default_factory=set)
    audits: set[str] = field(default_factory=set)
    outbox: set[str] = field(default_factory=set)
    keys: set[str] = field(default_factory=set)
    rule_codes: set[str] = field(default_factory=set)
    redirects: set[str] = field(default_factory=set)
    http: set[tuple[str, str, int]] = field(default_factory=set)
    ids: dict[str, int] = field(default_factory=dict)

    @property
    def key(self) -> str:
        return f"{self.path}::{self.name}"


@dataclass
class Route:
    method: str
    path: str
    handler: str
    access: str
    csrf: bool
    line: int

    @property
    def label(self) -> str:
        return f"{self.method} {self.path}"


@dataclass
class Table:
    name: str
    source: str
    line: int
    columns: list[tuple[str, str]] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    indexes: list[str] = field(default_factory=list)
    references: set[str] = field(default_factory=set)


@dataclass
class Template:
    path: str
    name: str
    extends: str = ""
    links: set[tuple[str, str, int]] = field(default_factory=set)  # (method, target, line)
    ids: dict[str, int] = field(default_factory=dict)


@dataclass
class Model:
    syms: dict[str, Sym] = field(default_factory=dict)
    routes: list[Route] = field(default_factory=list)
    tables: dict[str, Table] = field(default_factory=dict)
    templates: dict[str, Template] = field(default_factory=dict)
    imports: dict[str, set[str]] = field(default_factory=dict)
    consts: dict[str, dict[str, str]] = field(default_factory=dict)
    env: list[tuple[str, str, str]] = field(default_factory=list)
    entrypoints: list[tuple[str, str]] = field(default_factory=list)
    make: list[tuple[str, str]] = field(default_factory=list)
    defs: dict[str, dict] = field(default_factory=dict)  # requirement id -> definition
    mentions: dict[str, dict[str, int]] = field(default_factory=dict)  # id -> {file: line}
    backlog: dict[str, dict] = field(default_factory=dict)
    backlog_by_id: dict[str, set[str]] = field(default_factory=dict)
    unresolved: list[str] = field(default_factory=list)
    curated: dict = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)


# ------------------------------------------------------------------------- AST helpers


def walk(node: ast.AST, *, skip_nested: bool = False):
    stack = list(ast.iter_child_nodes(node))
    while stack:
        current = stack.pop()
        nested = isinstance(current, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
        if skip_nested and nested:
            continue
        yield current
        stack.extend(ast.iter_child_nodes(current))


def pattern(node: ast.AST | None, scope: ast.AST | None = None, depth: int = 0) -> str | None:
    """Render a string-like expression as text, with ``{...}`` for dynamic parts."""
    if node is None:
        return None
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts = []
        for value in node.values:
            if isinstance(value, ast.Constant):
                parts.append(str(value.value))
            elif isinstance(value, ast.FormattedValue):
                parts.append("{" + ast.unparse(value.value) + "}")
        return "".join(parts)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = pattern(node.left, scope, depth), pattern(node.right, scope, depth)
        return None if left is None or right is None else left + right
    if isinstance(node, ast.IfExp):
        body, other = pattern(node.body, scope, depth), pattern(node.orelse, scope, depth)
        return None if body is None or other is None else f"{body} | {other}"
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.args:
        if node.func.id == "with_token":
            return pattern(node.args[0], scope, depth)
    if isinstance(node, ast.Name) and scope is not None and depth < 2:
        for item in walk(scope):
            if isinstance(item, ast.Assign) and len(item.targets) == 1:
                target = item.targets[0]
                if isinstance(target, ast.Name) and target.id == node.id:
                    return pattern(item.value, scope, depth + 1)
    return None


def choices(node: ast.AST | None, scope: ast.AST | None) -> list[str]:
    """Every literal value a small string expression can take.

    ``f"submission.{new_status}"`` with ``new_status = "approved" if ... else "rejected"``
    in the same function becomes both concrete values. Anything that cannot be resolved
    falls back to `pattern`, which keeps the ``{name}`` placeholder visible.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.IfExp):
        return choices(node.body, scope) + choices(node.orelse, scope)
    if isinstance(node, ast.Name) and scope is not None:
        for item in walk(scope):
            if isinstance(item, ast.Assign) and len(item.targets) == 1:
                target = item.targets[0]
                if isinstance(target, ast.Name) and target.id == node.id:
                    return choices(item.value, None)
        return []
    if isinstance(node, ast.JoinedStr):
        results = [""]
        for value in node.values:
            if isinstance(value, ast.Constant):
                options = [str(value.value)]
            else:
                options = choices(getattr(value, "value", None), scope)
            if not options:
                fallback = pattern(node)
                return [fallback] if fallback else []
            results = [head + tail for head in results for tail in options]
        return results
    fallback = pattern(node)
    return [fallback] if fallback else []


def ints(node: ast.AST) -> set[int]:
    found = set()
    for item in [node, *walk(node)]:
        if isinstance(item, ast.Constant) and isinstance(item.value, int):
            if not isinstance(item.value, bool) and 100 <= item.value <= 599:
                found.add(item.value)
    return found


def first_line(text: str | None) -> str:
    if not text:
        return ""
    line = text.strip().splitlines()[0].strip()
    return line if len(line) <= 110 else line[:107] + "…"


class Module:
    """One parsed Python file plus what its names resolve to."""

    def __init__(self, path: Path) -> None:
        self.path = rel(path)
        self.text = read(path)
        self.lines = self.text.splitlines()
        self.tree = ast.parse(self.text)
        self.aliases: dict[str, str] = {}
        self.imported: dict[str, str] = {}
        self.consts: dict[str, str] = {}
        self.local: dict[str, tuple[ast.AST, bool]] = {}
        self.deps: set[str] = set()
        self.has_main = "__main__" in self.text
        self._scan()

    def _scan(self) -> None:
        for node in ast.walk(self.tree):
            if not isinstance(node, ast.ImportFrom) or not node.module:
                continue
            base = node.module.replace(".", "/")
            for alias in node.names:
                local = alias.asname or alias.name
                as_module = ROOT / f"{base}/{alias.name}.py"
                as_symbol = ROOT / f"{base}.py"
                if as_module.is_file():
                    self.aliases[local] = rel(as_module)
                    self.deps.add(rel(as_module))
                elif as_symbol.is_file():
                    self.imported[local] = f"{rel(as_symbol)}::{alias.name}"
                    self.deps.add(rel(as_symbol))
        for node in self.tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                value = pattern(node.value)
                if isinstance(target, ast.Name) and value is not None:
                    self.consts[target.id] = value
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                self.local[node.name] = (node, False)
                if node.name == "create_app":
                    for inner in node.body:
                        if isinstance(inner, ast.FunctionDef | ast.AsyncFunctionDef):
                            self.local[inner.name] = (inner, True)

    def resolve(self, name: str) -> str | None:
        if name in self.local:
            return f"{self.path}::{name}"
        return self.imported.get(name)


def decorator_calls(node: ast.AST):
    for decorator in getattr(node, "decorator_list", []):
        if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
            yield decorator.func.attr, decorator
        elif isinstance(decorator, ast.Attribute):
            yield decorator.attr, None


def kind_of(module: Module, node: ast.AST, nested: bool) -> str:
    names = {name for name, _ in decorator_calls(node)}
    if isinstance(node, ast.ClassDef):
        return "class"
    if module.path.startswith("tests/"):
        if "fixture" in names:
            return "fixture"
        return "test" if node.name.startswith("test_") else "helper"
    if names & HTTP_METHODS:
        return "route"
    if "middleware" in names:
        return "middleware"
    if "exception_handler" in names:
        return "exception-handler"
    return "closure" if nested else "function"


def analyze(module: Module, node: ast.AST, nested: bool, tables: set[str]) -> Sym:
    skip = node.name == "create_app"
    sym = Sym(
        path=module.path,
        name=node.name,
        line=node.lineno,
        end=node.end_lineno or node.lineno,
        kind=kind_of(module, node, nested),
        doc=first_line(ast.get_docstring(node)),
    )
    body = getattr(node, "body", [])
    doc_node = None
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        doc_node = body[0].value

    strings: list[str] = []
    for item in walk(node, skip_nested=skip):
        if isinstance(item, ast.Constant) and isinstance(item.value, str) and item is not doc_node:
            strings.append(item.value)
            if re.fullmatch(r"[a-z_]+\.html", item.value):
                sym.templates.add(item.value)
        elif isinstance(item, ast.Name) and item.id in module.consts:
            strings.append(module.consts[item.id])
        elif isinstance(item, ast.Raise) and isinstance(item.exc, ast.Call):
            if isinstance(item.exc.func, ast.Name) and item.exc.func.id == "LoginRequired":
                sym.statuses.add(303)
        elif isinstance(item, ast.Assign) and len(item.targets) == 1:
            target = item.targets[0]
            value = pattern(item.value) if isinstance(target, ast.Name) else None
            if value and target.id in {"rule_code", "SALES_RULE_CODE"}:
                sym.rule_codes.add(re.sub(r"\{[^}]*\}", "<…>", value))
            if value and target.id == "key" and isinstance(item.value, ast.JoinedStr):
                sym.keys.add(re.sub(r"\{.*\}", "<id>", value))
        if not isinstance(item, ast.Call):
            continue
        _call(module, sym, node, item)

    for text in strings:
        for regex in SQL_READ:
            sym.reads.update(name for name in regex.findall(text) if name in tables)
        for operation, regex in SQL_WRITE:
            for name in regex.findall(text):
                if name in tables:
                    sym.writes.add(name)
                    sym.ops.add((operation, name))
        if "INSERT INTO audit_logs" in text:
            sym.audits.update(re.findall(r"VALUES\s*\([^']*'([a-z_.]+)'", text))
        if "INSERT INTO outbox_events" in text:
            sym.outbox.update(re.findall(r"VALUES\s*\([^']*'([a-z_.]+)'", text))
        if text.startswith("E_") and text.isupper():
            sym.errors.add(("row-error", text))
    sym.calls.discard(sym.key)

    for number in range(sym.line, sym.end + 1):
        for found in ID_RE.findall(module.lines[number - 1]):
            sym.ids.setdefault(found, number)
    return sym


def _call(module: Module, sym: Sym, scope: ast.AST, call: ast.Call) -> None:
    func = call.func
    name = func.id if isinstance(func, ast.Name) else None
    attr = func.attr if isinstance(func, ast.Attribute) else None

    if name == "Depends" and call.args and isinstance(call.args[0], ast.Name):
        target = module.resolve(call.args[0].id)
        if target:
            sym.calls.add(target)
    elif name:
        target = module.resolve(name)
        if target:
            sym.calls.add(target)
    elif attr and isinstance(func.value, ast.Name):
        owner = func.value.id
        if owner in module.aliases:
            sym.calls.add(f"{module.aliases[owner]}::{attr}")
        elif owner in module.imported:
            sym.calls.add(module.imported[owner])

    if name in {"DomainError", "ScoringError"} and call.args:
        code = pattern(call.args[0])
        if code and code.isupper():
            sym.errors.add((name, code))
    if name == "audit" and len(call.args) >= 3:
        sym.audits.update(choices(call.args[2], scope))
    if name == "render_error":
        for arg in call.args[1:]:
            sym.statuses |= ints(arg)
    if name in {"go", "RedirectResponse"} and call.args:
        sym.statuses.add(303)
        target = pattern(call.args[0], scope)
        if target:
            sym.redirects.add(target)
    for keyword in call.keywords:
        if keyword.arg == "status_code":
            sym.statuses |= ints(keyword.value)

    # HTTP calls made by tests: client.get("/x"), client.post(f"/x/{id}"), post(c, s, "/x")
    candidate = None
    if attr in {"get", "post"} and call.args:
        candidate = (attr.upper(), call.args[0])
    elif name == "post" and len(call.args) >= 3:
        candidate = ("POST", call.args[2])
    if candidate and sym.path.startswith("tests/"):
        text = pattern(candidate[1])
        if text is not None:
            text = re.sub(r"\{[^}]*\}", "{}", text)
            sym.http.add((candidate[0], text, call.lineno))


# -------------------------------------------------------------------------- collectors


def parse_tables(text: str, source: str, tables: dict[str, Table]) -> None:
    for match in CREATE_TABLE.finditer(text):
        name, body = match.group(1), match.group(2)
        line = text.count("\n", 0, match.start()) + 1
        table = tables.setdefault(name, Table(name=name, source=source, line=line))
        for raw in body.splitlines():
            entry = raw.strip().rstrip(",")
            if not entry or entry.startswith("--"):
                continue
            table.references.update(re.findall(r"REFERENCES\s+([a-z_]+)", entry))
            head = entry.split()[0]
            if head in {"UNIQUE", "PRIMARY", "FOREIGN"}:
                table.constraints.append(re.sub(r"\s+", " ", entry))
            elif head == "CHECK":
                if table.columns:
                    column, rest = table.columns[-1]
                    table.columns[-1] = (column, f"{rest} {re.sub(r'[ ]+', ' ', entry)}")
            else:
                rest = re.sub(r"\s+", " ", entry[len(head) :].strip())
                table.columns.append((head, rest))
    for match in ALTER_ADD.finditer(text):
        name, column, rest = match.groups()
        if name in tables:
            tables[name].columns.append(
                (column, re.sub(r"\s+", " ", rest) + f" — added in {source}")
            )
    for match in CREATE_INDEX.finditer(text):
        unique, index, name, columns, where = match.groups()
        if name in tables:
            squeezed = re.sub(r"\s+", " ", columns).strip()
            entry = f"{'UNIQUE ' if unique else ''}`{index}` ({squeezed})"
            if where:
                entry += " WHERE " + re.sub(r"\s+", " ", where).strip()
            tables[name].indexes.append(f"{entry} — {source}")


def collect_tables(model: Model) -> None:
    for path in sorted((ROOT / "db" / "migrations").glob("*.sql")):
        parse_tables(read(path), rel(path), model.tables)
    for path in sorted((ROOT / "app").glob("*.py")):
        tree = ast.parse(read(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if "CREATE TABLE" in node.value:
                    parse_tables(node.value + "\n", rel(path), model.tables)


def collect_python(model: Model) -> dict[str, Module]:
    modules: dict[str, Module] = {}
    files = sorted((ROOT / "app").glob("*.py")) + sorted((ROOT / "tests").glob("*.py"))
    names = set(model.tables)
    for path in files:
        if path.name == "__init__.py":
            continue
        module = Module(path)
        modules[module.path] = module
        for _name, (node, nested) in module.local.items():
            sym = analyze(module, node, nested, names)
            model.syms[sym.key] = sym
        if module.path.startswith("app/"):
            model.consts[module.path] = dict(module.consts)
            model.imports[module.path] = {dep for dep in module.deps if dep.startswith("app/")}
            if module.has_main:
                dotted = module.path[:-3].replace("/", ".")
                model.entrypoints.append(
                    (f"python -m {dotted}", first_line(ast.get_docstring(module.tree)))
                )
    for sym in model.syms.values():
        sym.calls = {key for key in sym.calls if key in model.syms}
    return modules


def collect_routes(model: Model, modules: dict[str, Module]) -> None:
    module = modules["app/main.py"]
    for name, (node, _nested) in module.local.items():
        for method, call in decorator_calls(node):
            if method not in HTTP_METHODS or call is None or not call.args:
                continue
            owner = call.func.value
            if not (isinstance(owner, ast.Name) and owner.id == "app"):
                continue
            path = pattern(call.args[0])
            if path is None:
                continue
            csrf = any(
                isinstance(item, ast.Name) and item.id == "csrf_guard"
                for keyword in call.keywords
                if keyword.arg == "dependencies"
                for item in ast.walk(keyword.value)
            )
            access = "public"
            defaults = [*node.args.defaults, *[d for d in node.args.kw_defaults if d is not None]]
            for default in defaults:
                for item in ast.walk(default):
                    if isinstance(item, ast.Name) and item.id in ACCESS:
                        access = ACCESS[item.id]
            if access == "public" and csrf:
                access = "token"
            model.routes.append(
                Route(method.upper(), path, f"{module.path}::{name}", access, csrf, node.lineno)
            )
    model.routes.sort(key=lambda route: (route.path, route.method))


def match_route(model: Model, method: str, target: str) -> Route | None:
    target = target.split("?", 1)[0].split("#", 1)[0]
    if not target.startswith("/"):
        return None
    wanted = target.rstrip("/").split("/") if target != "/" else ["", ""]
    best: tuple[int, Route] | None = None
    for route in model.routes:
        if route.method != method:
            continue
        have = route.path.rstrip("/").split("/") if route.path != "/" else ["", ""]
        if len(have) != len(wanted):
            continue
        score = 0
        for mine, theirs in zip(have, wanted, strict=True):
            is_param = mine.startswith("{")
            dynamic = "{" in theirs
            if is_param:
                score += 2 if dynamic else 1
            elif mine == theirs:
                score += 3
            else:
                score = -1
                break
        if score >= 0 and (best is None or score > best[0]):
            best = (score, route)
    return best[1] if best else None


def template_targets(expression: str) -> list[str]:
    """`'/a/' ~ x['id'] ~ '/b'` -> ['/a/{}/b']; handles `A if cond else B`."""
    expression = re.sub(r"\[[^\]]*\]", "", expression)
    choice = re.match(r"^(?P<a>.*?)\s+if\s+.*?\s+else\s+(?P<b>.*)$", expression, flags=re.S)
    options = [choice.group("a"), choice.group("b")] if choice else [expression]
    targets = []
    for option in options:
        rendered = ""
        for part in option.split("~"):
            literal = re.search(r"'([^']*)'", part)
            rendered += literal.group(1) if literal else "{}"
        targets.append(rendered)
    return targets


def collect_templates(model: Model) -> None:
    link = re.compile(r'(href|action|src)="\{\{\s*url\((?P<expr>.*?)\)\s*\}\}"')
    plain = re.compile(r'(href|action|src)="(/[^"{]*)"')
    for path in sorted((ROOT / "app" / "templates").glob("*.html")):
        text = read(path)
        template = Template(path=rel(path), name=path.name)
        extends = re.search(r'\{%\s*extends\s+"([^"]+)"', text)
        template.extends = extends.group(1) if extends else ""
        for number, line in enumerate(text.splitlines(), start=1):
            for match in link.finditer(line):
                method = "POST" if match.group(1) == "action" else "GET"
                for target in template_targets(match.group("expr")):
                    template.links.add((method, target, number))
            for match in plain.finditer(line):
                method = "POST" if match.group(1) == "action" else "GET"
                template.links.add((method, match.group(2), number))
            for found in ID_RE.findall(line):
                template.ids.setdefault(found, number)
        model.templates[template.name] = template


def collect_config(model: Model) -> None:
    tree = ast.parse(read(ROOT / "app" / "config.py"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.keyword) or node.arg is None:
            continue
        for item in ast.walk(node.value):
            if not (isinstance(item, ast.Call) and item.args):
                continue
            first = item.args[0]
            if isinstance(first, ast.Constant) and str(first.value).startswith("KILOOS_"):
                default = ast.unparse(item.args[1]) if len(item.args) > 1 else "—"
                model.env.append((str(first.value), default, node.arg))
    model.env = sorted(set(model.env))
    makefile = ROOT / "Makefile"
    if makefile.is_file():
        for line in read(makefile).splitlines():
            match = re.match(r"^([a-z][a-z-]*):(?:[^#]*)(?:##\s*(.*))?$", line)
            if match:
                model.make.append((match.group(1), (match.group(2) or "").strip()))


def doc_files() -> list[Path]:
    found = set(ROOT.glob("*.md"))
    found |= set((ROOT / "docs").rglob("*.md"))
    found |= set((ROOT / ".agent").rglob("*.md"))
    found |= set((ROOT / "db").rglob("*.md"))
    return sorted(path for path in found if path not in {CODE_MAP, TRACE})


def collect_ids(model: Model) -> None:
    context = ROOT / ".agent" / "CONTEXT.md"
    for number, line in enumerate(read(context).splitlines(), start=1):
        row = re.match(r"^\|\s*((?:MVP|BR)-\d+)\s*\|\s*(.+?)\s*\|", line)
        if row:
            model.defs[row.group(1)] = {"title": row.group(2), "file": rel(context), "line": number}
        milestone = re.match(r"^\|\s*(MS-\d+)\s+([^|]+?)\s*\|\s*([^|]+?)\s*\|", line)
        if milestone:
            title = f"{milestone.group(2)} — {milestone.group(3)}".replace("**", "")
            model.defs[milestone.group(1)] = {"title": title, "file": rel(context), "line": number}
        if "EP-01" in line and "EP-02" in line:
            for epic, title in re.findall(r"(EP-\d{2})\s+([^·\n]+?)\s*(?:·|\.?$)", line):
                model.defs[epic] = {"title": title.strip(), "file": rel(context), "line": number}

    def headings(path: Path, prefix: str) -> None:
        lines = read(path).splitlines()
        inside_fence = False
        for number, line in enumerate(lines, start=1):
            if line.startswith("```"):
                inside_fence = not inside_fence
            match = re.match(rf"^## ({prefix}-\d+)\s*[—-]\s*(.+)$", line)
            if not match or inside_fence:
                continue
            status = ""
            for follow in lines[number : number + 8]:
                found = re.match(r"^-\s*Status:\s*(.+)$", follow)
                if found:
                    status = found.group(1).strip()
                    break
            model.defs[match.group(1)] = {
                "title": match.group(2).strip(),
                "file": rel(path),
                "line": number,
                "status": status,
            }

    headings(ROOT / "docs" / "decisions" / "open-decisions.md", "OD")
    headings(ROOT / "docs" / "decisions" / "decision-log.md", "D")
    for path in sorted((ROOT / "docs" / "architecture" / "decisions").glob("[0-9]*.md")):
        text = read(path)
        title = re.search(r"^#\s+(.+)$", text, flags=re.M)
        status = re.search(r"^-\s*Status:\s*(.+)$", text, flags=re.M)
        model.defs[f"ADR-{path.name[:4]}"] = {
            "title": re.sub(r"^ADR-\d+\s*[—:-]\s*", "", title.group(1)).strip()
            if title
            else path.stem,
            "file": rel(path),
            "line": 1,
            "status": status.group(1).strip().strip("*") if status else "",
        }

    scan = sorted((ROOT / "app").glob("*.py")) + sorted((ROOT / "tests").glob("*.py"))
    scan += sorted((ROOT / "app" / "templates").glob("*.html"))
    scan += sorted((ROOT / "db" / "migrations").glob("*.sql")) + doc_files()
    for path in scan:
        for number, line in enumerate(read(path).splitlines(), start=1):
            for found in ID_RE.findall(line):
                model.mentions.setdefault(found, {}).setdefault(rel(path), number)

    backlog = ROOT / "docs" / "delivery" / "backlog.md"
    if backlog.is_file():
        current = ""
        for number, line in enumerate(read(backlog).splitlines(), start=1):
            row = re.match(r"^\|\s*([ABCD]\d{1,2})\s*\|\s*(.+?)\s*\|", line)
            detail = re.match(r"^###\s+\S+\s+([ABCD]\d{1,2})\b", line)
            if row:
                current = row.group(1)
                cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
                status = cells[-1] if cells[-1] in {"TODO", "DOING", "DONE", "BLOCKED"} else ""
                model.backlog[current] = {"title": row.group(2), "line": number, "status": status}
            elif detail:
                current = detail.group(1)
            elif line.startswith("## ") or line.startswith("---"):
                current = ""
            if current:
                for found in ID_RE.findall(line):
                    model.backlog_by_id.setdefault(found, set()).add(current)


def collect_curated(model: Model) -> None:
    if not CURATED.is_file():
        model.problems.append(f"missing curated file: {rel(CURATED)}")
        return
    data = json.loads(read(CURATED))
    model.curated = data
    known = set(model.syms)
    for table in model.tables.values():
        known.add(f"{table.source}::{table.name}")
        for index in table.indexes:
            name = re.search(r"`([a-z_]+)`", index)
            source = index.rsplit(" — ", 1)[-1]
            if name:
                known.add(f"{source}::{name.group(1)}")
    for template in model.templates.values():
        known.add(template.path)
    for item_id, item in data.get("items", {}).items():
        if item_id not in model.defs:
            model.problems.append(f"{rel(CURATED)}: unknown id {item_id}")
        if item.get("state") not in STATES:
            model.problems.append(
                f"{rel(CURATED)}: {item_id} has invalid state {item.get('state')!r}"
            )
        for ref in [*item.get("code", []), *item.get("tests", [])]:
            if ref not in known:
                model.problems.append(f"{rel(CURATED)}: {item_id} points to missing symbol {ref}")
        for ref in item.get("tests", []):
            if "::test_" not in ref:
                model.problems.append(f"{rel(CURATED)}: {item_id} test entry is not a test: {ref}")
        for ref in item.get("backlog", []):
            if ref not in model.backlog:
                model.problems.append(
                    f"{rel(CURATED)}: {item_id} points to unknown backlog row {ref}"
                )


def build_model() -> Model:
    model = Model()
    collect_tables(model)
    modules = collect_python(model)
    collect_routes(model, modules)
    collect_templates(model)
    collect_config(model)
    collect_ids(model)
    collect_curated(model)
    for template in model.templates.values():
        for method, target, _line in sorted(template.links):
            if target.startswith("/static/"):
                continue
            if match_route(model, method, target) is None:
                model.unresolved.append(f"{template.path}: {method} {target} matches no route")
    for sym in model.syms.values():
        for method, target, _line in sorted(sym.http):
            if match_route(model, method, target) is None:
                model.unresolved.append(f"{sym.key}: {method} {target} matches no route")
    model.unresolved = sorted(set(model.unresolved))
    return model


# ---------------------------------------------------------------------------- queries


def closure(model: Model, key: str, *, only: str | None = None) -> set[str]:
    """Everything reachable from ``key`` through direct calls (including ``key``)."""
    seen: set[str] = set()
    stack = [key]
    while stack:
        current = stack.pop()
        if current in seen or current not in model.syms:
            continue
        seen.add(current)
        for callee in model.syms[current].calls:
            if only is None or callee.startswith(only):
                stack.append(callee)
    return seen


def effects(model: Model, key: str) -> tuple[set[str], set[str], set[tuple[str, str]]]:
    reads: set[str] = set()
    writes: set[str] = set()
    errors: set[tuple[str, str]] = set()
    for member in closure(model, key):
        sym = model.syms[member]
        reads |= sym.reads
        writes |= sym.writes
        errors |= sym.errors
    return reads, writes, errors


def tests_by_route(model: Model) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {route.label: set() for route in model.routes}
    for sym in model.syms.values():
        if sym.kind != "test":
            continue
        for member in closure(model, sym.key, only="tests/"):
            for method, target, _line in model.syms[member].http:
                route = match_route(model, method, target)
                if route:
                    result[route.label].add(sym.key)
    return result


def callers(model: Model) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for sym in model.syms.values():
        for callee in sym.calls:
            result.setdefault(callee, set()).add(sym.key)
    return result


def short(key: str) -> str:
    path, _, name = key.partition("::")
    stem = Path(path).stem
    return f"{stem}.{name}" if path.startswith("app/") else f"{stem}::{name}"


def code(items) -> str:
    values = sorted(items)
    return ", ".join(f"`{value}`" for value in values) if values else "—"


def table(headers: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for row in rows:
        lines.append("| " + " | ".join(str(cell).replace("|", "\\|") for cell in row) + " |")
    return lines


# ---------------------------------------------------------------------------- renderers

GENERATED_NOTE = (
    "> **GENERATED** by `.agent/tools/knowledge_map.py` — do not edit by hand.\n"
    "> Regenerate with `make docs` (or `python3 .agent/tools/knowledge_map.py`).\n"
    "> `tests/test_docs.py` fails when this file no longer matches the code."
)


def render_code_map(model: Model) -> str:
    by_route = tests_by_route(model)
    called_by = callers(model)
    handler_routes: dict[str, list[Route]] = {}
    for route in model.routes:
        handler_routes.setdefault(route.handler, []).append(route)
    out: list[str] = [
        "# Code Map",
        "",
        GENERATED_NOTE,
        "",
        'This file answers "where is it?" without searching: every route, the function that',
        "handles it, the tables it touches, the template it renders and the tests that reach it.",
        "It is a projection of the code. When it disagrees with the code, the code is right and",
        "this file must be regenerated.",
        "",
        "**Reading the notation**",
        "",
        "- `repo.review_submission` means `app/repo.py::review_submission`; jump there with",
        '  `grep -n "def review_submission" app/repo.py`.',
        "- `test_flow::test_x` means `tests/test_flow.py::test_x`; run it with",
        "  `.venv/bin/pytest tests/test_flow.py::test_x`.",
        '- "Reads" / "Writes" are SQL tables found in string literals. For a route they are',
        "  transitive (through every project function the handler calls).",
        "- Access: `public` (no session), `token` (a session token is required by the CSRF",
        "  guard, the user row is not loaded), `user` (any signed-in active user), `staff`",
        "  (operator or admin), `admin`. Organization scope is enforced inside the handler or",
        "  the query, not by the access level.",
        '- "Tests" counts tests whose code requests the route by a literal path, directly or',
        "  through a test helper. A page reached only by following a redirect is not counted.",
        "",
        "Contents: [1 Modules](#1-modules) · [2 Routes](#2-routes)"
        " · [3 Route details](#3-route-details)"
        " · [4 Functions](#4-functions-by-module) · [5 Tables](#5-database-tables)"
        " · [6 Templates](#6-templates) · [7 Tests](#7-tests) · [8 Error codes](#8-error-codes)"
        " · [9 Constants](#9-domain-constants) · [10 Configuration](#10-configuration)"
        " · [11 Commands](#11-commands) · [12 Unresolved](#12-unresolved-references)",
        "",
        "## 1. Modules",
        "",
    ]
    rows = []
    for path in sorted(model.imports):
        members = [sym for sym in model.syms.values() if sym.path == path]
        rows.append(
            [
                f"`{path}`",
                str(len(members)),
                code(Path(dep).stem for dep in model.imports[path]),
            ]
        )
    out += table(["Module", "Symbols", "Imports (project modules)"], rows)
    out += ["", "```mermaid", "graph LR"]
    for path in sorted(model.imports):
        for dep in sorted(model.imports[path]):
            out.append(f"    {Path(path).stem} --> {Path(dep).stem}")
    out += ["```", "", "## 2. Routes", ""]

    rows = []
    for route in model.routes:
        handler = model.syms[route.handler]
        csrf = "yes" if route.csrf else ("exempt" if route.method != "GET" else "—")
        rows.append(
            [
                route.method,
                f"`{route.path}`",
                route.access,
                csrf,
                f"`{short(route.handler)}`",
                code(handler.templates),
                str(len(by_route[route.label])),
            ]
        )
    out += table(["Method", "Path", "Access", "CSRF", "Handler", "Templates", "Tests"], rows)
    out += [
        "",
        f"{len(model.routes)} routes. FastAPI also serves `/api/docs`, `/openapi.json` and the",
        "`/static` mount; they are framework-provided and not listed.",
        "",
        "## 3. Route details",
        "",
    ]
    for route in model.routes:
        handler = model.syms[route.handler]
        reads, writes, errors = effects(model, route.handler)
        domain = {key for key in handler.calls if not key.startswith("app/main.py::")}
        helpers = {key for key in handler.calls if key.startswith("app/main.py::")}
        out.append(f"### `{route.label}`")
        out.append("")
        csrf = "yes" if route.csrf else ("exempt" if route.method != "GET" else "not needed (GET)")
        out.append(f"- Handler: `{short(route.handler)}` — access **{route.access}** — CSRF {csrf}")
        if handler.doc:
            out.append(f"- Purpose: {handler.doc}")
        out.append(f"- Renders: {code(handler.templates)} · Redirects: {code(handler.redirects)}")
        statuses = set(handler.statuses)
        for member in closure(model, route.handler, only="app/main.py"):
            statuses |= model.syms[member].statuses
        out.append(
            f"- Non-200 status codes (handler and its guards): {code(str(s) for s in statuses)}"
        )
        out.append(f"- Calls: {code(short(key) for key in domain)}")
        out.append(f"- Closures used: {code(short(key) for key in helpers)}")
        out.append(f"- Reads: {code(reads)}")
        out.append(f"- Writes: {code(writes)}")
        grouped = sorted({f"{name}:{value}" for name, value in errors})
        out.append(f"- Error codes reachable: {code(grouped)}")
        out.append(
            f"- Tests ({len(by_route[route.label])}): "
            f"{code(short(k) for k in by_route[route.label])}"
        )
        out.append("")

    out += ["## 4. Functions by module", ""]
    order = ["app/main.py", "app/repo.py", "app/scoring.py", "app/sales.py", "app/security.py"]
    order += sorted(path for path in model.imports if path not in order)
    for path in order:
        members = sorted(
            (sym for sym in model.syms.values() if sym.path == path), key=lambda sym: sym.name
        )
        if not members:
            continue
        out += [f"### `{path}`", ""]
        rows = []
        for sym in members:
            if sym.kind == "route":
                continue
            users = called_by.get(sym.key, set())
            used = f"{len(users)} callers" if len(users) > 8 else code(short(key) for key in users)
            rows.append(
                [
                    f"`{sym.name}`",
                    sym.kind,
                    sym.doc or "—",
                    code(sym.reads),
                    code(sym.writes),
                    code(short(key) for key in sym.calls),
                    used,
                ]
            )
        headers = ["Symbol", "Kind", "Purpose (docstring)", "Reads", "Writes", "Calls", "Called by"]
        out += table(headers, rows)
        out.append("")
    out += [
        'Route handlers of `app/main.py` are listed in section 3. "Reads" and "Writes" here are',
        'the SQL statements written in that function only; follow "Calls" for the rest of the',
        'chain. "Called by" shows direct callers; `Depends(...)` counts as a call.',
        "",
        "## 5. Database tables",
        "",
    ]
    app_ops = {
        entry for sym in model.syms.values() if sym.path.startswith("app/") for entry in sym.ops
    }
    for name in APPEND_ONLY:
        broken = sorted(
            op for op, target in app_ops if target == name and op in {"UPDATE", "DELETE"}
        )
        verdict = f"**VIOLATED** ({', '.join(broken)} found)" if broken else "holds"
        out.append(
            f"- Append-only check for `{name}`: {verdict} — "
            "no UPDATE or DELETE statement in `app/`."
            if not broken
            else f"- Append-only check for `{name}`: {verdict}."
        )
    out.append("")
    for name in sorted(model.tables):
        item = model.tables[name]
        readers = {
            sym.key
            for sym in model.syms.values()
            if name in sym.reads and sym.path.startswith("app/")
        }
        writers = {
            sym.key
            for sym in model.syms.values()
            if name in sym.writes and sym.path.startswith("app/")
        }
        out += [f"### `{name}`", "", f"- Defined in: `{item.source}`"]
        out.append(
            "- Columns: " + "; ".join(f"`{column}` {rest}".strip() for column, rest in item.columns)
        )
        if item.constraints:
            out.append("- Table constraints: " + "; ".join(item.constraints))
        if item.indexes:
            out.append("- Indexes: " + "; ".join(item.indexes))
        out.append(f"- References: {code(item.references)}")
        out.append(f"- Read by: {code(short(key) for key in readers)}")
        for operation in ("INSERT", "UPDATE", "DELETE", "DDL"):
            by = {key for key in writers if (operation, name) in model.syms[key].ops}
            if by:
                out.append(f"- {operation} by: {code(short(key) for key in by)}")
        if not writers:
            out.append("- Written by: —")
        out.append("")

    out += ["## 6. Templates", ""]
    rows = []
    for name in sorted(model.templates):
        item = model.templates[name]
        renderers = {sym.key for sym in model.syms.values() if name in sym.templates}
        targets = set()
        for method, target, _line in item.links:
            route = match_route(model, method, target)
            if route:
                targets.add(route.label)
        rows.append(
            [f"`{name}`", item.extends or "—", code(short(k) for k in renderers), code(targets)]
        )
    out += table(["Template", "Extends", "Rendered by", "Links and forms point to"], rows)
    out += [
        "",
        "All templates live in `app/templates/`. Every internal link goes through the `url()`",
        "helper so the `?s=` session token survives (see `app/main.py::create_app`).",
        "",
        "## 7. Tests",
        "",
    ]
    test_files = sorted({sym.path for sym in model.syms.values() if sym.kind == "test"})
    total = 0
    for path in test_files:
        members = sorted(
            (sym for sym in model.syms.values() if sym.path == path and sym.kind == "test"),
            key=lambda sym: sym.line,
        )
        total += len(members)
        out += [f"### `{path}` ({len(members)} tests)", ""]
        rows = []
        for sym in members:
            reached = set()
            domain = set()
            for member in closure(model, sym.key, only="tests/"):
                inner = model.syms[member]
                for method, target, _line in inner.http:
                    route = match_route(model, method, target)
                    if route:
                        reached.add(route.label)
                domain |= {key for key in inner.calls if key.startswith("app/")}
            domain = {key for key in domain if not key.endswith(("::Settings", "::create_app"))}
            rows.append(
                [f"`{sym.name}`", code(reached), code(short(k) for k in domain), code(sym.ids)]
            )
        out += table(["Test", "Routes exercised", "Direct domain calls", "IDs"], rows)
        out.append("")
    helpers = sorted(
        sym.key
        for sym in model.syms.values()
        if sym.path.startswith("tests/") and sym.kind in {"helper", "fixture"}
    )
    out += [
        f"{total} test functions. `tests/test_docs.py` is the pair that keeps this file honest.",
        f"Shared helpers and fixtures: {code(short(key) for key in helpers)}.",
        "",
        "## 8. Error codes",
        "",
    ]
    by_code: dict[tuple[str, str], set[str]] = {}
    for sym in model.syms.values():
        if not sym.path.startswith("app/"):
            continue
        for entry in sym.errors:
            by_code.setdefault(entry, set()).add(sym.key)
    rows = [
        [f"`{value}`", name, code(short(key) for key in by_code[(name, value)])]
        for name, value in sorted(by_code, key=lambda entry: (entry[1], entry[0]))
    ]
    out += table(["Code", "Raised as", "Raised in"], rows)
    out += [
        "",
        "`DomainError` carries a Persian message for the UI. `ScoringError` carries only the code;",
        "`repo.reverse_score_event` translates it, other callers do not (see backlog A1).",
        "`row-error` codes are stored on `sales_records.error_code`. HTTP status per code:",
        "`docs/engineering/api-spec.md`.",
        "",
        "## 9. Domain constants",
        "",
    ]
    for title, attribute in (
        ("Audit actions (`audit_logs.action`)", "audits"),
        ("Outbox event types (`outbox_events.event_type`)", "outbox"),
        ("Idempotency keys (`score_events.idempotency_key`)", "keys"),
        ("Rule codes (`scoring_rule_versions.rule_code`)", "rule_codes"),
    ):
        found: dict[str, set[str]] = {}
        for sym in model.syms.values():
            if not sym.path.startswith("app/"):
                continue
            for value in getattr(sym, attribute):
                found.setdefault(value, set()).add(sym.key)
        if attribute == "rule_codes":
            for path, consts in model.consts.items():
                for name, value in consts.items():
                    if name.endswith("RULE_CODE"):
                        found.setdefault(value, set()).add(f"{path}::{name}")
        out += [f"**{title}**", ""]
        out += table(
            ["Value", "Written in"],
            [[f"`{v}`", code(short(k) for k in found[v])] for v in sorted(found)],
        )
        out.append("")

    out += ["## 10. Configuration", ""]
    out += table(
        ["Environment variable", "Default (as written in code)", "`Settings` field"],
        [[f"`{name}`", f"`{default}`", f"`{attr}`"] for name, default, attr in model.env],
    )
    out += [
        "",
        "Read in `app/config.py::Settings.from_env`. Meaning of each variable:",
        "`docs/operations/runbook.md`.",
        "",
        "## 11. Commands",
        "",
    ]
    out += table(
        ["Make target", "Purpose"], [[f"`make {name}`", note or "—"] for name, note in model.make]
    )
    out.append("")
    out += table(
        ["Module entry point", "Purpose"],
        [[f"`{cmd}`", note or "—"] for cmd, note in sorted(model.entrypoints)],
    )
    out += ["", "## 12. Unresolved references", ""]
    if model.unresolved:
        out.append(
            "Paths written in templates or tests that match no route. An entry is expected when a"
        )
        out.append("test asks for an unknown page on purpose; anything else is a broken link.")
        out.append("")
        out += [f"- {entry}" for entry in model.unresolved]
    else:
        out.append("None: every internal link, form action and test request matches a route.")
    out.append("")
    return "\n".join(out)


def id_sort(value: str) -> tuple[int, str]:
    prefix = value.split("-")[0]
    return (ID_ORDER.index(prefix) if prefix in ID_ORDER else 99, value)


def render_traceability(model: Model) -> str:
    items = model.curated.get("items", {})
    meta = model.curated.get("meta", {})
    out = [
        "# Traceability",
        "",
        GENERATED_NOTE,
        "",
        "Which requirement lives where: every `MVP-xx`, `BR-xxx`, `EP-xx`, `OD-xx`, `D-xxx`, `ADR`",
        "and `MS` id, the code that implements it, the tests that check it and the documents that",
        "mention it.",
        "",
        "Two sources feed this file:",
        "",
        f"1. **Curated links** in `{rel(CURATED)}` — written by an agent after reading the code",
        f"   (last reviewed {meta.get('reviewed_on', '?')}). The generator verifies that every",
        "   symbol named there still exists, so a rename breaks the check instead of leaving a",
        "   stale row.",
        "2. **Automatic scan** of ids written in code, tests, templates, migrations and markdown.",
        "",
        "**State is implementation state, not approval.** `implemented` · `partial` ·",
        "`demo-only` · `sample` · `missing`. Nothing in this file is `APPROVED`; only",
        "`docs/decisions/decision-log.md` can approve a decision (`AGENTS.md` §3).",
        "",
    ]

    def curated_table(prefix: str, title: str) -> None:
        out.extend([f"## {title}", ""])
        rows = []
        for item_id in sorted(
            (key for key in model.defs if key.startswith(prefix + "-")), key=id_sort
        ):
            item = items.get(item_id, {})
            rows.append(
                [
                    f"**{item_id}**",
                    model.defs[item_id]["title"],
                    item.get("state", "—"),
                    code(
                        short(ref) if "::" in ref and ref.startswith(("app/", "tests/")) else ref
                        for ref in item.get("code", [])
                    ),
                    code(short(ref) for ref in item.get("tests", [])),
                    item.get("note", "—"),
                    ", ".join(item.get("backlog", [])) or "—",
                ]
            )
        out.extend(
            table(["ID", "Title", "State", "Code", "Tests", "Gaps and notes", "Backlog"], rows)
        )
        out.append("")

    curated_table("MVP", "1. MVP scope")
    curated_table("BR", "2. Business rules")
    curated_table("EP", "3. Epics")

    def where(item_id: str, prefixes: tuple[str, ...]) -> str:
        files = sorted(
            path for path in model.mentions.get(item_id, {}) if path.startswith(prefixes)
        )
        return code(files)

    out += ["## 4. Open decisions", ""]
    rows = []
    for item_id in sorted((key for key in model.defs if key.startswith("OD-")), key=id_sort):
        definition = model.defs[item_id]
        rows.append(
            [
                f"**{item_id}**",
                definition["title"],
                definition.get("status", "—") or "—",
                where(item_id, ("app/", "db/", "tests/")),
                ", ".join(sorted(model.backlog_by_id.get(item_id, []), key=backlog_sort)) or "—",
            ]
        )
    out += table(["ID", "Topic", "Status", "Assumption is coded in", "Backlog rows"], rows)
    out += [
        "",
        'Full text, options and impact: `docs/decisions/open-decisions.md`. The "coded in" column',
        "lists the files to revisit when the decision is made.",
        "",
        "## 5. Decisions and ADRs",
        "",
    ]
    rows = []
    for item_id in sorted(
        (key for key in model.defs if key.startswith(("D-", "ADR-"))), key=id_sort
    ):
        definition = model.defs[item_id]
        rows.append(
            [
                f"**{item_id}**",
                definition["title"],
                definition.get("status", "—") or "—",
                f"`{definition['file']}`",
                where(item_id, ("app/", "db/", "tests/")),
            ]
        )
    out += table(["ID", "Title", "Status", "Recorded in", "Referenced in code"], rows)
    out += ["", "## 6. Milestones", ""]
    rows = [
        [f"**{item_id}**", model.defs[item_id]["title"]]
        for item_id in sorted((key for key in model.defs if key.startswith("MS-")), key=id_sort)
    ]
    out += table(["ID", "Milestone — date"], rows)
    out += [
        "",
        "Source: `.agent/CONTEXT.md` §۱۰ and `docs/delivery/execution-plan.md`.",
        "",
        "## 7. Backlog rows",
        "",
    ]
    rows = []
    for item_id in sorted(model.backlog, key=backlog_sort):
        linked = sorted(
            (key for key, rows_ in model.backlog_by_id.items() if item_id in rows_), key=id_sort
        )
        item = model.backlog[item_id]
        rows.append(
            [f"**{item_id}**", item["title"], item["status"] or "—", ", ".join(linked) or "—"]
        )
    out += table(["Row", "Work", "Status", "Ids named in the row or its detail section"], rows)
    out += [
        "",
        "Evidence, sizes and order: `docs/delivery/backlog.md`.",
        "",
        "## 8. Where each id is mentioned",
        "",
        "Use this list when a decision changes: these are the files to re-read and update.",
        "",
    ]
    rows = []
    for item_id in sorted(model.mentions, key=id_sort):
        files = sorted(model.mentions[item_id])
        definition = model.defs.get(item_id)
        defined = f"`{definition['file']}`" if definition else "not defined in this repository"
        rows.append([f"**{item_id}**", defined, str(len(files)), code(files)])
    out += table(["ID", "Defined in", "Files", "Mentioned in"], rows)
    out.append("")
    return "\n".join(out)


def backlog_sort(value: str) -> tuple[str, int]:
    return (value[0], int(value[1:]))


# ------------------------------------------------------------------------------- graph


def graph_inputs() -> list[Path]:
    """Product knowledge only: code, tests, schema and prose. Tooling, empty templates and the
    licence are left out because they add nodes without adding answers."""
    files = sorted((ROOT / "app").glob("*.py")) + sorted((ROOT / "tests").glob("*.py"))
    files += sorted((ROOT / "db" / "migrations").glob("*.sql"))
    skipped = (ROOT / ".agent" / "templates", ROOT / ".agent" / "tools")
    for path in doc_files():
        if path.name == "LICENSE.md" or any(parent in path.parents for parent in skipped):
            continue
        files.append(path)
    return files


def fingerprint() -> tuple[str, int]:
    """Hash of everything the graph is built from, including this tool."""
    paths = graph_inputs() + sorted((ROOT / "app" / "templates").glob("*.html"))
    paths += [CURATED, Path(__file__).resolve()]
    digest = hashlib.sha256()
    for path in sorted(set(paths)):
        if not path.is_file():
            continue
        digest.update(rel(path).encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest(), len(set(paths))


GRAPH_FILES = ("graph.json", "graph.html", "GRAPH_REPORT.md")


def graph_is_current() -> bool:
    if not BUILD_INFO.is_file() or not all((GRAPH_OUT / name).is_file() for name in GRAPH_FILES):
        return False
    current, _count = fingerprint()
    return json.loads(read(BUILD_INFO)).get("fingerprint") == current


def graph_status() -> str:
    if not BUILD_INFO.is_file():
        return "knowledge graph: not built (run `make graph`)"
    if graph_is_current():
        info = json.loads(read(BUILD_INFO))
        return f"knowledge graph: up to date ({info.get('nodes')} nodes, {info.get('edges')} edges)"
    return "knowledge graph: STALE — sources changed since it was built (run `make graph`)"


def semantic_layer(model: Model, ast_nodes: list[dict]) -> tuple[list[dict], list[dict]]:
    """Nodes and edges the AST extractor cannot see, in graphify's extraction schema."""
    by_symbol: dict[tuple[str, str], str] = {}
    headings: dict[str, list[tuple[int, str]]] = {}
    pages: dict[str, str] = {}
    for node in ast_nodes:
        source = node.get("source_file") or ""
        label = str(node.get("label") or "")
        location = str(node.get("source_location") or "")
        by_symbol.setdefault((source, label.removesuffix("()")), node["id"])
        if node.get("node_kind") == "heading" and location.startswith("L"):
            headings.setdefault(source, []).append((int(location[1:]), node["id"]))
        if node.get("node_kind") == "page" or (
            location in {"", "L1", "None"} and label == Path(source).name
        ):
            pages.setdefault(source, node["id"])
    for entries in headings.values():
        entries.sort()

    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    seen: set[tuple[str, str, str, str]] = set()

    def add_node(
        node_id: str, label: str, kind: str, source: str, line: int | None, **extra
    ) -> str:
        nodes.setdefault(
            node_id,
            {
                "id": node_id,
                "label": label,
                "file_type": kind,
                "source_file": source,
                "source_location": f"L{line}" if line else None,
                **extra,
            },
        )
        return node_id

    def add_edge(
        source: str | None,
        target: str | None,
        relation: str,
        where: str,
        line: int | None,
        *,
        context: str,
        confidence: str = "EXTRACTED",
        score: float = 1.0,
    ) -> None:
        if not source or not target or source == target:
            return
        marker = (source, target, relation, context)
        if marker in seen:
            return
        seen.add(marker)
        edges.append(
            {
                "source": source,
                "target": target,
                "relation": relation,
                "context": context,
                "confidence": confidence,
                "confidence_score": score,
                "source_file": where,
                "source_location": f"L{line}" if line else None,
                "weight": 1.0,
            }
        )

    def symbol(key: str) -> str | None:
        path, _, name = key.partition("::")
        return by_symbol.get((path, name))

    def anchor(path: str, line: int) -> str | None:
        """Graph node that owns ``path:line`` — a function, a heading, or the file."""
        owners = [
            sym for sym in model.syms.values() if sym.path == path and sym.line <= line <= sym.end
        ]
        if owners:
            owner = min(owners, key=lambda sym: sym.end - sym.line)
            return symbol(owner.key)
        before = [node_id for start, node_id in headings.get(path, []) if start <= line]
        if before:
            return before[-1]
        return pages.get(path) or by_symbol.get((path, Path(path).name))

    def slug(text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")

    # requirement ids: reuse the heading node when a heading defines the id
    id_nodes: dict[str, str] = {}
    for item_id, definition in model.defs.items():
        heading = None
        if item_id.startswith(("OD-", "D-")):
            heading = next(
                (
                    node_id
                    for start, node_id in headings.get(definition["file"], [])
                    if start == definition["line"]
                ),
                None,
            )
        elif item_id.startswith("ADR-"):
            heading = pages.get(definition["file"])
        if heading:
            id_nodes[item_id] = heading
            continue
        node_id = add_node(
            f"req_{slug(item_id)}",
            f"{item_id} — {definition['title']}",
            "concept",
            definition["file"],
            definition["line"],
        )
        id_nodes[item_id] = node_id
        add_edge(
            anchor(definition["file"], definition["line"]),
            node_id,
            "contains",
            definition["file"],
            definition["line"],
            context="definition",
        )

    # routes
    route_nodes: dict[str, str] = {}
    for route in model.routes:
        node_id = add_node(
            f"route_{slug(route.label)}",
            route.label,
            "code",
            "app/main.py",
            route.line,
            access=route.access,
            csrf=route.csrf,
        )
        route_nodes[route.label] = node_id
        add_edge(
            node_id,
            symbol(route.handler),
            "calls",
            "app/main.py",
            route.line,
            context="route_handler",
        )

    # templates
    template_nodes: dict[str, str] = {}
    for item in model.templates.values():
        template_nodes[item.name] = add_node(
            slug(item.path.removesuffix(".html")), item.name, "code", item.path, 1
        )
    for item in model.templates.values():
        own = template_nodes[item.name]
        if item.extends in template_nodes:
            add_edge(own, template_nodes[item.extends], "extends", item.path, 1, context="template")
        for method, target, line in sorted(item.links):
            route = match_route(model, method, target)
            if route:
                add_edge(
                    own,
                    route_nodes[route.label],
                    "references",
                    item.path,
                    line,
                    context="form_action" if method == "POST" else "link",
                )
        for item_id, line in item.ids.items():
            add_edge(own, id_nodes.get(item_id), "references", item.path, line, context="mention")

    # functions: templates rendered, SQL tables, requirement ids, HTTP calls made by tests
    table_nodes = {name: by_symbol.get((item.source, name)) for name, item in model.tables.items()}
    for sym in model.syms.values():
        own = symbol(sym.key)
        if not own:
            continue
        for name in sorted(sym.templates):
            add_edge(
                own, template_nodes.get(name), "references", sym.path, sym.line, context="renders"
            )
        for name in sorted(sym.reads):
            add_edge(own, table_nodes.get(name), "uses", sym.path, sym.line, context="sql_read")
        for name in sorted(sym.writes):
            add_edge(own, table_nodes.get(name), "uses", sym.path, sym.line, context="sql_write")
        for item_id, line in sym.ids.items():
            add_edge(own, id_nodes.get(item_id), "references", sym.path, line, context="mention")
        for method, target, line in sorted(sym.http):
            route = match_route(model, method, target)
            if route:
                add_edge(
                    own, route_nodes[route.label], "calls", sym.path, line, context="http_test"
                )

    # ids mentioned in markdown and SQL (code and templates are handled above)
    for item_id, files in model.mentions.items():
        for path in files:
            if not path.endswith((".md", ".sql")):
                continue
            for number, line in enumerate(read(ROOT / path).splitlines(), start=1):
                if item_id in ID_RE.findall(line):
                    add_edge(
                        anchor(path, number),
                        id_nodes.get(item_id),
                        "references",
                        path,
                        number,
                        context="mention",
                    )

    # curated links (agent judgement, validated against the code)
    for item_id, item in model.curated.get("items", {}).items():
        target = id_nodes.get(item_id)
        for ref in item.get("code", []):
            path, _, name = ref.partition("::")
            source = (
                symbol(ref) or template_nodes.get(Path(path).name) or by_symbol.get((path, name))
            )
            add_edge(
                source,
                target,
                "implements",
                rel(CURATED),
                None,
                context="curated",
                confidence="INFERRED",
                score=0.85,
            )
        for ref in item.get("tests", []):
            add_edge(
                symbol(ref),
                target,
                "references",
                rel(CURATED),
                None,
                context="verifies",
                confidence="INFERRED",
                score=0.85,
            )

    for collection in (nodes.values(), edges):
        for entry in collection:
            entry["_origin"] = "semantic"
    return list(nodes.values()), edges


def build_graph(model: Model) -> int:
    try:
        from graphify.analyze import god_nodes, suggest_questions, surprising_connections
        from graphify.build import build_from_json
        from graphify.cluster import cluster, label_communities_by_hub, score_all
        from graphify.export import to_html, to_json
        from graphify.extract import extract
        from graphify.report import generate
    except ImportError:
        print(
            "graphify is not installed in this interpreter.\n"
            f"  run: make graph        (creates .venv/graph with graphifyy[sql]=={GRAPHIFY_PIN})",
            file=sys.stderr,
        )
        return 2
    from importlib.metadata import version

    inputs = graph_inputs()
    with tempfile.TemporaryDirectory() as cache:
        result = extract(inputs, cache_root=Path(cache), root=ROOT)
    extra_nodes, extra_edges = semantic_layer(model, result["nodes"])
    known = {node["id"] for node in result["nodes"]}
    extraction = {
        "nodes": result["nodes"] + [node for node in extra_nodes if node["id"] not in known],
        "edges": result["edges"] + extra_edges,
        "hyperedges": [],
        "input_tokens": 0,
        "output_tokens": 0,
    }
    graph = build_from_json(extraction, root=str(ROOT), directed=False)
    if graph.number_of_nodes() == 0:
        print("graph is empty — nothing written", file=sys.stderr)
        return 1
    communities = cluster(graph)
    cohesion = score_all(graph, communities)
    labels = label_communities_by_hub(graph, communities)
    gods = god_nodes(graph)
    surprises = surprising_connections(graph, communities)
    questions = suggest_questions(graph, communities, labels)

    GRAPH_OUT.mkdir(exist_ok=True)
    to_json(graph, communities, str(GRAPH_OUT / "graph.json"), force=True, community_labels=labels)
    words = sum(len(read(path).split()) for path in inputs)
    detection = {"total_files": len(inputs), "total_words": words, "files": {}}
    report = generate(
        graph,
        communities,
        cohesion,
        labels,
        gods,
        surprises,
        detection,
        {"input": 0, "output": 0},
        GRAPH_TITLE,  # a fixed label: the checkout directory name must not leak into the report
        suggested_questions=questions,
    )
    (GRAPH_OUT / "GRAPH_REPORT.md").write_text(report, encoding="utf-8")
    to_html(graph, communities, str(GRAPH_OUT / "graph.html"), community_labels=labels)
    digest, count = fingerprint()
    semantic_kinds: dict[str, int] = {}
    for edge in extra_edges:
        semantic_kinds[edge["context"]] = semantic_kinds.get(edge["context"], 0) + 1
    info = {
        "built_on": date.today().isoformat(),
        "graphify_version": version("graphifyy"),
        "fingerprint": digest,
        "input_files": count,
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "communities": len(communities),
        "ast_nodes": len(result["nodes"]),
        "ast_edges": len(result["edges"]),
        "semantic_nodes": len(extra_nodes),
        "semantic_edges_by_context": dict(sorted(semantic_kinds.items())),
        "llm_used": False,
        "how": "graphify AST extraction (tree-sitter, local) + .agent/tools/knowledge_map.py",
    }
    BUILD_INFO.write_text(json.dumps(info, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"graph: {info['nodes']} nodes, {info['edges']} edges, {info['communities']} communities "
        f"-> {rel(GRAPH_OUT)}/ (graphify {info['graphify_version']}, no LLM)"
    )
    return 0


# -------------------------------------------------------------------------------- main


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail when generated docs are stale")
    parser.add_argument("--graph", action="store_true", help="also rebuild graphify-out/")
    parser.add_argument(
        "--force", action="store_true", help="with --graph: rebuild even if current"
    )
    args = parser.parse_args(argv)

    model = build_model()
    outputs = {CODE_MAP: render_code_map(model), TRACE: render_traceability(model)}
    for problem in model.problems:
        print(f"error: {problem}")

    if args.check:
        stale = []
        for path, text in outputs.items():
            current = read(path) if path.is_file() else ""
            if current != text:
                stale.append(rel(path))
                diff = difflib.unified_diff(
                    current.splitlines(),
                    text.splitlines(),
                    rel(path),
                    "regenerated",
                    lineterm="",
                    n=0,
                )
                print("\n".join(list(diff)[:40]))
        print(graph_status())
        if stale or model.problems:
            print(
                f"STALE: {', '.join(stale) or 'curated links'} — "
                "run `make docs` and commit the result"
            )
            return 1
        print(
            f"generated docs are up to date ({len(model.routes)} routes, "
            f"{len(model.tables)} tables)"
        )
        return 0

    if model.problems:
        return 1
    GUIDE.mkdir(parents=True, exist_ok=True)
    for path, text in outputs.items():
        changed = not path.is_file() or read(path) != text
        path.write_text(text, encoding="utf-8")
        print(f"{'wrote' if changed else 'unchanged'}: {rel(path)}")
    if args.graph and (args.force or not graph_is_current()):
        return build_graph(model)
    print(graph_status() + (" — not rebuilt (--force to rebuild)" if args.graph else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
