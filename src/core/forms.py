from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Medicamento, PerfilPaciente, FotoDocumento

class RegistroForm(UserCreationForm):
    ROLES = (('paciente', 'Paciente (App móvil)'), ('tutor', 'Tutor (Panel web)'))
    rol = forms.ChoiceField(choices=ROLES, label="¿Cuál es tu rol?", widget=forms.RadioSelect())
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

class PerfilPacienteForm(forms.ModelForm):
    class Meta:
        model = PerfilPaciente
        fields = ['fecha_nacimiento', 'grupo_sanguineo', 'alergias', 
                  'contacto_emergencia', 'telefono_emergencia', 'medico_cabecera',
                  'obra_social', 'plan', 'numero_afiliado',
                  'requiere_control_presion', 'requiere_control_glucosa', 
                  'requiere_control_peso']
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'grupo_sanguineo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'O+, O-, A+, etc.'}),
            'alergias': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'contacto_emergencia': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono_emergencia': forms.TextInput(attrs={'class': 'form-control'}),
            'medico_cabecera': forms.TextInput(attrs={'class': 'form-control'}),
            'obra_social': forms.TextInput(attrs={'class': 'form-control'}),
            'plan': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_afiliado': forms.TextInput(attrs={'class': 'form-control'}),
            'requiere_control_presion': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'requiere_control_glucosa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'requiere_control_peso': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class MedicamentoForm(forms.ModelForm):
    class Meta:
        model = Medicamento
        fields = [
            'nombre', 'tipo_presentacion', 'unidad_medida', 'dosis_por_toma',
            'frecuencia_tipo', 'horario_fijo', 'evento_toma', 'cada_cuantas_horas',
            'duracion_tipo', 'fecha_fin',
            'stock_actual', 'stock_total', 'umbral_stock_minimo', 'activo'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Clonazepam'}),
            'tipo_presentacion': forms.Select(attrs={'class': 'form-control'}),
            'unidad_medida': forms.Select(attrs={'class': 'form-control'}),
            'dosis_por_toma': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'placeholder': 'Ej: 1, 15, 5.5'}),
            'frecuencia_tipo': forms.RadioSelect(),
            'horario_fijo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 08:00 hs'}),
            'evento_toma': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: al levantarse'}),
            'cada_cuantas_horas': forms.NumberInput(attrs={'class': 'form-control'}),
            'duracion_tipo': forms.RadioSelect(),
            'fecha_fin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'stock_actual': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock_total': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Cantidad en caja estándar'}),
            'umbral_stock_minimo': forms.NumberInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class SubirFotoForm(forms.ModelForm):
    class Meta:
        model = FotoDocumento
        fields = ['tipo', 'imagen', 'nota_paciente']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-control', 'style': 'padding: 10px; width: 100%; border-radius: 6px;'}),
            'imagen': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*,application/pdf'}),
            'nota_paciente': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Ej: Dejo la orden de la obra social...', 'style': 'width: 100%; border-radius: 6px; padding: 10px;'}),
        }
        labels = {
            'tipo': '¿Qué tipo de documento es?',
            'imagen': 'Seleccionar Foto o PDF',
            'nota_paciente': 'Nota del paciente (opcional)',
        }