from django.db import models
from django.contrib.auth.models import User

class Perfil(models.Model):
    ROLES = (
        ('anciano', 'Adulto Mayor'),
        ('tutor', 'Tutor/Familiar'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    rol = models.CharField(max_length=10, choices=ROLES)
    tutor_asignado = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='pacientes')

class Medicamento(models.Model):
    perfil = models.ForeignKey('Perfil', on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    
    # Lógica de Horario
    horario_fijo = models.BooleanField(default=True)
    horario = models.CharField(max_length=100) 
    
    dosis = models.CharField(max_length=50)
    
    # Lógica de Frecuencia (Luis completa "12" para el Lotrial)
    cada_cuantas_horas = models.IntegerField(default=24) 
    
    stock_inicial = models.IntegerField(default=30)
    stock_actual = models.IntegerField(default=30)
    stock_critico = models.IntegerField(default=5)
    
    tomado_hoy = models.BooleanField(default=False)

    @property
    def porcentaje_restante(self):
        if self.stock_inicial > 0:
            return int((self.stock_actual / self.stock_inicial) * 100)
        return 0

    def reponer_stock(self):
        """Suma el contenido de una caja al stock actual"""
        self.stock_actual += self.stock_inicial
        self.save()

    def __str__(self):
        return self.nombre

class FotoReceta(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    imagen = models.ImageField(upload_to='recetas/')

class Turno(models.Model):
    # Relacionamos el turno con el anciano (perfil)
    perfil = models.ForeignKey('Perfil', on_delete=models.CASCADE, related_name='turnos')
    especialidad = models.CharField(max_length=100) # Ej: "Cardiólogo"
    doctor = models.CharField(max_length=100, blank=True)
    fecha_hora = models.DateTimeField()
    lugar = models.CharField(max_length=200, blank=True) # Ej: "Hospital Alemán"
    notas = models.TextField(blank=True)

    def __str__(self):
        return f"{self.especialidad} - {self.fecha_hora.strftime('%d/%m/%Y %H:%M')}"