from kante.types import Info
import strawberry_django
import strawberry
from facade import types, models, inputs, enums, scalars, channels
from facade.channels import new_state_broadcast
import hashlib
import json
import logging
from facade.protocol import infer_protocols
from facade.utils import hash_input
import jsonpatch

logger = logging.getLogger(__name__)

def underscore(s: str) -> str:
    return s.replace(" ", "_").replace("-", "_").lower()



def set_state(info: Info, input: inputs.SetStateInput) -> types.State:

    state, _ = models.State.objects.update_or_create(
        state_schema_id=input.state_schema,
        defaults=dict(
            value=input.value,
        ),
    )

    return state



def update_state(info: Info, input: inputs.UpdateStateInput)-> types.State:
    
    state = models.State.objects.get(state_schema_id=input.state_schema)
    
    old_state = state.value

    patch = jsonpatch.JsonPatch([i for i in input.patches])

    new_state = patch.apply(old_state)

    state.value = new_state

    state.save()
    print("UPDATING STATE", state.id)
    new_state_broadcast(state.id, [f"new_state_stuff{state.id}", "farticarti"])


    return state



def archive_state(info: Info, input: inputs.ArchiveStateInput)-> types.State:


    state = models.State.objects.get(state_schema_id=input.state_schema)

    historical_state = models.HistoricalState.objects.create(
        state=state,
        value=state.value,
    )

    

    return historical_state.state

