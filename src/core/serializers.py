from rest_framework import serializers
from django.contrib.auth.models import User
from core.models import PerfilPaciente, Medicamento, EventoCalendario, Notificacion, FotoDocumento, DatoDispositivo, Mensaje, DatoMedicion

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']

class PerfilPacienteSerializer(serializers.ModelSerializer):
    user = UsuarioSerializer(read_only=True)
    tutores_info = serializers.SerializerMethodField()
    tutor_emergencia_id = serializers.IntegerField(read_only=True, allow_null=True)
    tiene_mensaje_no_leido = serializers.SerializerMethodField()

    class Meta:
        model = PerfilPaciente
        fields = ['id', 'user', 'fecha_nacimiento', 'grupo_sanguineo', 'alergias',
                  'contacto_emergencia', 'telefono_emergencia', 'medico_cabecera',
                   'obra_social', 'plan', 'numero_afiliado',
                   'requiere_control_presion', 'requiere_control_glucosa', 'requiere_control_peso',
                   'tutores_info', 'tutor_emergencia_id', 'tiene_mensaje_no_leido']

    def get_tutores_info(self, obj):
        resultado = []
        for tutor in obj.tutores.all():
            perfil_tutor = getattr(tutor, 'perfil_tutor', None)
            resultado.append({
                'id': tutor.id,
                'nombre': tutor.get_full_name() or tutor.username,
                'telefono': perfil_tutor.telefono if perfil_tutor else '',
                'parentesco': perfil_tutor.parentesco if perfil_tutor else '',
                'es_emergencia': obj.tutor_emergencia_id == tutor.id,
            })
        return resultado

    def get_tiene_mensaje_no_leido(self, obj):
        """
        Solo tiene sentido cuando quien pide el serializer es un cuidador
        viendo la lista de sus abuelos a cargo (mis_pacientes_api).
        """
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return Mensaje.objects.filter(
            paciente=obj.user,
            cuidador=request.user,
            leido=False
        ).exclude(remitente=request.user).exists()
        
class MedicamentoSerializer(serializers.ModelSerializer):
    tiene_stock_bajo   = serializers.BooleanField(read_only=True)
    porcentaje_stock   = serializers.IntegerField(read_only=True)
    tomas_restantes    = serializers.IntegerField(read_only=True)
    puede_tomar_ahora  = serializers.BooleanField(read_only=True)
    proxima_toma_texto = serializers.CharField(read_only=True)
    ultima_toma        = serializers.SerializerMethodField()
    fecha_inicio = serializers.DateField(format="%Y-%m-%d", allow_null=True)
    fecha_fin = serializers.DateField(format="%Y-%m-%d", allow_null=True)

    horarios = serializers.SerializerMethodField()
    horario_fijo = serializers.SerializerMethodField()

    presentacion_display = serializers.CharField(source='get_tipo_presentacion_display', read_only=True)
    frecuencia_display = serializers.CharField(source='get_frecuencia_tipo_display', read_only=True)

    class Meta:
        model = Medicamento
        fields = [
            'id', 'nombre', 'tipo_presentacion', 'presentacion_display',
            'unidad_medida', 'dosis_por_toma',
            'frecuencia_tipo', 'frecuencia_display',
            'horarios', 'horario_fijo', 'evento_toma', 'cada_cuantas_horas',
            'duracion_tipo', 'fecha_inicio', 'fecha_fin',
            'stock_actual', 'stock_total', 'umbral_stock_minimo',
            'activo', 'tiene_stock_bajo', 'porcentaje_stock', 'tomas_restantes',
            'puede_tomar_ahora', 'proxima_toma_texto', 'ultima_toma',
        ]

    def get_horarios(self, obj):
        return [h.hora.strftime("%H:%M") for h in obj.horarios.all()]

    def get_horario_fijo(self, obj):
        return ", ".join([h.hora.strftime("%H:%M") for h in obj.horarios.all()])

    def get_ultima_toma(self, obj):
        ultimo = obj.registros_toma.first()
        return ultimo.fecha_hora.isoformat() if ultimo else None

class EventoCalendarioSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    class Meta:
        model = EventoCalendario
        fields = ['id', 'titulo', 'fecha_hora', 'descripcion', 'tipo', 'tipo_display', 'lugar']
        
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


class DatoDispositivoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatoDispositivo
        fields = ['id', 'bateria', 'tipo_conexion', 'latitud', 'longitud', 'fecha_registro']


class MensajeSerializer(serializers.ModelSerializer):
    es_mio = serializers.SerializerMethodField()
    remitente_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Mensaje
        fields = ['id', 'texto', 'fecha_envio', 'leido', 'remitente_id', 'es_mio', 'remitente_nombre']

    def get_es_mio(self, obj):
        request = self.context.get('request')
        return bool(request and request.user.is_authenticated and obj.remitente_id == request.user.id)

    def get_remitente_nombre(self, obj):
        return obj.remitente.get_full_name() or obj.remitente.username

class DatoMedicionSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    
    class Meta:
        model = DatoMedicion
        fields = ['id', 'tipo', 'tipo_display', 'valor_1', 'valor_2', 'fecha_registro', 'observaciones', 'foto']