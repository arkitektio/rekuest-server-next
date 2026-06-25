import json
import re
import typing as t

from django.db import connection

from rekuest_core.inputs.types import PortMatchInput
from .inputs import ActionDemandInput, ObjectMatchInput

qt = re.compile(r"@(?P<package>[^\/]*)\/(?P<interface>[^\/]*)")

# A match is duck-typed: the type-level ``PortMatchInput`` (structural only), the runtime
# ``ObjectMatchInput`` (structural + ``descriptors``), and test ``SimpleNamespace`` stand-ins are
# all accepted — only attribute access is used.
MatchInput = t.Union[PortMatchInput, ObjectMatchInput]


# =========================================================================
# Relational port-matching engine (Actions only)
#
# Actions flatten their ports into the indexed ``facade_argport`` /
# ``facade_returnport`` tables (see facade.mutations.implementation). Matching
# an ``Action`` therefore becomes a set of correlated ``EXISTS`` subqueries over
# those tables instead of a sequential scan over the ``args``/``returns`` JSONB
# blobs. This uses the (action_id, parent_id), kind and identifier indexes,
# supports arbitrary nesting depth (via the self-referential ``parent`` FK), and
# enforces the compiled ``requires``/``provides`` micro-constraints via
# ``jsonb_path_match`` against a candidate descriptor object.
# =========================================================================

# Physical table names for the relational port rows, keyed by demand type.
PORT_TABLE = {"args": "facade_argport", "returns": "facade_returnport"}


def _build_match_exists(
    match: MatchInput,
    table: str,
    action_alias: str,
    parent_alias: str | None,
    id_path: str,
    params: dict[str, t.Any],
) -> str:
    """Build one correlated ``EXISTS`` clause for a single match.

    Accepts both the type-level ``PortMatchInput`` (structural targeting only) and the runtime
    ``ObjectMatchInput`` (same structural fields plus ``descriptors``) — the two are handled
    uniformly via attribute access; only the descriptor branch differs.

    Root matches correlate to the outer action row (``action_id = <action>.id`` and
    ``parent_id IS NULL``); nested matches correlate to their parent port row
    (``parent_id = <parent>.id``). Children recurse, so nesting depth is unbounded.
    """
    alias = f"p_{id_path}"
    conditions: list[str] = []

    if parent_alias is None:
        conditions.append(f"{alias}.action_id = {action_alias}.id")
        conditions.append(f"{alias}.parent_id IS NULL")
    else:
        conditions.append(f"{alias}.parent_id = {parent_alias}.id")

    if match.at is not None:
        key = f"at_{id_path}"
        params[key] = match.at
        conditions.append(f"{alias}.index = %({key})s")

    if match.key is not None:
        key = f"key_{id_path}"
        params[key] = match.key
        conditions.append(f"{alias}.key = %({key})s")

    if match.kind is not None:
        key = f"kind_{id_path}"
        params[key] = match.kind.value
        conditions.append(f"{alias}.kind = %({key})s")

    if match.identifier is not None:
        key = f"ident_{id_path}"
        params[key] = match.identifier
        conditions.append(f"{alias}.identifier = %({key})s")

    if match.nullable is not None:
        key = f"null_{id_path}"
        params[key] = match.nullable
        conditions.append(f"{alias}.nullable = %({key})s")

    descriptors = getattr(match, "descriptors", None)
    if descriptors:
        # Micro-constraint: the port's compiled requires/provides JSONPath must be satisfied by
        # the candidate object, assembled here from the runtime descriptor key/value pairs
        # (duplicate keys: last wins). A NULL compiled_jsonpath means the port declares no
        # constraints, so it accepts any object. ``silent => true`` makes structurally-invalid
        # evaluations return NULL instead of raising. Type-level PortMatchInput carries no
        # descriptors, so this branch is skipped and the match stays purely structural.
        candidate_object = {descriptor.key: descriptor.value for descriptor in descriptors}
        key = f"obj_{id_path}"
        params[key] = json.dumps(candidate_object)
        conditions.append(f"({alias}.compiled_jsonpath IS NULL OR jsonb_path_match(%({key})s::jsonb, {alias}.compiled_jsonpath::jsonpath, '{{}}'::jsonb, true))")

    for child_index, child in enumerate(match.children or []):
        conditions.append(_build_match_exists(child, table, action_alias, alias, f"{id_path}_{child_index}", params))

    inner = " AND ".join(conditions)
    return f"EXISTS (SELECT 1 FROM {table} {alias} WHERE {inner})"


def _root_count_subquery(table: str, action_alias: str, extra_condition: str, param_key: str, value: int, params: dict[str, t.Any]) -> str:
    """Build a ``(SELECT COUNT(*) ...) = N`` clause over an action's root ports."""
    params[param_key] = value
    return f"(SELECT COUNT(*) FROM {table} pc WHERE pc.action_id = {action_alias}.id AND pc.parent_id IS NULL AND {extra_condition}) = %({param_key})s"


def _execute_ids(sql: str, params: dict[str, t.Any]) -> list[t.Any]:
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return [row[0] for row in cursor.fetchall()]


def get_action_ids_by_demands(
    demands: t.Sequence[MatchInput] | None = None,
    type: t.Literal["args", "returns"] = "args",
    force_length: t.Optional[int] = None,
    force_non_nullable_length: t.Optional[int] = None,
    force_structure_length: t.Optional[int] = None,
    model: str = "facade_action",
    organization_id: str | None = None,
) -> list[t.Any]:
    """Return ids of rows in ``model`` whose ports of ``type`` satisfy every demand.

    For ``facade_action`` this uses the indexed relational port engine. Other models
    (e.g. ``facade_shortcut``) keep their own ``args``/``returns`` JSONB and fall back to
    the JSONB-scan matcher, since only Actions own relational port rows.
    """
    if type not in ("args", "returns"):
        raise ValueError("Type must be either 'args' or 'returns'")

    if model != "facade_action":
        return _json_scan_ids(
            demands,
            type=type,
            force_length=force_length,
            force_non_nullable_length=force_non_nullable_length,
            force_structure_length=force_structure_length,
            model=model,
        )

    table = PORT_TABLE[type]
    action_alias = "a"
    clauses: list[str] = []
    params: dict[str, t.Any] = {}

    if organization_id is not None:
        params["org"] = organization_id
        clauses.append(f"{action_alias}.organization_id = %(org)s")

    for index, match in enumerate(demands or []):
        clauses.append(_build_match_exists(match, table, action_alias, None, str(index), params))

    if force_length is not None:
        column = "arg_count" if type == "args" else "return_count"
        params["force_length"] = force_length
        clauses.append(f"{action_alias}.{column} = %(force_length)s")

    if force_non_nullable_length is not None:
        clauses.append(_root_count_subquery(table, action_alias, "pc.nullable = false", "force_non_nullable", force_non_nullable_length, params))

    if force_structure_length is not None:
        clauses.append(_root_count_subquery(table, action_alias, "pc.kind = 'STRUCTURE'", "force_structure", force_structure_length, params))

    if not clauses:
        raise ValueError("No search params provided")

    sql = f"SELECT {action_alias}.id FROM facade_action {action_alias} WHERE " + " AND ".join(clauses)
    return _execute_ids(sql, params)


def get_action_ids_by_action_demand(
    action_demand: ActionDemandInput,
    model: str = "facade_action",
    organization_id: str | None = None,
) -> list[t.Any]:
    """Return Action ids matching a full ``ActionDemandInput`` (args + returns together)."""
    action_alias = "a"
    clauses: list[str] = []
    params: dict[str, t.Any] = {}

    if organization_id is not None:
        params["org"] = organization_id
        clauses.append(f"{action_alias}.organization_id = %(org)s")

    if action_demand.hash:
        params["hash"] = action_demand.hash
        clauses.append(f"{action_alias}.hash = %(hash)s")
    else:
        if action_demand.name:
            params["name"] = action_demand.name
            clauses.append(f"{action_alias}.name = %(name)s")

        for index, match in enumerate(action_demand.arg_matches or []):
            clauses.append(_build_match_exists(match, PORT_TABLE["args"], action_alias, None, f"arg_{index}", params))

        for index, match in enumerate(action_demand.return_matches or []):
            clauses.append(_build_match_exists(match, PORT_TABLE["returns"], action_alias, None, f"ret_{index}", params))

        if action_demand.force_arg_length is not None:
            params["force_arg_length"] = action_demand.force_arg_length
            clauses.append(f"{action_alias}.arg_count = %(force_arg_length)s")

        if action_demand.force_return_length is not None:
            params["force_return_length"] = action_demand.force_return_length
            clauses.append(f"{action_alias}.return_count = %(force_return_length)s")

    if not clauses:
        raise ValueError(f"No search params provided {action_demand}")

    sql = f"SELECT {action_alias}.id FROM {model} {action_alias} WHERE " + " AND ".join(clauses)
    return _execute_ids(sql, params)


def get_implementation_ids_by_demands(
    demands: t.Sequence[MatchInput] | None = None,
    type: t.Literal["args", "returns"] = "args",
    force_length: t.Optional[int] = None,
    force_non_nullable_length: t.Optional[int] = None,
    force_structure_length: t.Optional[int] = None,
    agent: str | None = None,
    model: str = "facade_action",
) -> list[t.Any]:
    """Return Action ids matching the demands (kept for API compatibility)."""
    return get_action_ids_by_demands(
        demands,
        type=type,
        force_length=force_length,
        force_non_nullable_length=force_non_nullable_length,
        force_structure_length=force_structure_length,
        model=model,
    )


def filter_actions_by_demands(
    qs: t.Any,
    demands: t.Sequence[MatchInput] | None = None,
    type: t.Literal["args", "returns"] = "args",
    force_length: t.Optional[int] = None,
    force_non_nullable_length: t.Optional[int] = None,
    force_structure_length: t.Optional[int] = None,
    model: str = "facade_action",
) -> t.Any:
    ids = get_action_ids_by_demands(
        demands,
        type=type,
        force_length=force_length,
        force_non_nullable_length=force_non_nullable_length,
        force_structure_length=force_structure_length,
        model=model,
    )
    return qs.filter(id__in=ids)


# =========================================================================
# Legacy JSONB-scan matcher
#
# Retained for models that carry ``args``/``returns`` (or ``ports``) as JSONB but
# have no relational port rows: Shortcuts and State schemas. It only compares the
# coarse key/kind/identifier fields and matches children positionally one level
# deep; this is acceptable for those secondary lookups.
# =========================================================================


def build_child_recursively(item: MatchInput, prefix, value_path, parts, params):
    if item.key:
        parts.append(f"{prefix}->>'key' = %({value_path}_key)s")
        params[f"{value_path}_key"] = item.key

    if item.kind:
        parts.append(f"{prefix}->>'kind' = %({value_path}_kind)s")
        params[f"{value_path}_kind"] = item.kind.value

    if item.identifier:
        parts.append(f"{prefix}->>'identifier' = %({value_path}_identifier)s")
        params[f"{value_path}_identifier"] = item.identifier


def build_sql_for_item_recursive(item: MatchInput, index: int, at_value: int | None = None, prefix: str = "arg"):
    sql_parts = []
    params = {}

    if at_value is not None:
        sql_parts.append(f"idx = %({prefix}_at_{index})s")
        params[f"{prefix}_at_{index}"] = at_value + 1

    if item.key:
        sql_parts.append(f"item->>'key' = %({prefix}_key_{index})s")
        params[f"{prefix}_key_{index}"] = item.key

    if item.kind:
        sql_parts.append(f"item->>'kind' = %({prefix}_kind_{index})s")
        params[f"{prefix}_kind_{index}"] = item.kind.value

    if item.identifier:
        sql_parts.append(f"item->>'identifier' = %({prefix}_identifier_{index})s")
        params[f"{prefix}_identifier_{index}"] = item.identifier

    if item.children:
        child_parts = []
        child_params = {}
        for idx, child in enumerate(item.children):
            build_child_recursively(
                child,
                f"item->'children'->{idx + 1}",
                f"children_{index}_{idx}",
                child_parts,
                child_params,
            )
        sql_parts += child_parts
        params.update(child_params)

    return (" AND ".join(sql_parts), params)


def _json_scan_params(
    search_params: t.Sequence[MatchInput] | None,
    type: t.Literal["args", "returns"] = "args",
    force_length: t.Optional[int] = None,
    force_non_nullable_length: t.Optional[int] = None,
    force_structure_length: t.Optional[int] = None,
    model: str = "facade_shortcut",
):
    individual_queries = []
    all_params = {}
    if search_params:
        for index, item in enumerate(search_params):
            sql_part, params = build_sql_for_item_recursive(item, index, at_value=item.at)
            subquery = f"EXISTS (SELECT 1 FROM jsonb_array_elements({type}) WITH ORDINALITY AS j(item, idx) WHERE {sql_part})"
            individual_queries.append(subquery)
            all_params.update(params)

    if force_length is not None:
        individual_queries.append(f"jsonb_array_length({type}) = {force_length}")

    if force_non_nullable_length is not None:
        sql_part = "item->>'nullable'::text = 'false'"
        individual_queries.append(f"""(SELECT COUNT(*) FROM jsonb_array_elements({type}) AS j(item) WHERE {sql_part}) = {force_non_nullable_length}""")

    if force_structure_length is not None:
        sql_part = "item->>'kind' = 'STRUCTURE'"
        individual_queries.append(f"""(SELECT COUNT(*) FROM jsonb_array_elements({type}) AS j(item) WHERE {sql_part}) = {force_structure_length}""")

    if not individual_queries:
        raise ValueError("No search params provided")

    full_sql = f"SELECT id FROM {model} WHERE " + " AND ".join(individual_queries)
    return full_sql, all_params


def _json_scan_ids(
    demands: t.Sequence[MatchInput] | None = None,
    type: t.Literal["args", "returns"] = "args",
    force_length: t.Optional[int] = None,
    force_non_nullable_length: t.Optional[int] = None,
    force_structure_length: t.Optional[int] = None,
    model: str = "facade_shortcut",
) -> list[t.Any]:
    full_sql, all_params = _json_scan_params(
        demands,
        type=type,
        force_length=force_length,
        force_non_nullable_length=force_non_nullable_length,
        force_structure_length=force_structure_length,
        model=model,
    )
    return _execute_ids(full_sql, all_params)


def build_state_params(
    search_params: t.Sequence[MatchInput] | None,
    model: str = "facade_statedefinition",
):
    individual_queries = []
    all_params = {}
    if search_params:
        for index, item in enumerate(search_params):
            sql_part, params = build_sql_for_item_recursive(item, index, at_value=item.at)
            subquery = f"EXISTS (SELECT 1 FROM jsonb_array_elements(ports) WITH ORDINALITY AS j(item, idx) WHERE {sql_part})"
            individual_queries.append(subquery)
            all_params.update(params)

    if not individual_queries:
        raise ValueError("No search params provided")

    full_sql = f"SELECT id FROM {model} WHERE " + " AND ".join(individual_queries)
    return full_sql, all_params


def get_state_ids_by_demands(
    matches: t.Sequence[MatchInput] | None = None,
    model: str = "facade_statedefinition",
) -> list[t.Any]:
    full_sql, all_params = build_state_params(matches, model=model)
    return _execute_ids(full_sql, all_params)
