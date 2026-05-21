# Tasks: [FEATURE NAME]

**Input**: `[specs/.../spec.md]`, `[plan.md]`, `[data-model.md]`, `[contracts/]`, `[quickstart.md]`
**Feature**: [Feature description]

---

## Phase [N]: [Phase Name]

[Goal statement — optional, for context.]
[Independent Test Criteria — optional, for when a phase has external validation.]

- [ ] T001 [Tag] [Action] in `[path/to/file]`
- [ ] T002 [P] [Parallel-safe task] in `[path/to/file]`

## Phase [N+1]: [Phase Name]

...

---

## Dependencies

- [Phase A] must complete before [Phase B].
- [Task X] and [Task Y] are sequential: [X] must land before [Y].
- [Tasks A, B, C] are independent and can run in parallel.

## Parallel Execution Examples

### [Phase Name] Parallel Block

- Run T001, T002, T003 in parallel (different files).

## Implementation Strategy

1. [Execution order guidance, e.g.: "Complete core API surfaces first."]
2. ["Then close runtime production gaps."]
3. ["Finish quality gates and tests."]
