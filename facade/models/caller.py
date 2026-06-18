from authentikate.models import Client, Organization, User
from django.db import models


class Caller(models.Model):
    """The (client, user, organization) identity that *requests* work.

    A Caller is derived from the auth token on every authenticated request and is the
    requestor identity for assignations. It is independent of an Agent
    (the provider runtime): a pure frontend caller has a Caller but no Agent.

    """

    client = models.ForeignKey(Client, on_delete=models.CASCADE, help_text="The Associated Client")
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text="The Associatsed User",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        help_text="The Organization this Caller belongs to",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["client", "user", "organization"],
                name="No multiple Callers for same App and User in the same organization allowed",
            )
        ]

    def __str__(self) -> str:
        return f"{self.client} used by {self.user} in {self.organization}"
