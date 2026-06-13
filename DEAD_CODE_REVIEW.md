# Dead Code Review — Items Flagged for Decision

This document lists code that is **orphaned or unused but not obviously safe to
delete** — it works, or it's part of a wire protocol, so a human should decide
whether to remove it or wire it back into the API. A separate sweep already
removed the unambiguously-dead code (empty stubs, unused private helpers, the
defunct `Provision*` enums, and ghost `__all__` entries).

## 1. `delete_toolbox` — resolver exists but is not exposed in the API

- **Where:** `facade/mutations/toolbox.py:25` (`delete_toolbox(info, input)`),
  imported and exported in `facade/mutations/__init__.py`.
- **Problem:** `facade/schema.py` wires `create_toolbox` (and the `toolbox` /
  `toolboxes` queries) but **never** wires `delete_toolbox`. It is unreachable
  from any GraphQL client.
- **Looks like:** an omission, not intentional dead code — `create_toolbox` and
  `delete_toolbox` were presumably meant to ship together.
- **Decision needed:**
  - **Wire it** — add to `facade/schema.py`:
    `delete_toolbox = mutation(resolver=mutations.delete_toolbox, description="Delete a toolbox.")`
  - **or Remove it** — delete the resolver, its `from .toolbox import ... delete_toolbox`,
    and the `"delete_toolbox"` entry in `facade/mutations/__init__.py`.

## 2. `ToAgentMessageType.PROVIDE` / `UNPROVIDE` — protocol enum members, no implementation

- **Where:** `facade/messages.py:44-45`.
- **Problem:** These two message-type enum members have no corresponding message
  classes and are never constructed, sent, or handled anywhere in the codebase.
  They appear to be remnants of the old provision-based flow (same era as the
  removed `Provision` model).
- **Why not auto-removed:** they are part of the agent wire-protocol enum.
  External agent clients may still reference these string values; removing them
  is a protocol change, not a pure internal cleanup.
- **Decision needed:** confirm no deployed agent SDK emits/expects `PROVIDE` /
  `UNPROVIDE`, then remove both members (and audit any client libraries).

## 3. Unused input types in `facade/inputs.py` — needs per-symbol verification

- An earlier exploration pass flagged several `*Input` / `*InputModel` types as
  possibly unused (e.g. `ArchiveStateInput`, `UpdateStateInput`, `HookInput`,
  `PatchInput`, `JSONPatchInputModel`, `BlokAgentMappingInput`, and others).
- **Caveat:** that pass over-reported — many supposedly-orphaned types turned out
  to be referenced (`ActionDemandInput`, etc.). **Do not bulk-delete this list.**
- **Decision needed:** for each candidate, run a targeted check before removing,
  e.g.:
  ```
  grep -rn "ArchiveStateInput\b" --include="*.py" .
  ```
  Strawberry input types can be referenced by *name* (string annotations) and via
  `to_pydantic()`, so verify both the GraphQL type and its `*InputModel` are
  truly unreferenced before deleting.

---

*Generated as part of the dead-code sweep. Once each item is decided, remove it
from this file (or delete the file when empty).*
