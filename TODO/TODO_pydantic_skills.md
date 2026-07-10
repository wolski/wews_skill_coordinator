# Pydantic Skill URLs

Date: 2026-07-02

URLs used during the APB `params.model` review.

## Skill / Skill-Adjacent URLs

- <https://github.com/pydantic/skills>
  - Official Pydantic organization skills repository. Significant because it is
    the canonical place to check first, but the available skills currently focus
    on Pydantic AI / Logfire rather than core `BaseModel` schema review.

- <https://github.com/bobmatnyc/claude-mpm-skills/blob/main/toolchains/python/validation/pydantic/SKILL.md>
  - Useful unofficial Pydantic v2 validation skill. Significant for concrete
    review patterns around `ConfigDict`, `field_validator`, `model_validator`,
    `model_dump`, strict validation, and model tests.

- <https://github.com/CJHarmath/claude-agents-skills/blob/main/skills/py-pydantic-patterns/SKILL.md>
  - Useful unofficial Pydantic v2 pattern note. Significant for compact examples
    of validators, field constraints, and `extra="forbid"` style model config.

- <https://github.com/microsoft/skills/blob/main/.github/plugins/azure-sdk-python/skills/pydantic-models-py/SKILL.md>
  - Microsoft Azure SDK Python Pydantic model skill. Significant mostly as an
    API-schema reference for multi-model patterns and aliasing; less directly
    applicable to APB because APB has one sparse parameter exchange model.

- <https://github.com/pydantic/pydantic/issues/13189>
  - Official Pydantic issue discussing a possible core Pydantic `SKILL.md`.
    Significant because it shows that a first-party general Pydantic skill is
    not yet established, so unofficial skills should be treated as background,
    not normative guidance.

## Official Pydantic Docs Used As Ground Truth

These are not `SKILL.md` files, but they were the semantic references for the
review:

- <https://docs.pydantic.dev/latest/migration/#required-optional-and-nullable-fields>
  - Defines Pydantic v2 required/optional/nullable behavior. This was the key
    source for the `T | None` versus `T | None = None` distinction.

- <https://docs.pydantic.dev/latest/concepts/validators/>
  - Official validator semantics for `field_validator` and `model_validator`.

- <https://docs.pydantic.dev/latest/concepts/fields/>
  - Official field/default guidance, including how defaults interact with model
    fields and static type checkers.
