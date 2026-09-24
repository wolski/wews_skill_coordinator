# ChatGPT draft — "Python Interface-Driven Design"

> **Provenance:** verbatim first-assistant-message from the ChatGPT conversation "Python Interface Design"
> (`6a7b87cc-dc68-83eb-a6b0-3b8c55988e7b`), written in response to the request *"I need a skill file which
> teaches my agent those skills when writing Python code."* Extracted 2026-08-12 from the JSON export.
>
> **⚠ Truncated at source.** The message is 9,505 characters in a single part; there is no separate canvas
> node in the export. It **stops mid-sentence inside principle 13**, on an unterminated ```` ```python ````
> fence. Principles 1–12 are complete; 13 is a heading and two lines. Whether more principles were intended
> is unknown. Nothing has been added, completed, or reworded below.
>
> **Status:** raw source material, not a skill. Has no YAML frontmatter and is not installable as-is.

---

Yes. What you are describing maps very naturally to Python through **Protocols, ABCs, dependency injection, Strategy/Command objects, composition, and polymorphic dispatch**. The important part is teaching the agent that "`if type == ...`" is often a design smell, not merely a style issue.

I would give the agent a fairly opinionated skill like this:

# Python Interface-Driven Design

## Purpose

Design Python code around **behavioral interfaces and composition**, not concrete implementations, inheritance hierarchies, or large conditional dispatch blocks.

The default design preference is:

> depend on abstractions, inject behavior, compose objects, and let polymorphism replace type-based branching.

This skill applies when designing new Python code, refactoring existing code, reviewing architecture, defining function signatures, or deciding how modules/classes should interact.

---

# Core Principles

## 1. Depend on behavior, not concrete classes

Functions should usually accept the **smallest behavioral interface they require**.

Prefer:

```python
from typing import Protocol


class Reader(Protocol):
    def read(self) -> bytes: ...


def process(reader: Reader) -> Result:
    data = reader.read()
    ...
```

over:

```python
def process(reader: FileReader) -> Result:
    ...
```

when `process()` does not actually require a `FileReader`.

The parameter type should describe **what the function needs**, not **which implementation happens to provide it today**.

---

## 2. Prefer `Protocol` for interfaces

Python's `typing.Protocol` is usually the preferred mechanism for interface-driven design.

Prefer structural typing:

```python
class ProteinSource(Protocol):
    def proteins(self) -> Iterable[Protein]: ...
```

Implementations do not need to inherit from the protocol:

```python
class CsvProteinSource:
    def proteins(self) -> Iterable[Protein]:
        ...
```

This preserves loose coupling.

Use an abstract base class (`ABC`) only when there is a real need for:

- shared implementation,
- enforced runtime inheritance,
- protected helper methods/state,
- lifecycle behavior common to implementations.

Do not introduce ABC inheritance merely to express an interface.

---

# 3. Prefer composition over inheritance

Before creating:

```python
class SpecialAnalyzer(BaseAnalyzer):
    ...
```

ask whether the varying behavior can instead be injected:

```python
class Analyzer:
    def __init__(
        self,
        normalizer: Normalizer,
        scorer: Scorer,
        reporter: Reporter,
    ) -> None:
        self._normalizer = normalizer
        self._scorer = scorer
        self._reporter = reporter
```

Composition allows behavior to vary independently.

Prefer:

```text
Analyzer
 ├── Normalizer
 ├── Scorer
 └── Reporter
```

over:

```text
BaseAnalyzer
  ├── NormalizedAnalyzer
  │     ├── ScoredNormalizedAnalyzer
  │     └── ...
  └── SpecialAnalyzer
```

Do not build inheritance trees when the relationship is really "uses a".

Inheritance is appropriate primarily for a genuine, stable **is-a** relationship with substitutable behavior.

---

# 4. Replace type-dispatch conditionals with polymorphism

Strongly question code like:

```python
if isinstance(source, CsvSource):
    ...
elif isinstance(source, DatabaseSource):
    ...
elif isinstance(source, ApiSource):
    ...
```

or:

```python
if algorithm == "limma":
    ...
elif algorithm == "ttest":
    ...
elif algorithm == "wilcoxon":
    ...
```

These are often signs that the caller knows too much about implementations.

Prefer:

```python
class DifferentialExpressionMethod(Protocol):
    def fit(self, data: Dataset) -> DEResult: ...


def analyse(
    data: Dataset,
    method: DifferentialExpressionMethod,
) -> DEResult:
    return method.fit(data)
```

Then implementations own their behavior:

```python
class LimmaMethod:
    def fit(self, data: Dataset) -> DEResult:
        ...


class TTestMethod:
    def fit(self, data: Dataset) -> DEResult:
        ...
```

The central algorithm does not change when a new implementation is added.

---

# 5. Configuration may select implementations; domain logic should not

Some branching is legitimate.

For example, configuration parsing may contain:

```python
METHODS = {
    "limma": LimmaMethod,
    "ttest": TTestMethod,
    "wilcoxon": WilcoxonMethod,
}


def build_method(name: str) -> DifferentialExpressionMethod:
    try:
        return METHODS[name]()
    except KeyError:
        raise ValueError(f"Unknown method: {name}")
```

This is preferable to spreading:

```python
if method == ...
elif method == ...
```

throughout the application.

Keep implementation selection at the **composition root** or factory boundary.

After construction, the rest of the system should deal with interfaces.

---

# Interface Design

## 6. Make interfaces small

Follow interface segregation.

Bad:

```python
class DataBackend(Protocol):
    def read(self): ...
    def write(self): ...
    def delete(self): ...
    def connect(self): ...
    def disconnect(self): ...
    def export_excel(self): ...
    def create_plot(self): ...
```

A consumer that only needs reading should depend on:

```python
class Reader(Protocol):
    def read(self) -> Dataset: ...
```

Prefer several focused interfaces over one large interface.

Small interfaces:

- reduce coupling,
- improve testability,
- simplify mocks/fakes,
- permit more implementations,
- make dependencies obvious.

---

# 7. Function arguments should expose required capabilities

Before writing a function signature, ask:

> What is the minimum capability this function needs?

Prefer standard behavioral abstractions when possible.

Instead of:

```python
def analyse(values: list[float]) -> float:
```

consider whether:

```python
from collections.abc import Iterable


def analyse(values: Iterable[float]) -> float:
```

is sufficient.

Instead of:

```python
def save(path: Path) -> None:
```

if the function merely writes text, consider:

```python
from typing import TextIO


def save(stream: TextIO) -> None:
```

or an application-specific protocol.

Do not unnecessarily constrain callers.

---

# 8. Return useful abstractions, but avoid hiding important domain types

Accept interfaces liberally when appropriate.

Return concrete domain values when callers benefit from knowing exactly what they receive.

Good:

```python
def calculate(
    observations: Iterable[Observation],
    model: StatisticalModel,
) -> AnalysisResult:
    ...
```

The input uses behavioral abstractions.

The result is a meaningful concrete domain object.

---

# Dependency Injection

## 9. Inject collaborators

Do not instantiate replaceable dependencies deep inside business logic.

Avoid:

```python
class Pipeline:
    def run(self):
        reader = CsvReader("input.csv")
        scorer = LimmaScorer()
        reporter = ExcelReporter()
```

Prefer:

```python
class Pipeline:
    def __init__(
        self,
        reader: Reader,
        scorer: Scorer,
        reporter: Reporter,
    ) -> None:
        self.reader = reader
        self.scorer = scorer
        self.reporter = reporter
```

Construction happens elsewhere:

```python
pipeline = Pipeline(
    reader=CsvReader(path),
    scorer=LimmaScorer(),
    reporter=ExcelReporter(output),
)
```

This is the **composition root**.

The composition root may know concrete implementations.

Domain logic should generally not.

---

# 10. Separate construction from execution

Prefer:

```python
pipeline = build_pipeline(config)
pipeline.run()
```

over having `Pipeline.run()` inspect configuration and construct its collaborators.

Factories and composition roots may contain knowledge about concrete classes.

Core business/domain code should not.

---

# Strategy Objects

## 11. Use Strategy when behavior varies

If part of an algorithm varies independently, model that behavior explicitly.

Instead of:

```python
def normalize(data, method):
    if method == "median":
        ...
    elif method == "quantile":
        ...
    elif method == "none":
        ...
```

write:

```python
class Normalizer(Protocol):
    def normalize(self, data: Dataset) -> Dataset: ...


class MedianNormalizer:
    def normalize(self, data: Dataset) -> Dataset:
        ...


class QuantileNormalizer:
    def normalize(self, data: Dataset) -> Dataset:
        ...


class IdentityNormalizer:
    def normalize(self, data: Dataset) -> Dataset:
        return data
```

Then:

```python
def analyse(
    data: Dataset,
    normalizer: Normalizer,
) -> Result:
    normalized = normalizer.normalize(data)
    ...
```

Adding another normalization method should not require editing `analyse()`.

---

# 12. Use Null Object / Identity implementations instead of repeated optional checks

Question repeated code like:

```python
if logger is not None:
    logger.log(...)
```

or:

```python
if normalizer is not None:
    data = normalizer.normalize(data)
```

Consider a default implementation:

```python
class IdentityNormalizer:
    def normalize(self, data: Dataset) -> Dataset:
        return data
```

Then the algorithm remains unconditional:

```python
data = normalizer.normalize(data)
```

Use this when it makes the design simpler rather than artificially introducing objects.

---

# Functions Are Also Interfaces

## 13. Do not create a class when a callable is enough

Python supports lightweight dependency injection with functions.

Instead of:

```python

<!-- ─── SOURCE ENDS HERE, MID-SENTENCE ─── -->

---

## [end of truncated source]

The draft breaks off above. For the record, the closing framing from later in the same conversation —
which is *not* part of this draft but belongs with it:

> Don't teach the agent "few `if` statements = good." Teach it that repeated branching on
> *implementation/type/mode* is the smell. A simple guard clause like `if not values: return None` is
> perfectly good Python and shouldn't trigger an abstraction reflex.
