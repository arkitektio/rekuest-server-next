

from .inputs import PortDemandInput, PortMatchInput
from django.db import connection
import re
import typing as t
qt = re.compile(r"@(?P<package>[^\/]*)\/(?P<interface>[^\/]*)")


def build_child_recursively(item: PortMatchInput, prefix, value_path, parts, params):
    if item.key:
        parts.append(f"{prefix}->>'key' = %({value_path}_key)s")
        params[f"{value_path}_key"] = item.key

    if  item.kind:
        parts.append(f"{prefix}->>'kind' = %({value_path}_kind)s")
        params[f"{value_path}_kind"] = item.kind

    if item.identifier:
        parts.append(f"{prefix}->>'identifier' = %({value_path}_identifier)s")
        params[f"{value_path}_identifier"] = item.identifier

    if item.child:
        build_child_recursively(
            item.child, prefix + "->'child'", f"{value_path}_child", parts, params
        )


def build_sql_for_item_recursive(item: PortMatchInput, at_value=None):
    sql_parts = []
    params = {}

    if at_value is not None:
        sql_parts.append(f"idx = %(at_{at_value})s")
        params[f"at_{at_value}"] = at_value + 1

    if item.key:
        sql_parts.append(f"item->>'key' = %(key_{at_value})s")
        params[f"key_{at_value}"] = item.key

    if item.kind:
        sql_parts.append(f"item->>'kind' = %(kind_{at_value})s")
        params[f"kind_{at_value}"] = item.kind

    if item.identifier:
        sql_parts.append(f"item->>'identifier' = %(identifier_{at_value})s")
        params[f"identifier_{at_value}"] = item.identifier

    if item.child:
        # Adjusting the prefix for recursion
        child_parts = []
        child_params = {}
        build_child_recursively(
            item.child,
            "item->'child'",
            f"child_{at_value}",
            child_parts,
            child_params,
        )
        sql_parts += child_parts
        params.update(child_params)

    return (" AND ".join(sql_parts), params)


def build_params(search_params: list[PortMatchInput] | None, type: t.Literal["args", "returns"] = "args", force_length: t.Optional[int] = None, force_non_nullable_length: t.Optional[int] = None):
    individual_queries = []
    all_params = {}
    if search_params:
        for item in search_params:
            sql_part, params = build_sql_for_item_recursive(item, at_value=item.at)
            if type == "args":
                subquery = f"EXISTS (SELECT 1 FROM jsonb_array_elements(args) WITH ORDINALITY AS j(item, idx) WHERE {sql_part})"
            else:
                subquery = f"EXISTS (SELECT 1 FROM jsonb_array_elements(returns) WITH ORDINALITY AS j(item, idx) WHERE {sql_part})"

            individual_queries.append(subquery)
            all_params.update(params)

    if force_length is not None:
        individual_queries.append(f"jsonb_array_length({type}) = {force_length}")

    if force_non_nullable_length is not None:
        sql_part = f"item->>'nullable'::text = 'false'"
        count_condition = f"""
            (SELECT COUNT(*)
            FROM jsonb_array_elements({type}) AS j(item)
            WHERE {sql_part}) = {force_non_nullable_length}
        """
        individual_queries.append(count_condition)


    full_sql = "SELECT id FROM facade_node WHERE " + " AND ".join(individual_queries)
    print(full_sql, all_params)
    return full_sql, all_params



def filter_nodes_by_demands(qs: t.Any,
                            demands: list[PortMatchInput] = None,
                            type: t.Literal["args", "returns"] = "args",
                            force_length: t.Optional[int] = None,
                            force_non_nullable_length: t.Optional[int] = None
                            ):
    
    if type not in ["args", "returns"]:
        raise ValueError("Type must be either 'args' or 'returns'")
    
    full_sql, all_params = build_params(demands, type=type, force_length=force_length, force_non_nullable_length=force_non_nullable_length)

    with connection.cursor() as cursor:
        cursor.execute(full_sql, all_params)
        rows = cursor.fetchall()
        ids = [row[0] for row in rows]

    qs = qs.filter(id__in=ids)
    return qs

    return qs


