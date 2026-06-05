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
    obra_social = models.CharField(max_length=100, blank=True, verbose_name="Obra Social")
    plan = models.CharField(max_length=100, blank=True, verbose_name="Plan")
    numero_afiliado = models.CharField(max_length=50, blank=True, verbose_name="Número de Afiliado")

    # Configuración de Controles (Lo que Ana debe hacerse)
    requiere_control_presion = models.BooleanField(default=False)
    requiere_control_glucosa = models.BooleanField(default=False)
    requiere_control_peso = models.BooleanField(default=False)

    def __str__(self):
        return f"Perfil de {self.user.username} (Tutor: {self.tutor.username if self.tutor else 'Sin asignar'})"


# --- 2. MEDICACIÓN Y CALENDARIO 
class Medicamento(models.Model):
    PRESENTACION_CHOICES = [
        ('comprimido', 'Comprimido'),
        ('gota', 'Gotas'),
        ('liquido', 'Líquido'),
        ('inyectable', 'Inyectable'),
        ('otro', 'Otro'),
    ]
    UNIDAD_CHOICES = [
        ('unidades', 'Unidades'),
        ('gotas', 'Gotas'),
        ('ml', 'ml'),
        ('mg', 'mg'),
    ]

    paciente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='medicamentos')
    nombre = models.CharField(max_length=100)
    tipo_presentacion = models.CharField(max_length=20, choices=PRESENTACION_CHOICES, default='comprimido')
    unidad_medida = models.CharField(max_length=20, choices=UNIDAD_CHOICES, default='unidades')
    dosis_por_toma = models.FloatField(default=1)  # 1 comprimido, 15 gotas, 5ml, etc
    
    # Frecuencia
    FRECUENCIA_CHOICES = [
        ('fijo', 'Horario Fijo'),
        ('intervalo', 'Cada X horas'),
        ('evento', 'Relativo a Evento'),
    ]
    TIPO_DURACION_CHOICES = [
        ('cronico', 'Crónico (todos los días)'),
        ('temporal', 'Temporal'),
    ]
    
    frecuencia_tipo = models.CharField(max_length=20, choices=FRECUENCIA_CHOICES, default='fijo')
    horario_fijo = models.CharField(max_length=100, blank=True, help_text="Ej: 08:00 hs")
    evento_toma = models.CharField(max_length=100, blank=True, help_text="Ej: al levantarse, antes de acostarse")
    cada_cuantas_horas = models.IntegerField(default=8, help_text="Solo si frecuencia_tipo='fijo'")
    
    duracion_tipo = models.CharField(max_length=20, choices=TIPO_DURACION_CHOICES, default='cronico')
    fecha_inicio = models.DateField(auto_now_add=True)
    fecha_fin = models.DateField(null=True, blank=True, help_text="Solo si duracion_tipo='temporal'")
    
    # Stock
    stock_actual = models.IntegerField(default=0)
    stock_total = models.IntegerField(default=0, help_text="Cantidad en cada caja estándar")
    umbral_stock_minimo = models.IntegerField(default=5, help_text="Alertar cuando stock <= este valor")
    
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nombre} - {self.paciente.username}"
    
    def tiene_stock_bajo(self):
        return self.stock_actual <= self.umbral_stock_minimo
    
    def tomas_restantes(self):
        """Cuántas tomas completas se pueden dar con stock actual"""
        if self.dosis_por_toma == 0:
            return 0
        return int(self.stock_actual / self.dosis_por_toma)


class RegistroToma(models.Model):
    """Historial inmutable de cada toma registrada"""
    medicamento = models.ForeignKey(Medicamento, on_delete=models.CASCADE, related_name='registros_toma')
    paciente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='registros_toma')
    fecha_hora = models.DateTimeField(auto_now_add=True)
    cantidad_tomada = models.FloatField()  # dosis_por_toma al momento de la toma
    
    class Meta:
        ordering = ['-fecha_hora']
    
    def __str__(self):
        return f"{self.medicamento.nombre} - {self.paciente.username} ({self.fecha_hora.date()})"

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
    
class EventoCalendario(models.Model):
    TIPO_CHOICES = [
        ('medico', 'Médico / Turno'),
        ('social', 'Visita / Social'),
        ('actividad', 'Actividad / Taller'),
        ('otro', 'Otro'),
    ]
 
    paciente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='eventos')
    titulo = models.CharField(max_length=200)
    fecha_hora = models.DateTimeField()
    descripcion = models.TextField(blank=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='otro')
    lugar = models.CharField(max_length=200, blank=True)
 
    class Meta:
        ordering = ['fecha_hora']
 
    def __str__(self):
        return f"{self.titulo} - {self.fecha_hora.date()}"    