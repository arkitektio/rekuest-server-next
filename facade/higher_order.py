"""Pure projection logic for higher-order implementations (HOIs).

A higher-order implementation ``H`` wraps a lower-level implementation ``L`` and
remaps three channels:

* **args in** — ``H``'s bound params are spread as ``L``'s named args and the caller's
  args are remapped onto ``L``'s arg ports (renamed where the ``arg_map`` says so, with
  the remainder reified into a single dict port named ``args_key``);
* **dependencies in** — ``H``'s resolved dependency slots (an explicit, stored contract)
  plus any bound dependencies are projected onto ``L``'s dependency slots;
* **returns out** — ``L``'s returns dict is unfolded back onto ``H``'s declared return
  ports.

These functions are deliberately framework-free (plain dicts in, plain dicts out) so the
remap/unfold contract is unit-testable without a database or the websocket stack. The
config they consume is ``Implementation.higher_order_config`` — see that field's help text.
"""

from typing import Any, Dict, Iterable, Optional

# A resolved-dependency dict is whatever ``build_dependency_dict`` produces, keyed by the
# declaring implementation's dependency ``key``. We treat its values as opaque here.
DependencyDict = Dict[str, Any]


def build_lower_args(config: dict, caller_args: Dict[str, Any]) -> Dict[str, Any]:
    """Project ``H``'s bound params + the caller's args onto ``L``'s args.

    Order of precedence (later wins on key clash):
    1. ``config["bound"]`` spread as ``L``'s named args;
    2. each explicit ``config["arg_map"]`` entry sourced ``from: "caller"`` (renamed);
    3. the *remaining* caller args (those not consumed by an explicit map entry) either
       packed under ``config["args_key"]`` (the reified dict port) or, if no ``args_key``
       is set, spread directly onto ``L``'s args by their original key.
    """
    lower_args: Dict[str, Any] = dict(config.get("bound") or {})

    consumed: set[str] = set()
    for lower_key, spec in (config.get("arg_map") or {}).items():
        if (spec or {}).get("from") == "caller":
            caller_key = spec["key"]
            if caller_key not in caller_args:
                raise ValueError(f"Higher-order arg map references caller arg '{caller_key}' which was not supplied")
            lower_args[lower_key] = caller_args[caller_key]
            consumed.add(caller_key)

    remaining = {k: v for k, v in caller_args.items() if k not in consumed}

    args_key = config.get("args_key")
    if args_key:
        lower_args[args_key] = remaining
    else:
        lower_args.update(remaining)

    return lower_args


def build_lower_dependencies(config: dict, resolved_h_dependencies: DependencyDict) -> DependencyDict:
    """Project ``H``'s resolved dependencies + bound dependencies onto ``L``'s dep slots.

    ``resolved_h_dependencies`` is the dependency dict produced for ``H`` (keyed by ``H``'s
    declared dependency ``key``). With an empty ``dependency_map`` the contract is
    *pass-through by matching key*. Otherwise every entry of ``dependency_map`` names a
    lower dep key and its source — a bound (pre-resolved) value or one of ``H``'s declared
    dependencies by key.
    """
    dependency_map = config.get("dependency_map") or {}
    if not dependency_map:
        return dict(resolved_h_dependencies)

    lower_dependencies: DependencyDict = {}
    for lower_key, spec in dependency_map.items():
        spec = spec or {}
        source = spec.get("from")
        if source == "bound":
            lower_dependencies[lower_key] = spec.get("value")
        elif source == "caller":
            h_key = spec["key"]
            if h_key not in resolved_h_dependencies:
                raise ValueError(f"Higher-order dependency map references declared dependency '{h_key}' which the caller did not supply")
            lower_dependencies[lower_key] = resolved_h_dependencies[h_key]
        else:
            raise ValueError(f"Higher-order dependency map entry for '{lower_key}' must set 'from' to 'bound' or 'caller'")

    return lower_dependencies


def project_returns(config: dict, lower_returns: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Unfold ``L``'s returns dict back onto ``H``'s return ports.

    ``return_map`` is ``{higher_return_key: lower_return_key}``. Empty/None ⇒ identity
    (the returns are passed through unchanged). ``None`` returns stay ``None``.
    """
    if lower_returns is None:
        return None

    return_map = config.get("return_map") or {}
    if not return_map:
        return dict(lower_returns)

    return {higher_key: lower_returns.get(lower_key) for higher_key, lower_key in return_map.items()}


def required_lower_dependency_sources(config: dict) -> set[str]:
    """The set of ``H`` dependency keys the ``dependency_map`` sources ``from: caller``.

    Used at creation time to check the wrapper actually declares every dependency it
    promises to paste onto ``L``.
    """
    sources: set[str] = set()
    for spec in (config.get("dependency_map") or {}).values():
        if (spec or {}).get("from") == "caller":
            sources.add(spec["key"])
    return sources


def validate_dependency_coverage(config: dict, lower_dependency_keys: Iterable[str], declared_h_dependency_keys: Iterable[str]) -> None:
    """Ensure every lower dependency slot is satisfiable and every caller source is declared.

    Raises ``ValueError`` if a lower dep is neither bound nor mapped-from a declared ``H``
    dependency, or if the map references an ``H`` dependency the wrapper never declared.
    """
    dependency_map = config.get("dependency_map") or {}
    declared = set(declared_h_dependency_keys)

    # Every caller-sourced map entry must reference a really-declared H dependency.
    for h_key in required_lower_dependency_sources(config):
        if h_key not in declared:
            raise ValueError(f"Higher-order dependency map references undeclared dependency '{h_key}'. Declare it on the wrapper so the caller knows to pass it.")

    # Empty map ⇒ pass-through by key: every lower dep must be a declared H dependency.
    if not dependency_map:
        for lower_key in lower_dependency_keys:
            if lower_key not in declared:
                raise ValueError(f"Lower dependency '{lower_key}' has no mapping and no matching declared dependency on the wrapper.")
        return

    # Explicit map ⇒ every lower dep must be covered by a bound or caller entry.
    for lower_key in lower_dependency_keys:
        if lower_key not in dependency_map:
            raise ValueError(f"Lower dependency '{lower_key}' is neither bound nor mapped to a declared dependency.")


def validate_higher_order_pairing(higher_action_kind: str, lower_action_kind: str, lower_is_higher_order: bool) -> None:
    """Guard the wrapper↔wrapped pairing at creation time.

    - the wrapped implementation must not itself be a wrapper (MVP: no nested higher-order);
    - the wrapper and wrapped action kinds must agree (a FUNCTION wrapper cannot wrap a GENERATOR
      and vice-versa, since the unfold is per-yield for generators).
    """
    if lower_is_higher_order:
        raise ValueError("Nested higher-order implementations are not supported yet — wrap a concrete implementation, not another wrapper.")
    if higher_action_kind != lower_action_kind:
        raise ValueError(f"Higher-order kind mismatch: wrapper is {higher_action_kind} but the wrapped action is {lower_action_kind}; they must agree.")
