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
    
    # Configuración de sets para el torneo
    MEJOR_DE_SETS = [
        (1, 'Mejor de 1 set'),
        (3, 'Mejor de 3 sets'),
        (5, 'Mejor de 5 sets'),
        (7, 'Mejor de 7 sets'),
        (9, 'Mejor de 9 sets'),
    ]
    mejor_de_sets = models.PositiveIntegerField(choices=MEJOR_DE_SETS, default=3)
    mejor_de_sets_final = models.PositiveIntegerField(choices=MEJOR_DE_SETS, default=5)
    
    organizador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='torneos')

    def __str__(self):
        return self.nombre
    
class Participacion(models.Model):
    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE, related_name='participaciones')
    jugador = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name='participaciones')
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('torneo', 'jugador')



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

class JugadorBye(models.Model):
    """Modelo para representar un BYE en las llaves del torneo"""
    nombre = models.CharField(max_length=50, default='BYE')
    posicion_bye = models.PositiveIntegerField()
    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE, related_name='byes')

    class Meta:
        unique_together = ('torneo', 'posicion_bye')

    def __str__(self):
        return f"BYE - Posición {self.posicion_bye}"

class LlaveTorneo(models.Model):
    """Modelo para representar las llaves de eliminación directa"""
    
    ESTADOS_PARTIDO = [
        ('pendiente', 'Pendiente'),
        ('en_curso', 'En curso'),
        ('jugado', 'Jugado'),
    ]
    
    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE, related_name='llaves')
    ronda = models.PositiveIntegerField()
    posicion = models.PositiveIntegerField()
    jugador1 = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name='llaves_jugador1', null=True, blank=True)
    jugador2 = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name='llaves_jugador2', null=True, blank=True)
    bye1 = models.ForeignKey(JugadorBye, on_delete=models.CASCADE, related_name='llaves_bye1', null=True, blank=True)
    bye2 = models.ForeignKey(JugadorBye, on_delete=models.CASCADE, related_name='llaves_bye2', null=True, blank=True)
    ganador = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name='llaves_ganadas', null=True, blank=True)
    estado_partido = models.CharField(max_length=20, choices=ESTADOS_PARTIDO, default='pendiente')
    
    class Meta:
        unique_together = ('torneo', 'ronda', 'posicion')
        ordering = ['ronda', 'posicion']

    def __str__(self):
        return f"Llave {self.posicion} - Ronda {self.ronda} - {self.torneo.nombre}"

    @property
    def jugador1_nombre(self):
        if self.jugador1:
            return f"{self.jugador1.nombre} {self.jugador1.apellido}"
        elif self.bye1:
            return "BYE"
        return "Vacío"

    @property
    def jugador2_nombre(self):
        if self.jugador2:
            return f"{self.jugador2.nombre} {self.jugador2.apellido}"
        elif self.bye2:
            return "BYE"
        return "Vacío"
    
    @property
    def estado_badge_class(self):
        """Devuelve la clase CSS para el badge según el estado"""
        if self.estado_partido == 'pendiente':
            return 'bg-secondary'
        elif self.estado_partido == 'en_curso':
            return 'bg-warning text-dark'
        elif self.estado_partido == 'jugado':
            return 'bg-success'
        return 'bg-secondary'
    
    @property
    def puede_editarse(self):
        """Indica si el partido puede ser editado por un árbitro"""
        return self.estado_partido == 'en_curso'
    
    @property
    def puede_iniciarse(self):
        """Indica si el partido puede ser iniciado por el organizador"""
        return self.estado_partido == 'pendiente'

class Partido(models.Model):
    """Modelo para representar partidos individuales en las llaves"""
    
    ESTADOS_PARTIDO = [
        ('pendiente', 'Pendiente'),
        ('en_curso', 'En curso'),
        ('jugado', 'Jugado'),
    ]
    
    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE, related_name='partidos')
    llave_torneo = models.ForeignKey(LlaveTorneo, on_delete=models.CASCADE, related_name='partidos')
    jugador1 = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name='partidos_jugador1', null=True, blank=True)
    jugador2 = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name='partidos_jugador2', null=True, blank=True)
    bye1 = models.ForeignKey(JugadorBye, on_delete=models.CASCADE, related_name='partidos_bye1', null=True, blank=True)
    bye2 = models.ForeignKey(JugadorBye, on_delete=models.CASCADE, related_name='partidos_bye2', null=True, blank=True)
    ganador = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name='partidos_ganados', null=True, blank=True)
    estado_partido = models.CharField(max_length=20, choices=ESTADOS_PARTIDO, default='pendiente')
    fecha_hora = models.DateTimeField(null=True, blank=True)
    organizador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='partidos_organizados')

    class Meta:
        unique_together = ('torneo', 'llave_torneo')

    def __str__(self):
        return f"{self.jugador1} vs {self.jugador2} - {self.torneo}"

    @property
    def jugador1_nombre(self):
        if self.jugador1:
            return f"{self.jugador1.nombre} {self.jugador1.apellido}"
        elif self.bye1:
            return "BYE"
        return "Vacío"

    @property
    def jugador2_nombre(self):
        if self.jugador2:
            return f"{self.jugador2.nombre} {self.jugador2.apellido}"
        elif self.bye2:
            return "BYE"
        return "Vacío"
    
    def es_partido_bye(self):
        """
        Verifica si este partido tiene un BYE (uno de los jugadores es BYE)
        """
        return bool(self.bye1 or self.bye2)
    
    def procesar_partido_bye(self):
        """
        Procesa automáticamente un partido con BYE:
        - Declara ganador al jugador real
        - Crea el resultado con sets ganados correspondientes
        - Cambia el estado a 'jugado'
        """
        if not self.es_partido_bye():
            return False, "Este partido no tiene un BYE"
        
        if self.estado_partido == 'jugado':
            return False, "El partido ya está terminado"
        
        # Determinar el ganador (el jugador real, no el BYE)
        if self.jugador1 and (self.bye2 or not self.jugador2):
            ganador = self.jugador1
        elif self.jugador2 and (self.bye1 or not self.jugador1):
            ganador = self.jugador2
        else:
            return False, "No se puede determinar el ganador automáticamente"
        
        # Calcular sets necesarios para ganar
        sets_para_ganar = (self.torneo.mejor_de_sets // 2) + 1
        
        try:
            # Crear o actualizar el resultado
            resultado, created = Resultado.objects.get_or_create(
                partido=self,
                defaults={
                    'set1_jugador1': sets_para_ganar if ganador == self.jugador1 else 0,
                    'set1_jugador2': sets_para_ganar if ganador == self.jugador2 else 0,
                    'set2_jugador1': 0,
                    'set2_jugador2': 0,
                    'set3_jugador1': 0,
                    'set3_jugador2': 0,
                    'set4_jugador1': 0,
                    'set4_jugador2': 0,
                    'set5_jugador1': 0,
                    'set5_jugador2': 0,
                }
            )
            
            if not created:
                # Si el resultado ya existe, actualizarlo
                if ganador == self.jugador1:
                    resultado.set1_jugador1 = sets_para_ganar
                    resultado.set1_jugador2 = 0
                else:
                    resultado.set1_jugador1 = 0
                    resultado.set1_jugador2 = sets_para_ganar
                    
                resultado.set2_jugador1 = 0
                resultado.set2_jugador2 = 0
                resultado.set3_jugador1 = 0
                resultado.set3_jugador2 = 0
                resultado.set4_jugador1 = 0
                resultado.set4_jugador2 = 0
                resultado.set5_jugador1 = 0
                resultado.set5_jugador2 = 0
                resultado.save()  # Esto también calculará automáticamente los sets ganados
            
            # Asignar ganador y cambiar estado
            self.ganador = ganador
            self.estado_partido = 'jugado'
            self.save()
            
            ganador_nombre = f"{ganador.nombre} {ganador.apellido}"
            return True, f"Partido procesado automáticamente. Ganador: {ganador_nombre} por BYE"
            
        except Exception as e:
            return False, f"Error al procesar el partido: {str(e)}"
    
    def verificar_y_cerrar_partido(self):
        """
        Verifica si el partido debe cerrarse automáticamente basado en los sets ganados
        """
        if self.estado_partido == 'jugado':
            return False, "El partido ya está terminado"
        
        if not hasattr(self, 'resultado'):
            return False, "No hay resultado para este partido"
        
        sets_para_ganar = (self.torneo.mejor_de_sets // 2) + 1
        resultado = self.resultado
        
        if resultado.sets_ganados_jugador1 >= sets_para_ganar or resultado.sets_ganados_jugador2 >= sets_para_ganar:
            # Determinar el ganador
            if resultado.sets_ganados_jugador1 > resultado.sets_ganados_jugador2:
                self.ganador = self.jugador1
            elif resultado.sets_ganados_jugador2 > resultado.sets_ganados_jugador1:
                self.ganador = self.jugador2
            else:
                return False, "Empate en sets ganados - no se puede determinar ganador"
            
            # Cambiar estado del partido a "jugado"
            self.estado_partido = 'jugado'
            self.save()
            
            ganador_nombre = f"{self.ganador.nombre} {self.ganador.apellido}" if self.ganador else "N/A"
            return True, f"Partido cerrado automáticamente. Ganador: {ganador_nombre} ({resultado.sets_ganados_jugador1}-{resultado.sets_ganados_jugador2})"
        
        return False, "El partido aún no tiene un ganador definido"

class Resultado(models.Model):
    """Modelo para registrar los puntos de cada set en los partidos"""
    
    partido = models.OneToOneField(Partido, on_delete=models.CASCADE, related_name='resultado')
    
    # Puntos de cada set para el jugador 1
    set1_jugador1 = models.PositiveIntegerField(default=0)
    set2_jugador1 = models.PositiveIntegerField(default=0)
    set3_jugador1 = models.PositiveIntegerField(default=0)
    set4_jugador1 = models.PositiveIntegerField(default=0, blank=True)
    set5_jugador1 = models.PositiveIntegerField(default=0, blank=True)
    
    # Puntos de cada set para el jugador 2
    set1_jugador2 = models.PositiveIntegerField(default=0)
    set2_jugador2 = models.PositiveIntegerField(default=0)
    set3_jugador2 = models.PositiveIntegerField(default=0)
    set4_jugador2 = models.PositiveIntegerField(default=0, blank=True)
    set5_jugador2 = models.PositiveIntegerField(default=0, blank=True)
    
    # Campos calculados automáticamente
    sets_ganados_jugador1 = models.PositiveIntegerField(default=0)
    sets_ganados_jugador2 = models.PositiveIntegerField(default=0)
    resultado_jugador_1 = models.DecimalField(max_digits=5, decimal_places=3, null=True, blank=True)
    resultado_jugador_2 = models.DecimalField(max_digits=5, decimal_places=3, null=True, blank=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Resultado: {self.sets_ganados_jugador1}-{self.sets_ganados_jugador2} sets - {self.partido}"
    
    def calcular_sets_ganados(self):
        """Calcula cuántos sets ganó cada jugador basado en los puntos"""
        sets_j1 = 0
        sets_j2 = 0
        mejor_de_sets = self.partido.torneo.mejor_de_sets
        
        # Evaluar cada set jugado
        sets_a_evaluar = [
            (self.set1_jugador1, self.set1_jugador2),
            (self.set2_jugador1, self.set2_jugador2),
            (self.set3_jugador1, self.set3_jugador2),
        ]
        
        # Agregar sets adicionales si el torneo es al mejor de 5
        if mejor_de_sets == 5:
            if self.set4_jugador1 > 0 or self.set4_jugador2 > 0:
                sets_a_evaluar.append((self.set4_jugador1, self.set4_jugador2))
            if self.set5_jugador1 > 0 or self.set5_jugador2 > 0:
                sets_a_evaluar.append((self.set5_jugador1, self.set5_jugador2))
        
        for puntos_j1, puntos_j2 in sets_a_evaluar:
            # Solo contar sets que han sido realmente jugados (ambos jugadores tienen puntos o hay un ganador claro)
            if (puntos_j1 > 0 or puntos_j2 > 0) and (puntos_j1 != puntos_j2):
                if puntos_j1 > puntos_j2:
                    sets_j1 += 1
                elif puntos_j2 > puntos_j1:
                    sets_j2 += 1
        
        self.sets_ganados_jugador1 = sets_j1
        self.sets_ganados_jugador2 = sets_j2
    
    def calcular_coeficientes(self):
        """Calcula los coeficientes de puntos para ambos jugadores"""
        if self.sets_ganados_jugador2 > 0:
            self.resultado_jugador_1 = round(self.sets_ganados_jugador1 / self.sets_ganados_jugador2, 3)
        else:
            self.resultado_jugador_1 = self.sets_ganados_jugador1 if self.sets_ganados_jugador1 > 0 else 0
            
        if self.sets_ganados_jugador1 > 0:
            self.resultado_jugador_2 = round(self.sets_ganados_jugador2 / self.sets_ganados_jugador1, 3)
        else:
            self.resultado_jugador_2 = self.sets_ganados_jugador2 if self.sets_ganados_jugador2 > 0 else 0
    
    def obtener_sets_guardados(self):
        """
        Retorna un diccionario indicando qué sets ya están guardados y no deberían modificarse.
        Un set se considera guardado si ambos jugadores tienen puntos > 0.
        """
        sets_guardados = {
            'set1': self.set1_jugador1 > 0 or self.set1_jugador2 > 0,
            'set2': self.set2_jugador1 > 0 or self.set2_jugador2 > 0,
            'set3': self.set3_jugador1 > 0 or self.set3_jugador2 > 0,
            'set4': self.set4_jugador1 > 0 or self.set4_jugador2 > 0,
            'set5': self.set5_jugador1 > 0 or self.set5_jugador2 > 0,
        }
        return sets_guardados
    
    def obtener_resultado_detallado(self):
        """Devuelve el resultado detallado set por set"""
        mejor_de_sets = self.partido.torneo.mejor_de_sets
        sets_resultado = []
        
        # Siempre mostrar los primeros 3 sets
        sets_puntos = [
            (self.set1_jugador1, self.set1_jugador2),
            (self.set2_jugador1, self.set2_jugador2),
            (self.set3_jugador1, self.set3_jugador2),
        ]
        
        # Agregar sets adicionales si es al mejor de 5
        if mejor_de_sets == 5:
            if self.set4_jugador1 > 0 or self.set4_jugador2 > 0:
                sets_puntos.append((self.set4_jugador1, self.set4_jugador2))
            if self.set5_jugador1 > 0 or self.set5_jugador2 > 0:
                sets_puntos.append((self.set5_jugador1, self.set5_jugador2))
        
        for i, (puntos_j1, puntos_j2) in enumerate(sets_puntos, 1):
            if puntos_j1 > 0 or puntos_j2 > 0:  # Solo mostrar sets jugados
                sets_resultado.append(f"Set {i}: {puntos_j1}-{puntos_j2}")
        
        return " | ".join(sets_resultado) if sets_resultado else "Sin sets jugados"
    
    def save(self, *args, **kwargs):
        """Override save para calcular automáticamente sets ganados y coeficientes"""
        self.calcular_sets_ganados()
        self.calcular_coeficientes()
        super().save(*args, **kwargs)
        
        # Verificar si el partido debe cerrarse automáticamente después de guardar
        if hasattr(self, 'partido'):
            self.partido.verificar_y_cerrar_partido()
    
    def definir_ganador_directo(self, jugador_ganador):
        """
        Define directamente un ganador para el partido sin registrar sets detallados.
        Reutiliza la misma lógica que el procesamiento de BYE.
        
        Args:
            jugador_ganador: El jugador que se declarará como ganador (self.partido.jugador1 o self.partido.jugador2)
        """
        if self.partido.estado_partido == 'jugado':
            return False, "El partido ya está terminado"
        
        if jugador_ganador not in [self.partido.jugador1, self.partido.jugador2]:
            return False, "El jugador especificado no participa en este partido"
        
        if not jugador_ganador:
            return False, "Jugador ganador no válido"
        
        # Calcular sets necesarios para ganar (misma lógica que BYE)
        sets_para_ganar = (self.partido.torneo.mejor_de_sets // 2) + 1
        
        try:
            # Actualizar el resultado directamente
            if jugador_ganador == self.partido.jugador1:
                self.set1_jugador1 = sets_para_ganar
                self.set1_jugador2 = 0
            else:
                self.set1_jugador1 = 0
                self.set1_jugador2 = sets_para_ganar
                
            # Limpiar el resto de sets
            self.set2_jugador1 = 0
            self.set2_jugador2 = 0
            self.set3_jugador1 = 0
            self.set3_jugador2 = 0
            self.set4_jugador1 = 0
            self.set4_jugador2 = 0
            self.set5_jugador1 = 0
            self.set5_jugador2 = 0
            
            # Guardar resultado (esto calculará automáticamente los sets ganados)
            self.save()
            
            # Asignar ganador y cambiar estado del partido
            self.partido.ganador = jugador_ganador
            self.partido.estado_partido = 'jugado'
            self.partido.save()
            
            ganador_nombre = f"{jugador_ganador.nombre} {jugador_ganador.apellido}"
            perdedor = self.partido.jugador2 if jugador_ganador == self.partido.jugador1 else self.partido.jugador1
            perdedor_nombre = f"{perdedor.nombre} {perdedor.apellido}" if perdedor else "N/A"
            
            return True, f"Ganador definido: {ganador_nombre} vs {perdedor_nombre} - Victoria directa"
            
        except Exception as e:
            return False, f"Error al definir ganador: {str(e)}"
