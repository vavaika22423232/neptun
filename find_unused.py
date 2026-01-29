#!/usr/bin/env python3
import ast
import re

with open("app.py") as f:
    content = f.read()

tree = ast.parse(content)
functions = {}
for n in ast.walk(tree):
    if isinstance(n, ast.FunctionDef):
        functions[n.name] = (n.lineno, n.end_lineno, n.end_lineno - n.lineno)

used = set()
# Routes
for m in re.finditer(r"@app\.route.+?\ndef\s+(\w+)", content, re.DOTALL):
    used.add(m.group(1))

for name in functions:
    if len(list(re.finditer(rf"\b{name}\s*\(", content))) > 1:
        used.add(name)
    if re.search(rf"[=,(]\s*{name}\s*[,)\n]", content):
        used.add(name)

unused = set(functions.keys()) - used
total = sum(functions[n][2] for n in unused)
print(f"Unused: {len(unused)} funcs, ~{total} lines")
for n in sorted(unused, key=lambda x: -functions[x][2])[:25]:
    print(f"  {functions[n][2]:4d}: {n} (L{functions[n][0]}-{functions[n][1]})")
