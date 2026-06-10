from django.db import migrations


def copiar_tutor_a_tutores(apps, schema_editor):
    """Copia el tutor FK existente al nuevo campo M2M tutores"""
    PerfilPaciente = apps.get_model('core', 'PerfilPaciente')
    for perfil in PerfilPaciente.objects.filter(tutor__isnull=False):
        perfil.tutores.add(perfil.tutor)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0020_perfilpaciente_tutores'),
    ]

    operations = [
        migrations.RunPython(copiar_tutor_a_tutores, migrations.RunPython.noop),
    ]