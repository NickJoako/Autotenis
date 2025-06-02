from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
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
    nombre = models.CharField(max_length=100)
    organizador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='clubes')

    class Meta:
        unique_together = ('nombre', 'organizador')

    def __str__(self):
        return self.nombre

class Categoria(models.Model):
    nombre = models.CharField(max_length=100)
    edad_minima = models.PositiveIntegerField()
    edad_maxima = models.PositiveIntegerField()

    def __str__(self):
        return self.nombre

class Jugador(models.Model):
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    fecha_nacimiento = models.DateField()
    club = models.ForeignKey(Club, on_delete=models.SET_NULL, null=True, blank=True)
    organizador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='jugadores')
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True)
    email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return self.nombre

class Torneo(models.Model):
    nombre = models.CharField(max_length=100)
    fecha = models.DateField()
    ubicacion = models.CharField(max_length=100)
    organizador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='torneos')

    def __str__(self):
        return self.nombre

class Partido(models.Model):
    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE)
    jugador1 = models.ForeignKey(Jugador, related_name='partidos_jugador1', on_delete=models.CASCADE)
    jugador2 = models.ForeignKey(Jugador, related_name='partidos_jugador2', on_delete=models.CASCADE)
    fecha_hora = models.DateTimeField()
    organizador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='partidos')

    def __str__(self):
        return f"{self.jugador1} vs {self.jugador2} - {self.torneo}"

# class Resultado(models.Model):
#     partido = models.OneToOneField(Partido, on_delete=models.CASCADE)
#     puntos_jugador1 = models.IntegerField()
#     puntos_jugador2 = models.IntegerField()
#
#     def __str__(self):
#         return f"Resultado de {self.partido}"
