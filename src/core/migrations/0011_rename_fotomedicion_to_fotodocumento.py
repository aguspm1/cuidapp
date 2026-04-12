# Generated migration for renaming FotoMedicion to FotoDocumento and adding new fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_alter_medicamento_frecuencia'),
    ]

    operations = [
        # Rename the table from fotomedicion to fotodocumento
        migrations.RenameModel(
            old_name='FotoMedicion',
            new_name='FotoDocumento',
        ),
        # Add the tipo field with default 'medicion' for existing records
        migrations.AddField(
            model_name='fotodocumento',
            name='tipo',
            field=models.CharField(
                choices=[('medicion', 'Foto de Medición'), ('receta', 'Receta Médica'), ('indicacion', 'Indicación Médica'), ('otro', 'Otro Documento')],
                default='medicion',
                max_length=20
            ),
        ),
        # Add comentario_luis field for tutor notes
        migrations.AddField(
            model_name='fotodocumento',
            name='comentario_luis',
            field=models.CharField(blank=True, max_length=255),
        ),
        # Update the ordering in Meta
        migrations.AlterModelOptions(
            name='fotodocumento',
            options={'ordering': ['-fecha_subida'], 'verbose_name_plural': 'Documentos (Fotos)'},
        ),
    ]
