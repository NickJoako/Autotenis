from django.core.management.base import BaseCommand
from gestiontorneo.models import Jugador, Club
import re
import unicodedata
import pandas as pd


def limpiar_texto_estricto(texto):
    if pd.isna(texto) or texto is None or texto == '':
        return ''
    
    texto = str(texto).strip()
    
    texto = texto.replace('\r', ' ').replace('\n', ' ').replace('\t', ' ')
    texto = texto.replace('_x000D_', ' ').replace('_x000A_', ' ')
    texto = texto.replace('x000D', ' ').replace('x000A', ' ')
    
    texto = unicodedata.normalize('NFC', texto)
    
    texto = re.sub(r"[^a-zA-ZáéíóúÁÉÍÓÚñÑ0-9 .\-]", "", texto)
    
    texto = re.sub(r"\s+", " ", texto)
    
    texto = re.sub(r"-+", "-", texto)
    
    texto = re.sub(r"\.+", ".", texto)
    
    return texto.strip()


def limpiar_email_estricto(email):
    if pd.isna(email) or email is None or email == '':
        return ''
    
    email = str(email).strip().lower()
    
    email = email.replace('\r', '').replace('\n', '').replace('\t', '')
    email = email.replace('_x000D_', '').replace('_x000A_', '')
    email = email.replace('x000D', '').replace('x000A', '')
    
    email = unicodedata.normalize('NFC', email)
    
    email = re.sub(r"[^a-z0-9@.\-_]", "", email)
    
    return email.strip()


class Command(BaseCommand):
    help = 'Limpia todos los datos existentes de jugadores y clubes, removiendo caracteres especiales'

    def handle(self, *args, **options):
        self.stdout.write("Iniciando limpieza de datos existentes...")
        
        # Limpiar jugadores
        jugadores_actualizados = 0
        for jugador in Jugador.objects.all():
            nombre_original = jugador.nombre
            apellido_original = jugador.apellido
            email_original = jugador.email
            
            # Limpiar campos
            jugador.nombre = limpiar_texto_estricto(jugador.nombre)
            jugador.apellido = limpiar_texto_estricto(jugador.apellido)
            
            if jugador.email:
                jugador.email = limpiar_email_estricto(jugador.email)
                if not jugador.email:  # Si queda vacío después de limpiar
                    jugador.email = None
            
            # Solo guardar si hubo cambios
            if (nombre_original != jugador.nombre or 
                apellido_original != jugador.apellido or 
                email_original != jugador.email):
                
                try:
                    jugador.save()
                    jugadores_actualizados += 1
                    self.stdout.write(
                        f"Actualizado jugador: {nombre_original} -> {jugador.nombre}"
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Error actualizando jugador {jugador.id}: {e}")
                    )
        
        # Limpiar clubes
        clubes_actualizados = 0
        for club in Club.objects.all():
            nombre_original = club.nombre
            club.nombre = limpiar_texto_estricto(club.nombre)
            
            if nombre_original != club.nombre:
                try:
                    club.save()
                    clubes_actualizados += 1
                    self.stdout.write(
                        f"Actualizado club: {nombre_original} -> {club.nombre}"
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Error actualizando club {club.id}: {e}")
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Limpieza completada. "
                f"Jugadores actualizados: {jugadores_actualizados}, "
                f"Clubes actualizados: {clubes_actualizados}"
            )
        )
