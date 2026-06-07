from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_alter_medicamento_cada_cuantas_horas_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='fotodocumento',
            old_name='comentario_ana',
            new_name='nota_paciente',
        ),
        migrations.RenameField(
            model_name='fotodocumento',
            old_name='comentario_luis',
            new_name='nota_tutor',
        ),
    ]