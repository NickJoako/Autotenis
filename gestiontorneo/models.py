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

class JugadorBYE(models.Model):
    """Modelo para representar BYEs en el sistema"""
    nombre = models.CharField(max_length=50, default="BYE")
    posicion_bye = models.PositiveIntegerField()  # Para identificar diferentes BYEs
    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE, related_name='byes')
    
    class Meta:
        unique_together = ('torneo', 'posicion_bye')
    
    def __str__(self):
        return f"BYE #{self.posicion_bye} - {self.torneo.nombre}"
    
    @property
    def es_bye(self):
        return True

class LlaveTorneo(models.Model):
    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE, related_name='llaves')
    ronda = models.PositiveIntegerField()  # 1=Primera ronda, 2=Segunda ronda, etc.
    posicion = models.PositiveIntegerField()  # Posición dentro de la ronda
    jugador1 = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name='llaves_jugador1', null=True, blank=True)
    jugador2 = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name='llaves_jugador2', null=True, blank=True)
    bye1 = models.ForeignKey(JugadorBYE, on_delete=models.CASCADE, related_name='llaves_bye1', null=True, blank=True)
    bye2 = models.ForeignKey(JugadorBYE, on_delete=models.CASCADE, related_name='llaves_bye2', null=True, blank=True)
    ganador = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name='llaves_ganadas', null=True, blank=True)
    partido_jugado = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('torneo', 'ronda', 'posicion')
        ordering = ['ronda', 'posicion']

    def __str__(self):
        return f"Ronda {self.ronda} - Posición {self.posicion} - {self.torneo.nombre}"
    
    def get_participante1(self):
        """Retorna el primer participante (jugador o BYE)"""
        return self.jugador1 if self.jugador1 else self.bye1
    
    def get_participante2(self):
        """Retorna el segundo participante (jugador o BYE)"""
        return self.jugador2 if self.jugador2 else self.bye2
    
    def get_rival(self, jugador):
        """Retorna el rival del jugador dado en esta llave"""
        if self.jugador1 == jugador:
            return self.get_participante2()
        elif self.jugador2 == jugador:
            return self.get_participante1()
        return None
    
    def tiene_bye(self):
        """Verifica si esta llave tiene un BYE"""
        return self.bye1 is not None or self.bye2 is not None
    
    def avanzar_automaticamente(self):
        """Si hay un BYE, avanza automáticamente al jugador real"""
        if self.bye1 and self.jugador2:
            self.ganador = self.jugador2
            self.partido_jugado = True
            return self.jugador2
        elif self.bye2 and self.jugador1:
            self.ganador = self.jugador1
            self.partido_jugado = True
            return self.jugador1
        return None

# class Resultado(models.Model):
#     partido = models.OneToOneField(Partido, on_delete=models.CASCADE)
#     puntos_jugador1 = models.IntegerField()
#     puntos_jugador2 = models.IntegerField()
#
#     def __str__(self):
#         return f"Resultado de {self.partido}"
