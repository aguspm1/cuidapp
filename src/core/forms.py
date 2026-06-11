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
            'grupo_sanguineo': forms.Select(
                choices=[
                    ('', '— Seleccionar —'),
                    ('A+', 'A+'), ('A-', 'A-'),
                    ('B+', 'B+'), ('B-', 'B-'),
                    ('AB+', 'AB+'), ('AB-', 'AB-'),
                    ('O+', 'O+'), ('O-', 'O-'),
                ],
                attrs={'class': 'form-control'}
            ),
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
            'stock_actual', 'stock_total', 'umbral_stock_minimo'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Clonazepam'}),
            'tipo_presentacion': forms.Select(attrs={'class': 'form-control'}),
            'unidad_medida': forms.Select(attrs={'class': 'form-control'}),
            # 👇 Se agregó 'min': '0' a la dosis
            'dosis_por_toma': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'placeholder': 'Ej: 1, 15, 5.5', 'min': '0'}),
            'frecuencia_tipo': forms.RadioSelect(),
            'horario_fijo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 08:00 hs'}),
            'evento_toma': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: al levantarse'}),
            # 👇 Se agregó 'min': '0' a las horas
            'cada_cuantas_horas': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'duracion_tipo': forms.RadioSelect(),
            'fecha_fin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            # 👇 Se agregó 'min': '0' a todos los campos de stock
            'stock_actual': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'stock_total': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Cantidad en caja estándar', 'min': '0'}),
            'umbral_stock_minimo': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Validación estricta en el Backend para evitar números negativos
        self.fields['dosis_por_toma'].min_value = 0.0
        self.fields['stock_actual'].min_value = 0
        self.fields['stock_total'].min_value = 0
        self.fields['umbral_stock_minimo'].min_value = 0

    def clean(self):
        cleaned_data = super().clean()
        tipo_presentacion = cleaned_data.get('tipo_presentacion')
        unidad_medida = cleaned_data.get('unidad_medida')

        # 1. Matriz de correspondencia lógica entre Presentación y Unidad de Medida
        correspondencias = {
            'comprimido': ['unidades'],
            'gota': ['gotas', 'ml'],
            'liquido': ['ml'],
            'inyectable': ['ml'],
        }

        if tipo_presentacion and unidad_medida:
            unidades_permitidas = correspondencias.get(tipo_presentacion, [])
            
            if unidad_medida not in unidades_permitidas:
                # Obtenemos las etiquetas amigables para el mensaje de error
                nom_presentacion = dict(Medicamento.PRESENTACION_CHOICES).get(tipo_presentacion)
                nom_unidad = dict(Medicamento.UNIDAD_CHOICES).get(unidad_medida)
                
                raise forms.ValidationError(
                    f"Inconsistencia en los datos: La unidad de medida '{nom_unidad}' "
                    f"no corresponde para una presentación de tipo '{nom_presentacion}'."
                )
                
        stock_total = cleaned_data.get('stock_total')
        umbral = cleaned_data.get('umbral_stock_minimo')

        if stock_total is not None and umbral is not None:
            if umbral >= stock_total and stock_total > 0:
                raise forms.ValidationError(
                    "El umbral de alerta (stock mínimo) no puede ser mayor o igual a la cantidad total que trae la caja."
                )

        return cleaned_data


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