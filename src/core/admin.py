from django.contrib import admin
# Cambiamos los nombres viejos por los nuevos
from .models import PerfilPaciente, Medicamento, EventoCalendario, FotoDocumento, DatoMedicion

# Registramos los nuevos modelos para que aparezcan en el panel de control
admin.site.register(PerfilPaciente)
admin.site.register(Medicamento)
admin.site.register(EventoCalendario)
admin.site.register(FotoDocumento)
admin.site.register(DatoMedicion)