from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0002_stripecustomer'),
    ]

    operations = [
        migrations.AddField(
            model_name='donation',
            name='stripe_checkout_session_id',
            field=models.CharField(blank=True, max_length=100, null=True, unique=True),
        ),
    ]
