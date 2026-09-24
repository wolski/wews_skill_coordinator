---
name: constructor-or-dataclass
description: >-
  Decide whether a Python dataclass should remain an immutable value or become a normal class
  with an explicit __init__ and instance methods. Use when reviewing anemic dataclasses, wrapper
  constructors such as bind_x or make_x, free functions repeatedly accepting the same record,
  requests for Java-style object design, or questions such as "should this dataclass have an init?"
---

# Constructor or dataclass

Judge the design from the caller and from the invariant construction establishes, not from a preference for or against dataclasses.

## Keep the dataclass

Keep a dataclass when construction only receives complete typed values and stores them. A generated `__init__` is clearer than a handwritten list of assignments. Dataclasses may have instance methods; behavior alone does not require replacing one.

An immutable projected configuration is a good example: another object resolves its inputs, then supplies its completed fields. Add methods for questions answered entirely by that state, but retain the generated constructor.

## Write an explicit constructor

Use a normal class with `__init__` when construction resolves raw inputs, selects collaborators or formats, validates combinations, or prevents an invalid object from escaping. The constructor earns its syntax by establishing a named invariant.

Move related free functions onto the instance when they repeatedly receive the object, inspect its state, and implement its lifecycle. Remove wrapper functions that merely call hidden construction helpers.

Use an instance method when behavior needs one object's state. Use `@classmethod` only for a genuinely different named construction path.

## Review test

1. Show the intended caller in two or three lines.
2. Name the invariant established during construction.
3. If no invariant exists, keep the generated dataclass constructor.
4. Check whether callers stop passing the same state through several free functions.
5. Judge readability across the complete lifecycle, not by local line count.

`BoundTable(source, contract)` merits an explicit constructor because it resolves and validates one physical interpretation. `WorkingParseConfiguration(...)` does not: it is already a complete immutable value, while methods such as `accepts_header()` simply use that value.
