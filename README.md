# AutoTenis - Sistema de Gestión de Torneos de Tenis

## Descripción

AutoTenis es un sistema web completo para la gestión de torneos de tenis desarrollado con Django. El sistema permite organizar torneos con diferentes modalidades (llaves de eliminación directa y grupos), gestionar jugadores, arbitrar partidos en tiempo real y llevar un seguimiento completo de resultados y estadísticas.

## Características Principales

### 🎾 Gestión de Torneos
- Creación y configuración de torneos con diferentes modalidades
- Soporte para torneos de llaves (brackets) y grupos
- Configuración flexible de sets (mejor de 3, 5, 7 o 9 sets)
- Modalidades especiales para finales

### 👥 Gestión de Usuarios
- Sistema de autenticación personalizado con tres tipos de usuario:
  - **Organizadores**: Crean y gestionan torneos
  - **Árbitros**: Arbitran partidos y registran resultados
  - **Jugadores**: Participan en torneos
- Control de acceso basado en roles

### 🏆 Sistema de Llaves
- Generación automática de brackets de eliminación
- Avance automático de ganadores entre rondas
- Creación automática de partidos por el tercer lugar
- Gestión inteligente de BYEs

### ⚡ Arbitraje en Tiempo Real
- Panel de control para árbitros con puntaje en vivo
- WebSockets para actualizaciones en tiempo real
- Validación automática de resultados
- Sistema de confirmación de resultados por organizadores

### 📊 Gestión de Resultados
- Registro detallado de puntos por set
- Cálculo automático de sets ganados
- Coeficientes y estadísticas
- Historial completo de partidos

## Requisitos del Sistema

### Software Necesario
- **XAMPP** (para Apache y MySQL)
- **Visual Studio Code** (recomendado)
- **Python 3.8+**
- **Git** (opcional, para control de versiones)

### Dependencias Python
- Django 5.2.1
- django-channels (para WebSockets)
- mysqlclient
- pandas (para exportación de datos)
- daphne (servidor ASGI)

## Instalación

### 1. Preparar el Entorno

#### Iniciar XAMPP
- Abrir el panel de control de XAMPP
- Iniciar los servicios de **Apache** y **MySQL**

#### Configurar el Proyecto
- Abrir la carpeta del proyecto `AutoTenis` en Visual Studio Code
- Abrir una nueva terminal (`Ctrl + Ñ` o desde el menú Terminal > Nueva terminal)

### 2. Instalar Dependencias

```bash
# Instalar Django
pip install django

# Instalar cliente MySQL
pip install mysqlclient

# Instalar Django Channels para WebSockets
pip install channels

# Instalar dependencias adicionales
pip install pandas daphne
```

### 3. Configurar Base de Datos

#### Crear Base de Datos en phpMyAdmin
**IMPORTANTE**: Antes de ejecutar las migraciones, debes crear la base de datos manualmente:

1. **Abrir phpMyAdmin**:
   - En tu navegador, ir a: `http://localhost/phpmyadmin`
   - Hacer clic en "Bases de datos" en el menú superior

2. **Crear la Base de Datos**:
   - En el campo "Crear base de datos", escribir: `autotenis`
   - Seleccionar cotejamiento: `utf8mb4_general_ci` (recomendado)
   - Hacer clic en "Crear"

3. **Verificar Creación**:
   - La base de datos `autotenis` debe aparecer en la lista de la izquierda
   - Debe estar vacía (sin tablas inicialmente)

#### Ejecutar Migraciones de Django

```bash
# Crear archivos de migración
python manage.py makemigrations

# Aplicar migraciones a la base de datos
python manage.py migrate

# (Opcional) Crear superusuario
python manage.py createsuperuser
```

**Nota**: Si no creas la base de datos `autotenis` manualmente en phpMyAdmin, Django mostrará un error al intentar ejecutar `makemigrations` o `migrate`.

### 4. Ejecutar el Servidor

```bash
# Iniciar el servidor de desarrollo
python manage.py runserver
```

El sistema estará disponible en: `http://localhost:8000`

## Estructura del Proyecto

```
AutoTenis/
├── AutoTenis/                 # Configuración principal del proyecto
│   ├── settings.py           # Configuraciones de Django
│   ├── urls.py              # URLs principales
│   ├── asgi.py              # Configuración ASGI para WebSockets
│   └── wsgi.py              # Configuración WSGI
├── gestiontorneo/           # Aplicación principal
│   ├── models.py            # Modelos de datos (Torneo, Jugador, Partido, etc.)
│   ├── views.py             # Vistas principales
│   ├── decorators.py        # Decoradores de control de acceso
│   ├── forms.py             # Formularios Django
│   └── urls.py              # URLs de la aplicación
├── gestionarbitros/         # Aplicación de árbitros
│   ├── views.py             # Vistas para árbitros
│   ├── consumers.py         # WebSocket consumers
│   └── routing.py           # Routing de WebSockets
├── templates/               # Plantillas HTML
├── static/                  # Archivos estáticos (CSS, JS, imágenes)
└── manage.py               # Utilidad de gestión de Django
```

## Uso del Sistema

### Para Organizadores
1. **Crear Torneo**: Definir modalidad, fechas y configuración de sets
2. **Gestionar Inscripciones**: Registrar jugadores participantes
3. **Generar Llaves**: Crear automáticamente la estructura del torneo
4. **Asignar Árbitros**: Designar árbitros para los partidos
5. **Supervisar Progreso**: Monitorear el avance del torneo

### Para Árbitros
1. **Acceder al Panel**: Ver partidos asignados
2. **Arbitrar Partidos**: Usar la interfaz de puntaje en tiempo real
3. **Registrar Resultados**: Ingresar puntos set por set
4. **Enviar Confirmación**: Enviar resultado para aprobación del organizador

### Para Jugadores
1. **Ver Torneos**: Consultar torneos disponibles
2. **Inscribirse**: Registrarse en torneos abiertos
3. **Consultar Llaves**: Ver bracket y próximos partidos
4. **Ver Historial**: Consultar resultados anteriores

## Características Técnicas

### Arquitectura
- **Backend**: Django 5.2.1 con patrón MTV
- **Base de Datos**: MySQL con relaciones complejas
- **Frontend**: HTML5, CSS3, Bootstrap 5, JavaScript
- **Tiempo Real**: Django Channels con WebSockets
- **Autenticación**: Sistema personalizado basado en roles

### Funcionalidades Avanzadas
- **Avance Automático**: Los ganadores avanzan automáticamente entre rondas
- **Validación Inteligente**: Verificación automática de resultados
- **Gestión de BYEs**: Manejo automático de posiciones vacías
- **Tercer Lugar**: Creación automática de partidos por el tercer puesto
- **Modalidades Flexibles**: Soporte para diferentes formatos de sets

### Seguridad
- Decoradores de control de acceso por tipo de usuario
- Validación de permisos en todas las operaciones
- Protección CSRF en formularios
- Sanitización de datos de entrada

## Solución de Problemas Comunes

### Error: "Unknown database 'autotenis'"

**Problema**: Al ejecutar `python manage.py migrate` aparece el error:
```
django.db.utils.OperationalError: (1049, "Unknown database 'autotenis'")
```

**Solución**:
1. Verificar que XAMPP esté ejecutándose (Apache y MySQL)
2. Abrir phpMyAdmin en `http://localhost/phpmyadmin`
3. Crear manualmente la base de datos `autotenis`
4. Volver a ejecutar las migraciones

### Error: "Access denied for user"

**Problema**: Error de acceso a MySQL.

**Solución**:
1. Verificar que MySQL esté ejecutándose en XAMPP
2. Comprobar configuración en `settings.py`:
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.mysql',
           'NAME': 'autotenis',
           'USER': 'root',
           'PASSWORD': '',  # Por defecto está vacía en XAMPP
           'HOST': 'localhost',
           'PORT': '3306',
       }
   }
   ```

### Error: "No module named 'mysqlclient'"

**Problema**: Cliente MySQL no instalado.

**Solución**:
```bash
pip install mysqlclient
```

## Contribución

Para contribuir al proyecto:

1. Fork el repositorio
2. Crear una rama para la nueva funcionalidad
3. Desarrollar y documentar los cambios
4. Escribir tests para las nuevas funcionalidades
5. Enviar un Pull Request

## Licencia

Este proyecto está desarrollado para fines educativos y de gestión de torneos de tenis.

## Soporte

Para reportar problemas o solicitar nuevas funcionalidades, crear un issue en el repositorio del proyecto.
