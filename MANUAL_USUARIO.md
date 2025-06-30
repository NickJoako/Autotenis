# Manual de Usuario - AutoTenis

## Introducción

AutoTenis es un sistema completo para la gestión de torneos de tenis que permite organizar competencias, gestionar jugadores, arbitrar partidos en tiempo real y llevar un control detallado de resultados y estadísticas.

## Tipos de Usuario

El sistema maneja tres tipos de usuarios diferentes, cada uno con funcionalidades específicas:

### 🏆 Organizador
- Crea y configura torneos
- Gestiona inscripciones de jugadores
- Genera llaves automáticamente
- Asigna árbitros a partidos
- Confirma resultados finales
- Supervisa el progreso del torneo

### ⚖️ Árbitro
- Ve partidos asignados
- Arbitra partidos en tiempo real
- Registra puntos set por set
- Envía resultados para confirmación
- Accede a historial de arbitrajes

### 🎾 Jugador
- Ve torneos disponibles
- Se inscribe en competencias
- Consulta llaves y fixture
- Ve historial de partidos
- Accede a estadísticas personales

## Guía de Inicio Rápido

### 1. Acceso al Sistema

1. Abrir navegador web e ir a la dirección del sistema
2. En la página de login, seleccionar el tipo de usuario
3. Ingresar email y contraseña
4. Hacer clic en "Iniciar Sesión"

### 2. Navegación Principal

- **Dashboard**: Página de inicio con resumen de actividades
- **Menú Principal**: Navegación según tipo de usuario
- **Perfil**: Configuración de cuenta personal
- **Cerrar Sesión**: Salir del sistema

## Manual para Organizadores

### Crear un Nuevo Torneo

1. **Acceder al Panel de Organizador**
   - Desde el dashboard, clic en "Gestionar Torneos"
   - Seleccionar "Crear Nuevo Torneo"

2. **Configuración Básica**
   ```
   Nombre: Ej. "Torneo Primavera 2024"
   Fecha: Seleccionar fecha del torneo
   Ubicación: Lugar donde se realizará
   Categoría: Edad de participantes
   ```

3. **Modalidad del Torneo**
   - **Llaves (Brackets)**: Eliminación directa
   - **Grupos**: Fase de grupos + eliminatorias

4. **Configuración de Sets**
   ```
   Partidos regulares: Mejor de 3 sets (recomendado)
   Final: Mejor de 5 sets
   ```

5. **Guardar Configuración**
   - Revisar datos ingresados
   - Hacer clic en "Crear Torneo"

### Gestionar Inscripciones

1. **Abrir Torneo Creado**
   - Ir a "Mis Torneos"
   - Seleccionar el torneo

2. **Registrar Jugadores**
   - Clic en "Gestionar Participantes"
   - Opción 1: "Agregar Jugador Existente"
   - Opción 2: "Registrar Nuevo Jugador"

3. **Validar Participantes**
   - Revisar lista de inscritos
   - Verificar categorías
   - Eliminar inscripciones si es necesario

4. **Cerrar Inscripciones**
   - Cuando esté lista la lista final
   - Clic en "Cerrar Inscripciones"

### Generar Llaves del Torneo

1. **Condiciones Previas**
   - Inscripciones cerradas
   - Mínimo 4 participantes
   - Máximo potencia de 2 (4, 8, 16, 32, etc.)

2. **Generar Estructura**
   - Clic en "Generar Llaves"
   - El sistema crea automáticamente:
     - Bracket de eliminación directa
     - Posiciones con/sin BYE según número de participantes
     - Primera ronda lista para asignar árbitros

3. **Revisar Bracket**
   - Verificar correcta distribución
   - Confirmar posiciones de jugadores

### Asignar Árbitros

1. **Acceder a Gestión de Partidos**
   - Ir a "Partidos del Torneo"
   - Ver lista de enfrentamientos

2. **Asignar por Partido**
   ```
   Para cada partido:
   - Seleccionar árbitro disponible
   - Programar fecha y hora
   - Confirmar asignación
   ```

3. **Asignación Masiva** (si disponible)
   - Seleccionar múltiples partidos
   - Asignar árbitros automáticamente
   - Distribuir horarios

### Iniciar el Torneo

1. **Verificación Final**
   - Todos los partidos de primera ronda tienen árbitro
   - Fechas y horarios programados
   - Participantes confirmados

2. **Activar Torneo**
   - Clic en "Iniciar Torneo"
   - El sistema cambia estado a "En Curso"
   - Los árbitros pueden comenzar a arbitrar

### Supervisar Progreso

1. **Dashboard del Torneo**
   - Estado actual de cada ronda
   - Partidos completados vs pendientes
   - Próximos enfrentamientos

2. **Confirmar Resultados**
   ```
   Cuando un árbitro termina un partido:
   1. Resultado aparece como "Pendiente Confirmación"
   2. Revisar marcador registrado
   3. Confirmar o solicitar corrección
   4. Una vez confirmado: ganador avanza automáticamente
   ```

3. **Gestión de Incidencias**
   - Reasignar árbitros si es necesario
   - Reprogramar partidos
   - Resolver conflictos de resultados

## Manual para Árbitros

### Acceder a Partidos Asignados

1. **Panel Principal**
   - Dashboard muestra resumen de arbitrajes
   - Lista de partidos pendientes
   - Próximos compromisos

2. **Ver Detalle de Partido**
   - Clic en partido asignado
   - Información de jugadores
   - Modalidad del encuentro (sets a jugar)

### Arbitrar un Partido

1. **Iniciar Arbitraje**
   - Clic en "Arbitrar Partido"
   - Se abre panel de control de puntos
   - Estado cambia a "En Curso"

2. **Panel de Control**
   ```
   Interfaz muestra:
   - Nombres de ambos jugadores
   - Set actual en juego
   - Puntos por set
   - Total de sets ganados
   - Botones para registrar puntos
   ```

3. **Registrar Puntos**
   ```
   Para cada punto ganado:
   1. Hacer clic en botón del jugador ganador
   2. Sistema actualiza marcador automáticamente
   3. Al completar set: avanza automáticamente al siguiente
   4. Sistema calcula ganador cuando se alcanzan sets necesarios
   ```

4. **Modalidades Soportadas**
   - **Mejor de 3**: Primero en ganar 2 sets
   - **Mejor de 5**: Primero en ganar 3 sets
   - **Mejor de 7**: Primero en ganar 4 sets
   - **Mejor de 9**: Primero en ganar 5 sets

### Finalizar Partido

1. **Confirmación Automática**
   - Sistema detecta cuando se alcanza sets necesarios
   - Marcador se marca como "Pendiente Confirmación"
   - Árbitro no puede modificar más el resultado

2. **Envío a Organizador**
   - Resultado se envía automáticamente para confirmación
   - Organizador debe aprobar antes del avance
   - Árbitro recibe notificación de confirmación

### Historial de Arbitrajes

1. **Consultar Historial**
   - Ir a "Mis Arbitrajes"
   - Ver partidos completados
   - Revisar estadísticas personales

2. **Información Disponible**
   - Fecha y hora de cada partido
   - Jugadores enfrentados
   - Marcador final
   - Torneo correspondiente

## Manual para Jugadores

### Inscribirse en Torneos

1. **Ver Torneos Disponibles**
   - Dashboard muestra torneos abiertos
   - Filtrar por categoría o fecha
   - Ver detalles de cada competencia

2. **Proceso de Inscripción**
   ```
   1. Seleccionar torneo de interés
   2. Verificar que cumple requisitos de categoría
   3. Clic en "Inscribirse"
   4. Confirmar datos personales
   5. Esperar confirmación del organizador
   ```

### Consultar Llaves y Fixture

1. **Estado del Torneo**
   - **Pre-torneo**: Ver lista de participantes
   - **En curso**: Consultar bracket actualizado
   - **Finalizado**: Resultados finales

2. **Información Disponible**
   ```
   - Posición en el bracket
   - Próximo rival (si está definido)
   - Horario del partido (si está programado)
   - Árbitro asignado
   - Resultados de partidos anteriores
   ```

### Seguimiento de Partidos

1. **Partidos Propios**
   - Ver próximos compromisos
   - Historial de resultados
   - Estadísticas de rendimiento

2. **Seguimiento en Vivo** (si disponible)
   - Ver partidos en tiempo real
   - Seguir progreso de otros enfrentamientos
   - Consultar avance general del torneo

## Funcionalidades Avanzadas

### Sistema de BYEs

**¿Qué es un BYE?**
Un BYE es un pase automático a la siguiente ronda cuando no hay suficientes participantes para completar todas las posiciones del bracket.

**Procesamiento Automático:**
- Sistema detecta BYEs automáticamente
- Jugador real avanza sin jugar
- Se registra resultado automático
- Ganador pasa a siguiente ronda

### Tercer Lugar Automático

**Cuándo se Crea:**
- Al completarse ambas semifinales
- Sistema identifica perdedores automáticamente
- Crea partido por tercer puesto

**Proceso:**
1. Semifinales completadas → Sistema detecta perdedores
2. Crea automáticamente partido de "Tercer Lugar"
3. Asigna árbitro (puede requerir intervención del organizador)
4. Se juega como cualquier otro partido

### Avance Automático

**Funcionamiento:**
- Al confirmarse resultado de un partido
- Ganador avanza automáticamente a posición correcta en siguiente ronda
- Si ambos jugadores de la siguiente llave están listos → se crea partido automáticamente
- Proceso continúa hasta la final

**Algoritmo de Posiciones:**
```
Ronda siguiente = Ronda actual + 1
Posición siguiente = (Posición actual + 1) ÷ 2
- Posición impar → Jugador 1 en siguiente ronda
- Posición par → Jugador 2 en siguiente ronda
```

## Solución de Problemas Comunes

### Problemas de Acceso

**No puedo iniciar sesión:**
1. Verificar tipo de usuario seleccionado
2. Confirmar email y contraseña
3. Contactar administrador si persiste

**No veo mis torneos/partidos:**
1. Verificar tipo de usuario correcto
2. Confirmar que está asignado al torneo
3. Revisar estado del torneo

### Problemas en Arbitraje

**No puedo registrar puntos:**
1. Verificar que partido esté "En Curso"
2. Confirmar asignación como árbitro
3. Actualizar página si es necesario

**Marcador incorrecto:**
1. Contactar organizador inmediatamente
2. No continuar arbitrando
3. Reportar problema específico

### Problemas de Torneo

**Llaves no se generan:**
1. Verificar inscripciones cerradas
2. Confirmar número mínimo de participantes
3. Revisar que no haya errores en inscripciones

**Resultados no avanzan:**
1. Verificar confirmación del organizador
2. Revisar que resultado esté completo
3. Contactar soporte técnico

## Contacto y Soporte

Para problemas técnicos o consultas sobre el sistema:

- **Soporte Técnico**: [email del administrador]
- **Manual Extendido**: Documentación adicional disponible
- **Reportar Bugs**: Sistema de tickets interno
- **Solicitar Funcionalidades**: A través del organizador principal

## Consejos y Mejores Prácticas

### Para Organizadores
- Planificar torneos con anticipación
- Cerrar inscripciones con tiempo suficiente
- Asignar árbitros experimentados para finales
- Mantener comunicación constante con participantes

### Para Árbitros
- Llegar temprano a los partidos asignados
- Familiarizarse con la interfaz antes del torneo
- Comunicar cualquier problema inmediatamente
- Mantener registro mental del marcador como respaldo

### Para Jugadores
- Inscribirse temprano en torneos de interés
- Confirmar horarios de partidos regularmente
- Reportar cualquier inconsistencia en el bracket
- Mantener datos personales actualizados

## Actualizaciones del Sistema

El sistema se actualiza periódicamente con nuevas funcionalidades:

- **Notificaciones**: Se implementarán avisos automáticos
- **Estadísticas Avanzadas**: Métricas detalladas de rendimiento
- **Exportación**: Descarga de resultados y brackets
- **App Móvil**: Versión para dispositivos móviles en desarrollo
