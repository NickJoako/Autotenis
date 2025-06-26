#!/usr/bin/env python
"""
Script de prueba para validar las reglas de tenis de mesa
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AutoTenis.settings')
django.setup()

from gestiontorneo.views import validar_set

def test_casos_validacion():
    print("=== PRUEBAS DE VALIDACIÓN DE SETS ===\n")
    
    casos_prueba = [
        # (puntos_j1, puntos_j2, descripcion, esperado_valido)
        (11, 9, "Ganador normal 11-9", True),
        (11, 10, "Ganador normal 11-10", True),
        (9, 11, "Ganador normal 9-11", True),
        (10, 11, "Ganador normal 10-11", True),
        
        (10, 10, "Empate 10-10 (en progreso)", True),
        (11, 11, "Empate 11-11 (en progreso)", True),
        (12, 10, "Ganador en deuce 12-10", True),
        (10, 12, "Ganador en deuce 10-12", True),
        (13, 11, "Ganador en deuce 13-11", True),
        (11, 13, "Ganador en deuce 11-13", True),
        (14, 12, "Ganador en deuce 14-12", True),
        (12, 14, "Ganador en deuce 12-14", True),
        
        (12, 9, "Inválido: 12-9 (no llegó a 10)", False),
        (9, 12, "Inválido: 9-12 (no llegó a 10)", False),
        (13, 10, "Inválido: 13-10 (diferencia >2)", False),
        (10, 13, "Inválido: 10-13 (diferencia >2)", False),
        (14, 11, "Inválido: 14-11 (diferencia >2)", False),
        (13, 12, "Inválido: 13-12 (ambos >11, dif≠2)", False),
        (15, 14, "Inválido: 15-14 (ambos >11, dif≠2)", False),
        
        (0, 0, "Set no jugado 0-0", True),
        (0, 5, "Set en progreso 0-5", True),
        (7, 3, "Set en progreso 7-3", True),
    ]
    
    errores = 0
    
    for puntos_j1, puntos_j2, descripcion, esperado_valido in casos_prueba:
        error = validar_set(puntos_j1, puntos_j2, "Set de prueba")
        es_valido = error is None
        
        if es_valido == esperado_valido:
            estado = "✓ PASS"
        else:
            estado = "✗ FAIL"
            errores += 1
        
        print(f"{estado} {descripcion}: {puntos_j1}-{puntos_j2}")
        if error:
            print(f"    Error: {error}")
        print()
    
    print(f"=== RESUMEN ===")
    total = len(casos_prueba)
    exitosos = total - errores
    print(f"Casos exitosos: {exitosos}/{total}")
    print(f"Casos fallidos: {errores}/{total}")
    
    if errores == 0:
        print("🎉 ¡Todas las pruebas pasaron!")
    else:
        print("⚠️  Hay casos que necesitan revisión")
    
    return errores == 0

if __name__ == "__main__":
    test_casos_validacion()
