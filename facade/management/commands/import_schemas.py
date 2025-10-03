from django.core.management.base import BaseCommand
from django.conf import settings
from facade import models
import json
import omegaconf
from pydantic import BaseModel
from rekuest_core.inputs.models import StructurePackageInputModel


class StrcuturePackagesParser(BaseModel):
    packages: list[StructurePackageInputModel]


class Command(BaseCommand):
    help = "Creates all configured apps or overwrites them"

    def handle(self, *args, **options):
        

        packages = settings.PACKAGES
        parser = StrcuturePackagesParser(packages=packages)


        for package in parser.packages:

            pack, _ = models.StructurePackage.objects.update_or_create(
                key=package.key.lower(),
                defaults=dict(
                    description=package.description,
                ),
            )
            
            for descriptor in package.descriptors or []:
                models.Descriptor.objects.update_or_create(
                    package=pack,
                    key=descriptor.key.lower(),
                    defaults=dict(
                        description=descriptor.description,
                    ),
                )
            
            for interface in package.interfaces or []:
                models.Interface.objects.update_or_create(
                    package=pack,
                    key=interface.key.lower(),
                    defaults=dict(
                        description=interface.description,
                        default_widget=json.dumps(
                            interface.default_widget.model_dump()
                        )
                        if interface.default_widget
                        else None,
                        default_return_widget=json.dumps(
                            interface.default_return_widget.model_dump()
                        )
                        if interface.default_return_widget
                        else None,
                    ),
                )
                
            for structure in package.structures or []:
                struc, _ = models.Structure.objects.update_or_create(
                    package=pack,
                    key=structure.key.lower(),
                    defaults=dict(
                        description=structure.description,
                        default_widget=json.dumps(
                            structure.default_widget.model_dump()
                        )
                        if structure.default_widget
                        else None,
                        default_return_widget=json.dumps(
                            structure.default_return_widget.model_dump()
                        )
                        if structure.default_return_widget
                        else None,
                    ),
                )
                
                struc.implements.set(
                    models.Interface.objects.filter(
                        key__in=structure.implements or []
                    )
                )
                struc.descriptors.set(
                    models.Descriptor.objects.filter(
                        key__in=structure.descriptors or []
                    )
                )
                
                
            
            
            
            
            
            
            
            
            