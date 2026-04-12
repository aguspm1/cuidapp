from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Medicamento

class RegistroForm(UserCreationForm):
    ROLES = (('anciano', 'Anciano (App)'), ('tutor', 'Tutor (Gestión Web)'))
    rol = forms.ChoiceField(choices=ROLES, label="¿Quién sos?")
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

class MedicamentoForm(forms.ModelForm):
    # Campos adicionales que no están en el modelo pero se muestran en el formulario
    horario_fijo = forms.BooleanField(required=False, label="¿Tiene horario exacto?", widget=forms.CheckboxInput(attrs={'id': 'check_horario'}))
    horario = forms.CharField(required=False, label="Horario / Momento", widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'input_horario'}))
    dosis = forms.CharField(required=False, label="Dosis", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 1 comprimido'}))
    cada_cuantas_horas = forms.IntegerField(required=False, label="Se toma cada (horas)", widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 12'}))
    stock_inicial = forms.IntegerField(required=False, label="Stock inicial (para referencia)", widget=forms.NumberInput(attrs={'class': 'form-control'}))
    stock_critico = forms.IntegerField(required=False, label="Stock crítico", widget=forms.NumberInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Medicamento
        fields = ['nombre', 'stock_actual', 'stock_total', 'frecuencia', 'activo']
        labels = {
            'nombre': 'Nombre del Medicamento',
            'stock_actual': 'Stock Actual',
            'stock_total': 'Stock Total',
            'frecuencia': 'Frecuencia',
            'activo': 'Medicamento Activo'
        }
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Lotrial 10'}),
            'stock_actual': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock_total': forms.NumberInput(attrs={'class': 'form-control'}),
            'frecuencia': forms.TextInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-control'}),
        }
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Guardamos los campos extras en el campo 'frecuencia' como referencia
        dosis = self.cleaned_data.get('dosis') or ""
        horario = self.cleaned_data.get('horario') or ""
        cada = self.cleaned_data.get('cada_cuantas_horas') or ""
        
        if horario or dosis or cada:
            instance.frecuencia = f"{dosis} - {horario} (Cada {cada}hs)".strip(" - (Cada hs)")
        
        if commit:
            instance.save()
        return instance