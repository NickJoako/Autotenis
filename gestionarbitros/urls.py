from django.urls import path
from . import views

app_name = 'arbitros'

urlpatterns = [
    path('', views.panel_arbitro, name='panel'),
    path('partidos/', views.partidos_asignados, name='partidos_asignados'),
    path('partidos/verificar-ajax/', views.verificar_partidos_ajax, name='verificar_partidos_ajax'),
    path('historial/', views.historial_arbitrajes, name='historial'),
    path('partido/<int:partido_id>/arbitrar/', views.arbitrar_partido, name='arbitrar_partido'),
    path('partido/<int:partido_id>/guardar-set/', views.guardar_set, name='guardar_set'),
    path('partido/<int:partido_id>/cerrar-partido/', views.cerrar_partido, name='cerrar_partido'),
    path('partido/<int:partido_id>/actualizar-puntos/', views.actualizar_puntos, name='actualizar_puntos'),
]
