# Generated for KIKI AI Clean-Room Reset

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_kikiauditlog'),
    ]

    operations = [
        migrations.DeleteModel(
            name='KikiAuditLog',
        ),
    ]
