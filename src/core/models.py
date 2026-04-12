from django.db import models
from django.contrib.auth.models import User

# --- 1. PERFIL DE PACIENTE (La ficha que Luis edita) ---
class PerfilPaciente(models.Model):
    # Relación con el User que es el paciente (Ana)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil_medico')
    
    # El tutor asignado (Luis)
    tutor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='pacientes_a_cargo')
    
    # Datos biométricos y médicos (Cargados por Luis)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    grupo_sanguineo = models.CharField(max_length=5, blank=True)
    alergias = models.TextField(blank=True, verbose_name="Alergias Conocidas")
    contacto_emergencia = models.CharField(max_length=100, blank=True)
    telefono_emergencia = models.CharField(max_length=20, blank=True)
    medico_cabecera = models.CharField(max_length=100, blank=True)

    # Configuración de Controles (Lo que Ana debe hacerse)
    requiere_control_presion = models.BooleanField(default=False)
    requiere_control_glucosa = models.BooleanField(default=False)
    requiere_control_peso = models.BooleanField(default=False)

    def __str__(self):
        return f"Perfil de {self.user.username} (Tutor: {self.tutor.username if self.tutor else 'Sin asignar'})"


# --- 2. MEDICACIÓN Y CALENDARIO 
class Medicamento(models.Model):
    paciente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='medicamentos')
    nombre = models.CharField(max_length=100)
    frecuencia = models.CharField(max_length=100, null=True, blank=True)
    stock_actual = models.IntegerField(default=0)
    stock_total = models.IntegerField(default=0)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} - {self.paciente.username}"

class EventoCalendario(models.Model):
    paciente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='eventos')
    titulo = models.CharField(max_length=200)
    fecha_hora = models.DateTimeField()
    descripcion = models.TextField(blank=True)

    def __str__(self):
        return f"{self.titulo} - {self.fecha_hora.date()}"


# --- 3. GESTIÓN DE MEDICIONES (Fotos y Datos) ---

class FotoDocumento(models.Model):
    """ Documentos fotográficos que Ana sube: mediciones, recetas, indicaciones, etc. """
    TIPO_CHOICES = [
        ('medicion', 'Foto de Medición'),
        ('receta', 'Receta Médica'),
        ('indicacion', 'Indicación Médica'),
        ('otro', 'Otro Documento'),
    ]
    
    paciente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fotos_documentos')
    imagen = models.ImageField(upload_to='documentos/fotos/')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='medicion')
    fecha_subida = models.DateTimeField(auto_now_add=True)
    procesada = models.BooleanField(default=False) # True cuando Luis revisa/procesa
    comentario_ana = models.CharField(max_length=255, blank=True)
    comentario_luis = models.CharField(max_length=255, blank=True) # Lo que Luis anota

    class Meta:
        verbose_name_plural = "Documentos (Fotos)"
        ordering = ['-fecha_subida']

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.paciente.username} ({self.fecha_subida.date()})"

# Compatibilidad hacia atrás
FotoMedicion = FotoDocumento

class DatoMedicion(models.Model):
    """ Datos numéricos que Luis carga basándose en la foto de Ana """
    TIPO_CHOICES = [
        ('presion', 'Presión Arterial'),
        ('glucosa', 'Glucosa'),
        ('peso', 'Peso'),
    ]
    paciente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='datos_mediciones')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    
    # Valor principal (Sistólica para presión, o el peso/glucosa)
    valor_1 = models.FloatField() 
    # Valor secundario (Diastólica para presión)
    valor_2 = models.FloatField(null=True, blank=True) 
    
    fecha_registro = models.DateTimeField(auto_now_add=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        ordering = ['-fecha_registro']
        verbose_name_plural = "Datos de Mediciones"

    def __str__(self):
        return f"{self.get_tipo_display()}: {self.valor_1}/{self.valor_2 if self.valor_2 else ''} ({self.paciente.username})"