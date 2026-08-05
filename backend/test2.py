from vendors.models import VendorMasterBasicDetail; print(VendorMasterBasicDetail.objects.all().values('id', 'tenant_id'))
