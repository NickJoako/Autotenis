import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from gestiontorneo.models import Partido

class PartidoConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.partido_id = self.scope['url_route']['kwargs']['partido_id']
        self.partido_group_name = f'partido_{self.partido_id}'

        # Join partido group
        await self.channel_layer.group_add(
            self.partido_group_name,
            self.channel_name
        )

        await self.accept()

        # Enviar estado actual del partido al conectar
        await self.send_partido_status()

    async def disconnect(self, close_code):
        # Leave partido group
        await self.channel_layer.group_discard(
            self.partido_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json['type']

        if message_type == 'get_status':
            await self.send_partido_status()

    # Receive message from partido group
    async def partido_update(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'partido_update',
            'data': event['data']
        }))

    async def send_partido_status(self):
        """Envía el estado actual del partido"""
        partido_data = await self.get_partido_data()
        await self.send(text_data=json.dumps({
            'type': 'partido_status',
            'data': partido_data
        }))

    @database_sync_to_async
    def get_partido_data(self):
        """Obtiene los datos actuales del partido"""
        try:
            partido = Partido.objects.select_related('resultado_detallado', 'jugador1', 'jugador2').get(id=self.partido_id)
            
            # Obtener puntos actuales y sets
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
                    if not self.tiene_ganador_set(puntos_set_j1, puntos_set_j2):
                        puntos_j1 = puntos_set_j1
                        puntos_j2 = puntos_set_j2
                        set_actual = i
                        break
                    elif i > sets_j1 + sets_j2:  # Siguiente set después de los completados
                        set_actual = i
                        break

            return {
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
        except Partido.DoesNotExist:
            return None

    def tiene_ganador_set(self, puntos_j1, puntos_j2):
        """Verifica si un set tiene ganador según las reglas de tenis de mesa"""
        if puntos_j1 == 0 and puntos_j2 == 0:
            return False
        
        diferencia = abs(puntos_j1 - puntos_j2)
        max_puntos = max(puntos_j1, puntos_j2)
        
        # Victoria normal (11 vs menos de 10)
        if max_puntos == 11 and min(puntos_j1, puntos_j2) < 10:
            return True
        
        # Victoria en deuce (ambos >= 10 y exactamente 2 de diferencia)
        if puntos_j1 >= 10 and puntos_j2 >= 10 and diferencia == 2:
            return True
        
        return False
