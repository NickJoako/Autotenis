#!/usr/bin/env python
"""
Utilidad de línea de comandos de Django para el proyecto AutoTenis.

Este script proporciona acceso a las herramientas administrativas de Django
para el sistema de gestión de torneos de tenis, incluyendo:
- Ejecución del servidor de desarrollo
- Migraciones de base de datos
- Creación de superusuarios
- Comandos personalizados

Uso:
    python manage.py <comando> [opciones]

Ejemplos:
    python manage.py runserver          # Ejecutar servidor de desarrollo
    python manage.py makemigrations     # Crear migraciones
    python manage.py migrate            # Aplicar migraciones
    python manage.py createsuperuser    # Crear superusuario
"""
import os
import sys


def main():
    """
    Ejecuta tareas administrativas de Django.
    
    Configura las variables de entorno necesarias y ejecuta
    los comandos de gestión de Django.
    """
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AutoTenis.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
