from kante.types import Info
from facade import types, models, inputs, enums, managers
import uuid
import strawberry





def materialize_blok(info: Info, input: inputs.MaterializeBlokInput) -> types.MaterializedBlok:
    
    mblok, _ = models.MaterializedBlok.objects.update_or_create(
        blok_id=input.blok,
        dashboard_id=input.dashboard,
        agent_id=input.agent,
    )
    
    blok = models.Blok.objects.get(id=input.blok)
    agent = models.Agent.objects.get(id=input.agent)
    
    
    for action in blok.action_demands:
        
        demand = inputs.ActionDemandInputModel(
            **action,
        )
        
        ids = managers.get_action_ids_by_action_demand(demand)
        
        implementation = agent.implementations.filter(action_id__in=ids).first()
        if not implementation:
            raise ValueError(
                f"No implementation found for action demand {demand} in blok {blok.name}."
            )
            
        mapping, _ = models.ActionMapping.objects.update_or_create(
            key = demand.key,
            materialized_blok=mblok,
            defaults=dict(
                implementation=implementation
            )
            
        )
        
    for state in blok.state_demands:
        demand = inputs.SchemaDemandInputModel(
            **state,
        )
        
        ids = managers.get_state_ids_by_demands(demand.matches)
        
        state = agent.states.filter(state_schema_id__in=ids).first()
        if not state:
            raise ValueError(
                f"No state found for state demand {demand} in blok {blok.name}."
            )
            
        mapping, _ = models.StateMapping.objects.update_or_create(
            key = demand.key,
            materialized_blok=mblok,
            defaults=dict(
                state=state
            )
            
        )
        
        
        
    
    
    
    
    

    return mblok
