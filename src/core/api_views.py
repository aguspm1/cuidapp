from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404

# Modelos
from .models import (
    PerfilPaciente, 
    Medicamento, 
    EventoCalendario, 
    Notificacion, 
    RegistroToma, 
    FotoDocumento
)

# Serializadores
from .serializers import (
    PerfilPacienteSerializer,
    MedicamentoSerializer,
    EventoCalendarioSerializer,
    NotificacionSerializer,
    FotoDocumentoSerializer
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    # Define el rol y da diferentes respuestas
    user = request.user
    try:
        perfil = PerfilPaciente.objects.get(user=user)
        return Response({
            'rol': 'paciente',
            'perfil': PerfilPacienteSerializer(perfil).data,
        })
    except PerfilPaciente.DoesNotExist:
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
    from django.utils import timezone
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
    med = get_object_or_404(Medicamento, pk=medicamento_id, paciente=request.user, activo=True)

    if med.stock_actual >= med.dosis_por_toma:
        # Descontar stock
        med.stock_actual = max(0.0, float(med.stock_actual) - float(med.dosis_por_toma))
        med.save()

        # Registrar la toma en el historial
        RegistroToma.objects.create(
            medicamento=med,
            paciente=request.user,
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
        # Guardamos la foto asignándole el paciente actual automáticamente
        serializer.save(paciente=request.user)
        return Response(
            {'status': 'ok', 'mensaje': 'Documento subido correctamente.', 'data': serializer.data},
            status=status.HTTP_201_CREATED
        )
        
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)