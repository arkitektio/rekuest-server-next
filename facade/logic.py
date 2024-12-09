import json
import logging
from facade import models, types, enums, inputs
from django.db.models import Q
from guardian.shortcuts import get_objects_for_user
from rekuest_core.inputs import models as rimodels
import hashlib
class UnresolvableDependencyError(Exception):
    pass


def unlink(provision: models.Provision, reservation: models.Reservation):
    provision.reservations.remove(reservation)
    provision.save()



def link(provision: models.Provision, reservation: models.Reservation):
    provision.reservations.add(reservation)
    provision.save()





def get_desired_templates_for_dependency(dependency: rimodels.DependencyInputModel):
    templates = models.Template.objects

    if dependency.clients:
        templates = templates.filter(
            agent__registry__client__client_id__in=dependency.clients
        )

    if dependency.templates:
        templates = templates.filter(id__in=dependency.templates)

    if dependency.protocols:
        templates = templates.filter(
            agent__registry__client__protocols__in=dependency.protocols
        )

    return templates


def get_desired_templates(
    dependency: rimodels.DependencyInputModel, reservation: models.Reservation
):
    # us filter out templates that are not assignable to the waiter.
    templates = get_objects_for_user(reservation.waiter, "facade.can_depend_on")

    if dependency.node:
        templates = templates.filter(node=dependency.node)

    # us filter out templates that are not assignable to the waiter.

    if dependency.binds:
        templates = templates.filter(
            Q(binds__templates__in=dependency.binds.templates)
            | Q(binds__clients__in=dependency.binds.clients)
        )

        # TODO: Filter out templates that do not have the required binds.

    if dependency.count:
        templates = templates[: dependency.count]
        # TODO: Lets check if we have enough templates to satisfy the dependency.
    else:
        templates = templates.first()
        # Apparently we don't care about the count, so lets just get the first one.

    return templates  # Should not be all templates, but the ones that match the dependency.


def can_active_provision(provision: models.Provision):
    if provision.dependencies.count() == 0:
        return True  # If the provision is not linked to any reservations, it can be activated, without any further checks.

    for dependency in provision.dependencies.all():
        # Lets check if the reservation is crucial, if it is, we need to check if it is active.
        if dependency.non_crucial:
            continue

        if (
            not dependency.active
        ):  # If the reservation is not active, we cannot activate the provision. And
            # we need to wait for the reservation to be active.
            return False

    return True


def on_agent_connected(agent: models.Agent):
    for provision in agent.provisions.all():
        # We need to check if even though the agent is connected, if all of the dependencies are active.
        if can_active_provision(provision):
            activate_provision(provision)


def check_viability(reservation: models.Reservation):

    binds = (
        rimodels.BindsInputModel(**reservation.binds)
        if reservation.binds
        else rimodels.BindsInputModel()
    )

    old_status = reservation.status

    if len(reservation.provisions.all()) == 0:
        new_status =  enums.ReservationEventKind.INACTIVE
    
    if len(reservation.provisions.all()) < binds.minimum_instances:
        new_status = enums.ReservationEventKind.UNHAPPY

    if len(reservation.provisions.all()) >= binds.desired_instances:
        new_status = enums.ReservationEventKind.HAPPY
    

    if old_status != new_status:
        reservation.status = new_status
        reservation.save()

        x = models.ReservationEvent.objects.create(
            reservation=reservation,
            kind=new_status,
            level=enums.LogLevel.INFO,
            message=f"Reservation transitioned to {new_status}",
        )

    return reservation





def activate_provision(provision: models.Provision) -> models.Provision:
    """This should recursively active the reservations that are linked to this provision"""
    provision.active = True
    provision.save()

    for connecting_reservation in provision.reservations.all():
        check_viability(connecting_reservation) # We need to check if the reservation is viable, and happy.

    return provision





async def apropagate_reservation_change(reservation: models.Reservation):
    """ This should propagate the change to a reservation which
    links where potentially updated.

    """

    binds = (
        rimodels.BindsInputModel(**reservation.binds)
        if reservation.binds
        else rimodels.BindsInputModel()
    )

    old_viable = reservation.viable


    active_provisions = []

    async for provision in reservation.provisions.all():
        if provision.is_viable:
            active_provisions.append(provision)


        

    if len(active_provisions) >= binds.minimum_instances:
        reservation.viable = True
    else:
        reservation.viable = False

    if len(active_provisions) >= binds.desired_instances:
        reservation.happy = True
    else:
        reservation.happy = False

    
    await reservation.asave()

    
    if old_viable != reservation.viable:
        x = await models.ReservationEvent.objects.acreate(
            reservation=reservation,
            kind=enums.ReservationEventKind.CHANGE,
            message=f"Reservation transitioned to {enums.ReservationEventKind.CHANGE}",
        )

        if reservation.causing_provision:
            await apropagate_provision_change(reservation.causing_provision)

    else:
        logging.info("We didn't change state. So no need to propagate.")
        await reservation.asave()




async def apropagate_provision_change(provision: models.Provision):

    unactive_reservations = []

    async for reservation in provision.caused_reservations.all():
        if reservation.viable:
            continue
        else:
            unactive_reservations.append(reservation)


    if len(unactive_reservations) == 0:
        provision.dependencies_met = True

    else:
        provision.dependencies_met = False

    await provision.asave()

    if provision.is_viable:
        logging.info("The provision is now active, and the dependencies are met. We can active potential reservations.")
        async for reservation in provision.reservations.all():
            await apropagate_reservation_change(reservation)
    
    else:
        logging.info("The provision is not active, or the dependencies are not met. So we need to check the reservations.")
        async for reservation in provision.reservations.all():
            await apropagate_reservation_change(reservation)



async def aset_provision_provided(provision: models.Provision):
    provision.provided = True
    await provision.asave()


   
    return provision

async def aset_provision_unprovided(provision: models.Provision):
    provision.provided = False
    await provision.asave()

   
    return provision



async def aset_provision_active(provision: models.Provision):
    provision.active = True
    await provision.asave()
    await apropagate_provision_change(provision)


   
    return provision


async def aset_provision_inactive(provision: models.Provision):
    provision.active = False
    await provision.asave()

    apropagate_provision_change(provision)
    return provision






def link_or_linkcreate_provisions_for_dependency(
    dependency: rimodels.DependencyInputModel, reservation: models.Reservation
):
    """hould return a list of provision ids that match the dependency.

    If the dependency is unresolvable, and a provision cannot be created
    to satisfy the dependency, this method should return an empty list.

    """

    templates = get_desired_templates(dependency)

    provisions = []

    for temp in templates:
        if temp.provision:
            link(temp.provision, reservation)
            provisions.append(temp.provision)
        else:
            # Permission are handled on the template level, so we don't need to check
            provision = models.Provision.objects.create(
                template=temp,
                causing_reservation=reservation,  # we set a causing reservation as informativ, but provisions should always check if they
                # are linked to a reservation before they are deleted.
            )
            link(provision, reservation)
            provisions.append(provision)

    return provisions


def create_reservation_for_dependency(
    dependency: rimodels.DependencyInputModel, waiter: models.Waiter
):
    """Creates a reservation for a dependency."""

    node_id = dependency.node

    reservation = models.Reservation.objects.create(
        node=dependency.node,
        waiter=waiter,
    )

    link_or_linkcreate_provisions_for_dependency(dependency, reservation)





def schedule_provision(provision: models.Provision):
    """This should schedule a provision, and all of its dependencies"""

    for dependency in provision.template.dependencies.all():
        if dependency.node:
            # We are creating all of the reservations for the dependencies.
            waiter, _ = models.Waiter.objects.get_or_create(
                registry=provision.agent.registry, instance_id=provision.agent.instance_id, defaults=dict(name="default")
            )

            res, _ = models.Reservation.objects.update_or_create(
                reference=dependency.reference,
                node=dependency.node,
                waiter=waiter,
                defaults=dict(
                    title=dependency.reference,
                    binds=dependency.binds,
                    causing_provision=provision,
                    causing_dependency=dependency,
                ),
            )

            schedule_reservation(res)

        else:
            raise NotImplementedError(
                "No node specified. Template reservation not implemented yet."
            )
        
    return activate_provision(provision)
        
            


def schedule_reservation(reservation: models.Reservation):
    forwards = []
    linked_provisions = []

    binds = (
        rimodels.BindsInputModel(**reservation.binds)
        if reservation.binds
        else rimodels.BindsInputModel()
    )

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


                for dependency in template.dependencies.all():

                    waiter, _ = models.Waiter.objects.get_or_create(
                        registry=template.agent.registry, instance_id=template.agent.instance_id, defaults=dict(name="default")
                    )

                    res, _ = models.Reservation.objects.update_or_create(
                            reference=dependency.reference,
                            node=models.Node.objects.get(hash=dependency.initial_hash) if dependency.initial_hash else None,
                            waiter=waiter,
                            defaults=dict(
                                title=dependency.reference,
                                binds=dependency.binds,
                                causing_provision=prov,
                                causing_dependency=dependency,
                            ),
                    )

                    schedule_reservation(res)




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






