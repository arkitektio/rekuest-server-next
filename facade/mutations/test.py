from kante.types import Info
import strawberry_django
import strawberry
from facade import types, models, inputs, enums, scalars
import hashlib
import json
import logging
from facade.protocol import infer_protocols
from facade.utils import hash_input

logger = logging.getLogger(__name__)


@strawberry.input
class CreateTestCaseInput:
    node: strawberry.ID
    key: str
    is_benchmark: bool = False
    description: str | None = None
    name: str | None = None


def create_test_case(info: Info, input: CreateTestCaseInput)-> types.TestCase:

    raise NotImplementedError("TODO: implement reserve")




@strawberry.input
class CreateTestResultInput:
    case: strawberry.ID
    template: strawberry.ID
    passed: bool
    result: str | None = None



def create_test_result(info: Info, input: CreateTestResultInput)-> types.Reservation:

    reference = input.reference or hash_input(input.binds or inputs.BindsInput(templates=[]))

    models.Reservation.objects.get_or_create(
        reference=reference,
    )

