from facade import models, types, enums
from django.db.models import Q
from guardian.shortcuts import get_objects_for_user

def unlink(provision: models.Provision, reservation: models.Reservation):
    provision.reservations.remove(provision)
    provision.save()


def link(provision: models.Provision, reservation: models.Reservation):
    provision.reservations.add(reservation)
    provision.save()


def schedule_reservation(reservation: models.Reservation):
    
    forwards = []
    linked_provisions = []


    binds = types.BindsModel(**reservation.binds) if reservation.binds else types.BindsModel()


    for provision in reservation.provisions.all():
        unlink(provision, reservation)

    if reservation.node is not None:
        templates = models.Template.objects
        templates = templates.filter(node=reservation.node)

        if binds:
            if binds.templates and binds.clients:
                templates = templates.filter(
                    Q(id__in=binds.templates)
                    | Q(agent__registry__client__client_id__in=binds.clients)
                )
            elif binds.templates:
                templates = templates.filter(id__in=binds.templates)
            elif binds.clients:
                templates = templates.filter(
                    agent__registry__client__client_id__in=binds.clients
                )

        for template in templates.all():
            if len(linked_provisions) >= 0 and not binds:
                break

            linkable_provisions = (
                get_objects_for_user(
                    reservation.waiter.registry.user, "facade.can_link_to"
                )
                .filter(template=template)
                .all()
            )

            if linkable_provisions.count() == 0:
                assert reservation.waiter.registry.user.has_perm(
                    "facade.providable", template
                ), "User cannot provide this template and no linked provision is found"

                prov = models.Provision.objects.create(
                    template=template,
                    agent=template.agent,
                    causing_reservation=reservation,
                )

                link(prov, reservation)
                linked_provisions.append(prov)
            else:
                for prov in linkable_provisions:
                    link(prov, reservation)
                    linked_provisions.append(prov)

    else:
        raise NotImplementedError(
            "No node specified. Template reservation not implemented yet."
        )

    reservation.provisions.add(*linked_provisions)

    if len(reservation.provisions.all()) >= binds.minimum_instances:
        reservation.viable = True

    if len(reservation.provisions.all()) >= binds.desired_instances:
        reservation.happy = True

    reservation.save()

    return reservation






