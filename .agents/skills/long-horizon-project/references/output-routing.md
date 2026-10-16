# Output Routing

Classify every generated file before creating it.

## Project Deliverables

Keep files requested as part of the product in normal project paths:

- source code and tests
- runtime configuration
- migrations and deployment configuration
- user-requested documentation
- assets required by the product

## Assistant Artifacts

When the path is configurable, use:

```text
skilluse/plans/<skill-name>/
skilluse/context/<skill-name>/
skilluse/logs/<skill-name>/
skilluse/artifacts/<skill-name>/
```

Typical assistant artifacts are plans, handoffs, research notes, reports, screenshots, generated comparisons, and verbose command logs.

## Exceptions

Some Skills or scripts write to a fixed temporary or project path. Prompt instructions cannot override a hard-coded path. Use a supported output option or wrapper when available. Otherwise record the path and reason in `skilluse/context/decisions.md`, and keep all other controllable outputs under `skilluse/`.
