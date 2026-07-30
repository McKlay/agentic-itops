## Summary

<!-- One-sentence description of what this PR does. -->

## Checklist Item(s)

<!-- Reference the IMPLEMENTATION_CHECKLIST.md item(s) this PR completes. -->

- Closes checklist item(s): <!-- e.g. 2.3, 2.4, 2.5 -->

## Changes

<!-- Brief bullet list of files added/modified. -->

-

## Design Decisions

<!-- Any non-obvious choices made. If none, write "N/A". -->

## Testing

- [ ] Existing tests pass (`pytest tests/ -v`)
- [ ] New tests added for new behaviour
- [ ] Manually tested locally (describe steps if non-trivial)

## Approval / Security Checklist

- [ ] No secrets or credentials committed
- [ ] New connector code has an in-memory fallback (`_live` flag pattern)
- [ ] Any agent output that writes to ServiceNow has `requires_approval=True`
- [ ] All new state mutations call `store.log_event()`
- [ ] Type hints are complete on all new function signatures
