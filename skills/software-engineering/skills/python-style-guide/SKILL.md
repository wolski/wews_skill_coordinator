---
name: python-style-guide
description: >
  This skill should be used when the user asks to "write Python code", "review Python
  style", "refactor Python code", "add type annotations", "write a docstring", or
  "check Python conventions". Also use when working with .py files, discussing Python
  imports, naming, formatting, or type hints — even if not explicitly requesting style
  guidance. Covers language rules (imports, exceptions, type annotations), style rules
  (naming, formatting, docstrings), modern Python features, and best practices based on
  Google's Python Style Guide.
---

# Python Style Guide

Follow these guidelines when writing or reviewing Python code, based on [Google's Python Style Guide](https://google.github.io/styleguide/pyguide.html).

## Core Philosophy

Match the surrounding project where it has an explicit convention. Style guidance does not choose
the architecture: establish ownership, dependency direction, public contracts, and the product being
constructed before applying formatting or pattern advice.

## Architecture Before Style

For refactors, first map the production callers, the intended public boundary, and the data that each
operation actually needs. Tests are evidence of behavior, but a function used only by tests is not
automatically public API or automatically dead. Check package exports, documented entry points,
external consumers in scope, and production imports before deleting or preserving it.

Do not introduce a design-pattern name as a substitute for this audit. In particular, use a Builder
only when construction of a named product is genuinely complex:

- Identify the product class first.
- Put the builder in the same module as the product it builds.
- Bind the evidence and intermediate values needed to construct that product.
- Expose `build() -> Product`; invalid, unavailable, or ambiguous construction raises a precise
  exception.
- Filtering that determines which product can be constructed belongs in the builder when it is part
  of that construction contract.

A lookup object, locator, result union, or collection of saved function combinations is not a
Builder merely because it has a method. If construction is simple, prefer the constructor or one
exactly named function. Do not create compatibility aliases unless the supported API contract
requires them.

Organize modules by ownership and one-way dependency direction. Shared value objects may sit below
passive source models, which may sit below an effective product and its builder. A circular import is
evidence that ownership or dependency direction needs examination; do not invent a `Protocol`, move
the builder away from its product, or switch import syntax solely to hide the cycle.

## Language Rules

### Imports

Follow the project's import convention and make dependencies explicit. Importing a module instead
of a name does not prevent a circular dependency; cycles are determined by module initialization and
dependency direction. Avoid cross-module imports of private names unless the project explicitly
defines those modules as a package-internal API.

**Yes:**
```python
from pathlib import Path

from pydantic import BaseModel

from myproject import config
from myproject.rules.parse_rule import ParseRule
```

**No:**
```python
from myproject.rules._composition import _merge_fragments  # Cross-module private dependency
```

#### Import Formatting

- Group imports: standard library, third-party, application-specific
- Alphabetize within each group
- Use absolute imports (not relative imports)
- One import per line (except for multiple items from `typing` or `collections.abc`)

```python
# Standard library
import os
import sys

# Third-party
import numpy as np
import tensorflow as tf

# Application-specific
from myproject.backend import api_utils
```

### Exceptions

Use exceptions appropriately. Do not suppress errors with bare `except:` clauses.

**Yes:**
```python
try:
    result = risky_operation()
except ValueError as e:
    logging.error(f"Invalid value: {e}")
    raise
```

**No:**
```python
try:
    result = risky_operation()
except:  # Too broad, hides bugs
    pass
```

### Type Annotations

Annotate all function signatures. Type annotations improve readability and catch errors early.

**General rules:**
- Annotate all public APIs
- Use built-in types (`list`, `dict`, `set`) instead of `typing.List`, etc. (Python 3.9+)
- Import typing symbols directly: `from typing import Any, Union`
- Use `None` instead of `type(None)` or `NoneType`
- Give filesystem boundaries one exact type. Prefer `Path` inside typed application code and convert
  external strings at the CLI, UI, JSON, or environment boundary. Do not spread `Path | str` through
  internal APIs as a convenience.

```python
def fetch_data(url: str, timeout: int = 30) -> dict[str, Any]:
    """Fetch data from URL."""
    ...

def process_items(items: list[str]) -> None:
    """Process a list of items."""
    ...
```

### Default Argument Values

Never use mutable objects as default values. Use one of these two approaches:

**1. Simple types with defaults** — for few, independent parameters:
```python
def fetch_data(url: str, timeout: int = 30, retries: int = 3) -> dict:
    ...
```

**2. A validated model** — only when the values form a real reusable invariant or external data
contract, not merely because a function has several parameters:
```python
from pydantic import BaseModel

class ProcessConfig(BaseModel):
    timeout: int = 30
    retries: int = 3

def process(items: list[str], config: ProcessConfig) -> int:
    """Process items with config."""
    return len(items)

# Caller uses ProcessConfig() for defaults
process(items, ProcessConfig())
```

When such a model is justified, benefits include:
- Function signatures are honest (expects config, gets config)
- Defaults live in one place (the model)
- Caller intent is explicit (`Config()` means "I want defaults")
- No `None` checks cluttering function bodies
- Built-in validation

**No:**
```python
# Mutable default - WRONG!
def foo(a: int, b: list[int] = []) -> None:
    b.append(a)

# None is valid only when absence is part of the contract.
def foo(a: int, b: list[int] | None = None) -> None:
    if b is None:
        b = []
```

### True/False Evaluations

Use implicit false where possible. Empty sequences, `None`, and `0` are false in boolean contexts.

**Yes:**
```python
if not users:  # Preferred
if not some_dict:
if value:
```

**No:**
```python
if len(users) == 0:  # Verbose
if users == []:
if value == True:  # Never compare to True/False explicitly
```

### Comprehensions & Generators

Use comprehensions and generators for simple cases. Keep them readable.

**Yes:**
```python
result = [x for x in data if x > 0]
squares = (x**2 for x in range(10))
```

**No:**
```python
# Too complex
result = [
    x.strip().lower() for x in data 
    if x and len(x) > 5 and not x.startswith('#')
    for y in x.split(',') if y
]  # Use a regular loop instead
```

### Lambda Functions

Use lambdas for one-liners only. For anything complex, define a proper function.

**Yes:**
```python
sorted(data, key=lambda x: x.timestamp)
```

**Acceptable but prefer named function:**
```python
def get_timestamp(item):
    return item.timestamp

sorted(data, key=get_timestamp)
```

## Style Rules

### Line Length

Maximum line length: 88 characters. Exceptions allowed for imports, URLs, and long strings that can't be broken.

### Indentation

Use 4 spaces per indentation level. Never use tabs.

For hanging indents, align wrapped elements vertically or use 4-space hanging indent:

```python
# Aligned with opening delimiter
foo = long_function_name(var_one, var_two,
                         var_three, var_four)

# Hanging indent (4 spaces)
foo = long_function_name(
    var_one, var_two, var_three,
    var_four)
```

### Blank Lines

- Two blank lines between top-level definitions
- One blank line between method definitions
- Use blank lines sparingly within functions to show logical sections

### Naming Conventions

| Type | Convention | Examples |
|------|-----------|----------|
| Packages/Modules | `lower_with_under` | `my_module.py` |
| Classes | `CapWords` | `MyClass` |
| Functions/Methods | `lower_with_under()` | `my_function()` |
| Constants | `CAPS_WITH_UNDER` | `MAX_SIZE` |
| Variables | `lower_with_under` | `my_var` |
| Private | `_leading_underscore` | `_private_var` |

**Avoid:**
- Single character names except for counters/iterators (`i`, `j`, `k`)
- Dashes in any name
- `__double_leading_and_trailing_underscore__` (reserved for Python)

### Comments and Docstrings

#### Docstring Format

Use Google-style docstrings for all public modules, functions, classes, and methods.

**Function docstring:**
```python
def fetch_smalltable_rows(
    table_handle: smalltable.Table,
    keys: Sequence[bytes | str],
    require_all_keys: bool = False,
) -> Mapping[bytes, tuple[str, ...]]:
    """Fetches rows from a Smalltable.

    Retrieves rows pertaining to the given keys from the Table instance
    represented by table_handle. String keys will be UTF-8 encoded.

    Args:
        table_handle: An open smalltable.Table instance.
        keys: A sequence of strings representing the key of each table
            row to fetch. String keys will be UTF-8 encoded.
        require_all_keys: If True, raise ValueError if any key is missing.

    Returns:
        A dict mapping keys to the corresponding table row data
        fetched. Each row is represented as a tuple of strings.

    Raises:
        IOError: An error occurred accessing the smalltable.
        ValueError: A key is missing and require_all_keys is True.
    """
    ...
```

**Class docstring:**
```python
class SampleClass:
    """Summary of class here.

    Longer class information...
    Longer class information...

    Attributes:
        likes_spam: A boolean indicating if we like SPAM or not.
        eggs: An integer count of the eggs we have laid.
    """

    def __init__(self, likes_spam: bool = False):
        """Initializes the instance based on spam preference.

        Args:
            likes_spam: Defines if instance exhibits this preference.
        """
        self.likes_spam = likes_spam
        self.eggs = 0
```

#### Block and Inline Comments

- Use complete sentences with proper capitalization
- Block comments indent to the same level as the code
- Inline comments should be separated by at least 2 spaces
- Use inline comments sparingly

```python
# Block comment explaining the following code.
# Can span multiple lines.
x = x + 1  # Inline comment (use sparingly)
```

### Strings

Use f-strings for formatting (Python 3.6+).

**Yes:**
```python
x = f"name: {name}; score: {score}"
```

**Acceptable:**
```python
x = "name: %s; score: %d" % (name, score)
x = "name: {}; score: {}".format(name, score)
```

**No:**
```python
x = "name: " + name + "; score: " + str(score)  # Avoid + for formatting
```

#### Logging

Use **Loguru** for logging with brace-style lazy formatting:

```python
logger.info("Request from {} resulted in {}", ip_address, status_code)
```

**Avoid** standard `logging` with `%` formatting.

### Files and Resources

For simple text operations, prefer `pathlib` methods:

```python
data = Path("file.txt").read_text()
Path("output.txt").write_text("content")
```

For complex operations or non-text files, use context managers:

```python
with open("image.png", "rb") as f:
    data = f.read()
```

### Statements

Generally avoid multiple statements on one line.

**Yes:**
```python
if foo:
    bar()
```

**No:**
```python
if foo: bar()  # Avoid
```

### Main

For executable scripts, use:

```python
def main():
    ...

if __name__ == "__main__":
    main()
```

### Function Length

Keep functions conceptually focused. Line count and cyclomatic complexity are diagnostic signals,
not refactoring targets. Split only when the extracted operation has its own coherent contract and
meaningful typed inputs/outputs; do not turn readable structural descent or a linear transformation
into forwarding helpers to satisfy a number.

## Type Annotation Details

### Forward Declarations

Use string quotes for forward references:

```python
class MyClass:
    def method(self) -> "MyClass":
        return self
```

### Type Aliases

Create aliases for complex types:

```python
from typing import TypeAlias

ConnectionOptions: TypeAlias = dict[str, str]
Address: TypeAlias = tuple[str, int]
Server: TypeAlias = tuple[Address, ConnectionOptions]
```

### TypeVars

Use descriptive names for TypeVars:

```python
from typing import TypeVar

_T = TypeVar("_T")  # Good: private, unconstrained
AddableType = TypeVar("AddableType", int, float, str)  # Good: descriptive
```

### Generics

Always specify type parameters for generic types:

**Yes:**
```python
def get_names(employee_ids: list[int]) -> dict[int, str]:
    ...
```

**No:**
```python
def get_names(employee_ids: list) -> dict:  # Missing type parameters
    ...
```

### Imports for Typing

Import typing symbols directly:

```python
from collections.abc import Mapping, Sequence
from typing import Any, Union

# Use built-in types for containers (Python 3.9+)
def foo(items: list[str]) -> dict[str, int]:
    ...
```

## Modern Python Features

### Match Statements (Python 3.10+)

Use structural pattern matching for complex conditionals:

```python
def handle_response(response: dict) -> str:
    match response:
        case {"status": "ok", "data": data}:
            return f"Success: {data}"
        case {"status": "error", "message": msg}:
            return f"Error: {msg}"
        case {"status": status}:
            return f"Unknown status: {status}"
        case _:
            return "Invalid response"
```

Pattern matching with types:

```python
def process(value: int | str | list) -> str:
    match value:
        case int(n) if n > 0:
            return f"Positive int: {n}"
        case int(n):
            return f"Non-positive int: {n}"
        case str(s):
            return f"String: {s}"
        case [first, *rest]:
            return f"List starting with {first}"
```

### Dataclasses with Slots (Python 3.10+)

Use `slots=True` for memory efficiency and faster attribute access:

```python
from dataclasses import dataclass

@dataclass(slots=True)
class Point:
    x: float
    y: float

@dataclass(slots=True, frozen=True)
class ImmutableConfig:
    host: str
    port: int
    timeout: float = 30.0
```

### Postponed Annotation Evaluation

Use `from __future__ import annotations` for:
- Forward references without quotes
- Faster module import (annotations not evaluated at definition time)

```python
from __future__ import annotations

class Node:
    def __init__(self, children: list[Node]) -> None:  # No quotes needed
        self.children = children

    def add_child(self, child: Node) -> None:
        self.children.append(child)
```

### Exception Groups (Python 3.11+)

Handle multiple exceptions simultaneously:

```python
try:
    async with asyncio.TaskGroup() as tg:
        tg.create_task(task1())
        tg.create_task(task2())
except* ValueError as eg:
    for exc in eg.exceptions:
        logger.error("ValueError: {}", exc)
except* TypeError as eg:
    for exc in eg.exceptions:
        logger.error("TypeError: {}", exc)
```

## Common Patterns

### Properties

Use properties for simple attribute access:

```python
class Square:
    def __init__(self, side: float):
        self._side = side
    
    @property
    def area(self) -> float:
        return self._side ** 2
```

### Conditional Expressions

Use ternary operators for simple conditions:

```python
x = "yes" if condition else "no"
```

### Context Managers

Create custom context managers when appropriate:

```python
from contextlib import contextmanager

@contextmanager
def managed_resource(*args, **kwargs):
    resource = acquire_resource(*args, **kwargs)
    try:
        yield resource
    finally:
        release_resource(resource)
```

## Linting

Run `ruff` on all Python code. Suppress warnings only when necessary:

```python
dict = 'something'  # noqa: A001
```

### Package `__init__.py` Files

Follow the package's established export policy. Empty `__init__.py` files are useful when callers
must import owning modules directly; deliberate re-exports are also valid when the package defines a
stable facade. Do not create re-export aliases merely to preserve an API that the contract audit has
retired.

```python
# __init__.py
# Empty when the project requires direct owning-module imports.
```

When the project uses direct owning-module imports:
```python
# Instead of: from mypackage import MyClass
# Use: from mypackage.core import MyClass
```

### Preferred Libraries

Prefer the libraries already selected by the project when they fit the required contract. Do not add
a framework or dependency just because it appears in this table:

| Purpose | Library |
|---------|---------|
| Data validation/models | `pydantic` |
| Logging | `loguru` |
| CLI | `cyclopts`, `rich` |
| Testing | `pytest`, `pytest-mock` |

## Summary

When writing Python code:

1. Use type annotations for all functions
2. Follow naming conventions consistently
3. Write clear docstrings for all public APIs
4. Keep functions conceptually focused; do not refactor to a metric
5. Use comprehensions for simple cases
6. Prefer implicit false in boolean contexts
7. Use f-strings for formatting
8. Always use context managers for resources
9. Run `ruff check` and `ruff format`
10. Audit ownership, dependency direction, and public callers before restructuring
11. Use a Builder only for complex construction of its colocated product
12. Follow the project's `__init__.py` export policy
13. **Stay consistent** with existing code

## Additional Resources

For detailed reference on specific topics, see:

- **references/advanced_types.md** - Advanced type annotation patterns including Protocol, TypedDict, Literal, ParamSpec, and more
- **references/antipatterns.md** - Common Python mistakes and their fixes
- **references/docstring_examples.md** - Comprehensive docstring examples for all Python constructs
