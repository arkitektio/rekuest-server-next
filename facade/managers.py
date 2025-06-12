import re
import typing as t

from django.db import connection

from .inputs import PortMatchInput, ActionDemandInput

qt = re.compile(r"@(?P<package>[^\/]*)\/(?P<interface>[^\/]*)")


def build_child_recursively(item: PortMatchInput, prefix, value_path, parts, params):
    if item.key:
        parts.append(f"{prefix}->>'key' = %({value_path}_key)s")
        params[f"{value_path}_key"] = item.key

    if item.kind:
        parts.append(f"{prefix}->>'kind' = %({value_path}_kind)s")
        params[f"{value_path}_kind"] = item.kind.value

    if item.identifier:
        parts.append(f"{prefix}->>'identifier' = %({value_path}_identifier)s")
        params[f"{value_path}_identifier"] = item.identifier

    if item.children:
        raise ValueError("Children should not be present in the child item")
        build_child_recursively(item.child, prefix + "->'children'", f"{value_path}_child", parts, params)


def build_sql_for_item_recursive(item: PortMatchInput, index: int, at_value: int | None = None, prefix: str = "arg"):
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
        # Adjusting the prefix for recursion
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


def build_params(
    search_params: list[PortMatchInput] | None,
    type: t.Literal["args", "returns"] = "args",
    force_length: t.Optional[int] = None,
    force_non_nullable_length: t.Optional[int] = None,
    force_structure_length: t.Optional[int] = None,
    model: str = "facade_action",
):
    individual_queries = []
    all_params = {}
    if search_params:
        for index, item in enumerate(search_params):
            sql_part, params = build_sql_for_item_recursive(item, index, at_value=item.at)
            if type == "args":
                subquery = f"EXISTS (SELECT 1 FROM jsonb_array_elements(args) WITH ORDINALITY AS j(item, idx) WHERE {sql_part})"
            else:
                subquery = f"EXISTS (SELECT 1 FROM jsonb_array_elements(returns) WITH ORDINALITY AS j(item, idx) WHERE {sql_part})"

            individual_queries.append(subquery)
            all_params.update(params)

    if force_length is not None:
        individual_queries.append(f"jsonb_array_length({type}) = {force_length}")

    if force_non_nullable_length is not None:
        sql_part = "item->>'nullable'::text = 'false'"
        count_condition = f"""(SELECT COUNT(*) FROM jsonb_array_elements({type}) AS j(item) WHERE {sql_part}) = {force_non_nullable_length}"""
        individual_queries.append(count_condition)

    if force_structure_length is not None:
        sql_part = "item->>'kind' = 'STRUCTURE'"
        count_condition = f"""(SELECT COUNT(*) FROM jsonb_array_elements({type}) AS j(item) WHERE {sql_part}) = {force_structure_length}"""
        individual_queries.append(count_condition)

    if not individual_queries:
        raise ValueError("No search params provided")

    full_sql = f"SELECT id FROM {model} WHERE " + " AND ".join(individual_queries)

    return full_sql, all_params


def build_action_demand_params(
    action_demand: ActionDemandInput,
    model: str = "facade_action",
) -> tuple[str, dict[str, t.Any]]:
    """Build SQL for action demand"""
    individual_queries = []
    all_params = {}
    
    
    if action_demand.name:
        individual_queries.append(f"name = %(name)s")
        all_params["name"] = action_demand.name
        

    if action_demand.arg_matches:
        for index, item in enumerate(action_demand.arg_matches):
            sql_part, params = build_sql_for_item_recursive(item, index, at_value=item.at, prefix="arg")
            subquery = f"EXISTS (SELECT 1 FROM jsonb_array_elements(args) WITH ORDINALITY AS j(item, idx) WHERE {sql_part})"

            individual_queries.append(subquery)
            all_params.update(params)

    if action_demand.return_matches:
        for index, item in enumerate(action_demand.return_matches):
            sql_part, params = build_sql_for_item_recursive(item, index, at_value=item.at, prefix="return")
            subquery = f"EXISTS (SELECT 1 FROM jsonb_array_elements(returns) WITH ORDINALITY AS j(item, idx) WHERE {sql_part})"

            individual_queries.append(subquery)
            all_params.update(params)

    if action_demand.force_arg_length is not None:
        individual_queries.append(f"jsonb_array_length(args) = {action_demand.force_arg_length}")
    if action_demand.force_return_length is not None:
        individual_queries.append(f"jsonb_array_length(returns) = {action_demand.force_return_length}")

    if not individual_queries:
        raise ValueError("No search params provided")

    full_sql = f"SELECT id FROM {model} WHERE " + " AND ".join(individual_queries)

    return full_sql, all_params


def build_state_params(
    search_params: list[PortMatchInput] | None,
    model: str = "facade_state_schema",
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


def filter_actions_by_demands(
    qs: t.Any,
    demands: list[PortMatchInput] = None,
    type: t.Literal["args", "returns"] = "args",
    force_length: t.Optional[int] = None,
    force_non_nullable_length: t.Optional[int] = None,
    force_structure_length: t.Optional[int] = None,
    model: str = "facade_action",
):
    if type not in ["args", "returns"]:
        raise ValueError("Type must be either 'args' or 'returns'")

    full_sql, all_params = build_params(
        demands,
        type=type,
        force_length=force_length,
        force_non_nullable_length=force_non_nullable_length,
        force_structure_length=force_structure_length,
        model=model,
    )

    with connection.cursor() as cursor:
        cursor.execute(full_sql, all_params)
        rows = cursor.fetchall()
        ids = [row[0] for row in rows]

    qs = qs.filter(id__in=ids)
    return qs


def get_action_ids_by_demands(
    demands: list[PortMatchInput] = None,
    type: t.Literal["args", "returns"] = "args",
    force_length: t.Optional[int] = None,
    force_non_nullable_length: t.Optional[int] = None,
    force_structure_length: t.Optional[int] = None,
    model: str = "facade_action",
):
    if type not in ["args", "returns"]:
        raise ValueError("Type must be either 'args' or 'returns'")

    full_sql, all_params = build_params(
        demands,
        type=type,
        force_length=force_length,
        force_non_nullable_length=force_non_nullable_length,
        force_structure_length=force_structure_length,
        model=model,
    )

    with connection.cursor() as cursor:
        cursor.execute(full_sql, all_params)
        rows = cursor.fetchall()
        ids = [row[0] for row in rows]
        return ids


def get_action_ids_by_action_demand(
    action_demand: ActionDemandInput,
    model: str = "facade_action",
):
    full_sql, all_params = build_action_demand_params(
        action_demand,
        model=model,
    )

    with connection.cursor() as cursor:
        cursor.execute(full_sql, all_params)
        rows = cursor.fetchall()
        ids = [row[0] for row in rows]
        return ids


def get_state_ids_by_demands(
    matches: list[PortMatchInput] = None,
    model: str = "facade_stateschema",
):
    full_sql, all_params = build_state_params(
        matches,
        model=model,
    )

    with connection.cursor() as cursor:
        cursor.execute(full_sql, all_params)
        rows = cursor.fetchall()
        ids = [row[0] for row in rows]
        return ids
