from vendors.models import VendorMasterBasicDetail
print(VendorMasterBasicDetail.objects.filter(id=177).values('id', 'tenant_id', 'is_deleted', 'is_active'))
