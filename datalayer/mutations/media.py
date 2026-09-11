from kante.types import Info
from typing import cast
from datalayer import types, inputs
from datalayer.datalayer import get_current_datalayer
from datalayer import models


def _owned_store(info: Info, store_id: str) -> models.MediaStore:
    """Fetch a MediaStore the caller's organization owns, or refuse.

    A store id is an opaque handle a client can simply hold, so trading one for S3 credentials
    has to be authorized.
    """
    organization = info.context.request.organization
    try:
        return models.MediaStore.objects.get(id=store_id, organization=organization)
    except models.MediaStore.DoesNotExist:
        raise PermissionError(f"No media store {store_id} in organization {organization.slug}.")


def request_media_upload(info: Info, input: inputs.RequestMediaUploadInput) -> types.MediaUploadGrant:
    """Request temporary S3 upload credentials for a media file."""

    dl = get_current_datalayer()
    input_model = getattr(input, "to_pydantic")()
    grant = dl.generate_media_upload_grant(
        input_model,
        organization_id=info.context.request.organization.id,
        creator_id=info.context.request.user.id,
    )
    return types.MediaUploadGrant(**grant.model_dump())


def finish_media_upload(info: Info, input: inputs.FinishMediaUploadInput) -> types.MediaStore:
    """Mark the MediaStore as populated after a successful upload."""

    dl = get_current_datalayer()
    input_model = getattr(input, "to_pydantic")()
    _owned_store(info, input_model.store_id)
    return cast(types.MediaStore, dl.finish_media_upload(input_model))


def request_media_access(info: Info, input: inputs.RequestMediaAccessInput) -> types.MediaAccessGrant:
    """Request temporary S3 read credentials for a media file."""

    dl = get_current_datalayer()
    model = input.to_pydantic()

    store = _owned_store(info, model.store_id)
    return types.MediaAccessGrant.from_pydantic(dl.generate_media_access_grant(store))

