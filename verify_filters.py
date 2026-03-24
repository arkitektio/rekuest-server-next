import django
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rekuest.settings")
django.setup()

from facade import filters

filter_classes = [
    'TestCaseFilter', 'ResolutionFilter', 'ResolvedDependencyFilter', 'AgentFilter',
    'WaiterFilter', 'FilesystemShelveFilter', 'MemoryShelveFilter', 'FileDrawerFilter',
    'MemoryDrawerFilter', 'ReservationFilter', 'AssignationFilter', 'AssignationEventFilter',
    'TestResultFilter', 'DependencyFilter', 'UserFilter', 'OrganizationFilter',
    'ClientFilter', 'ProtocolFilter', 'ToolboxFilter', 'ShortcutActionFilter',
    'ShortcutFilter', 'HardwareRecordFilter', 'StructurePackageFilter', 'StructureFilter',
    'InterfaceFilter', 'InputInterfaceUsageFilter', 'OutputInterfaceUsageFilter',
    'InputStructureUsageFilter', 'OutputStructureUsageFilter', 'ActionFilter',
    'ImplementationAgentFilter', 'ImplementationActionFilter', 'ImplementationFilter',
]

order_classes = [
    'AssignationOrder', 'AssignationEventOrder', 'UserOrder', 'OrganizationOrder',
    'ClientOrder', 'AgentOrder', 'ActionOrder', 'ProtocolOrder', 'ShortcutOrder',
    'ToolboxOrder', 'MemoryShelveOrder', 'ImplementationOrder',
]

for cls in filter_classes:
    obj = getattr(filters, cls)
    assert hasattr(obj, '__strawberry_definition__'), f'{cls} missing strawberry definition'
    fields = obj.__strawberry_definition__.fields
    print(f'  OK: {cls} ({len(fields)} fields)')

for cls in order_classes:
    obj = getattr(filters, cls)
    assert hasattr(obj, '__strawberry_definition__'), f'{cls} missing strawberry definition'
    print(f'  OK: {cls} (order)')

print(f'\n=== All {len(filter_classes)} filter classes and {len(order_classes)} order classes verified ===')
