# Object System Guidance (S3 / S4 / R6)

Read this when choosing an object system for a new API, or when reviewing whether an
existing one fits the domain. Choose from the domain model and API shape, not from
familiarity with other languages.

## Use S3 when

- objects are mostly values with attributes;
- users should work with ordinary R objects;
- dispatch on one primary argument is enough;
- extensibility through generics is useful;
- the class is simple enough to validate with constructors and helper functions.

## Use S4 when

- formal slots and validity checks are essential;
- multiple dispatch is a real requirement;
- the code participates in an S4-heavy ecosystem such as Bioconductor;
- many related classes need a stable inheritance graph;
- direct slot access can be hidden behind accessors.

## Use R6 when

- mutation is part of the model rather than an implementation accident;
- resources need explicit lifecycle handling;
- caches, parsers, queues, handles, sessions, or live connections are core;
- object identity matters;
- shared mutable state is documented and tested.

## Anti-patterns

- Avoid choosing R6 only because it resembles Python or Java. Reach for it when mutable
  state is genuinely central, not as a default style.
- Avoid choosing S4 when a constructor, a validator, and an S3 method set would be enough.

## Validators belong with the class

Whatever the system, enforce invariants where the object is born: a constructor + validator
for S3, `setValidity()`/`validObject()` for S4, validation in `initialize()` (or active
bindings) for R6. An object that can only exist in a valid state removes a whole category of
downstream defensive checks.
