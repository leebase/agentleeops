# External Adapter Contract

The canonical adapter contract for future external providers (for example Jira and Azure DevOps) lives in:

- `lib/workitem/adapter_contract.py`

## Required Adapter Behaviors

Implementations must provide:

1. `to_work_item(payload) -> WorkItem`
2. `to_identity(payload) -> WorkItemIdentity`
3. `resolve_state(native_state) -> WorkItemState`
4. `supported_state_mappings() -> list[StateMapping]`

## Design Constraints

- Use deterministic mappings from provider payloads into `WorkItem`.
- Keep transitions idempotent and retry-safe.
- Keep state mapping explicit to avoid ambiguous column/status translation.
- Preserve provider-native IDs and URLs for traceability and migration.

## Mapping Storage

Local work packages persist external references in `manifest.yaml` under `external_refs.items`.
Use `tools/workpackage.py map-add`, `map-export`, and `map-import` for migration workflows.
