from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/partido/(?P<partido_id>\d+)/$', consumers.PartidoConsumer.as_asgi()),
]
