# -*- coding: utf-8 -*-
"""
Vistas para configuración de sets y modalidades de torneo
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Torneo


@login_required
def configurar_sets_llaves(request, torneo_id):
    """Vista para configurar los sets de las llaves"""
    torneo = get_object_or_404(Torneo, id=torneo_id)
    
    if request.method == 'POST':
        # Procesar configuración de sets
        sets_config = request.POST.get('sets_config')
        if sets_config:
            # Guardar configuración
            messages.success(request, 'Configuración de sets guardada correctamente.')
            return redirect('modalidad_llaves', torneo_id=torneo.id)
    
    return render(request, 'configurar_sets_llaves.html', {'torneo': torneo})


@login_required
def modalidad_llaves(request, torneo_id):
    """Vista para gestionar la modalidad de llaves"""
    torneo = get_object_or_404(Torneo, id=torneo_id)
    
    context = {
        'torneo': torneo,
    }
    return render(request, 'modalidad_llaves.html', context)


@login_required
def modalidad_grupos(request, torneo_id):
    """Vista para gestionar la modalidad de grupos"""
    torneo = get_object_or_404(Torneo, id=torneo_id)
    
    context = {
        'torneo': torneo,
    }
    return render(request, 'modalidad_grupos.html', context)
