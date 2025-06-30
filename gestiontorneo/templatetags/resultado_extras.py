from django import template

register = template.Library()

@register.filter
def get_guardado(sets_guardados, set_num):
    """Obtiene si un set específico está guardado"""
    return sets_guardados.get(f"set{set_num}", False)

@register.filter
def get_set_value(resultado, args):
    """Obtiene el valor de un set específico de un jugador"""
    try:
        set_num, jugador = args.split(',')
        return getattr(resultado, f"set{set_num}_{jugador}", "")
    except:
        return ""

@register.filter 
def get_set_value_simple(resultado, field_name):
    """Obtiene el valor de un campo específico del resultado"""
    return getattr(resultado, field_name, "")

@register.filter
def get_set_jugador(resultado, set_jugador):
    """Obtiene el valor del set y jugador específico (ej: set1_jugador1)"""
    return getattr(resultado, set_jugador, "")

@register.filter
def has_guardados(sets_guardados, sets_list):
    """Verifica si hay algún set guardado"""
    for set_num in sets_list:
        if sets_guardados.get(f"set{set_num}", False):
            return True
    return False

@register.filter
def get_valor_set(resultado, args):
    """Obtiene el valor del set usando set_num y jugador"""
    try:
        parts = args.split(',')
        set_num = parts[0].strip()
        jugador = parts[1].strip()
        field_name = f"set{set_num}_{jugador}"
        valor = getattr(resultado, field_name, None)
        return valor if valor is not None else ""
    except:
        return ""

@register.filter
def get_from_dict(dictionary, key):
    """Obtiene un valor de un diccionario usando una clave"""
    return dictionary.get(key, "")