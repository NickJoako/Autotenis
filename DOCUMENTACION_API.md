# Documentación de la API - AutoTenis

## Descripción General

Esta documentación describe la estructura interna del sistema AutoTenis, incluyendo los modelos principales, vistas importantes y flujos de trabajo del sistema.

## Modelos Principales

### UsuarioPersonalizado
```python
class UsuarioPersonalizado(AbstractUser)
```
**Propósito**: Gestiona los diferentes tipos de usuarios del sistema.

**Campos principales**:
- `tipo_usuario`: Choices entre 'organizador', 'arbitro', 'jugador'
- `activo`: Estado del usuario
- `email`: Campo principal de autenticación (USERNAME_FIELD)

**Métodos**:
- `__str__()`: Retorna "username (tipo_usuario)"

### Jugador
```python
class Jugador(models.Model)
```
**Propósito**: Representa a los jugadores participantes en torneos.

**Campos principales**:
- `rut`: Identificador único del jugador
- `nombre`, `apellido`: Datos personales
- `fecha_nacimiento`: Para cálculo de categorías
- `genero`: 'M' o 'F'
- `club`: Relación opcional con Club
- `email`: Email único opcional

**Métodos**:
- `calcular_categoria()`: Determina la categoría basada en la edad

### Torneo
```python
class Torneo(models.Model)
```
**Propósito**: Gestiona la configuración y estado de los torneos.

**Campos principales**:
- `modalidad`: 'llaves' o 'grupos'
- `mejor_de_sets`: Configuración para partidos regulares (1, 3, 5, 7, 9)
- `mejor_de_sets_final`: Configuración específica para la final
- `torneo_iniciado`, `finalizado`: Estados del torneo
- `organizador`: Usuario responsable

### LlaveTorneo
```python
class LlaveTorneo(models.Model)
```
**Propósito**: Representa las posiciones en el bracket de eliminación directa.

**Campos principales**:
- `ronda`: Número de ronda (1=primera ronda, 2=segunda, etc.)
- `posicion`: Posición dentro de la ronda
- `tipo_llave`: 'normal' o 'tercer_lugar'
- `jugador1`, `jugador2`: Participantes
- `bye1`, `bye2`: Referencias a BYEs si aplica
- `ganador`: Resultado del enfrentamiento

**Propiedades**:
- `jugador1_nombre`, `jugador2_nombre`: Nombres formateados
- `estado_badge_class`: Clase CSS para estado visual
- `puede_editarse`, `puede_iniciarse`: Permisos de acción

### Partido
```python
class Partido(models.Model)
```
**Propósito**: Gestiona los aspectos detallados de cada enfrentamiento.

**Campos principales**:
- `llave_torneo`: Referencia a la llave correspondiente
- `arbitro`: Árbitro asignado
- `estado_partido`: 'pendiente', 'en_curso', 'jugado'
- `fecha_programada`, `hora_programada`: Programación
- `pendiente_confirmacion`: Para validación de organizador
- `finalizado`: Estado final del partido

**Métodos principales**:
- `es_partido_bye()`: Detecta si hay un BYE
- `procesar_partido_bye()`: Procesamiento automático de BYEs
- `verificar_y_cerrar_partido()`: Validación automática de finalización
- `confirmar_y_cerrar_partido()`: Confirmación por organizador
- `avanzar_ganador_automaticamente()`: Avance a siguiente ronda
- `verificar_y_crear_tercer_lugar()`: Creación automática de tercer lugar

### Resultado
```python
class Resultado(models.Model)
```
**Propósito**: Registra el marcador detallado de cada partido.

**Campos principales**:
- `set1_jugador1` a `set9_jugador1`: Puntos por set del jugador 1
- `set1_jugador2` a `set9_jugador2`: Puntos por set del jugador 2
- `sets_ganados_jugador1`, `sets_ganados_jugador2`: Calculados automáticamente
- `resultado_jugador_1`, `resultado_jugador_2`: Coeficientes

**Métodos principales**:
- `calcular_sets_ganados()`: Cálculo automático basado en modalidad
- `calcular_coeficientes()`: Ratios para estadísticas
- `obtener_sets_guardados()`: Validación de sets completados
- `obtener_resultado_detallado()`: Formateo de resultados
- `definir_ganador_directo()`: Victoria sin marcador detallado
- `save()`: Override para cálculos automáticos

## Flujos de Trabajo Principales

### 1. Creación de Torneo con Llaves

```python
# 1. Crear torneo
torneo = Torneo.objects.create(
    nombre="Mi Torneo",
    modalidad='llaves',
    mejor_de_sets=3,
    mejor_de_sets_final=5,
    organizador=user
)

# 2. Registrar participantes
for jugador in jugadores:
    Participacion.objects.create(torneo=torneo, jugador=jugador)

# 3. Generar llaves automáticamente
# Se ejecuta desde la vista correspondiente
```

### 2. Procesamiento de Partidos

```python
# Flujo automático para partidos con BYE
if partido.es_partido_bye():
    exito, mensaje = partido.procesar_partido_bye()
    # Resultado: ganador avanza automáticamente

# Flujo para partidos normales
# 1. Árbitro registra puntos en Resultado
# 2. Sistema calcula sets ganados automáticamente
# 3. Al alcanzar sets necesarios: partido queda pendiente confirmación
# 4. Organizador confirma resultado
# 5. Ganador avanza automáticamente a siguiente ronda
```

### 3. Avance Automático entre Rondas

```python
def avanzar_ganador_automaticamente(self):
    """
    Algoritmo de avance:
    - Ronda siguiente = ronda_actual + 1
    - Posición siguiente = (posición_actual + 1) // 2
    - Si posición actual es impar → jugador1 en siguiente ronda
    - Si posición actual es par → jugador2 en siguiente ronda
    """
```

### 4. Creación Automática de Tercer Lugar

```python
def verificar_y_crear_tercer_lugar(self):
    """
    Condiciones:
    1. Partido debe ser de semifinales (ronda = total_rondas - 1)
    2. Ambas semifinales deben estar completas
    3. No debe existir ya un partido de tercer lugar
    
    Resultado:
    - Crea LlaveTorneo con tipo_llave='tercer_lugar'
    - Asigna perdedores de semifinales como participantes
    - Crea Partido automáticamente
    """
```

## Decoradores de Seguridad

### @require_user_type()
```python
@require_user_type('organizador', 'arbitro')
def mi_vista(request):
    # Solo organizadores y árbitros pueden acceder
    pass
```

### Decoradores Específicos
- `@require_organizador`: Solo organizadores
- `@require_arbitro`: Solo árbitros  
- `@require_jugador`: Solo jugadores
- `@require_organizador_or_arbitro`: Organizadores y árbitros
- `@require_jugador_or_organizador`: Jugadores y organizadores

## WebSockets para Tiempo Real

### Consumer de Partidos
```python
class PartidoConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.partido_id = self.scope['url_route']['kwargs']['partido_id']
        self.partido_group_name = f'partido_{self.partido_id}'
        
    async def partido_update(self, event):
        # Envía actualizaciones en tiempo real del partido
```

### Eventos Principales
- `partido_update`: Actualización de puntos
- `partido_finalizado`: Partido completado
- `ganador_confirmado`: Resultado confirmado por organizador

## APIs JSON

### Actualizar Puntos
```javascript
POST /arbitros/actualizar_puntos/
{
    "partido_id": 123,
    "set_actual": 1,
    "puntos_j1": 6,
    "puntos_j2": 4
}
```

### Confirmar Resultado
```javascript
POST /organizador/confirmar_resultado/
{
    "partido_id": 123,
    "confirmar": true
}
```

## Configuraciones Importantes

### Settings.py
```python
# Modelo de usuario personalizado
AUTH_USER_MODEL = 'gestiontorneo.UsuarioPersonalizado'

# Configuración de Channels
ASGI_APPLICATION = 'AutoTenis.asgi.application'
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}
```

### URLs Principales
- `/`: Página de inicio
- `/login/`: Autenticación personalizada
- `/organizador/`: Panel de organizador
- `/arbitro/`: Panel de árbitro
- `/jugador/`: Panel de jugador

## Consideraciones de Desarrollo

### Transacciones
- Usar `@transaction.atomic` para operaciones críticas
- El avance automático de ganadores debe ser atómico

### Validaciones
- Siempre validar permisos de usuario
- Verificar estados de torneo antes de modificaciones
- Validar modalidades de sets según configuración

### Performance
- Usar `select_related()` para JOINs eficientes
- Prefetch data relacionada cuando sea necesario
- Índices en campos frecuentemente consultados

### Testing
- Tests unitarios para cada modelo principal
- Tests de integración para flujos completos
- Tests de WebSockets para tiempo real

## Extensiones Futuras

### Posibles Mejoras
1. **Sistema de Rankings**: Basado en resultados históricos
2. **Notificaciones**: Push notifications para árbitros/jugadores
3. **Exportación**: PDF de brackets y resultados
4. **Estadísticas Avanzadas**: Análisis detallado de rendimiento
5. **API REST**: Para aplicaciones móviles
6. **Torneos por Equipos**: Modalidad adicional
7. **Streaming**: Integración con plataformas de video

### Arquitectura Escalable
- Separar lógica de negocio en servicios
- Implementar cache para consultas frecuentes
- Considerar microservicios para funcionalidades específicas
