# -*- coding: utf-8 -*-
"""
Vistas para gestión de participantes
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Torneo, Participacion, Jugador
from .utils import normalizar_rut, limpiar_texto_estricto


@login_required
def ingresar_participantes(request, torneo_id):
    """Vista para ingresar participantes al torneo"""
    torneo = get_object_or_404(Torneo, id=torneo_id)
    
    if request.method == 'POST':
        # Lógica para procesar participantes
        pass
    
    return render(request, 'ingresar_participantes.html', {'torneo': torneo})


@login_required
def listado_participantes(request, torneo_id):
    """Vista para mostrar el listado de participantes"""
    torneo = get_object_or_404(Torneo, id=torneo_id)
    participaciones = Participacion.objects.filter(torneo=torneo)
    
    context = {
        'torneo': torneo,
        'participaciones': participaciones,
    }
    return render(request, 'listado_participantes.html', context)


@login_required
def eliminar_participante(request, torneo_id, participante_rut):
    """Vista para eliminar un participante del torneo"""
    torneo = get_object_or_404(Torneo, id=torneo_id)
    participante_rut_normalizado = normalizar_rut(participante_rut)
    
    try:
        participacion = Participacion.objects.get(
            torneo=torneo, 
            jugador__rut=participante_rut_normalizado
        )
        participacion.delete()
        messages.success(request, f'Participante {participante_rut} eliminado del torneo.')
    except Participacion.DoesNotExist:
        messages.error(request, 'Participante no encontrado.')
    
    return redirect('listado_participantes', torneo_id=torneo.id)
