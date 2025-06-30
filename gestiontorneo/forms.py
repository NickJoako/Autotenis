from django import forms
from gestiontorneo.models import *
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
import re
import unicodedata
import pandas as pd
from django.utils import timezone
from datetime import date

class ImportarJugadoresForm(forms.Form):
    archivo = forms.FileField(label="Archivo Excel (.xlsx)")

class ImportarParticipantesForm(forms.Form):
    archivo_participantes = forms.FileField(
        label="Archivo Excel con RUTs (.xlsx)",
        help_text="Sube un archivo Excel con una columna 'RUT' que contenga los RUTs de los jugadores a agregar al torneo."
    )

class RegistroPersonalizadoForm(UserCreationForm):

    username = forms.CharField(
        label="Nombre de usuario",
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            "placeholder": "Ingrese un nombre de usuario",
            "class": "form-control"
        })
    )

    first_name = forms.CharField(
        label="Nombre",
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            "placeholder": "Ingrese su nombre",
            "class": "form-control"
        })
    )
    
    last_name = forms.CharField(
        label="Apellido",
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            "placeholder": "Ingrese su apellido",
            "class": "form-control"
        })
    )

    email = forms.EmailField(
        label="Correo electrónico", 
        required=True,  # Ahora es obligatorio porque será el campo de login
        widget=forms.EmailInput(attrs={
            "placeholder": "Ingrese su correo electrónico",
            "class": "form-control"
        }),
    )

    password1 = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Ingrese su contraseña',
            "class": "form-control"
            }),
        help_text='La contraseña debe tener al menos 8 caracteres, una letra mayúscula y un número.'
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Confirme su contraseña',
            "class": "form-control"
        }),
        strip=False,
        help_text="Repite la contraseña para confirmar.",
    )

    tipo_usuario = forms.ChoiceField(
        choices=[
            ('organizador', 'Organizador'),
            ('arbitro', 'Árbitro'),
            ('jugador', 'Jugador')
        ],
        label="Tipo de Usuario",
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'placeholder': 'Seleccione un tipo de usuario'
        }),
        help_text="Debe seleccionar un tipo de usuario para continuar.",
    )

    class Meta:
        model = UsuarioPersonalizado
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2', 'tipo_usuario']
    
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
        
    def clean_tipo_usuario(self):
        tipo_usuario = self.cleaned_data.get('tipo_usuario')
        
        if not tipo_usuario:
            raise forms.ValidationError("Debe seleccionar un tipo de usuario.")
        
        if tipo_usuario not in ['organizador', 'arbitro', 'jugador']:
            raise forms.ValidationError("Tipo de usuario inválido.")
        
        return tipo_usuario

    def clean_email(self):
        email = self.cleaned_data.get('email')
        tipo_usuario = self.cleaned_data.get('tipo_usuario')
        
        if not email:
            raise forms.ValidationError("El correo electrónico es obligatorio.")
        
        # Validar que no exista el mismo email para el mismo tipo de usuario
        if UsuarioPersonalizado.objects.filter(email=email, tipo_usuario=tipo_usuario).exists():
            raise forms.ValidationError(f"Ya existe un {tipo_usuario} con este correo electrónico.")
        
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        tipo_usuario = self.cleaned_data.get('tipo_usuario')
        
        # Asignar permisos según tipo de usuario
        if tipo_usuario == 'organizador':
            user.is_staff = True
            user.is_superuser = False
        elif tipo_usuario == 'arbitro':
            user.is_staff = False
            user.is_superuser = True
        else:  # jugador
            user.is_staff = False
            user.is_superuser = False
        
        user.tipo_usuario = tipo_usuario
        
        if commit:
            user.save()
        return user

class TorneoForm(forms.ModelForm):
    nombre = forms.CharField(
        label="Nombre del Torneo",
        required=True,
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: Torneo de Verano"})
    )
    fecha = forms.DateField(
        label="Fecha del Torneo",
        required=True,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date", "class": "form-control"}),
    )
    hora = forms.TimeField(
        label="Hora del Torneo",
        required=True,
        widget=forms.TimeInput(format="%H:%M", attrs={"type": "time", "class": "form-control"}),
    )
    federado = forms.BooleanField(
        label="¿Es torneo federado?",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    ubicacion = forms.CharField(
        label="Ubicación",
        required=True,
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: Gimnasio Municipal"})
    )
    categoria = forms.ModelChoiceField(
        label="Categoría del Torneo",
        queryset=Categoria.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"})
    )
    todo_competidor = forms.BooleanField(
        label="Todo Competidor (TC)",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"})
    )

    class Meta:
        model = Torneo
        fields = ['nombre', 'fecha', 'hora', 'ubicacion', 'federado', 'categoria', 'todo_competidor']

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

    def clean(self):
        cleaned_data = super().clean()
        categoria = cleaned_data.get('categoria')
        todo_competidor = cleaned_data.get('todo_competidor')

        # Validación personalizada
        if not categoria and not todo_competidor:
            raise forms.ValidationError(
                "Debes seleccionar una categoría o marcar la opción 'Todo Competidor (TC)'."
            )
        return cleaned_data

class ClubForm(forms.ModelForm):
    class Meta:
        model = Club
        fields = ['nombre']

    def __init__(self, *args, **kwargs):
        self.organizador = kwargs.pop('organizador', None)
        super().__init__(*args, **kwargs)

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre']
        nombre = limpiar_texto_estricto(nombre)
        if not nombre:
            raise forms.ValidationError("El nombre del club es requerido.")
        if Club.objects.filter(nombre=nombre, organizador=self.organizador).exists():
            raise forms.ValidationError("Ya tienes un club con ese nombre.")
        return nombre
    
class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'edad_minima', 'edad_maxima']

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre']
        nombre = limpiar_texto_estricto(nombre)
        if not nombre:
            raise forms.ValidationError("El nombre de la categoría es requerido.")
        return nombre

    def clean(self):
        cleaned_data = super().clean()
        edad_minima = cleaned_data.get('edad_minima')
        edad_maxima = cleaned_data.get('edad_maxima')

        if edad_minima is not None and (edad_minima < 0 or edad_minima > 120):
            self.add_error('edad_minima', "La edad mínima debe estar entre 0 y 120.")

        if edad_maxima is not None and (edad_maxima < 0 or edad_maxima > 120):
            self.add_error('edad_maxima', "La edad máxima debe estar entre 0 y 120.")

        if edad_minima is not None and edad_maxima is not None:
            if edad_minima > edad_maxima:
                raise forms.ValidationError("La edad mínima no puede ser mayor que la edad máxima.")

class JugadorForm(forms.ModelForm):
    rut = forms.CharField(
        label="RUT",
        required=True,
        max_length=12,
        widget=forms.TextInput(attrs={
            "placeholder": "Ej: 12345678-9",
            "class": "form-control"
        })
    )
    nombre = forms.CharField(
        label="Nombre",
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )
    apellido = forms.CharField(
        label="Apellido",
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )
    fecha_nacimiento = forms.DateField(
        label="Fecha de nacimiento",
        required=True,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={
            "type": "date",
            "class": "form-control"
        }),
    )
    genero = forms.ChoiceField(
        label="Género",
        choices=[('M', 'Masculino'), ('F', 'Femenino')],
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    club = forms.ModelChoiceField(
        label="Club o Asociación",
        queryset=Club.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    email = forms.EmailField(
        label="Correo electrónico", 
        required=False, 
        widget=forms.EmailInput(attrs={
            "placeholder": "Opcional",
            "class": "form-control"
        }),
    )

    class Meta:
        model = Jugador
        fields = ['rut', 'nombre', 'apellido', 'fecha_nacimiento', 'genero', 'club', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['club'].queryset = Club.objects.all()

    def clean_rut(self):
        rut = self.cleaned_data['rut']
        rut = rut.replace('.', '').replace(' ', '').upper()
        if not re.match(r'^\d{7,8}-[\dkK]$', rut):
            raise forms.ValidationError("Ingrese un RUT válido, sin puntos y con guion. Ejemplo: 12345678-9")
        if Jugador.objects.filter(rut=rut).exists():
            raise forms.ValidationError("Ya existe un jugador con este RUT.")
        return rut
    
    def clean_nombre(self):
        nombre = self.cleaned_data['nombre']
        nombre = limpiar_texto_estricto(nombre)
        if not nombre:
            raise forms.ValidationError("El nombre es requerido.")
        if len(nombre) > 50:
            raise forms.ValidationError("El nombre no puede superar los 50 caracteres.")
        return nombre

    def clean_apellido(self):
        apellido = self.cleaned_data['apellido']
        apellido = limpiar_texto_estricto(apellido)
        if not apellido:
            raise forms.ValidationError("El apellido es requerido.")
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
            email = limpiar_email_estricto(email)
            if email and Jugador.objects.filter(email=email).exists():
                raise forms.ValidationError("Ya existe un jugador con este correo electrónico.")
        return email if email else None
    
    def save(self, commit=True):
        jugador = super().save(commit=False)
        if not jugador.email or jugador.email.strip().lower() == "opcional":
            jugador.email = None
        hoy = date.today()
        edad = hoy.year - jugador.fecha_nacimiento.year - (
            (hoy.month, hoy.day) < (jugador.fecha_nacimiento.month, jugador.fecha_nacimiento.day)
        )
        categoria = Categoria.objects.filter(
            edad_minima__lte=edad,
            edad_maxima__gte=edad
        ).first()
        jugador.categoria = categoria
        if commit:
            jugador.save()
        return jugador

class ConfigurarSetsForm(forms.Form):
    """Formulario para configurar la cantidad de sets del torneo"""
    MEJOR_DE_SETS = [
        (1, 'Mejor de 1 set'),
        (3, 'Mejor de 3 sets'),
        (5, 'Mejor de 5 sets'),
        (7, 'Mejor de 7 sets'),
        (9, 'Mejor de 9 sets'),
    ]
    
    mejor_de_sets = forms.ChoiceField(
        choices=MEJOR_DE_SETS, 
        initial=3, 
        label="Mejor de sets (rondas normales)",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    mejor_de_sets_final = forms.ChoiceField(
        choices=MEJOR_DE_SETS, 
        initial=5, 
        label="Mejor de sets (final)",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

def limpiar_texto_estricto(texto):
    if pd.isna(texto) or texto is None or texto == '':
        return ''
    
    texto = str(texto).strip()
    
    texto = texto.replace('\r', ' ').replace('\n', ' ').replace('\t', ' ')
    texto = texto.replace('_x000D_', ' ').replace('_x000A_', ' ')
    texto = texto.replace('x000D', ' ').replace('x000A', ' ')
    
    texto = unicodedata.normalize('NFC', texto)
    
    texto = re.sub(r"[^a-zA-ZáéíóúÁÉÍÓÚñÑ0-9 .\-]", "", texto)
    
    texto = re.sub(r"\s+", " ", texto)
    
    texto = re.sub(r"-+", "-", texto)
    
    texto = re.sub(r"\.+", ".", texto)
    
    return texto.strip()

def limpiar_email_estricto(email):
    if pd.isna(email) or email is None or email == '':
        return ''
    
    email = str(email).strip().lower()
    
    email = email.replace('\r', '').replace('\n', '').replace('\t', '')
    email = email.replace('_x000D_', '').replace('_x000A_', '')
    email = email.replace('x000D', '').replace('x000A', '')
    
    email = unicodedata.normalize('NFC', email)
    
    email = re.sub(r"[^a-z0-9@.\-_]", "", email)
    
    return email.strip()

