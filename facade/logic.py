from facade import models, managers
from kante.types import Info
from dataclasses import dataclass
import uuid


def auto_resolve(info: Info, implementation: models.Implementation, resolution: models.Resolution, visited_implementations: set[str] | None = None) -> None:
    if not visited_implementations:
        visited_implementations = set()

    for dependency in implementation.dependencies.all():
        print(f"Resolving, {dependency}")
        agentsqs = models.Agent.objects.filter(registry__organization=info.context.request.organization)

        matched_ids: dict[str, list[int]] = {}

        for ports_demand in dependency.get_action_demands():
            new_ids = managers.get_action_ids_by_action_demand(
                action_demand=ports_demand,
                organization_id=info.context.request.organization.id,
            )

            if len(new_ids) == 0:
                raise ValueError(f"No actions found that match the given action demands {ports_demand}")

            # Further logic to create resolution would go here.
            agentsqs = agentsqs.filter(implementations__action__id__in=new_ids)
            matched_ids[ports_demand.key] = new_ids

        # todo: select best agent from agentsqs
        selected_agent = agentsqs.first()

        if not selected_agent:
            raise ValueError(f"No agent found that can satisfy dependency {dependency.key}")

        for key, action_id_list in matched_ids.items():
            implementations = models.Implementation.objects.filter(
                action__id__in=action_id_list,
                agent=selected_agent,
            )

            count = 0

            for impl in implementations:
                if impl.id in visited_implementations:
                    continue
                else:
                    if impl.dependencies.exists():
                        visited_implementations.add(impl.id)
                        sresolution = models.Resolution.objects.create(
                            name=f"Auto-resolve for {dependency}{key} on {implementation}",
                            implementation=impl,
                            creator=info.context.request.user,
                            organization=info.context.request.organization,
                        )
                        auto_resolve(info, impl, sresolution, visited_implementations=visited_implementations)

                        models.ResolvedDependency.objects.create(
                            key=key,
                            resolution=resolution,
                            dependency=dependency,
                            resolution_key=str(uuid.uuid4()),
                            implementation=impl,
                            down_stream_resolution=sresolution,
                        )
                    else:
                        models.ResolvedDependency.objects.create(
                            key=key,
                            resolution=resolution,
                            dependency=dependency,
                            resolution_key=str(uuid.uuid4()),
                            implementation=impl,
                        )
                        visited_implementations.add(impl.id)

                count += 1
                if count >= dependency.prefered_instances:
                    break
