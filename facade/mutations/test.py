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
    tester: strawberry.ID
    description: str | None = None
    name: str | None = None


def create_test_case(info: Info, input: CreateTestCaseInput)-> types.TestCase:

    x, _  = models.TestCase.objects.update_or_create(
        node=models.Node.objects.get(pk=input.node),
        tester=models.Node.objects.get(pk=input.tester),
        defaults=dict(
        description=input.description,
        name=input.name,
        )
    )
    return x



@strawberry.input
class CreateTestResultInput:
    case: strawberry.ID
    tester: strawberry.ID
    template: strawberry.ID
    passed: bool
    result: str | None = None



def create_test_result(info: Info, input: CreateTestResultInput)-> types.TestResult:

    return models.TestResult.objects.create(
        case=models.TestCase.objects.get(pk=input.case),
        template=models.Template.objects.get(pk=input.template),
        tester=models.Template.objects.get(pk=input.tester),
        passed=input.passed,
        result=input.result,
    )

