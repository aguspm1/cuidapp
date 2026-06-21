from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.utils import timezone

#Agrego los datos del dispositivo al final 

from .models import (
    PerfilPaciente, 
    Medicamento, 
    EventoCalendario, 
    Notificacion, 
    RegistroToma, 
    FotoDocumento,
    PerfilTutor,
    DatoDispositivo,
    Mensaje,
    DatoMedicion
)

# IMPORTACIÓN DE SERIALIZADORES
from .serializers import (
    PerfilPacienteSerializer,
    MedicamentoSerializer,
    EventoCalendarioSerializer,
    NotificacionSerializer,
    FotoDocumentoSerializer,
    DatoDispositivoSerializer,
    MensajeSerializer,
    DatoMedicionSerializer
)


# ========== HELPERS PARA LA API ==========

def es_tutor(user):
    """Un usuario es tutor si está autenticado y tiene un PerfilTutor o califica como tal."""
    if not user.is_authenticated:
        return False
    if PerfilTutor.objects.filter(user=user).exists():
        return True
    if not PerfilPaciente.objects.filter(user=user).exists():
        PerfilTutor.objects.get_or_create(user=user)
        return True
    return False

def es_paciente(user):
    """Un usuario es paciente si está autenticado y tiene un PerfilPaciente."""
    if not user.is_authenticated:
        return False
    return PerfilPaciente.objects.filter(user=user).exists()


# =======================================================
# ========== ENDPOINTS DE LA API (FLUTTER) ===========
# =======================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    user = request.user
    if es_paciente(user):
        perfil = PerfilPaciente.objects.get(user=user)
        return Response({
            'rol': 'paciente',
            'perfil': PerfilPacienteSerializer(perfil).data,
        })
    elif es_tutor(user):
        tutor_perfil = PerfilTutor.objects.filter(user=user).first()
        return Response({
            'rol': 'cuidador',
            'perfil': {
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'telefono': tutor_perfil.telefono if tutor_perfil else '',
                'parentesco': tutor_perfil.parentesco if tutor_perfil else '',
            }
        })
    return Response({'status': 'error', 'mensaje': 'Usuario incompleto o sin rol asignado.'}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mis_medicamentos(request):
    medicamentos = Medicamento.objects.filter(
        paciente=request.user,
        activo=True
    )
    return Response(MedicamentoSerializer(medicamentos, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mis_eventos(request):
    # 💡 MEJORA DE UX: Traemos los eventos desde el inicio del día de hoy local.
    # Así el paciente puede ver turnos matutinos aunque consulte la app por la tarde.
    ahora_local = timezone.localtime(timezone.now())
    inicio_hoy = ahora_local.replace(hour=0, minute=0, second=0, microsecond=0)
    
    eventos = EventoCalendario.objects.filter(
        paciente=request.user,
        fecha_hora__gte=inicio_hoy
    ).order_by('fecha_hora')
    
    return Response(EventoCalendarioSerializer(eventos, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mis_notificaciones(request):
    """Devuelve al celular las notificaciones sin leer del paciente activo"""
    notificaciones = Notificacion.objects.filter(
        usuario=request.user, 
        leida=False
    )
    return Response(NotificacionSerializer(notificaciones, many=True).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mis_pacientes_api(request):
    """Devuelve la lista de pacientes vinculados al tutor autenticado."""
    user = request.user
    if not es_tutor(user):
        return Response(
            {'status': 'error', 'mensaje': 'Solo los cuidadores pueden acceder a esta lista.'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Buscamos los pacientes que tienen a este usuario en su lista ManyToMany 'tutores'
    pacientes = PerfilPaciente.objects.filter(tutores=user)
    
    return Response(PerfilPacienteSerializer(pacientes, many=True, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def marcar_notificaciones_api(request):
    """Permite que Flutter avise que el usuario ya abrió la campanita"""
    Notificacion.objects.filter(usuario=request.user, leida=False).update(leida=True)
    return Response({'status': 'ok', 'mensaje': 'Notificaciones marcadas como leídas'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def registrar_toma_api(request, medicamento_id):
    """Recibe la confirmación desde Flutter de que el paciente tomó el remedio"""
    user = request.user

    if es_tutor(user):
        return Response(
            {
                'status': 'error', 
                'mensaje': 'Acción denegada: Los tutores no pueden registrar tomas de medicamentos.'
            }, 
            status=status.HTTP_403_FORBIDDEN
        )

    med = get_object_or_404(Medicamento, pk=medicamento_id, paciente=user, activo=True)

    # ── Restricción: no se puede tomar dos veces antes de hora ──────────
    if not med.puede_tomar_ahora:
        return Response(
            {
                'status': 'error',
                'mensaje': f'Ya registraste esta toma. La próxima es a las {med.proxima_toma_texto}.'
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    if med.stock_actual < med.dosis_por_toma:
        return Response(
            {'status': 'error', 'mensaje': 'No hay stock suficiente para registrar esta toma.'}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    med.stock_actual = max(0.0, float(med.stock_actual) - float(med.dosis_por_toma))
    med.save()

    RegistroToma.objects.create(
        medicamento=med,
        paciente=user,
        cantidad_tomada=med.dosis_por_toma
    )

    # ── Notificación de confirmación para el paciente ────────────────────
    hora_actual = timezone.localtime(timezone.now()).strftime('%H:%M')
    Notificacion.objects.create(
        usuario=user,
        tipo='medicacion',
        titulo='Toma registrada',
        mensaje=f'Registraste la toma de {med.nombre} a las {hora_actual}.',
        referencia_id=med.id
    )

    # ── Notificación para los cuidadores/tutores vinculados ──────────────
    perfil = PerfilPaciente.objects.filter(user=user).first()
    if perfil:
        nombre_paciente = user.get_full_name() or user.username
        for tutor in perfil.tutores.all():
            Notificacion.objects.create(
                usuario=tutor,
                tipo='medicacion',
                titulo=f'{nombre_paciente} tomó su medicación',
                mensaje=f'Se registró la toma de {med.nombre} a las {hora_actual}.',
                referencia_id=med.id
            )

    return Response({'status': 'ok', 'mensaje': f'Toma de {med.nombre} registrada correctamente.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def subir_foto_api(request):
    """Recibe la imagen de una receta o medición desde la cámara del celular en Flutter"""
    serializer = FotoDocumentoSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        serializer.save(paciente=request.user)
        return Response(
            {'status': 'ok', 'mensaje': 'Documento subido correctamente.', 'data': serializer.data},
            status=status.HTTP_201_CREATED
        )
        
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#Agrego datos de dispositivo
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def registrar_dato_dispositivo(request):
    dato = DatoDispositivo.objects.create(
        paciente      = request.user,
        bateria       = request.data.get('bateria', 0),
        tipo_conexion = request.data.get('tipo_conexion', ''),
        latitud       = request.data.get('latitud'),
        longitud      = request.data.get('longitud'),
    )
    return Response({'ok': True, 'id': dato.id}, status=status.HTTP_201_CREATED)


# =======================================================
# ===== ENDPOINTS PARA QUE EL CUIDADOR VEA A UN PACIENTE =====
# =======================================================

def _validar_tutor_de(request, paciente_id):
    """Devuelve el perfil del paciente si request.user es uno de sus tutores, o None si no tiene permiso."""
    perfil = PerfilPaciente.objects.filter(user_id=paciente_id).first()
    if not perfil:
        return None
    if not perfil.tutores.filter(id=request.user.id).exists():
        return None
    return perfil


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detalle_paciente_dispositivo(request, paciente_id):
    """Último dato de batería/conexión/ubicación de un paciente puntual."""
    perfil = _validar_tutor_de(request, paciente_id)
    if not perfil:
        return Response({'status': 'error', 'mensaje': 'No autorizado.'}, status=status.HTTP_403_FORBIDDEN)

    dato = DatoDispositivo.objects.filter(paciente_id=paciente_id).order_by('-fecha_registro').first()
    if not dato:
        return Response({'status': 'sin_datos', 'mensaje': 'Todavía no hay datos de este paciente.'})

    return Response(DatoDispositivoSerializer(dato).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detalle_paciente_fotos(request, paciente_id):
    """Fotos de mediciones/recetas que subió un paciente puntual."""
    perfil = _validar_tutor_de(request, paciente_id)
    if not perfil:
        return Response({'status': 'error', 'mensaje': 'No autorizado.'}, status=status.HTTP_403_FORBIDDEN)

    fotos = FotoDocumento.objects.filter(paciente_id=paciente_id)
    return Response(FotoDocumentoSerializer(fotos, many=True, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def marcar_foto_revisada(request, foto_id):
    """El cuidador marca un documento/foto como ya revisado desde la app."""
    foto = get_object_or_404(FotoDocumento, pk=foto_id)
    perfil = _validar_tutor_de(request, foto.paciente_id)
    if not perfil:
        return Response({'status': 'error', 'mensaje': 'No autorizado.'}, status=status.HTTP_403_FORBIDDEN)

    foto.procesada = True
    nota = (request.data.get('nota') or '').strip()
    if nota:
        foto.nota_tutor = nota
    foto.save()

    return Response(FotoDocumentoSerializer(foto, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detalle_paciente_medicamentos(request, paciente_id):
    """Medicamentos activos de un paciente puntual (para que el tutor los vea)."""
    perfil = _validar_tutor_de(request, paciente_id)
    if not perfil:
        return Response({'status': 'error', 'mensaje': 'No autorizado.'}, status=status.HTTP_403_FORBIDDEN)

    medicamentos = Medicamento.objects.filter(paciente_id=paciente_id, activo=True)
    return Response(MedicamentoSerializer(medicamentos, many=True).data)


class EventoCalendarioViewSet(viewsets.ModelViewSet):
    serializer_class = EventoCalendarioSerializer

    def get_queryset(self):
        paciente_id = self.request.query_params.get('paciente_id', None)
        if paciente_id:
            return EventoCalendario.objects.filter(paciente__id=paciente_id).order_by('fecha_hora')
        return EventoCalendario.objects.filter(paciente=self.request.user).order_by('fecha_hora')

    def perform_create(self, serializer):
        # Si quien crea el turno es un tutor, el evento queda a nombre del paciente
        # que esté viendo (paciente_id en query params); si no, es el propio usuario.
        paciente_id = self.request.query_params.get('paciente_id') or self.request.data.get('paciente_id')
        paciente_target = self.request.user
        if paciente_id:
            paciente_target = get_object_or_404(PerfilPaciente, user_id=paciente_id).user

        evento = serializer.save(paciente=paciente_target)
        self._notificar_evento(evento, creado=True)
        return evento

    def perform_update(self, serializer):
        evento = serializer.save()
        self._notificar_evento(evento, creado=False)
        return evento

    def _notificar_evento(self, evento, creado=True):
        """Avisa al paciente y a sus cuidadores que hay un turno nuevo o modificado."""
        accion = 'Nuevo turno agendado' if creado else 'Turno actualizado'
        fecha_str = timezone.localtime(evento.fecha_hora).strftime('%d/%m a las %H:%M')

        Notificacion.objects.create(
            usuario=evento.paciente,
            tipo='evento',
            titulo=accion,
            mensaje=f'{evento.titulo} - {fecha_str}',
            referencia_id=evento.id
        )

        perfil = PerfilPaciente.objects.filter(user=evento.paciente).first()
        if perfil:
            nombre_paciente = evento.paciente.get_full_name() or evento.paciente.username
            for tutor in perfil.tutores.all():
                Notificacion.objects.create(
                    usuario=tutor,
                    tipo='evento',
                    titulo=f'{accion} para {nombre_paciente}',
                    mensaje=f'{evento.titulo} - {fecha_str}',
                    referencia_id=evento.id
                )


# =======================================================
# ===================== CHAT ==========================
# =======================================================

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def chat_mensajes(request, otro_id):
    """
    Hilo de chat entre un paciente y un cuidador puntual.
    - Si quien llama es el paciente: otro_id = id del cuidador.
    - Si quien llama es el cuidador: otro_id = id del paciente.
    GET: trae el historial y marca como leídos los mensajes recibidos.
    POST: envía un mensaje nuevo (campo 'texto').
    """
    user = request.user

    if es_paciente(user):
        paciente_id = user.id
        cuidador_id = otro_id
        perfil = PerfilPaciente.objects.filter(user=user).first()
        if not perfil or not perfil.tutores.filter(id=cuidador_id).exists():
            return Response({'status': 'error', 'mensaje': 'No autorizado.'}, status=status.HTTP_403_FORBIDDEN)
    elif es_tutor(user):
        paciente_id = otro_id
        cuidador_id = user.id
        perfil = PerfilPaciente.objects.filter(user_id=paciente_id).first()
        if not perfil or not perfil.tutores.filter(id=user.id).exists():
            return Response({'status': 'error', 'mensaje': 'No autorizado.'}, status=status.HTTP_403_FORBIDDEN)
    else:
        return Response({'status': 'error', 'mensaje': 'Rol no reconocido.'}, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'POST':
        texto = (request.data.get('texto') or '').strip()
        if not texto:
            return Response({'status': 'error', 'mensaje': 'El mensaje no puede estar vacío.'}, status=status.HTTP_400_BAD_REQUEST)

        mensaje = Mensaje.objects.create(
            paciente_id=paciente_id,
            cuidador_id=cuidador_id,
            remitente=user,
            texto=texto
        )

        # ── Avisamos al destinatario con el sistema de notificaciones existente ──
        destinatario_id = cuidador_id if user.id == paciente_id else paciente_id
        nombre_remitente = user.get_full_name() or user.username
        Notificacion.objects.create(
            usuario_id=destinatario_id,
            tipo='mensaje',
            titulo=f'Nuevo mensaje de {nombre_remitente}',
            mensaje=texto[:140],
            referencia_id=user.id
        )

        return Response(
            MensajeSerializer(mensaje, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )

    # ── GET: historial completo del hilo ──────────────────────────────
    mensajes = Mensaje.objects.filter(
        paciente_id=paciente_id,
        cuidador_id=cuidador_id
    ).order_by('fecha_envio')

    # Marcamos como leídos los mensajes que no escribió el usuario actual
    mensajes.exclude(remitente=user).filter(leido=False).update(leido=True)

    return Response(MensajeSerializer(mensajes, many=True, context={'request': request}).data)

from .models import DatoMedicion
from .serializers import DatoMedicionSerializer

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def extraer_dato_medicion(request, foto_id):
    """El cuidador extrae un dato numérico (presión/glucosa) a partir de una foto subida por el abuelo."""
    foto = get_object_or_404(FotoDocumento, pk=foto_id)
    perfil = _validar_tutor_de(request, foto.paciente_id)
    
    if not perfil:
        return Response({'status': 'error', 'mensaje': 'No autorizado.'}, status=status.HTTP_403_FORBIDDEN)

    tipo = request.data.get('tipo')
    valor_1 = request.data.get('valor_1')
    valor_2 = request.data.get('valor_2') # Opcional (ej. presión diastólica)
    
    if not tipo or not valor_1:
        return Response({'status': 'error', 'mensaje': 'El tipo y el valor 1 son obligatorios.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        DatoMedicion.objects.create(
            paciente_id=foto.paciente_id,
            foto=foto,
            tipo=tipo,
            valor_1=float(valor_1),
            valor_2=float(valor_2) if valor_2 else None,
            observaciones=request.data.get('observaciones', '')
        )
        
        # Opcional: Marcar la foto como procesada automáticamente
        foto.procesada = True
        foto.save()
        
        return Response({'status': 'ok', 'mensaje': 'Medición guardada correctamente.'})
    except ValueError:
        return Response({'status': 'error', 'mensaje': 'Los valores deben ser numéricos.'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def historial_mediciones_paciente(request, paciente_id):
    """Devuelve el historial numérico para armar los gráficos."""
    perfil = _validar_tutor_de(request, paciente_id)
    if not perfil:
        return Response({'status': 'error', 'mensaje': 'No autorizado.'}, status=status.HTTP_403_FORBIDDEN)

    mediciones = DatoMedicion.objects.filter(paciente_id=paciente_id).order_by('fecha_registro')
    return Response(DatoMedicionSerializer(mediciones, many=True).data)