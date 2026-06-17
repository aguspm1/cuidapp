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
    fecha_inicio = serializers.DateField(format="%Y-%m-%d", allow_null=True)
    fecha_fin = serializers.DateField(format="%Y-%m-%d", allow_null=True)
    
    # 💡 DOBLE BLINDAJE: Mandamos el array moderno y mantenemos el string viejo por si las moscas
    horarios = serializers.SerializerMethodField()
    horario_fijo = serializers.SerializerMethodField()
    
    presentacion_display = serializers.CharField(source='get_tipo_presentacion_display', read_only=True)
    frecuencia_display = serializers.CharField(source='get_frecuencia_tipo_display', read_only=True)

    class Meta:
        model = Medicamento
        fields = [
            'id', 'nombre', 'tipo_presentacion', 'presentacion_display',
            'unidad_medida', 'unidad_medida', 'dosis_por_toma',
            'frecuencia_tipo', 'frecuencia_display',
            'horarios', 'horario_fijo', 'evento_toma', 'cada_cuantas_horas', 
            'duracion_tipo', 'fecha_inicio', 'fecha_fin',
            'stock_actual', 'stock_total', 'umbral_stock_minimo',
            'activo', 'tiene_stock_bajo', 'porcentaje_stock', 'tomas_restantes',
        ]

    # Devuelve un array nativo: ["08:00", "14:00"]
    def get_horarios(self, obj):
        return [h.hora.strftime("%H:%M") for h in obj.horarios.all()]

    def get_horario_fijo(self, obj):
        return ", ".join([h.hora.strftime("%H:%M") for h in obj.horarios.all()])

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
    imagen_url = serializers.SerializerMethodField()
    
    class Meta:
        model = FotoDocumento
        fields = ['id', 'tipo', 'imagen', 'imagen_url', 'nota_paciente', 'fecha_subida', 'procesada']
        # Protegemos estos campos para que Flutter no los pueda sobreescribir por error
        read_only_fields = ['fecha_subida', 'procesada']
    
    def get_imagen_url(self, obj):
        request = self.context.get('request')
        if obj.imagen and request:
            return request.build_absolute_uri(obj.imagen.url)
        return None