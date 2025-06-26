def validar_set(puntos_j1, puntos_j2, nombre_set):
    """
    Valida los puntos de un set según las reglas de tenis de mesa:
    - Máximo 11 puntos normalmente
    - Si empate 10-10, se necesita diferencia de 2 puntos
    - El ganador puede tener más de 11 solo si el oponente tiene al menos 10
    """
    # Validar que los puntos no sean negativos
    if puntos_j1 < 0 or puntos_j2 < 0:
        return f"{nombre_set}: Los puntos no pueden ser negativos."
    
    # Si ambos tienen 0 puntos, está permitido (set no jugado)
    if puntos_j1 == 0 and puntos_j2 == 0:
        return None
    
    # Caso 1: Ninguno llegó a 11 - válido siempre
    if puntos_j1 < 11 and puntos_j2 < 11:
        return None
    
    # Caso 2: Uno llegó a 11 y el otro tiene menos de 10
    if puntos_j1 == 11 and puntos_j2 < 10:
        return None
    if puntos_j2 == 11 and puntos_j1 < 10:
        return None
    
    # Caso 3: Uno pasó de 11 pero el otro no tiene al menos 10
    if puntos_j1 > 11 and puntos_j2 < 10:
        return f"{nombre_set}: No puedes tener más de 11 puntos si el oponente tiene menos de 10."
    if puntos_j2 > 11 and puntos_j1 < 10:
        return f"{nombre_set}: No puedes tener más de 11 puntos si el oponente tiene menos de 10."
    
    # Caso 4: Ambos pasaron de 11 - solo válido si la diferencia es exactamente 2
    if puntos_j1 > 11 and puntos_j2 > 11:
        diferencia = abs(puntos_j1 - puntos_j2)
        if diferencia != 2:
            return f"{nombre_set}: Cuando ambos pasan de 11 puntos, debe haber exactamente 2 puntos de diferencia."
        return None
    
    # Caso 5: Empate en 10-10 o más - validar diferencia de 2
    if puntos_j1 >= 10 and puntos_j2 >= 10:
        diferencia = abs(puntos_j1 - puntos_j2)
        if diferencia < 2:
            # Si no hay diferencia de 2, el set no está terminado (válido)
            return None
        elif diferencia == 2:
            # Diferencia correcta de 2, set terminado válido
            return None
        else:
            # Diferencia mayor a 2, inválido
            return f"{nombre_set}: Cuando hay empate en 10-10, la diferencia máxima debe ser de 2 puntos."
    
    return None

# Casos de prueba
if __name__ == "__main__":
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
    
    print("=== PRUEBAS DE VALIDACIÓN DE SETS ===\n")
    
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
