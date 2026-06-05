from .models import PerfilPaciente
 
def rol_usuario(request):
    """
    Inyecta 'usuario_es_tutor' en todos los templates.
    
    Lógica:
    - Anciano → tiene PerfilPaciente con user=él mismo
    - Tutor   → NO tiene PerfilPaciente propio, pero sí tiene pacientes a cargo
    
    Un usuario es tutor si tiene al menos un paciente a cargo
    Y es paciente si tiene un PerfilPaciente propio
    """
    if request.user.is_authenticated:
        tiene_pacientes  = PerfilPaciente.objects.filter(tutor=request.user).exists()
        tiene_perfil_propio = PerfilPaciente.objects.filter(user=request.user).exists()
 
        # Es tutor si tiene pacientes a cargo (aunque no tenga perfil propio)
        # Es paciente si tiene perfil propio
        # Nota: si alguien tiene ambos (caso raro) se lo trata como tutor
        es_tutor = tiene_pacientes or (not tiene_perfil_propio)
    else:
        es_tutor = False
 
    return {'usuario_es_tutor': es_tutor}
 