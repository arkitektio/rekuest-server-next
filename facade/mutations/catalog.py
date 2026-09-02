"""UI catalog registration."""

from kante.types import Info

from facade import inputs, models, types


def register_ui_catalog(info: Info, input: inputs.RegisterUiCatalogInput) -> types.UICatalog:
    """Upsert a catalog by name in the caller's organization with the components and operations a UI app announces."""
    model = input.to_pydantic()
    catalog, _ = models.UICatalog.objects.update_or_create(
        name=model.name,
        organization=info.context.request.organization,
        defaults=dict(
            description=model.description,
            components=[component.model_dump() for component in model.components],
            operations=[operation.model_dump() for operation in model.operations],
            registered_by=info.context.request.client,
        ),
    )
    return catalog
