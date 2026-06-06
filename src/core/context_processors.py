from .models import PerfilPaciente

def rol_usuario(request):
    """
    Inyecta 'usuario_es_tutor' en todos los templates.

    Lógica robusta:
    - Tiene PerfilPaciente propio  → es paciente/anciano
    - No tiene PerfilPaciente propio → es tutor
    (un tutor nunca debería tener PerfilPaciente propio si el registro funciona bien)
    """
    if not request.user.is_authenticated:
        return {'usuario_es_tutor': False}

    tiene_perfil_propio = PerfilPaciente.objects.filter(user=request.user).exists()
    es_tutor = not tiene_perfil_propio

    return {'usuario_es_tutor': es_tutor}