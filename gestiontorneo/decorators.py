"""
Decoradores para control de acceso basado en tipos de usuario.

Este módulo proporciona decoradores para restringir el acceso a vistas
según el tipo de usuario (organizador, jugador, árbitro) en el sistema
de gestión de torneos.
"""

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps


def require_user_type(*allowed_types):
    """
    Decorador que restringe el acceso a una vista basado en el tipo de usuario.
    
    Verifica que el usuario autenticado tenga uno de los tipos permitidos
    antes de permitir el acceso a la vista decorada.
    
    Args:
        *allowed_types (str): Tipos de usuario permitidos ('organizador', 'jugador', 'arbitro')
        
    Returns:
        function: Decorador que valida el tipo de usuario
        
    Example:
        @require_user_type('organizador', 'arbitro')
        def mi_vista(request):
            # Solo organizadores y árbitros pueden acceder
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            user = request.user
            
            # Verificar si el usuario tiene el atributo tipo_usuario
            if not hasattr(user, 'tipo_usuario'):
                messages.error(request, 'Tu cuenta no tiene un tipo de usuario asignado. Contacta al administrador.')
                return redirect('home')
            
            # Verificar si el tipo de usuario está permitido
            if user.tipo_usuario not in allowed_types:
                messages.error(request, f'No tienes permisos para acceder a esta página. Acceso restringido a: {", ".join(allowed_types)}')
                return redirect('home')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_organizador(view_func):
    """
    Decorador específico para vistas que solo pueden acceder organizadores.
    
    Args:
        view_func (function): Vista a decorar
        
    Returns:
        function: Vista decorada con restricción a organizadores
    """
    return require_user_type('organizador')(view_func)


def require_jugador(view_func):
    """
    Decorador específico para vistas que solo pueden acceder jugadores.
    
    Args:
        view_func (function): Vista a decorar
        
    Returns:
        function: Vista decorada con restricción a jugadores
    """
    return require_user_type('jugador')(view_func)


def require_arbitro(view_func):
    """
    Decorador específico para vistas que solo pueden acceder árbitros.
    
    Args:
        view_func (function): Vista a decorar
        
    Returns:
        function: Vista decorada con restricción a árbitros
    """
    return require_user_type('arbitro')(view_func)


def require_organizador_or_arbitro(view_func):
    """
    Decorador para vistas que pueden acceder organizadores y árbitros.
    
    Args:
        view_func (function): Vista a decorar
        
    Returns:
        function: Vista decorada con restricción a organizadores y árbitros
    """
    return require_user_type('organizador', 'arbitro')(view_func)


def require_jugador_or_organizador(view_func):
    """
    Decorador para vistas que pueden acceder jugadores y organizadores.
    
    Args:
        view_func (function): Vista a decorar
        
    Returns:
        function: Vista decorada con restricción a jugadores y organizadores
    """
    return require_user_type('jugador', 'organizador')(view_func)
