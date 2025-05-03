from django.contrib import admin
from facade import models

# Register your models here.


admin.site.register(models.Action)
admin.site.register(models.HardwareRecord)
admin.site.register(models.Implementation)
admin.site.register(models.Reservation)
admin.site.register(models.Registry)
admin.site.register(models.Waiter)
admin.site.register(models.AssignationEvent)
admin.site.register(models.Agent)
admin.site.register(models.Assignation)
