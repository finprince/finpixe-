from customerportal.models import CustomerCategory; print(CustomerCategory.objects.all().values('id', 'category', 'group', 'subgroup'))
