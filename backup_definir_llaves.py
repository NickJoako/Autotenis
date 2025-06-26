# Backup de la función definir_llaves corregida

@login_required
def definir_llaves_temporal(request, torneo_id):
    """Función temporal para definir llaves"""
    torneo = get_object_or_404(Torneo, id=torneo_id, organizador=request.user)
    
    # Verificar que el torneo esté en modalidad llaves
    if torneo.modalidad != 'llaves' or not torneo.torneo_iniciado:
        messages.error(request, "El torneo no está en modalidad llaves o no ha sido iniciado.")
        return redirect('gestionar_torneo', torneo_id=torneo.id)
    
    participantes = list(torneo.participaciones.select_related('jugador').all())
    num_participantes = len(participantes)
    
    # Calcular la potencia de 2 más cercana (hacia arriba)
    import math
    potencia_2_siguiente = 2 ** math.ceil(math.log2(max(num_participantes, 2)))
    
    # Calcular BYE necesarias
    byes_necesarias = potencia_2_siguiente - num_participantes if num_participantes > 0 else 0
    
    # Calcular número de rondas
    rondas_necesarias = math.ceil(math.log2(potencia_2_siguiente)) if num_participantes > 1 else 1
    
    # Determinar si es un bracket perfecto (potencia de 2)
    es_bracket_perfecto = num_participantes > 0 and (num_participantes & (num_participantes - 1)) == 0
    
    # Crear lista de enfrentamientos para la primera ronda
    num_enfrentamientos = potencia_2_siguiente // 2
    enfrentamientos = []
    for i in range(1, num_enfrentamientos + 1):
        enfrentamientos.append({
            'numero': i,
            'jugador1': None,
            'jugador2': None,
            'es_bye1': False,
            'es_bye2': False
        })
    
    # Mensaje informativo
    if request.method == 'POST':
        messages.info(request, "Funcionalidad de asignación manual en desarrollo. Usa asignación automática por ahora.")
        return redirect('organizar_llaves', torneo_id=torneo.id)
    
    context = {
        'torneo': torneo,
        'participantes': participantes,
        'num_participantes': num_participantes,
        'potencia_2_siguiente': potencia_2_siguiente,
        'byes_necesarias': byes_necesarias,
        'rondas_necesarias': rondas_necesarias,
        'es_bracket_perfecto': es_bracket_perfecto,
        'enfrentamientos': enfrentamientos,
        'num_enfrentamientos': num_enfrentamientos,
    }
    
    return render(request, 'definir_llaves.html', context)
