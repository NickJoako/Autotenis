from django import forms
from gestiontorneo.models import *
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
import re
from django.utils import timezone
from datetime import date


class RegistroPersonalizadoForm(UserCreationForm):

    email = forms.EmailField(
        label='Correo Electrónico',
        widget=forms.EmailInput(attrs={'placeholder': 'Ingrese su correo electrónico'}),
        required=True
    )

    password1 = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'placeholder': 'Ingrese su contraseña'}),
        help_text='La contraseña debe tener al menos 8 caracteres, una letra mayúscula y un número.'
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput,
        strip=False,
        help_text="Repite la contraseña para confirmar.",
    )

    tipo_usuario = forms.ChoiceField(
        choices=[
            ('',''),
            ('organizador', 'Organizador'),
            ('arbitro', 'Árbitro'),
            ('jugador', 'Jugador')
        ],
        label="Tipo de Usuario",
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = UsuarioPersonalizado
        fields = ['username', 'email', 'password1', 'password2','tipo_usuario']
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if len(username) > 20:
            raise forms.ValidationError("El nombre de usuario no puede tener más de 20 caracteres.")
        return username

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        if len(password1) < 8:
            raise ValidationError("La contraseña debe tener al menos 8 caracteres.")
        if not re.search(r'[A-Z]', password1):
            raise ValidationError("La contraseña debe tener al menos una letra mayúscula.")
        if not re.search(r'[0-9]', password1):
            raise ValidationError("La contraseña debe tener al menos un número.")
        return password1

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise ValidationError("Las contraseñas no coinciden.")
        
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if UsuarioPersonalizado.objects.filter(email=email).exists():
            raise forms.ValidationError("Ya existe un usuario con ese correo electrónico.")
        return email

class TorneoForm(forms.ModelForm):
    fecha = forms.DateField(
        label="Fecha del Torneo",
        required=True,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
    )
    class Meta:
        model = Torneo
        fields = ['nombre', 'fecha', 'ubicacion']

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        if len(nombre) > 100:
            raise forms.ValidationError("El nombre no puede superar los 100 caracteres.")
        return nombre

    def clean_ubicacion(self):
        ubicacion = self.cleaned_data.get('ubicacion')
        if len(ubicacion) > 100:
            raise forms.ValidationError("La ubicación no puede superar los 100 caracteres.")
        return ubicacion

    def clean_fecha(self):
        fecha = self.cleaned_data.get('fecha')
        if fecha < timezone.now().date():
            raise forms.ValidationError("La fecha del torneo no puede ser anterior a hoy.")
        return fecha

class ClubForm(forms.ModelForm):
    class Meta:
        model = Club
        fields = ['nombre']

    def __init__(self, *args, **kwargs):
        self.organizador = kwargs.pop('organizador', None)
        super().__init__(*args, **kwargs)

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre']
        if Club.objects.filter(nombre=nombre, organizador=self.organizador).exists():
            raise forms.ValidationError("Ya tienes un club con ese nombre.")
        return nombre
    
class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'edad_minima', 'edad_maxima']

    def clean(self):
        cleaned_data = super().clean()
        edad_minima = cleaned_data.get('edad_minima')
        edad_maxima = cleaned_data.get('edad_maxima')

        if edad_minima is not None:
            if edad_minima < 0 or edad_minima > 99:
                self.add_error('edad_minima', "La edad mínima debe estar entre 0 y 99.")

        if edad_maxima is not None:
            if edad_maxima < 0 or edad_maxima > 99:
                self.add_error('edad_maxima', "La edad máxima debe estar entre 0 y 99.")

        if edad_minima is not None and edad_maxima is not None:
            if edad_minima > edad_maxima:
                raise forms.ValidationError("La edad mínima no puede ser mayor que la edad máxima.")

class JugadorForm(forms.ModelForm):
    fecha_nacimiento = forms.DateField(
        label="Fecha de nacimiento",
        required=True,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
    )

    email = forms.EmailField(
        label="Correo electrónico", 
        required=False, 
        widget=forms.EmailInput(attrs={"placeholder": "Opcional"}),
        )

    class Meta:
        model = Jugador
        fields = ['nombre', 'apellido', 'fecha_nacimiento', 'club', 'email']

    def __init__(self, *args, **kwargs):
        self.organizador = kwargs.pop('organizador', None)
        super().__init__(*args, **kwargs)

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre']
        if len(nombre) > 50:
            raise forms.ValidationError("El nombre no puede superar los 50 caracteres.")
        return nombre

    def clean_apellido(self):
        apellido = self.cleaned_data['apellido']
        if len(apellido) > 50:
            raise forms.ValidationError("El apellido no puede superar los 50 caracteres.")
        return apellido
    
    def clean_fecha_nacimiento(self):
        fecha_nacimiento = self.cleaned_data['fecha_nacimiento']
        if fecha_nacimiento > date.today():
            raise forms.ValidationError("La fecha de nacimiento no puede ser posterior a hoy.")
        return fecha_nacimiento
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            if Jugador.objects.filter(email=email).exists():
                raise forms.ValidationError("Ya existe un jugador con este correo electrónico.")
        return email
    
    def save(self, commit=True):
        jugador = super().save(commit=False)
        # Calcular edad
        hoy = date.today()
        edad = hoy.year - jugador.fecha_nacimiento.year - ((hoy.month, hoy.day) < (jugador.fecha_nacimiento.month, jugador.fecha_nacimiento.day))
        # Buscar categoría
        categoria = Categoria.objects.filter(edad_minima__lte=edad, edad_maxima__gte=edad).first()
        jugador.categoria = categoria
        if commit:
            jugador.save()
        return jugador
        