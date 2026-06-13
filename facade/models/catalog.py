from authentikate.models import Client, Organization
from django.contrib.auth import get_user_model
from django.db import models


class Collection(models.Model):
    """A collection is a group of actions that are related to each other.

    You can put actions into a collection to group them together, and
    app developers can specify which collection a action belongs to
    by default.

    Collections should remain domain specific.

    Example collections are:
    - Segmentation
    - Classification
    - Image Processing


    """

    name = models.CharField(max_length=1000, unique=True, help_text="The name of this Collection")
    description = models.TextField(help_text="A description for the Collection")
    defined_at = models.DateTimeField(
        auto_created=True,
        auto_now_add=True,
        help_text="Date this Collection was created",
    )
    updated_at = models.DateTimeField(auto_now=True, help_text="Date this Collection was last updated")
    creator = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="collections",
        help_text="The user that created this Collection",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="collections",
        help_text="The Organization this Collection belongs to",
    )


class Protocol(models.Model):
    """Protocols are ways to describe the input and output relations
    of a action. When a new action is created the
    interference module will try to infer the protocol of the action
    and assign it to the action. This is done by looking at the
    input and output types of the action and matching them to the
    protocols that are defined by your installed inference modules.

    """

    name = models.CharField(max_length=1000, unique=True, help_text="The name of this Protocol")
    description = models.TextField(help_text="A description for the Protocol")

    def __str__(self) -> str:
        return self.name


class UICatalog(models.Model):
    """A UICatalog is a collection of UI components that are used to
    represent actions in the UI. You can create your own UI catalogs
    and use them to customize the look of your actions.

    """

    name = models.CharField(max_length=1000)
    schema = models.JSONField(default=dict)

    def validate_surface(self, surface: str) -> bool:
        """Validate if this catalog can be used for a given surface (e.g. 'web', 'mobile', 'desktop')"""
        return True


class IconPack(models.Model):
    """An IconPack is a collection of icons that are used to
    represent actions in the UI. You can create your own icon packs
    and use them to customize the look of your actions.

    """

    name = models.CharField(max_length=1000)


class Toolbox(models.Model):
    name = models.CharField(max_length=1000)
    description = models.TextField()
    creator = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="toolboxes",
        help_text="The user that created this Shortcut",
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="toolboxes",
        help_text="The client this Toolbox belongs to",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="toolboxes",
        help_text="The Organization this Collection belongs to",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Shortcut(models.Model):
    name = models.CharField(max_length=1000)
    description = models.TextField(null=True, blank=True)
    toolbox = models.ForeignKey(Toolbox, on_delete=models.CASCADE, related_name="shortcuts")
    action = models.ForeignKey("Action", on_delete=models.CASCADE, related_name="shortcuts", null=True)
    implementation = models.ForeignKey("Implementation", on_delete=models.CASCADE, related_name="shortcuts", null=True)
    saved_args = models.JSONField(default=dict)
    creator = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="shortcuts",
        help_text="The user that created this Shortcut",
    )
    bind_number = models.IntegerField(
        default=0,
        null=True,
        blank=True,
        help_text="Which shortcut should be bound to this Action by default. 0 means no binding",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    args = models.JSONField(default=list, help_text="Inputs for this Shortcut")
    returns = models.JSONField(default=list, help_text="Outputs for this Shortcut")
    allow_quick = models.BooleanField(
        default=False,
        help_text="Allow quick execution of this Shortcut (e.g. run without confirmation)",
    )
    use_returns = models.BooleanField(
        default=False,
        help_text="Use the result of this Shortcut (e.g. use the result in the next Shortcut)",
    )


class Icon(models.Model):
    pack = models.ForeignKey(IconPack, on_delete=models.CASCADE)
    icon_url = models.CharField(max_length=10000)
    hash = models.CharField(max_length=1000)
    action = models.ForeignKey("Action", on_delete=models.SET_NULL, null=True, related_name="icons")
