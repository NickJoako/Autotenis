"""
Vistas para la gestión de árbitros en el sistema de torneos de tenis.

Este módulo contiene todas las vistas relacionadas con las funcionalidades
de los árbitros, incluyendo panel de control, gestión de partidos,
arbitraje en tiempo real y historial de arbitrajes.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import models
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json
from gestiontorneo.models import Partido, Torneo, UsuarioPersonalizado, Resultado
from gestiontorneo.decorators import require_arbitro

@require_arbitro
def panel_arbitro(request):
    """
    Vista principal del panel de control del árbitro.
    
    Muestra estadísticas generales del árbitro incluyendo:
    - Partidos asignados
    - Partidos completados
    - Partidos pendientes
    - Torneos activos donde participa
    
    Args:
        request (HttpRequest): Objeto de petición HTTP
        
    Returns:
        HttpResponse: Template del panel con estadísticas
    """    
    # Obtener estadísticas del árbitro
    partidos_asignados = Partido.objects.filter(arbitro=request.user).count()
    partidos_completados = Partido.objects.filter(arbitro=request.user, finalizado=True).count()
    partidos_pendientes = Partido.objects.filter(arbitro=request.user, finalizado=False).count()
    
    # Obtener torneos activos donde participa como árbitro
    torneos_activos = Torneo.objects.filter(
        partidos__arbitro=request.user,
        finalizado=False
    ).distinct().count()
    
    context = {
        'partidos_asignados': partidos_asignados,
        'partidos_completados': partidos_completados,
        'partidos_pendientes': partidos_pendientes,
        'torneos_activos': torneos_activos,
    }
    
    return render(request, 'arbitros/panel.html', context)

@require_arbitro
def partidos_asignados(request):
    """
    Vista para mostrar todos los partidos asignados al árbitro.
    
    Muestra únicamente los partidos que están pendientes o en curso,
    ordenados por fecha y hora programada.
    
    Args:
        request (HttpRequest): Objeto de petición HTTP
        
    Returns:
        HttpResponse: Template con lista de partidos asignados
    """    
    partidos = Partido.objects.filter(
        arbitro=request.user,
        finalizado=False
    ).select_related('torneo', 'jugador1', 'jugador2').order_by('fecha_programada', 'hora_programada')
    
    context = {
        'partidos': partidos,
    }
    
    return render(request, 'arbitros/partidos_asignados.html', context)

@require_arbitro
def historial_arbitrajes(request):
    """
    Vista para mostrar el historial completo de arbitrajes del árbitro.
    
    Muestra todos los partidos que el árbitro ha completado,
    ordenados por fecha de finalización más reciente.
    
    Args:
        request (HttpRequest): Objeto de petición HTTP
        
    Returns:
        HttpResponse: Template con historial de arbitrajes
    """    
    partidos = Partido.objects.filter(
        arbitro=request.user,
        finalizado=True
    ).select_related('torneo', 'jugador1', 'jugador2').order_by('-fecha_fin')
    
    context = {
        'partidos': partidos,
    }
    
    return render(request, 'arbitros/historial.html', context)

@require_arbitro
def arbitrar_partido(request, partido_id):
    """
    Vista principal para arbitrar un partido específico.
    
    Proporciona la interfaz de control de puntos en tiempo real,
    con soporte para diferentes modalidades de sets y cálculo
    automático del estado del partido.
    
    Args:
        request (HttpRequest): Objeto de petición HTTP
        partido_id (int): ID del partido a arbitrar
        
    Returns:
        HttpResponse: Template del panel de arbitraje
    """    
    partido = get_object_or_404(Partido, id=partido_id, arbitro=request.user)
    
    # Obtener o crear resultado
    resultado, created = Resultado.objects.get_or_create(partido=partido)
    
    # Determinar modalidad (final vs normal)
    total_rondas = partido.torneo.llaves.aggregate(max_ronda=models.Max('ronda'))['max_ronda'] or 1
    es_partido_final = partido.llave_torneo.ronda == total_rondas
    mejor_de_sets = partido.torneo.mejor_de_sets_final if es_partido_final else partido.torneo.mejor_de_sets
    sets_para_ganar = (mejor_de_sets // 2) + 1
    
    # Calcular set actual y puntos actuales
    set_actual = calcular_set_actual(resultado, mejor_de_sets)
    puntos_actuales = obtener_puntos_set_actual(resultado, set_actual)
    
    context = {
        'partido': partido,
        'resultado': resultado,
        'mejor_de_sets': mejor_de_sets,
        'sets_para_ganar': sets_para_ganar,
        'set_actual': set_actual,
        'puntos_actuales': puntos_actuales,
    }
    
    return render(request, 'arbitros/arbitrar_partido.html', context)


def calcular_set_actual(resultado, mejor_de_sets):
    """
    Calcula qué set se está jugando actualmente.
    
    Determina el primer set que no tiene puntos registrados
    o que está en curso basándose en la modalidad del torneo.
    
    Args:
        resultado (Resultado): Objeto resultado del partido
        mejor_de_sets (int): Modalidad del torneo (3, 5, 7, 9)
        
    Returns:
        int: Número del set actual (1-9)
    """
    # Calcular cuántos sets deberían estar ganados según los puntos
    sets_j1_por_puntos = 0
    sets_j2_por_puntos = 0
    
    for i in range(1, mejor_de_sets + 1):
        puntos_j1 = getattr(resultado, f'set{i}_jugador1', 0)
        puntos_j2 = getattr(resultado, f'set{i}_jugador2', 0)
        
        if tiene_ganador_set(puntos_j1, puntos_j2):
            if puntos_j1 > puntos_j2:
                sets_j1_por_puntos += 1
            else:
                sets_j2_por_puntos += 1
    
    # Si los sets ganados oficiales no coinciden con los calculados,
    # significa que hay sets pendientes de "guardar"
    if (resultado.sets_ganados_jugador1 != sets_j1_por_puntos or 
        resultado.sets_ganados_jugador2 != sets_j2_por_puntos):
        
        # Encontrar el primer set con ganador que no esté reflejado en sets_ganados
        sets_procesados_j1 = 0
        sets_procesados_j2 = 0
        
        for i in range(1, mejor_de_sets + 1):
            puntos_j1 = getattr(resultado, f'set{i}_jugador1', 0)
            puntos_j2 = getattr(resultado, f'set{i}_jugador2', 0)
            
            if tiene_ganador_set(puntos_j1, puntos_j2):
                if puntos_j1 > puntos_j2:
                    sets_procesados_j1 += 1
                else:
                    sets_procesados_j2 += 1
                
                # Si este set hace que los contadores excedan los oficiales,
                # este es el set actual (pendiente de guardar)
                if (sets_procesados_j1 > resultado.sets_ganados_jugador1 or 
                    sets_procesados_j2 > resultado.sets_ganados_jugador2):
                    return i
    
    # Si no hay sets pendientes, buscar el primer set sin ganador
    for i in range(1, mejor_de_sets + 1):
        puntos_j1 = getattr(resultado, f'set{i}_jugador1', 0)
        puntos_j2 = getattr(resultado, f'set{i}_jugador2', 0)
        
        if not tiene_ganador_set(puntos_j1, puntos_j2):
            return i
    
    # Si todos los sets tienen ganador y están sincronizados, el partido terminó
    return mejor_de_sets

def tiene_ganador_set(puntos_j1, puntos_j2):
    """Determina si un set tiene un ganador claro según las reglas de tenis de mesa"""
    if puntos_j1 == 0 and puntos_j2 == 0:
        return False  # Set no jugado
    
    diferencia = abs(puntos_j1 - puntos_j2)
    max_puntos = max(puntos_j1, puntos_j2)
    min_puntos = min(puntos_j1, puntos_j2)
    
    # Victoria normal: 11 vs menos de 10
    if max_puntos == 11 and min_puntos < 10:
        return True
    
    # Victoria en deuce: ambos >= 10 y diferencia exacta de 2
    if min_puntos >= 10 and diferencia == 2:
        return True
    
    return False

def obtener_puntos_set_actual(resultado, set_actual):
    """Obtiene los puntos del set que se está jugando actualmente"""
    puntos_j1 = getattr(resultado, f'set{set_actual}_jugador1', 0)
    puntos_j2 = getattr(resultado, f'set{set_actual}_jugador2', 0)
    return [puntos_j1, puntos_j2]

@require_arbitro
@csrf_exempt
def guardar_set(request, partido_id):
    """Vista AJAX para guardar un set"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})
    
    try:
        partido = get_object_or_404(Partido, id=partido_id, arbitro=request.user)
        data = json.loads(request.body)
        
        set_numero = data.get('set_numero')
        puntos_j1 = data.get('puntos_jugador1')
        puntos_j2 = data.get('puntos_jugador2')
        ganador_set = data.get('ganador_set')
        
        # Validaciones
        if not all([set_numero, puntos_j1 is not None, puntos_j2 is not None, ganador_set]):
            return JsonResponse({'success': False, 'message': 'Datos incompletos'})
        
        # Validar puntos según reglas de tenis de mesa
        error_validacion = validar_set_tenis_mesa(puntos_j1, puntos_j2)
        if error_validacion:
            return JsonResponse({'success': False, 'message': error_validacion})
        
        # Verificar que hay un ganador válido
        if not tiene_ganador_set(puntos_j1, puntos_j2):
            return JsonResponse({'success': False, 'message': 'El set no tiene un ganador válido'})
        
        # Obtener resultado
        resultado, created = Resultado.objects.get_or_create(partido=partido)
        
        # Verificar que este set específico puede ser guardado
        # Un set puede ser guardado si:
        # 1. Los puntos enviados constituyen un ganador válido
        # 2. Los sets_ganados oficiales no reflejan aún este resultado
        
        puntos_actuales_j1 = getattr(resultado, f'set{set_numero}_jugador1', 0)
        puntos_actuales_j2 = getattr(resultado, f'set{set_numero}_jugador2', 0)
        
        # Verificar si este set ya fue oficialmente procesado
        # Contamos cuántos sets con ganador hay hasta este set número
        sets_con_ganador_j1 = 0
        sets_con_ganador_j2 = 0
        
        for i in range(1, set_numero + 1):
            p_j1 = getattr(resultado, f'set{i}_jugador1', 0)
            p_j2 = getattr(resultado, f'set{i}_jugador2', 0)
            
            # Si es el set actual, usar los puntos enviados
            if i == set_numero:
                if puntos_j1 > puntos_j2:
                    sets_con_ganador_j1 += 1
                elif puntos_j2 > puntos_j1:
                    sets_con_ganador_j2 += 1
            # Para otros sets, usar los puntos guardados
            elif tiene_ganador_set(p_j1, p_j2):
                if p_j1 > p_j2:
                    sets_con_ganador_j1 += 1
                elif p_j2 > p_j1:
                    sets_con_ganador_j2 += 1
        
        # Si los sets ganados oficiales ya reflejan este resultado, el set ya está guardado
        if (resultado.sets_ganados_jugador1 >= sets_con_ganador_j1 and 
            resultado.sets_ganados_jugador2 >= sets_con_ganador_j2):
            return JsonResponse({'success': False, 'message': f'El set {set_numero} ya está guardado'})
        
        # Guardar puntos del set
        setattr(resultado, f'set{set_numero}_jugador1', puntos_j1)
        setattr(resultado, f'set{set_numero}_jugador2', puntos_j2)
        resultado.save()
        
        # **NUEVO**: Enviar actualización via WebSocket
        enviar_actualizacion_partido(partido.id)
        
        # Determinar modalidad y verificar si el partido terminó
        total_rondas = partido.torneo.llaves.aggregate(max_ronda=models.Max('ronda'))['max_ronda'] or 1
        es_partido_final = partido.llave_torneo.ronda == total_rondas
        mejor_de_sets = partido.torneo.mejor_de_sets_final if es_partido_final else partido.torneo.mejor_de_sets
        sets_para_ganar = (mejor_de_sets // 2) + 1
        
        # Verificar si el partido terminó
        cerrado, mensaje = partido.verificar_y_cerrar_partido()
        if cerrado:
            ganador_nombre = partido.jugador1_nombre if resultado.sets_ganados_jugador1 > resultado.sets_ganados_jugador2 else partido.jugador2_nombre
            
            return JsonResponse({
                'success': True, 
                'message': f'Set {set_numero} guardado exitosamente',
                'partido_terminado': True,
                'ganador_partido': ganador_nombre
            })
        
        return JsonResponse({
            'success': True, 
            'message': f'Set {set_numero} guardado exitosamente',
            'partido_terminado': False
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})

@require_arbitro
@csrf_exempt
def cerrar_partido(request, partido_id):
    """Vista AJAX para cerrar un partido"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})
    
    try:
        partido = get_object_or_404(Partido, id=partido_id, arbitro=request.user)
        data = json.loads(request.body)
        
        sets_j1 = data.get('sets_jugador1')
        sets_j2 = data.get('sets_jugador2')
        
        # Determinar modalidad
        total_rondas = partido.torneo.llaves.aggregate(max_ronda=models.Max('ronda'))['max_ronda'] or 1
        es_partido_final = partido.llave_torneo.ronda == total_rondas
        mejor_de_sets = partido.torneo.mejor_de_sets_final if es_partido_final else partido.torneo.mejor_de_sets
        sets_para_ganar = (mejor_de_sets // 2) + 1
        
        # Validaciones
        if sets_j1 < sets_para_ganar and sets_j2 < sets_para_ganar:
            return JsonResponse({
                'success': False, 
                'message': f'No se puede cerrar el partido. Ningún jugador ha alcanzado {sets_para_ganar} sets.'
            })
        
        if sets_j1 == sets_j2:
            return JsonResponse({'success': False, 'message': 'No se puede cerrar el partido en empate.'})
        
        # Determinar el ganador
        if sets_j1 > sets_j2:
            ganador = partido.jugador1
            ganador_nombre = partido.jugador1_nombre
        else:
            ganador = partido.jugador2
            ganador_nombre = partido.jugador2_nombre
        
        # Cerrar partido y asignar ganador
        partido.finalizado = True
        partido.estado_partido = 'jugado'
        partido.ganador = ganador
        partido.fecha_fin = timezone.now()
        partido.save()
        
        # **CRUCIAL**: Actualizar también el ganador en la LlaveTorneo
        if partido.llave_torneo:
            partido.llave_torneo.ganador = ganador
            partido.llave_torneo.estado_partido = 'jugado'
            partido.llave_torneo.save()
            
            # Avanzar automáticamente a la siguiente ronda
            partido.avanzar_ganador_automaticamente()
            
            # Verificar si se completaron las semifinales para crear tercer lugar
            partido.verificar_y_crear_tercer_lugar()
        
        # **NUEVO**: Enviar actualización via WebSocket
        enviar_actualizacion_partido(partido.id)
        
        return JsonResponse({
            'success': True,
            'message': 'Partido cerrado exitosamente',
            'ganador': ganador_nombre
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})

@require_arbitro
@csrf_exempt
def actualizar_puntos(request, partido_id):
    """Vista AJAX para actualizar puntos en tiempo real"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})
    
    try:
        partido = get_object_or_404(Partido, id=partido_id, arbitro=request.user)
        data = json.loads(request.body)
        
        accion = data.get('accion')  # 'sumar' o 'restar'
        jugador = data.get('jugador')  # 1 o 2
        
        if accion not in ['sumar', 'restar'] or jugador not in [1, 2]:
            return JsonResponse({'success': False, 'message': 'Datos inválidos'})
        
        # Obtener o crear resultado
        resultado, created = Resultado.objects.get_or_create(partido=partido)
        
        # Determinar el set actual
        sets_j1 = resultado.sets_ganados_jugador1
        sets_j2 = resultado.sets_ganados_jugador2
        set_actual = sets_j1 + sets_j2 + 1
        
        # Obtener puntos actuales del set en progreso
        puntos_j1 = getattr(resultado, f'set{set_actual}_jugador1', 0)
        puntos_j2 = getattr(resultado, f'set{set_actual}_jugador2', 0)
        
        # Aplicar la acción
        if jugador == 1:
            if accion == 'sumar':
                puntos_j1 += 1
            elif accion == 'restar' and puntos_j1 > 0:
                puntos_j1 -= 1
        else:  # jugador == 2
            if accion == 'sumar':
                puntos_j2 += 1
            elif accion == 'restar' and puntos_j2 > 0:
                puntos_j2 -= 1
        
        # Guardar los puntos actualizados SIN disparar lógica automática de cierre
        # Usamos update() en lugar de save() para evitar el método save() que tiene verificar_y_cerrar_partido()
        Resultado.objects.filter(id=resultado.id).update(**{
            f'set{set_actual}_jugador1': puntos_j1,
            f'set{set_actual}_jugador2': puntos_j2
        })
        
        # Refrescar el objeto desde la base de datos
        resultado.refresh_from_db()
        
        # Enviar actualización via WebSocket
        enviar_actualizacion_partido(partido.id)
        
        return JsonResponse({
            'success': True,
            'puntos_j1': puntos_j1,
            'puntos_j2': puntos_j2,
            'set_actual': set_actual
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})

def validar_set_tenis_mesa(puntos_j1, puntos_j2):
    """Valida los puntos de un set según las reglas de tenis de mesa"""
    if puntos_j1 < 0 or puntos_j2 < 0:
        return "Los puntos no pueden ser negativos"
    
    # Si ambos tienen 0 puntos, está permitido (set no jugado)
    if puntos_j1 == 0 and puntos_j2 == 0:
        return "El set no se ha jugado"
    
    if puntos_j1 == puntos_j2:
        return "No se puede terminar un set en empate"
    
    diferencia = abs(puntos_j1 - puntos_j2)
    max_puntos = max(puntos_j1, puntos_j2)
    min_puntos = min(puntos_j1, puntos_j2)
    
    # Caso 1: Ninguno llegó a 11 - set no terminado
    if max_puntos < 11:
        return "El set no está terminado. Se necesita al menos 11 puntos para ganar"
    
    # Caso 2: Victoria normal (11 vs menos de 10)
    if max_puntos == 11 and min_puntos < 10:
        return None  # Válido
    
    # Caso 3: Uno pasó de 11 pero el otro no tiene al menos 10
    if max_puntos > 11 and min_puntos < 10:
        return "No puedes tener más de 11 puntos si el oponente tiene menos de 10"
    
    # Caso 4: Ambos >= 10, debe haber exactamente 2 de diferencia
    if min_puntos >= 10:
        if diferencia == 2:
            return None  # Válido
        elif diferencia < 2:
            return "En empate 10-10 o más, debe haber exactamente 2 puntos de diferencia para ganar"
        else:
            return "La diferencia máxima permitida es de 2 puntos en deuce"
    
    return "Puntuación inválida para terminar el set"

def enviar_actualizacion_partido(partido_id):
    """Envía actualización del partido via WebSocket"""
    try:
        channel_layer = get_channel_layer()
        partido_group_name = f'partido_{partido_id}'
        
        # Obtener datos actualizados del partido
        partido = Partido.objects.select_related('resultado_detallado', 'jugador1', 'jugador2', 'ganador').get(id=partido_id)
        
        # Calcular puntos y sets actuales
        puntos_j1, puntos_j2 = 0, 0
        sets_j1, sets_j2 = 0, 0
        set_actual = 1
        
        if hasattr(partido, 'resultado_detallado'):
            resultado = partido.resultado_detallado
            sets_j1 = resultado.sets_ganados_jugador1
            sets_j2 = resultado.sets_ganados_jugador2
            
            # Buscar el set actual en progreso
            for i in range(1, 8):  # Máximo 7 sets
                puntos_set_j1 = getattr(resultado, f'set{i}_jugador1', 0)
                puntos_set_j2 = getattr(resultado, f'set{i}_jugador2', 0)
                
                # Si el set no tiene ganador, es el set actual
                if not tiene_ganador_set(puntos_set_j1, puntos_set_j2):
                    puntos_j1 = puntos_set_j1
                    puntos_j2 = puntos_set_j2
                    set_actual = i
                    break
                elif i > sets_j1 + sets_j2:  # Siguiente set después de los completados
                    set_actual = i
                    break

        data = {
            'partido_id': partido.id,
            'jugador1': {
                'nombre': f"{partido.jugador1.nombre} {partido.jugador1.apellido}" if partido.jugador1 else "BYE",
                'puntos': puntos_j1,
                'sets': sets_j1
            },
            'jugador2': {
                'nombre': f"{partido.jugador2.nombre} {partido.jugador2.apellido}" if partido.jugador2 else "BYE",
                'puntos': puntos_j2,
                'sets': sets_j2
            },
            'set_actual': set_actual,
            'estado': partido.estado_partido,
            'finalizado': partido.finalizado,
            'ganador': f"{partido.ganador.nombre} {partido.ganador.apellido}" if partido.ganador else None
        }
        
        async_to_sync(channel_layer.group_send)(
            partido_group_name,
            {
                'type': 'partido_update',
                'data': data
            }
        )
    except Exception as e:
        print(f"Error enviando actualización WebSocket: {e}")

@require_arbitro
def verificar_partidos_ajax(request):
    """Vista AJAX para verificar partidos asignados al árbitro en tiempo real"""
    try:
        # Obtener partidos actuales del árbitro
        partidos_actuales = Partido.objects.filter(
            arbitro=request.user,
            finalizado=False
        ).values('id', 'pendiente_confirmacion')
        
        # Crear listas de IDs y estados
        partidos_ids = [p['id'] for p in partidos_actuales]
        partidos_pendientes = [p['id'] for p in partidos_actuales if p['pendiente_confirmacion']]
        
        # Contar partidos
        total_partidos = len(partidos_ids)
        
        data = {
            'total_partidos': total_partidos,
            'partidos_ids': partidos_ids,
            'partidos_pendientes_confirmacion': partidos_pendientes,
            'timestamp': timezone.now().isoformat(),
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
