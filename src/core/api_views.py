from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from .models import PerfilPaciente, Medicamento, EventoCalendario
from .serializers import (
    PerfilPacienteSerializer,
    MedicamentoSerializer,
    EventoCalendarioSerializer,
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