from django.db import models


class StructurePackage(models.Model):
    key = models.CharField(max_length=2000, unique=True)
    description = models.CharField(max_length=2000, blank=True, null=True)


class Interface(models.Model):
    package = models.ForeignKey(StructurePackage, on_delete=models.CASCADE, related_name="interfaces")
    key = models.CharField(max_length=2000)
    description = models.CharField(max_length=2000, blank=True, null=True)
    default_widget = models.JSONField(blank=True, null=True)
    default_return_widget = models.JSONField(blank=True, null=True)
    protocols = models.ManyToManyField("Protocol", blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["package", "key"],
                name="No multiple Interfaces with same key in the same package allowed",
            )
        ]


class Descriptor(models.Model):
    package = models.ForeignKey(StructurePackage, on_delete=models.CASCADE, related_name="descriptors")
    key = models.CharField(max_length=2000)
    description = models.CharField(max_length=2000, blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["package", "key"],
                name="No multiple Descriptors with same key in the same package allowed",
            )
        ]


class Structure(models.Model):
    """A Structure is a way to describe a data structure that can be used"""

    package = models.ForeignKey(StructurePackage, on_delete=models.CASCADE, related_name="structures")
    key = models.CharField(max_length=2000, help_text="A unique identifier for this structure")
    label = models.CharField(max_length=2000, blank=True, null=True)
    description = models.CharField(max_length=2000, blank=True, null=True)
    get_query = models.CharField(max_length=2000, blank=True, null=True)
    describe_query = models.CharField(max_length=2000, blank=True, null=True)
    default_widget = models.JSONField(blank=True, null=True)
    default_return_widget = models.JSONField(blank=True, null=True)
    implements = models.ManyToManyField(Interface, blank=True)
    descriptors = models.ManyToManyField(Descriptor, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["package", "key"],
                name="No multiple Structures with same key in the same package allowed",
            )
        ]
