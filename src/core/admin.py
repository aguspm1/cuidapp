from django.contrib import admin
from .models import PerfilPaciente, Medicamento, RegistroToma, FotoDocumento, DatoMedicion, EventoCalendario

@admin.register(PerfilPaciente)
class PerfilPacienteAdmin(admin.ModelAdmin):
    list_display = ('user', 'tutor', 'fecha_nacimiento', 'obra_social')
    search_fields = ('user__username', 'tutor__username')
    list_filter = ('requiere_control_presion', 'requiere_control_glucosa', 'requiere_control_peso')

@admin.register(Medicamento)
class MedicamentoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'paciente', 'tipo_presentacion', 'dosis_por_toma', 'stock_actual', 'activo')
    list_filter = ('tipo_presentacion', 'duracion_tipo', 'activo')
    search_fields = ('nombre', 'paciente__username')

@admin.register(RegistroToma)
class RegistroTomaAdmin(admin.ModelAdmin):
    list_display = ('medicamento', 'paciente', 'fecha_hora', 'cantidad_tomada')
    list_filter = ('fecha_hora', 'medicamento__nombre')
    search_fields = ('paciente__username', 'medicamento__nombre')
    readonly_fields = ('fecha_hora',)

@admin.register(EventoCalendario)
class EventoCalendarioAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'paciente', 'fecha_hora', 'tipo', 'lugar')
    list_filter = ('tipo', 'fecha_hora')
    search_fields = ('paciente__username', 'titulo')

@admin.register(FotoDocumento)
class FotoDocumentoAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'paciente', 'fecha_subida', 'procesada')
    list_filter = ('tipo', 'procesada', 'fecha_subida')
    search_fields = ('paciente__username',)

@admin.register(DatoMedicion)
class DatoMedicionAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'paciente', 'valor_1', 'valor_2')
    list_filter = ('tipo', 'fecha_registro')
    search_fields = ('paciente__username',)