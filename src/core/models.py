from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator


# ============================================================
# 1. PERFIL DE PACIENTE
# ============================================================

class PerfilPaciente(models.Model):
    user   = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil_medico')
    tutor  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='pacientes_a_cargo')  # Mantenido por compatibilidad
    tutores = models.ManyToManyField(User, related_name='pacientes_vinculados', blank=True, verbose_name='Tutores asignados')

    fecha_nacimiento     = models.DateField(null=True, blank=True)
    grupo_sanguineo      = models.CharField(max_length=5, blank=True)
    alergias             = models.TextField(blank=True, verbose_name='Alergias Conocidas')
    contacto_emergencia  = models.CharField(max_length=100, blank=True)
    telefono_emergencia  = models.CharField(max_length=20, blank=True)
    medico_cabecera      = models.CharField(max_length=100, blank=True)
    obra_social          = models.CharField(max_length=100, blank=True, verbose_name='Obra Social')
    plan                 = models.CharField(max_length=100, blank=True, verbose_name='Plan')
    numero_afiliado      = models.CharField(max_length=50, blank=True, verbose_name='Número de Afiliado')

    requiere_control_presion = models.BooleanField(default=False)
    requiere_control_glucosa = models.BooleanField(default=False)
    requiere_control_peso    = models.BooleanField(default=False)

    def __str__(self):
        return f"Perfil de {self.user.username} (Tutor: {self.tutor.username if self.tutor else 'Sin asignar'})"


# ============================================================
# 2. MEDICAMENTOS Y TOMAS
# ============================================================

class Medicamento(models.Model):
    PRESENTACION_CHOICES = [
        ('comprimido', 'Comprimido'),
        ('gota',       'Gotas'),
        ('liquido',    'Jarabe o Líquido'),
        ('inyectable', 'Inyectable'),
    ]
    UNIDAD_CHOICES = [
        ('unidades', 'Unidades'),
        ('gotas',    'Gotas'),
        ('ml',       'ml'),
        ('mg',       'mg'),
    ]
    FRECUENCIA_CHOICES = [
        ('fijo',      'Horario Fijo'),
        ('intervalo', 'Cada X horas'),
        ('evento',    'Relativo a Evento'),
    ]
    DURACION_CHOICES = [
        ('cronico',  'Crónico (todos los días)'),
        ('temporal', 'Temporal'),
    ]

    paciente          = models.ForeignKey(User, on_delete=models.CASCADE, related_name='medicamentos')
    nombre            = models.CharField(max_length=100)
    tipo_presentacion = models.CharField(max_length=20, choices=PRESENTACION_CHOICES, default='comprimido')
    unidad_medida     = models.CharField(max_length=20, choices=UNIDAD_CHOICES, default='unidades')
    dosis_por_toma    = models.FloatField(default=1)

    frecuencia_tipo    = models.CharField(max_length=20, choices=FRECUENCIA_CHOICES, default='fijo')
    horario_fijo       = models.CharField(max_length=200, blank=True, help_text='Ej: 08:00, 14:00, 20:00')
    evento_toma        = models.CharField(max_length=200, blank=True, help_text='Ej: al levantarse, antes de acostarse')
    cada_cuantas_horas = models.IntegerField(null=True, blank=True, help_text='Ej: 6, 8, 12, 24')

    duracion_tipo = models.CharField(max_length=20, choices=DURACION_CHOICES, default='cronico')
    fecha_inicio  = models.DateField(auto_now_add=True)
    fecha_fin     = models.DateField(null=True, blank=True, help_text="Solo si duracion_tipo='temporal'")

    stock_actual        = models.IntegerField(default=0)
    stock_total         = models.IntegerField(default=0, help_text='Cantidad en cada caja estándar')
    umbral_stock_minimo = models.IntegerField(default=5, help_text='Alertar cuando stock <= este valor')

    activo      = models.BooleanField(default=True)
    creado      = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nombre} - {self.paciente.username}"

    @property
    def tiene_stock_bajo(self):
        return self.stock_actual <= self.umbral_stock_minimo

    @property
    def porcentaje_stock(self):
        """Porcentaje de stock actual respecto al total (0–100), para la barra visual."""
        if not self.stock_total or self.stock_total <= 0:
            return 0
        return min(100, round((self.stock_actual / self.stock_total) * 100))

    @property
    def tomas_restantes(self):
        """Cuántas tomas completas se pueden dar con el stock actual."""
        if self.dosis_por_toma == 0:
            return 0
        return int(self.stock_actual / self.dosis_por_toma)


class RegistroToma(models.Model):
    """Historial inmutable de cada toma registrada."""
    medicamento   = models.ForeignKey(Medicamento, on_delete=models.CASCADE, related_name='registros_toma')
    paciente      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='registros_toma')
    fecha_hora    = models.DateTimeField(auto_now_add=True)
    cantidad_tomada = models.FloatField()

    class Meta:
        ordering = ['-fecha_hora']

    def __str__(self):
        return f"{self.medicamento.nombre} - {self.paciente.username} ({self.fecha_hora.date()})"


# ============================================================
# 3. DOCUMENTOS MÉDICOS Y MEDICIONES
# ============================================================

class FotoDocumento(models.Model):
    """Archivos (fotos o PDFs) que el paciente sube para que el tutor los revise."""
    TIPO_CHOICES = [
        ('medicion',  'Foto de Medición'),
        ('receta',    'Receta Médica'),
        ('indicacion','Indicación Médica'),
        ('otro',      'Otro Documento'),
    ]

    paciente      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fotos_documentos')
    imagen        = models.FileField(
        upload_to='documentos/fotos/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'pdf'])]
    )
    tipo          = models.CharField(max_length=20, choices=TIPO_CHOICES, default='medicion')
    fecha_subida  = models.DateTimeField(auto_now_add=True)
    procesada     = models.BooleanField(default=False)
    nota_paciente = models.CharField(max_length=255, blank=True)
    nota_tutor    = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name_plural = 'Documentos (Fotos)'
        ordering = ['-fecha_subida']

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.paciente.username} ({self.fecha_subida.date()})"


class DatoMedicion(models.Model):
    """Datos numéricos que el tutor extrae a partir de una foto de medición."""
    TIPO_CHOICES = [
        ('presion', 'Presión Arterial'),
        ('glucosa', 'Glucosa'),
        ('peso',    'Peso'),
    ]

    paciente      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='datos_mediciones')
    tipo          = models.CharField(max_length=20, choices=TIPO_CHOICES)
    valor_1       = models.FloatField()
    valor_2       = models.FloatField(null=True, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    observaciones = models.TextField(blank=True)
    foto = models.OneToOneField(FotoDocumento, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-fecha_registro']
        verbose_name_plural = 'Datos de Mediciones'

    def __str__(self):
        v2 = f"/{self.valor_2}" if self.valor_2 else ""
        return f"{self.get_tipo_display()}: {self.valor_1}{v2} ({self.paciente.username})"


# ============================================================
# 4. CALENDARIO
# ============================================================

class EventoCalendario(models.Model):
    TIPO_CHOICES = [
        ('medico',    'Médico / Turno'),
        ('social',    'Visita / Social'),
        ('actividad', 'Actividad / Taller'),
        ('otro',      'Otro'),
    ]

    paciente    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='eventos')
    titulo      = models.CharField(max_length=200)
    fecha_hora  = models.DateTimeField()
    tipo        = models.CharField(max_length=20, choices=TIPO_CHOICES, default='otro')
    lugar       = models.CharField(max_length=200, blank=True)
    descripcion = models.TextField(blank=True)

    class Meta:
        ordering = ['fecha_hora']

    def __str__(self):
        return f"{self.titulo} - {self.fecha_hora.date()}"
    
# ============================================================
# 5. NOTIFICACIONES
# ============================================================

class Notificacion(models.Model):
    TIPO_CHOICES = [
        ('medicacion', 'Recordatorio de Toma'),
        ('evento', 'Evento Próximo'),
        ('sistema', 'Aviso del Sistema'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificaciones')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='sistema')
    titulo = models.CharField(max_length=150)
    mensaje = models.TextField()
    leida = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    # Campo clave para evitar notificaciones duplicadas
    referencia_id = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"[{self.get_tipo_display()}] {self.titulo} - {self.usuario.username}"