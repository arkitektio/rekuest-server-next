from authentikate.models import Client, Organization, User
from django.db import models


class Registry(models.Model):
    """A registry is an app that is bound to a specific user on the
    backend.

    It is the root type for all agents and waiters that are
    created by this app.

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
        help_text="The Organization this Registry belongs to",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["client", "user", "organization"],
                name="No multiple Registries for same App and User in the same organization allowed",
            )
        ]

    def __str__(self) -> str:
        return f"{self.client} used by {self.user} in {self.organization}"
