# Generated by Django 5.2.3 on 2025-06-29 05:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestiontorneo', '0005_alter_usuariopersonalizado_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usuariopersonalizado',
            name='tipo_usuario',
            field=models.CharField(choices=[('organizador', 'Organizador'), ('arbitro', 'Árbitro'), ('jugador', 'Jugador')], default='jugador', max_length=20),
            preserve_default=False,
        ),
    ]
