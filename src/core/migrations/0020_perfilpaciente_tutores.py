from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_alter_fotodocumento_imagen'),
    ]

    operations = [
        # Paso 1: agregar el campo ManyToMany nuevo
        migrations.AddField(
            model_name='perfilpaciente',
            name='tutores',
            field=models.ManyToManyField(
                to='auth.User',
                related_name='pacientes_vinculados',
                blank=True,
                verbose_name='Tutores asignados',
            ),
        ),
        # Nota: el campo 'tutor' (ForeignKey) se mantiene por compatibilidad
        # y se migra su valor al M2M en el data migration de abajo
    ]