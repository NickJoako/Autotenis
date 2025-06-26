# -*- coding: utf-8 -*-
"""
Vistas principales del sistema de gestión de torneos
Este archivo importa las vistas desde archivos separados para mejor organización
"""

# Imports principales de Django
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from .models import Club, Categoria

# Importar vistas desde archivos separados
from .views_torneos import (
    crear_torneo, lista_torneos, gestionar_torneo, gestionar_torneo_federado
)
from .views_jugadores import (
    lista_jugadores, importar_jugadores, anadir_correo_jugador
)
from .views_llaves import (
    definir_llaves, organizar_llaves, iniciar_partidos, 
    registrar_resultado, crear_siguientes_rondas
)

# Importar utilidades
from .utils import (
    rut_valido, normalizar_rut, limpiar_texto_estricto, 
    limpiar_email_estricto, fecha_valida, correo_valido
)


# ================= VISTAS BÁSICAS =================

def mi_vista_restringida(request):
    """Vista de prueba restringida"""
    return render(request, 'mi_template.html')


@login_required
def home(request):
    """Vista principal después del login"""
    if request.user.groups.filter(name='Jugadores').exists():
        return render(request, 'home_jugador.html')
    else:
        return render(request, 'home_organizador.html')


def registro(request):
    """Vista para registro de nuevos usuarios"""
    if request.method == 'POST':
        # Lógica de registro aquí
        pass
    return render(request, 'registro.html')


# ================= VISTAS DE LISTAS =================

@login_required
def lista_clubes(request):
    """Vista para listar clubes"""
    clubes = Club.objects.all()
    return render(request, 'lista_clubes.html', {'clubes': clubes})


@login_required
def lista_categorias(request):
    """Vista para listar categorías"""
    categorias = Categoria.objects.all()
    
    # Dividir categorías por tipo
    categorias_masculinas = []
    categorias_femeninas = []
    categorias_mixtas = []
    
    for categoria in categorias:
        if 'Masculin' in categoria.nombre or 'masculin' in categoria.nombre:
            categorias_masculinas.append(categoria)
        elif 'Femenin' in categoria.nombre or 'femenin' in categoria.nombre:
            categorias_femeninas.append(categoria)
        else:
            categorias_mixtas.append(categoria)
    
    context = {
        'categorias_masculinas': categorias_masculinas,
        'categorias_femeninas': categorias_femeninas,
        'categorias_mixtas': categorias_mixtas,
    }
    return render(request, 'lista_categorias.html', context)


# ================= FUNCIONES DE UTILIDAD EXPORTADAS =================
# Estas funciones están disponibles para usar en templates o otras vistas

__all__ = [
    # Vistas principales
    'home', 'registro', 'mi_vista_restringida',
    
    # Vistas de listas
    'lista_clubes', 'lista_categorias',
    
    # Vistas de torneos (importadas)
    'crear_torneo', 'lista_torneos', 'gestionar_torneo', 'gestionar_torneo_federado',
    
    # Vistas de jugadores (importadas)
    'lista_jugadores', 'importar_jugadores', 'anadir_correo_jugador',
    
    # Vistas de llaves (importadas)
    'definir_llaves', 'organizar_llaves', 'iniciar_partidos', 
    'registrar_resultado', 'crear_siguientes_rondas',
    
    # Utilidades (importadas)
    'rut_valido', 'normalizar_rut', 'limpiar_texto_estricto', 
    'limpiar_email_estricto', 'fecha_valida', 'correo_valido',
]
