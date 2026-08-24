"""Media stores are organization-scoped.

``request_media_access`` trades a store id for temporary S3 read credentials. The id is an
opaque handle a client can simply hold, so the exchange has to be authorized — before this,
``MediaStore`` carried no owner at all and ``MediaStore.objects.get(id=...)`` was the whole
check, letting any authenticated user read any organization's media.

The ownership check runs before any S3/STS call, so these tests need no moto fixture.
"""

from types import SimpleNamespace

import pytest

from datalayer import models
from datalayer.mutations.media import _owned_store

from tests.factories import create_registry_bundle
from tests.graphql.test_cross_tenant_isolation import _context_for


def _info_for(user, client, org):
    """A minimal ``Info`` stand-in: the resolver only reaches ``info.context.request``."""
    return SimpleNamespace(context=_context_for(user, client, org))


@pytest.mark.django_db(transaction=True)
class TestMediaStoreOwnership:
    def test_owner_can_fetch_its_own_store(self):
        user, client, org, _ = create_registry_bundle("media-own")
        store = models.MediaStore.objects.create(key="media-own-key", bucket="media", organization=org)

        assert _owned_store(_info_for(user, client, org), str(store.pk)).pk == store.pk

    def test_other_organization_is_refused(self):
        _, _, owner_org, _ = create_registry_bundle("media-x-owner")
        store = models.MediaStore.objects.create(key="media-x-key", bucket="media", organization=owner_org)

        other_user, other_client, other_org, _ = create_registry_bundle("media-x-other")

        with pytest.raises(PermissionError):
            _owned_store(_info_for(other_user, other_client, other_org), str(store.pk))
