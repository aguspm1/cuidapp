from rest_framework import serializers
from django.contrib.auth.models import User
from core.models import PerfilPaciente, Medicamento, EventoCalendario, Notificacion, FotoDocumento


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']

class PerfilPacienteSerializer(serializers.ModelSerializer):
    user = UsuarioSerializer(read_only=True)

    class Meta:
        model = PerfilPaciente
        fields = ['id', 'user', 'fecha_nacimiento', 'grupo_sanguineo', 'alergias',
                  'contacto_emergencia', 'telefono_emergencia', 'medico_cabecera',
                   'obra_social', 'plan', 'numero_afiliado',
                   'requiere_control_presion', 'requiere_control_glucosa', 'requiere_control_peso']
        
class MedicamentoSerializer(serializers.ModelSerializer):
    tiene_stock_bajo   = serializers.BooleanField(read_only=True)
    porcentaje_stock   = serializers.IntegerField(read_only=True)
    tomas_restantes    = serializers.IntegerField(read_only=True)

    class Meta:
        model = Medicamento
        fields = [
            'id', 'nombre', 'tipo_presentacion', 'unidad_medida', 'dosis_por_toma',
            'frecuencia_tipo', 'horario_fijo', 'evento_toma', 'cada_cuantas_horas',
            'duracion_tipo', 'fecha_inicio', 'fecha_fin',
            'stock_actual', 'stock_total', 'umbral_stock_minimo',
            'activo', 'tiene_stock_bajo', 'porcentaje_stock', 'tomas_restantes',
        ]

class EventoCalendarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventoCalendario
        fields = ['id', 'titulo', 'fecha_hora', 'tipo', 'lugar', 'descripcion']

class NotificacionSerializer(serializers.ModelSerializer):
    # Agregamos este campo extra para que Flutter reciba el texto legible (ej: "Recordatorio de Toma")
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)

    class Meta:
        model = Notificacion
        fields = [
            'id', 'tipo', 'tipo_display', 'titulo', 'mensaje', 
            'leida', 'fecha_creacion', 'referencia_id'
        ]

class FotoDocumentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = FotoDocumento
        fields = ['id', 'tipo', 'imagen', 'nota_paciente', 'fecha_subida', 'procesada']
        # Protegemos estos campos para que Flutter no los pueda sobreescribir por error
        read_only_fields = ['fecha_subida', 'procesada']