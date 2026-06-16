from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import (
    PerfilPaciente, 
    Medicamento, 
    EventoCalendario, 
    Notificacion, 
    RegistroToma, 
    FotoDocumento,
    PerfilTutor
)

# IMPORTACIÓN DE SERIALIZADORES
from .serializers import (
    PerfilPacienteSerializer,
    MedicamentoSerializer,
    EventoCalendarioSerializer,
    NotificacionSerializer,
    FotoDocumentoSerializer
)


# ========== HELPERS PARA LA API ==========
# Definirlos acá evita problemas de importación circular con views.py

def es_tutor(user):
    """Un usuario es tutor si está autenticado y tiene un PerfilTutor."""
    if not user.is_authenticated:
        return False
    return PerfilTutor.objects.filter(user=user).exists()

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
        return Response({
            'rol': 'cuidador',
            'perfil': {
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
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
    eventos = EventoCalendario.objects.filter(
        paciente=request.user,
        fecha_hora__gte=timezone.now()
    )
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

    # 🛡️ BLINDAJE EXPLÍCITO DE LA API: Si es un tutor, le bloqueamos la acción
    if es_tutor(user):
        return Response(
            {
                'status': 'error', 
                'mensaje': 'Acción denegada: Los tutores no pueden registrar tomas de medicamentos.'
            }, 
            status=status.HTTP_403_FORBIDDEN
        )

    # Si pasa el filtro, procedemos asegurando que el medicamento le pertenece estrictamente al usuario paciente
    med = get_object_or_404(Medicamento, pk=medicamento_id, paciente=user, activo=True)

    if med.stock_actual >= med.dosis_por_toma:
        med.stock_actual = max(0.0, float(med.stock_actual) - float(med.dosis_por_toma))
        med.save()

        # Registrar la toma en el historial
        RegistroToma.objects.create(
            medicamento=med,
            paciente=user,
            cantidad_tomada=med.dosis_por_toma
        )
        return Response({'status': 'ok', 'mensaje': f'Toma de {med.nombre} registrada correctamente.'})
    else:
        return Response(
            {'status': 'error', 'mensaje': 'No hay stock suficiente para registrar esta toma.'}, 
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def subir_foto_api(request):
    """Recibe la imagen de una receta o medición desde la cámara del celular en Flutter"""
    serializer = FotoDocumentoSerializer(data=request.data)
    
    if serializer.is_valid():
        serializer.save(paciente=request.user)
        return Response(
            {'status': 'ok', 'mensaje': 'Documento subido correctamente.', 'data': serializer.data},
            status=status.HTTP_201_CREATED
        )
        
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)