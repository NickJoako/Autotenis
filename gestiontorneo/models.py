from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from datetime import date
from django.conf import settings

class UsuarioPersonalizado(AbstractUser):
    """
    Modelo personalizado de usuario que extiende AbstractUser.
    
    Permite diferentes tipos de usuarios (organizador, árbitro, jugador) y utiliza
    el email como campo principal de autenticación en lugar del username.
    
    Attributes:
        username (CharField): Nombre de usuario con longitud máxima de 20 caracteres
        tipo_usuario (CharField): Tipo de usuario ('organizador', 'arbitro', 'jugador')
        activo (BooleanField): Estado activo del usuario
    """
    username = models.CharField(
        max_length=20,
        unique=False,  # Permitir usernames duplicados
        help_text='',
        validators=[UnicodeUsernameValidator()],
    )
    TIPO_USUARIO = [
        ('organizador', 'Organizador'),
        ('arbitro', 'Árbitro'),
        ('jugador', 'Jugador'),
    ]
    tipo_usuario = models.CharField(max_length=20, choices=TIPO_USUARIO, null=False, blank=False)
    activo = models.BooleanField(default=True)

    # Usar email como campo principal de autenticación
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        # Hacer que email + tipo_usuario sean únicos juntos
        unique_together = [['email', 'tipo_usuario']]
        verbose_name = 'Usuario Personalizado'
        verbose_name_plural = 'Usuarios Personalizados'

    def __str__(self):
        """
        Representación en string del usuario.
        
        Returns:
            str: Formato "username (tipo_usuario)"
        """
        return f"{self.username} ({self.tipo_usuario})"

class Club(models.Model):
    """
    Modelo que representa un club deportivo.
    
    Attributes:
        nombre (CharField): Nombre único del club
    """
    nombre = models.CharField(max_length=100, unique=True) 

    def __str__(self):
        """
        Representación en string del club.
        
        Returns:
            str: Nombre del club
        """
        return self.nombre

class Categoria(models.Model):
    """
    Modelo que representa una categoría por edad en los torneos.
    
    Attributes:
        nombre (CharField): Nombre de la categoría
        edad_minima (PositiveIntegerField): Edad mínima para la categoría
        edad_maxima (PositiveIntegerField): Edad máxima para la categoría
    """
    nombre = models.CharField(max_length=100)
    edad_minima = models.PositiveIntegerField(null=True, blank=True)
    edad_maxima = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        """
        Representación en string de la categoría.
        
        Returns:
            str: Nombre de la categoría
        """
        return self.nombre

    def rango_edades(self):
        """
        Obtiene el rango de edades de la categoría en formato texto.
        
        Returns:
            str: Descripción del rango de edades de la categoría
        """
        if self.edad_minima is not None and self.edad_maxima is not None:
            return f"{self.edad_minima}-{self.edad_maxima}"
        elif self.edad_minima is not None:
            return f"Desde {self.edad_minima}"
        elif self.edad_maxima is not None:
            return f"Hasta {self.edad_maxima}"
        else:
            return "Sin restricción"
        
    def rango_anios_nacimiento(self):
        """
        Calcula el rango de años de nacimiento correspondiente a la categoría.
        
        Returns:
            str: Descripción del rango de años de nacimiento válidos
        """
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
    """
    Modelo que representa un jugador de tenis.
    
    Attributes:
        rut (CharField): RUT único del jugador
        nombre (CharField): Nombre del jugador
        apellido (CharField): Apellido del jugador
        fecha_nacimiento (DateField): Fecha de nacimiento
        genero (CharField): Género del jugador ('M' o 'F')
        club (ForeignKey): Club al que pertenece el jugador
        email (EmailField): Email único del jugador
    """
    rut = models.CharField(max_length=12, unique=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    fecha_nacimiento = models.DateField()
    genero = models.CharField(max_length=1, choices=[('M', 'Masculino'), ('F', 'Femenino')])
    club = models.ForeignKey(Club, on_delete=models.SET_NULL, null=True, blank=True)
    email = models.EmailField(blank=True, null=True, unique=True)

    def __str__(self):
        """
        Representación en string del jugador.
        
        Returns:
            str: Formato "nombre apellido (rut)"
        """
        return f"{self.nombre} {self.apellido} ({self.rut})"
    
    def calcular_categoria(self):
        """
        Calcula la categoría correspondiente al jugador basada en su edad.
        
        Returns:
            str: Nombre de la categoría correspondiente o "Sin categoría" si no encuentra una
        """
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
    """
    Modelo que representa un torneo de tenis.
    
    Attributes:
        nombre (CharField): Nombre del torneo
        fecha (DateField): Fecha del torneo
        hora (TimeField): Hora de inicio del torneo
        ubicacion (CharField): Lugar donde se realiza el torneo
        federado (BooleanField): Si el torneo es federado o no
        categoria (ForeignKey): Categoría del torneo
        todo_competidor (BooleanField): Si está abierto a todos los competidores
        inscripciones_cerradas (BooleanField): Estado de las inscripciones
        modalidad (CharField): Modalidad del torneo ('llaves' o 'grupos')
        torneo_iniciado (BooleanField): Si el torneo ha comenzado
        finalizado (BooleanField): Si el torneo ha finalizado
        mejor_de_sets (PositiveIntegerField): Formato de sets para partidos regulares
        mejor_de_sets_final (PositiveIntegerField): Formato de sets para la final
        organizador (ForeignKey): Usuario organizador del torneo
    """
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
    finalizado = models.BooleanField(default=False)
    
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
        """
        Representación en string del torneo.
        
        Returns:
            str: Nombre del torneo
        """
        return self.nombre
    
class Participacion(models.Model):
    """
    Modelo que representa la participación de un jugador en un torneo.
    
    Attributes:
        torneo (ForeignKey): Torneo en el que participa
        jugador (ForeignKey): Jugador que participa
        fecha_registro (DateTimeField): Fecha y hora de registro
    """
    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE, related_name='participaciones')
    jugador = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name='participaciones')
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('torneo', 'jugador')



class ArbitroTorneo(models.Model):
    """Modelo para relacionar árbitros con torneos"""
    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE, related_name='arbitros_asignados')
    arbitro = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='torneos_asignados')
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ('torneo', 'arbitro')
        verbose_name = 'Árbitro del Torneo'
        verbose_name_plural = 'Árbitros del Torneo'

    def __str__(self):
        return f"{self.arbitro.first_name} {self.arbitro.last_name} - {self.torneo.nombre}"

class GrupoTorneo(models.Model):
    """
    Modelo que representa un grupo dentro de un torneo de modalidad grupos.
    
    Attributes:
        torneo (ForeignKey): Torneo al que pertenece el grupo
        nombre (CharField): Nombre del grupo (A, B, C, etc.)
        numero (PositiveIntegerField): Número del grupo
    """
    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE, related_name='grupos')
    nombre = models.CharField(max_length=10)  # A, B, C, etc.
    numero = models.PositiveIntegerField()  # 1, 2, 3, etc.

    class Meta:
        unique_together = ('torneo', 'numero')
        ordering = ['numero']

    def __str__(self):
        """
        Representación en string del grupo.
        
        Returns:
            str: Formato "Grupo {nombre} - {torneo}"
        """
        return f"Grupo {self.nombre} - {self.torneo.nombre}"

class ParticipanteGrupo(models.Model):
    """
    Modelo que representa un participante dentro de un grupo específico.
    
    Attributes:
        grupo (ForeignKey): Grupo al que pertenece
        jugador (ForeignKey): Jugador participante
        es_cabeza_serie (BooleanField): Si es cabeza de serie
        posicion_grupo (PositiveIntegerField): Posición dentro del grupo
    """
    grupo = models.ForeignKey(GrupoTorneo, on_delete=models.CASCADE, related_name='participantes')
    jugador = models.ForeignKey(Jugador, on_delete=models.CASCADE)
    es_cabeza_serie = models.BooleanField(default=False)
    posicion_grupo = models.PositiveIntegerField()  # 1, 2, 3, 4 dentro del grupo

    class Meta:
        unique_together = ('grupo', 'jugador')
        ordering = ['posicion_grupo']

    def __str__(self):
        """
        Representación en string del participante.
        
        Returns:
            str: Formato "{nombre} {apellido} - {grupo}"
        """
        return f"{self.jugador.nombre} {self.jugador.apellido} - {self.grupo.nombre}"

class JugadorBye(models.Model):
    """
    Modelo para representar un BYE en las llaves del torneo.
    
    Un BYE es un pase automático a la siguiente ronda cuando un jugador
    no tiene oponente en una posición específica de la llave.
    
    Attributes:
        nombre (CharField): Nombre del BYE (por defecto 'BYE')
        posicion_bye (PositiveIntegerField): Posición del BYE en la llave
        torneo (ForeignKey): Torneo al que pertenece el BYE
    """
    nombre = models.CharField(max_length=50, default='BYE')
    posicion_bye = models.PositiveIntegerField()
    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE, related_name='byes')

    class Meta:
        unique_together = ('torneo', 'posicion_bye')

    def __str__(self):
        """
        Representación en string del BYE.
        
        Returns:
            str: Formato "BYE - Posición {posicion}"
        """
        return f"BYE - Posición {self.posicion_bye}"

class LlaveTorneo(models.Model):
    """
    Modelo para representar las llaves de eliminación directa.
    
    Gestiona la estructura de brackets/llaves en torneos de eliminación directa,
    incluyendo tanto partidos normales como partidos por el tercer lugar.
    
    Attributes:
        torneo (ForeignKey): Torneo al que pertenece la llave
        ronda (PositiveIntegerField): Número de ronda (1, 2, 3, etc.)
        posicion (PositiveIntegerField): Posición dentro de la ronda
        tipo_llave (CharField): Tipo de llave ('normal' o 'tercer_lugar')
        jugador1 (ForeignKey): Primer jugador del enfrentamiento
        jugador2 (ForeignKey): Segundo jugador del enfrentamiento
        bye1 (ForeignKey): BYE para el primer jugador si aplica
        bye2 (ForeignKey): BYE para el segundo jugador si aplica
        ganador (ForeignKey): Jugador ganador del enfrentamiento
        estado_partido (CharField): Estado actual del partido
    """
    
    ESTADOS_PARTIDO = [
        ('pendiente', 'Pendiente'),
        ('en_curso', 'En curso'),
        ('jugado', 'Jugado'),
    ]
    
    TIPOS_LLAVE = [
        ('normal', 'Normal'),
        ('tercer_lugar', 'Tercer Lugar'),
    ]
    
    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE, related_name='llaves')
    ronda = models.PositiveIntegerField()
    posicion = models.PositiveIntegerField()
    tipo_llave = models.CharField(max_length=20, choices=TIPOS_LLAVE, default='normal')
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
        """
        Representación en string de la llave.
        
        Returns:
            str: Formato "Llave {posicion} - Ronda {ronda} - {torneo}"
        """
        return f"Llave {self.posicion} - Ronda {self.ronda} - {self.torneo.nombre}"

    @property
    def jugador1_nombre(self):
        """
        Obtiene el nombre del primer jugador o BYE.
        
        Returns:
            str: Nombre del jugador, "BYE" o "Vacío"
        """
        if self.jugador1:
            return f"{self.jugador1.nombre} {self.jugador1.apellido}"
        elif self.bye1:
            return "BYE"
        return "Vacío"

    @property
    def jugador2_nombre(self):
        """
        Obtiene el nombre del segundo jugador o BYE.
        
        Returns:
            str: Nombre del jugador, "BYE" o "Vacío"
        """
        if self.jugador2:
            return f"{self.jugador2.nombre} {self.jugador2.apellido}"
        elif self.bye2:
            return "BYE"
        return "Vacío"
    
    @property
    def estado_badge_class(self):
        """
        Devuelve la clase CSS para el badge según el estado.
        
        Returns:
            str: Clase CSS para mostrar el estado del partido
        """
        if self.estado_partido == 'pendiente':
            return 'bg-secondary'
        elif self.estado_partido == 'en_curso':
            return 'bg-warning text-dark'
        elif self.estado_partido == 'jugado':
            return 'bg-success'
        return 'bg-secondary'
    
    @property
    def puede_editarse(self):
        """
        Indica si el partido puede ser editado por un árbitro.
        
        Returns:
            bool: True si el partido está en curso y puede editarse
        """
        return self.estado_partido == 'en_curso'
    
    @property
    def puede_iniciarse(self):
        """
        Indica si el partido puede ser iniciado por el organizador.
        
        Returns:
            bool: True si el partido está pendiente y puede iniciarse
        """
        return self.estado_partido == 'pendiente'

class Partido(models.Model):
    """
    Modelo para representar partidos individuales en las llaves.
    
    Gestiona todos los aspectos de un partido específico, incluyendo jugadores,
    estado, programación, arbitraje y resultados.
    
    Attributes:
        torneo (ForeignKey): Torneo al que pertenece el partido
        llave_torneo (ForeignKey): Llave específica del torneo
        jugador1 (ForeignKey): Primer jugador del partido
        jugador2 (ForeignKey): Segundo jugador del partido
        bye1 (ForeignKey): BYE para el primer jugador si aplica
        bye2 (ForeignKey): BYE para el segundo jugador si aplica
        ganador (ForeignKey): Jugador ganador del partido
        arbitro (ForeignKey): Árbitro asignado al partido
        estado_partido (CharField): Estado actual del partido
        fecha_hora (DateTimeField): Fecha y hora del partido
        fecha_programada (DateField): Fecha programada para el partido
        hora_programada (TimeField): Hora programada para el partido
        fecha_inicio (DateTimeField): Fecha y hora de inicio real
        fecha_fin (DateTimeField): Fecha y hora de finalización
        marcador (CharField): Marcador final del partido
        observaciones (TextField): Observaciones adicionales
        finalizado (BooleanField): Si el partido ha finalizado
        pendiente_confirmacion (BooleanField): Si está pendiente de confirmación
        organizador (ForeignKey): Organizador responsable del partido
    """
    
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
    arbitro = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='partidos_arbitrados', null=True, blank=True)
    estado_partido = models.CharField(max_length=20, choices=ESTADOS_PARTIDO, default='pendiente')
    fecha_hora = models.DateTimeField(null=True, blank=True)
    fecha_programada = models.DateField(null=True, blank=True)
    hora_programada = models.TimeField(null=True, blank=True)
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    marcador = models.CharField(max_length=100, null=True, blank=True)
    observaciones = models.TextField(null=True, blank=True)
    finalizado = models.BooleanField(default=False)
    pendiente_confirmacion = models.BooleanField(default=False)
    organizador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='partidos_organizados')

    class Meta:
        unique_together = ('torneo', 'llave_torneo')

    def __str__(self):
        """
        Representación en string del partido.
        
        Returns:
            str: Formato "{jugador1} vs {jugador2} - {torneo}"
        """
        return f"{self.jugador1} vs {self.jugador2} - {self.torneo}"

    @property
    def jugador1_nombre(self):
        """
        Obtiene el nombre del primer jugador o BYE.
        
        Returns:
            str: Nombre del jugador, "BYE" o "Vacío"
        """
        if self.jugador1:
            return f"{self.jugador1.nombre} {self.jugador1.apellido}"
        elif self.bye1:
            return "BYE"
        return "Vacío"

    @property
    def jugador2_nombre(self):
        """
        Obtiene el nombre del segundo jugador o BYE.
        
        Returns:
            str: Nombre del jugador, "BYE" o "Vacío"
        """
        if self.jugador2:
            return f"{self.jugador2.nombre} {self.jugador2.apellido}"
        elif self.bye2:
            return "BYE"
        return "Vacío"
    
    def es_partido_bye(self):
        """
        Verifica si este partido tiene un BYE (uno de los jugadores es BYE).
        
        Returns:
            bool: True si hay un BYE en el partido
        """
        return bool(self.bye1 or self.bye2)
    
    def procesar_partido_bye(self):
        """
        Procesa automáticamente un partido con BYE.
        
        - Declara ganador al jugador real
        - Crea el resultado con sets ganados correspondientes
        - Cambia el estado a 'jugado'
        - Avanza automáticamente al ganador a la siguiente ronda
        
        Returns:
            tuple: (bool, str) - (éxito, mensaje)
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
        
        # Determinar si es un partido final para usar la modalidad correcta
        total_rondas = self.torneo.llaves.aggregate(max_ronda=models.Max('ronda'))['max_ronda'] or 1
        es_partido_final = self.llave_torneo.ronda == total_rondas
        
        # Usar la modalidad correcta según si es final o no
        mejor_de_sets = self.torneo.mejor_de_sets_final if es_partido_final else self.torneo.mejor_de_sets
        sets_para_ganar = (mejor_de_sets // 2) + 1
        
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
            
            # **CRUCIAL**: Actualizar también el ganador en la LlaveTorneo
            if self.llave_torneo:
                self.llave_torneo.ganador = ganador
                self.llave_torneo.estado_partido = 'jugado'
                self.llave_torneo.save()
            
            # Avanzar automáticamente a la siguiente ronda
            self.avanzar_ganador_automaticamente()
            
            # Verificar si se completaron las semifinales para crear tercer lugar
            self.verificar_y_crear_tercer_lugar()
            
            ganador_nombre = f"{ganador.nombre} {ganador.apellido}"
            return True, f"Partido procesado automáticamente. Ganador: {ganador_nombre} por BYE"
            
        except Exception as e:
            return False, f"Error al procesar el partido: {str(e)}"
    
    def verificar_y_cerrar_partido(self):
        """
        Verifica si el partido debe cerrarse automáticamente basado en los sets ganados.
        
        NUEVO: Solo marca para confirmación, no cierra automáticamente.
        Determina el ganador provisional cuando se alcanza el número de sets necesarios.
        
        Returns:
            tuple: (bool, str) - (éxito, mensaje)
        """
        if self.estado_partido == 'jugado':
            return False, "El partido ya está terminado"
        
        if not hasattr(self, 'resultado_detallado'):
            return False, "No hay resultado para este partido"
        
        # Determinar si es un partido final para usar la modalidad correcta
        total_rondas = self.torneo.llaves.aggregate(max_ronda=models.Max('ronda'))['max_ronda'] or 1
        es_partido_final = self.llave_torneo.ronda == total_rondas
        
        # Usar la modalidad correcta según si es final o no
        mejor_de_sets = self.torneo.mejor_de_sets_final if es_partido_final else self.torneo.mejor_de_sets
        sets_para_ganar = (mejor_de_sets // 2) + 1
        resultado = self.resultado_detallado
        
        if resultado.sets_ganados_jugador1 >= sets_para_ganar or resultado.sets_ganados_jugador2 >= sets_para_ganar:
            # Determinar el ganador provisional
            if resultado.sets_ganados_jugador1 > resultado.sets_ganados_jugador2:
                ganador_provisional = self.jugador1
            elif resultado.sets_ganados_jugador2 > resultado.sets_ganados_jugador1:
                ganador_provisional = self.jugador2
            else:
                return False, "Empate en sets ganados - no se puede determinar ganador"
            
            # **NUEVO**: Marcar como pendiente de confirmación en lugar de cerrar
            self.pendiente_confirmacion = True
            self.ganador = ganador_provisional  # Guardar ganador provisional
            self.save()
            
            ganador_nombre = f"{ganador_provisional.nombre} {ganador_provisional.apellido}"
            return True, f"Resultado enviado para confirmación del organizador. Ganador provisional: {ganador_nombre} ({resultado.sets_ganados_jugador1}-{resultado.sets_ganados_jugador2})"
        
        return False, "El partido aún no tiene un ganador definido"

    def confirmar_y_cerrar_partido(self):
        """
        NUEVO: Método para que el organizador confirme y cierre definitivamente el partido.
        
        Finaliza un partido que está pendiente de confirmación, actualizando
        el estado y avanzando al ganador a la siguiente ronda.
        
        Returns:
            tuple: (bool, str) - (éxito, mensaje)
        """
        if self.estado_partido == 'jugado':
            return False, "El partido ya está terminado"
        
        if not self.pendiente_confirmacion:
            return False, "El partido no está pendiente de confirmación"
        
        # Cerrar el partido definitivamente
        self.estado_partido = 'jugado'
        self.pendiente_confirmacion = False
        self.finalizado = True  # NUEVO: Marcar como finalizado para el panel de árbitros
        self.save()
        
        # Actualizar también el ganador en la LlaveTorneo
        if self.llave_torneo:
            self.llave_torneo.ganador = self.ganador
            self.llave_torneo.estado_partido = 'jugado'
            self.llave_torneo.save()
        
        # Avanzar automáticamente a la siguiente ronda
        self.avanzar_ganador_automaticamente()
        
        # Verificar si se completaron las semifinales para crear tercer lugar
        self.verificar_y_crear_tercer_lugar()
        
        ganador_nombre = f"{self.ganador.nombre} {self.ganador.apellido}" if self.ganador else "N/A"
        return True, f"Partido confirmado y cerrado. Ganador: {ganador_nombre}"
    
    def avanzar_ganador_automaticamente(self):
        """
        Avanza automáticamente al ganador a la siguiente ronda.
        
        Calcula la posición correcta en la siguiente ronda y asigna
        al ganador como jugador1 o jugador2 según corresponda.
        Si ambos jugadores están listos, crea el partido automáticamente.
        """
        if not self.ganador or not self.llave_torneo:
            return
        
        try:
            # Obtener la ronda actual y siguiente
            ronda_actual = self.llave_torneo.ronda
            ronda_siguiente = ronda_actual + 1
            
            # Buscar la llave de la siguiente ronda donde debe ir este ganador
            # Algoritmo: posición en ronda siguiente = (posición_actual + 1) // 2
            posicion_siguiente = (self.llave_torneo.posicion + 1) // 2
            
            # Buscar la llave de destino en la siguiente ronda
            llave_siguiente = LlaveTorneo.objects.filter(
                torneo=self.torneo,
                ronda=ronda_siguiente,
                posicion=posicion_siguiente
            ).first()
            
            if llave_siguiente:
                # Determinar si el ganador va como jugador1 o jugador2
                # Si la posición actual es impar, va como jugador1
                # Si la posición actual es par, va como jugador2
                if self.llave_torneo.posicion % 2 == 1:
                    # Posición impar -> jugador1 en la siguiente ronda
                    llave_siguiente.jugador1 = self.ganador
                else:
                    # Posición par -> jugador2 en la siguiente ronda
                    llave_siguiente.jugador2 = self.ganador
                
                llave_siguiente.save()
                print(f"✅ Ganador {self.ganador.nombre} {self.ganador.apellido} avanzado automáticamente a la ronda {ronda_siguiente}, posición {posicion_siguiente}")
                
                # Si ambos jugadores ya están asignados en la siguiente ronda, crear el partido
                if llave_siguiente.jugador1 and llave_siguiente.jugador2:
                    self.crear_partido_siguiente_ronda(llave_siguiente)
            
        except Exception as e:
            print(f"❌ Error al avanzar ganador automáticamente: {e}")
    
    def crear_partido_siguiente_ronda(self, llave_siguiente):
        """
        Crea automáticamente el partido para la siguiente ronda si ambos jugadores están listos.
        
        Args:
            llave_siguiente (LlaveTorneo): La llave de la siguiente ronda donde crear el partido
        """
        try:
            # Verificar si ya existe un partido para esta llave
            partido_existente = Partido.objects.filter(
                torneo=self.torneo, 
                llave_torneo=llave_siguiente
            ).first()
            
            if not partido_existente:
                # Crear el nuevo partido
                nuevo_partido = Partido.objects.create(
                    torneo=self.torneo,
                    llave_torneo=llave_siguiente,
                    jugador1=llave_siguiente.jugador1,
                    jugador2=llave_siguiente.jugador2,
                    bye1=llave_siguiente.bye1,
                    bye2=llave_siguiente.bye2,
                    estado_partido='en_curso',
                    organizador=self.torneo.organizador
                )
                
                # Crear el resultado automáticamente
                Resultado.objects.create(partido=nuevo_partido)
                
                print(f"✅ Partido creado automáticamente para la ronda {llave_siguiente.ronda}: {llave_siguiente.jugador1.nombre} vs {llave_siguiente.jugador2.nombre}")
                
        except Exception as e:
            print(f"❌ Error al crear partido siguiente ronda: {e}")

    def verificar_y_crear_tercer_lugar(self):
        """
        Verifica si se completaron las semifinales y crea automáticamente el partido de tercer lugar.
        
        Detecta cuando ambas semifinales han terminado, obtiene los perdedores
        y crea el partido por el tercer puesto automáticamente.
        """
        try:
            # Obtener información de la estructura del torneo
            total_rondas = LlaveTorneo.objects.filter(torneo=self.torneo).aggregate(
                max_ronda=models.Max('ronda')
            )['max_ronda']
            
            if not total_rondas or total_rondas < 3:
                return  # No hay suficientes rondas para tener semifinales
            
            # Verificar si este partido pertenece a las semifinales
            ronda_semifinales = total_rondas - 1
            
            if self.llave_torneo.ronda != ronda_semifinales:
                return  # Este no es un partido de semifinales
            
            # Verificar si ya existe una llave de tercer lugar
            llave_tercer_lugar_existente = LlaveTorneo.objects.filter(
                torneo=self.torneo,
                tipo_llave='tercer_lugar'
            ).exists()
            
            if llave_tercer_lugar_existente:
                return  # Ya existe el tercer lugar
            
            # Verificar si todas las semifinales están completas
            semifinales = LlaveTorneo.objects.filter(
                torneo=self.torneo,
                ronda=ronda_semifinales,
                tipo_llave='normal'
            )
            
            if semifinales.count() != 2:
                return  # No hay exactamente 2 semifinales
            
            semifinales_completas = semifinales.filter(ganador__isnull=False)
            
            if semifinales_completas.count() != 2:
                return  # No todas las semifinales están completas
            
            # Obtener los perdedores de las semifinales
            perdedores = []
            for semifinal in semifinales:
                if semifinal.ganador == semifinal.jugador1:
                    perdedor = semifinal.jugador2
                elif semifinal.ganador == semifinal.jugador2:
                    perdedor = semifinal.jugador1
                else:
                    continue
                
                if perdedor:
                    perdedores.append(perdedor)
            
            if len(perdedores) != 2:
                return  # No se pudieron obtener 2 perdedores
            
            # Crear la llave de tercer lugar
            llave_tercer_lugar = LlaveTorneo.objects.create(
                torneo=self.torneo,
                ronda=ronda_semifinales,
                posicion=999,
                tipo_llave='tercer_lugar',
                jugador1=perdedores[0],
                jugador2=perdedores[1],
                estado_partido='pendiente'
            )
            
            # Crear el partido de tercer lugar
            partido_tercer_lugar = Partido.objects.create(
                torneo=self.torneo,
                llave_torneo=llave_tercer_lugar,
                jugador1=perdedores[0],
                jugador2=perdedores[1],
                estado_partido='en_curso',  # Cambiar a 'en_curso' para permitir registro de resultados
                organizador=self.torneo.organizador
            )
            
            # Crear el resultado
            Resultado.objects.create(partido=partido_tercer_lugar)
            
            print(f"🥉 Tercer lugar creado automáticamente: {perdedores[0].nombre} vs {perdedores[1].nombre}")
            
        except Exception as e:
            print(f"❌ Error al verificar/crear tercer lugar: {str(e)}")

class Resultado(models.Model):
    """
    Modelo para registrar los puntos de cada set en los partidos.
    
    Gestiona el marcador detallado de cada partido, calculando automáticamente
    los sets ganados por cada jugador y los coeficientes correspondientes.
    
    Attributes:
        partido (OneToOneField): Partido al que pertenece este resultado
        set1_jugador1 - set9_jugador1 (PositiveIntegerField): Puntos del jugador 1 en cada set
        set1_jugador2 - set9_jugador2 (PositiveIntegerField): Puntos del jugador 2 en cada set
        sets_ganados_jugador1 (PositiveIntegerField): Sets ganados por jugador 1 (calculado)
        sets_ganados_jugador2 (PositiveIntegerField): Sets ganados por jugador 2 (calculado)
        resultado_jugador_1 (DecimalField): Coeficiente de resultado para jugador 1
        resultado_jugador_2 (DecimalField): Coeficiente de resultado para jugador 2
        fecha_actualizacion (DateTimeField): Última actualización del resultado
    """
    
    partido = models.OneToOneField(Partido, on_delete=models.CASCADE, related_name='resultado_detallado')
    
    # Puntos de cada set para el jugador 1
    set1_jugador1 = models.PositiveIntegerField(default=0)
    set2_jugador1 = models.PositiveIntegerField(default=0)
    set3_jugador1 = models.PositiveIntegerField(default=0)
    set4_jugador1 = models.PositiveIntegerField(default=0, blank=True)
    set5_jugador1 = models.PositiveIntegerField(default=0, blank=True)
    set6_jugador1 = models.PositiveIntegerField(default=0, blank=True)
    set7_jugador1 = models.PositiveIntegerField(default=0, blank=True)
    set8_jugador1 = models.PositiveIntegerField(default=0, blank=True)
    set9_jugador1 = models.PositiveIntegerField(default=0, blank=True)

    # Puntos de cada set para el jugador 2
    set1_jugador2 = models.PositiveIntegerField(default=0)
    set2_jugador2 = models.PositiveIntegerField(default=0)
    set3_jugador2 = models.PositiveIntegerField(default=0)
    set4_jugador2 = models.PositiveIntegerField(default=0, blank=True)
    set5_jugador2 = models.PositiveIntegerField(default=0, blank=True)
    set6_jugador2 = models.PositiveIntegerField(default=0, blank=True)
    set7_jugador2 = models.PositiveIntegerField(default=0, blank=True)
    set8_jugador2 = models.PositiveIntegerField(default=0, blank=True)
    set9_jugador2 = models.PositiveIntegerField(default=0, blank=True)
    
    # Campos calculados automáticamente
    sets_ganados_jugador1 = models.PositiveIntegerField(default=0)
    sets_ganados_jugador2 = models.PositiveIntegerField(default=0)
    resultado_jugador_1 = models.DecimalField(max_digits=5, decimal_places=3, null=True, blank=True)
    resultado_jugador_2 = models.DecimalField(max_digits=5, decimal_places=3, null=True, blank=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        """
        Representación en string del resultado.
        
        Returns:
            str: Formato "Resultado: {sets_j1}-{sets_j2} sets - {partido}"
        """
        return f"Resultado: {self.sets_ganados_jugador1}-{self.sets_ganados_jugador2} sets - {self.partido}"

    def calcular_sets_ganados(self):
        """
        Calcula cuántos sets ganó cada jugador basado en los puntos.
        
        Utiliza la modalidad del torneo (mejor de 3, 5, 7 o 9 sets) para
        determinar qué sets evaluar y actualiza automáticamente los contadores.
        """
        sets_j1 = 0
        sets_j2 = 0
        
        # Determinar si es un partido final para usar la modalidad correcta
        total_rondas = self.partido.torneo.llaves.aggregate(max_ronda=models.Max('ronda'))['max_ronda'] or 1
        es_partido_final = self.partido.llave_torneo.ronda == total_rondas
        
        # Usar la modalidad correcta según si es final o no
        mejor_de_sets = self.partido.torneo.mejor_de_sets_final if es_partido_final else self.partido.torneo.mejor_de_sets
        
        # Crear lista de sets a evaluar basándose ÚNICAMENTE en la modalidad
        sets_a_evaluar = [
            (self.set1_jugador1, self.set1_jugador2),
            (self.set2_jugador1, self.set2_jugador2),
            (self.set3_jugador1, self.set3_jugador2),
        ]
        
        # Agregar sets adicionales según la modalidad (NO duplicar)
        if mejor_de_sets >= 5:
            sets_a_evaluar.append((self.set4_jugador1, self.set4_jugador2))
            sets_a_evaluar.append((self.set5_jugador1, self.set5_jugador2))
        if mejor_de_sets >= 7:
            sets_a_evaluar.append((self.set6_jugador1, self.set6_jugador2))
            sets_a_evaluar.append((self.set7_jugador1, self.set7_jugador2))
        if mejor_de_sets >= 9:
            sets_a_evaluar.append((self.set8_jugador1, self.set8_jugador2))
            sets_a_evaluar.append((self.set9_jugador1, self.set9_jugador2))
        
        # Evaluar solo los sets que corresponden a la modalidad actual
        for puntos_j1, puntos_j2 in sets_a_evaluar:
            # Solo contar sets que han sido realmente jugados (ambos jugadores tienen puntos or hay un ganador claro)
            if (puntos_j1 > 0 or puntos_j2 > 0) and (puntos_j1 != puntos_j2):
                if puntos_j1 > puntos_j2:
                    sets_j1 += 1
                elif puntos_j2 > puntos_j1:
                    sets_j2 += 1
        
        self.sets_ganados_jugador1 = sets_j1
        self.sets_ganados_jugador2 = sets_j2
    
    def calcular_coeficientes(self):
        """
        Calcula los coeficientes de puntos para ambos jugadores.
        
        Los coeficientes se usan para rankings y estadísticas, calculando
        la relación de sets ganados entre los jugadores.
        """
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
        Esto evita modificaciones accidentales de sets ya completados.
        
        Returns:
            dict: Diccionario con claves 'set1' a 'set9' y valores booleanos
        """
        sets_guardados = {
            'set1': self.set1_jugador1 > 0 or self.set1_jugador2 > 0,
            'set2': self.set2_jugador1 > 0 or self.set2_jugador2 > 0,
            'set3': self.set3_jugador1 > 0 or self.set3_jugador2 > 0,
            'set4': self.set4_jugador1 > 0 or self.set4_jugador2 > 0,
            'set5': self.set5_jugador1 > 0 or self.set5_jugador2 > 0,
            'set6': self.set6_jugador1 > 0 or self.set6_jugador2 > 0,
            'set7': self.set7_jugador1 > 0 or self.set7_jugador2 > 0,
            'set8': self.set8_jugador1 > 0 or self.set8_jugador2 > 0,
            'set9': self.set9_jugador1 > 0 or self.set9_jugador2 > 0,
        }
        return sets_guardados
    
    def obtener_resultado_detallado(self):
        """
        Devuelve el resultado detallado set por set.
        
        Formatea los resultados de cada set en una cadena legible,
        considerando la modalidad del torneo para mostrar solo los sets relevantes.
        
        Returns:
            str: Resultado formateado como "Set 1: 6-4 | Set 2: 3-6 | ..."
        """
        # Determinar si es un partido final para usar la modalidad correcta
        total_rondas = self.partido.torneo.llaves.aggregate(max_ronda=models.Max('ronda'))['max_ronda'] or 1
        es_partido_final = self.partido.llave_torneo.ronda == total_rondas
        
        # Usar la modalidad correcta según si es final o no
        mejor_de_sets = self.partido.torneo.mejor_de_sets_final if es_partido_final else self.partido.torneo.mejor_de_sets
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
        """
        Override del método save para cálculos automáticos.
        
        Calcula automáticamente sets ganados y coeficientes antes de guardar,
        y verifica si el partido debe cerrarse automáticamente.
        """
        self.calcular_sets_ganados()
        self.calcular_coeficientes()
        super().save(*args, **kwargs)
        
        # Verificar si el partido debe cerrarse automáticamente después de guardar
        if hasattr(self, 'partido'):
            self.partido.verificar_y_cerrar_partido()
    
    def definir_ganador_directo(self, jugador_ganador):
        """
        Define directamente un ganador para el partido sin registrar sets detallados.
        
        Reutiliza la misma lógica que el procesamiento de BYE para declarar
        un ganador directo cuando no se requiere el marcador detallado.
        
        Args:
            jugador_ganador (Jugador): El jugador que se declarará como ganador
            
        Returns:
            tuple: (bool, str) - (éxito, mensaje)
        """
        if self.partido.estado_partido == 'jugado':
            return False, "El partido ya está terminado"
        
        if jugador_ganador not in [self.partido.jugador1, self.partido.jugador2]:
            return False, "El jugador especificado no participa en este partido"
        
        if not jugador_ganador:
            return False, "Jugador ganador no válido"
        
        # Determinar si es un partido final para usar la modalidad correcta
        total_rondas = self.partido.torneo.llaves.aggregate(max_ronda=models.Max('ronda'))['max_ronda'] or 1
        es_partido_final = self.partido.llave_torneo.ronda == total_rondas
        
        # Usar la modalidad correcta según si es final o no
        mejor_de_sets = self.partido.torneo.mejor_de_sets_final if es_partido_final else self.partido.torneo.mejor_de_sets
        sets_para_ganar = (mejor_de_sets // 2) + 1
        
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
            self.set6_jugador1 = 0
            self.set6_jugador2 = 0
            self.set7_jugador1 = 0
            self.set7_jugador2 = 0
            self.set8_jugador1 = 0
            self.set8_jugador2 = 0
            self.set9_jugador1 = 0
            self.set9_jugador2 = 0

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
