from kante.types import Info
import strawberry
from facade import types, models
import logging

logger = logging.getLogger(__name__)


@strawberry.input
class CreateTestCaseInput:
    action: strawberry.ID
    tester: strawberry.ID
    description: str | None = None
    name: str | None = None


def create_test_case(info: Info, input: CreateTestCaseInput) -> types.TestCase:
    x, _ = models.TestCase.objects.update_or_create(
        action=models.Action.objects.get(pk=input.action),
        tester=models.Action.objects.get(pk=input.tester),
        defaults=dict(
            description=input.description,
            name=input.name,
        ),
    )
    return x


@strawberry.input
class CreateTestResultInput:
    case: strawberry.ID
    tester: strawberry.ID
    implementation: strawberry.ID
    passed: bool
    result: str | None = None


def create_test_result(info: Info, input: CreateTestResultInput) -> types.TestResult:
    return models.TestResult.objects.create(
        case=models.TestCase.objects.get(pk=input.case),
        implementation=models.Implementation.objects.get(pk=input.implementation),
        tester=models.Implementation.objects.get(pk=input.tester),
        passed=input.passed,
        result=input.result,
    )
