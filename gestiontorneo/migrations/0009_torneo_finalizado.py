# Generated by Django 5.2.3 on 2025-06-29 15:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestiontorneo', '0008_alter_resultado_partido'),
    ]

    operations = [
        migrations.AddField(
            model_name='torneo',
            name='finalizado',
            field=models.BooleanField(default=False),
        ),
    ]
