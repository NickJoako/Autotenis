from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from datetime import date
from django.conf import settings
# Create your models here.

class UsuarioPersonalizado(AbstractUser):
    username = models.CharField(
        max_length=20,
        unique=True,
        help_text='',
        validators=[UnicodeUsernameValidator()],
        error_messages={
            'unique': "Ya existe un usuario con ese nombre.",
        },
    )
    TIPO_USUARIO = [
        ('organizador', 'Organizador'),
        ('arbitro', 'Árbitro'),
        ('jugador', 'Jugador'),
    ]
    tipo_usuario = models.CharField(max_length=20, choices=TIPO_USUARIO, null=True, blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.username

class Club(models.Model):
    nombre = models.CharField(max_length=100, unique=True) 

    def __str__(self):
        return self.nombre

class Categoria(models.Model):
    nombre = models.CharField(max_length=100)
    edad_minima = models.PositiveIntegerField(null=True, blank=True)
    edad_maxima = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return self.nombre

    def rango_edades(self):
        if self.edad_minima is not None and self.edad_maxima is not None:
            return f"{self.edad_minima}-{self.edad_maxima}"
        elif self.edad_minima is not None:
            return f"Desde {self.edad_minima}"
        elif self.edad_maxima is not None:
            return f"Hasta {self.edad_maxima}"
        else:
            return "Sin restricción"
        
    def rango_anios_nacimiento(self):
        anio_actual = date.today().year
        if self.edad_minima is not None and self.edad_maxima is not None:
            anio_max = anio_actual - self.edad_minima
            anio_min = anio_actual - self.edad_maxima
            return f"{anio_min}-{anio_max}"
        elif self.edad_minima is not None:
            anio_max = anio_actual - self.edad_minima
            return f"Hasta {anio_max}"
        elif self.edad_maxima is not None:
            anio_min = anio_actual - self.edad_maxima
            return f"Desde {anio_min}"
        else:
            return "Sin restricción"

class Jugador(models.Model):
    rut = models.CharField(max_length=12, unique=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    fecha_nacimiento = models.DateField()
    genero = models.CharField(max_length=1, choices=[('M', 'Masculino'), ('F', 'Femenino')])
    club = models.ForeignKey(Club, on_delete=models.SET_NULL, null=True, blank=True)
    email = models.EmailField(blank=True, null=True, unique=True)

    def __str__(self):        return f"{self.nombre} {self.apellido} ({self.rut})"
    
    def calcular_categoria(self):
        hoy = date.today()
        edad = hoy.year - self.fecha_nacimiento.year
        categoria = Categoria.objects.filter(
            edad_minima__lte=edad,
            edad_maxima__gte=edad
        ).first()
        if not categoria:
            categoria = Categoria.objects.filter(
                edad_minima__lte=edad,
                edad_maxima__isnull=True
            ).first()
        if not categoria:
            categoria = Categoria.objects.filter(
                edad_maxima__gte=edad,
                edad_minima__isnull=True
            ).first()
        return categoria.nombre if categoria else "Sin categoría"

class Torneo(models.Model):
    nombre = models.CharField(max_length=100)
    fecha = models.DateField()
    hora = models.TimeField(null=True, blank=True)
    ubicacion = models.CharField(max_length=100)
    federado = models.BooleanField(default=False)
    categoria = models.ForeignKey('Categoria', null=True, blank=True, on_delete=models.SET_NULL)
    todo_competidor = models.BooleanField(default=False)
    inscripciones_cerradas = models.BooleanField(default=False)
    
    # Nuevos campos para modalidad del torneo
    MODALIDADES = [
        ('', 'Sin definir'),
        ('llaves', 'Llaves (Brackets)'),
        ('grupos', 'Fases de Grupos'),
    ]
    modalidad = models.CharField(max_length=20, choices=MODALIDADES, default='', blank=True)
    torneo_iniciado = models.BooleanField(default=False)
    
    organizador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='torneos')

    def __str__(self):
        return self.nombre
    
class Participacion(models.Model):
    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE, related_name='participaciones')
    jugador = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name='participaciones')
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('torneo', 'jugador')

class Partido(models.Model):
    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE)
    jugador1 = models.ForeignKey(Jugador, related_name='partidos_jugador1', on_delete=models.CASCADE)
    jugador2 = models.ForeignKey(Jugador, related_name='partidos_jugador2', on_delete=models.CASCADE)
    fecha_hora = models.DateTimeField()
    organizador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='partidos')

    def __str__(self):
        return f"{self.jugador1} vs {self.jugador2} - {self.torneo}"

class GrupoTorneo(models.Model):
    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE, related_name='grupos')
    nombre = models.CharField(max_length=10)  # A, B, C, etc.
    numero = models.PositiveIntegerField()  # 1, 2, 3, etc.

    class Meta:
        unique_together = ('torneo', 'numero')
        ordering = ['numero']

    def __str__(self):
        return f"Grupo {self.nombre} - {self.torneo.nombre}"

class ParticipanteGrupo(models.Model):
    grupo = models.ForeignKey(GrupoTorneo, on_delete=models.CASCADE, related_name='participantes')
    jugador = models.ForeignKey(Jugador, on_delete=models.CASCADE)
    es_cabeza_serie = models.BooleanField(default=False)
    posicion_grupo = models.PositiveIntegerField()  # 1, 2, 3, 4 dentro del grupo

    class Meta:
        unique_together = ('grupo', 'jugador')
        ordering = ['posicion_grupo']

    def __str__(self):
        return f"{self.jugador.nombre} {self.jugador.apellido} - {self.grupo.nombre}"


# class Resultado(models.Model):
#     partido = models.OneToOneField(Partido, on_delete=models.CASCADE)
#     puntos_jugador1 = models.IntegerField()
#     puntos_jugador2 = models.IntegerField()
#
#     def __str__(self):
#         return f"Resultado de {self.partido}"
