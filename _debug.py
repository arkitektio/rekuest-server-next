import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rekuest.settings')
django.setup()

from rekuest_core.objects.types import SearchAssignWidget, Port

# Check if Port's children field (also uses LazyType) resolves correctly
port_defn = Port.__strawberry_definition__
for f in port_defn.fields:
    if f.name in ('children', 'filters', 'assign_widget'):
        print(f"Port.{f.name}: {f.type!r}")

# Check SearchAssignWidget
sw_defn = SearchAssignWidget.__strawberry_definition__
for f in sw_defn.fields:
    print(f"SearchAssignWidget.{f.name}: {f.type!r}")
