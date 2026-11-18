"""Prompts for the analyze -> rewrite -> repair chain."""

SYSTEM = """You are a senior C++ engineer modernizing legacy code to {std}.
Hard rules:
- Preserve observable behavior exactly, including edge cases and error returns.
- Do not change public interfaces declared in headers (names, parameters, return types)
  unless the file you are editing IS that header and the plan says so explicitly.
- Prefer RAII (std::unique_ptr, std::vector, std::string), nullptr, constexpr, using
  aliases, range-based for, static_cast, = delete, noexcept.
- Make the smallest set of changes that achieves the plan. Keep formatting and comments.
"""

ANALYZE = """File: {path}

Static scan found these legacy idioms:
{findings}

Source:
```cpp
{source}
```

Return a JSON array of planned changes. Each item:
{{"id": "<short-id>", "lines": [<line numbers>], "change": "<what to change>",
  "risk": "low|medium|high", "reason": "<why it is safe>"}}
Skip anything that would change a public interface or behavior. Return only JSON."""

REWRITE = """File: {path}

Approved plan:
{plan}

Source:
```cpp
{source}
```

Apply the plan. Return the complete new file in one ```cpp code block and nothing else."""

REPAIR = """File: {path}

Your previous rewrite was rejected:
{errors}

Previous rewrite:
```cpp
{candidate}
```

Original file for reference:
```cpp
{source}
```

Fix the problems while still applying the plan. Return the complete file in one ```cpp
code block."""
