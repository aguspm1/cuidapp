from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Medicamento

class RegistroForm(UserCreationForm):
    ROLES = (
        ('anciano', 'Anciano (App)'),
        ('tutor', 'Tutor (Gestión Web)'),
    )
    rol = forms.ChoiceField(choices=ROLES, label="¿Quién sos?")

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'login-input'})

class MedicamentoForm(forms.ModelForm):
    class Meta:
        model = Medicamento
        fields = [
            'nombre', 'dosis', 'horario_fijo', 'horario', 
            'cada_cuantas_horas', 'stock_inicial', 'stock_actual', 'stock_critico'
        ]
        
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Lotrial 10'}),
            'dosis': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 1 comprimido'}),
            'horario_fijo': forms.CheckboxInput(attrs={'id': 'check_horario'}),
            'horario': forms.TextInput(attrs={'class': 'form-control', 'id': 'input_horario'}),
            'cada_cuantas_horas': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 12'}),
            'stock_inicial': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock_actual': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock_critico': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        
        labels = {
            'horario_fijo': '¿Tiene horario exacto?',
            'cada_cuantas_horas': 'Se toma cada (horas)',
            'stock_inicial': 'Cantidad total de la caja',
            'stock_actual': 'Cantidad disponible hoy',
            'stock_critico': 'Avisar cuando queden menos de:'
        }