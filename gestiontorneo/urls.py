from django.urls import path
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('', views.home, name='home'),
    path('registro/', views.registro, name='registro'),
    path('torneos/', views.lista_torneos, name='lista_torneos'),
    path('torneos/crear/', views.crear_torneo, name='crear_torneo'),
    path('clubes/', views.lista_clubes, name='lista_clubes'),
    path('jugadores/', views.lista_jugadores, name='lista_jugadores'),
    path('categorias/', views.lista_categorias, name='lista_categorias'),
    path('torneos/<int:torneo_id>/gestionar/', views.gestionar_torneo, name='gestionar_torneo'),
    path('jugadores/importar/', views.importar_jugadores, name='importar_jugadores'),    path('jugadores/<int:jugador_id>/anadir_correo/', views.anadir_correo_jugador, name='anadir_correo_jugador'),
    path('torneos/<int:torneo_id>/gestionar/', views.gestionar_torneo, name='gestionar_torneo'),
    path('torneos/<int:torneo_id>/gestionar_federado/', views.gestionar_torneo_federado, name='gestionar_torneo_federado'),    path('torneos/<int:torneo_id>/participantes/', views.ingresar_participantes, name='ingresar_participantes'),    path('torneos/<int:torneo_id>/listado_participantes/', views.listado_participantes, name='listado_participantes'),    path('torneos/<int:torneo_id>/eliminar_participante/<str:participante_rut>/', views.eliminar_participante, name='eliminar_participante'),
    # URLs para modalidades de torneo
    path('torneos/<int:torneo_id>/modalidad/llaves/', views.modalidad_llaves, name='modalidad_llaves'),
    path('torneos/<int:torneo_id>/modalidad/grupos/', views.modalidad_grupos, name='modalidad_grupos'),
    # URLs para organización de grupos
    path('torneos/<int:torneo_id>/organizar-grupos/', views.organizar_grupos, name='organizar_grupos'),
    path('torneos/<int:torneo_id>/definir-cabezas-serie/', views.definir_cabezas_serie, name='definir_cabezas_serie'),
    # URLs para llaves
    path('torneos/<int:torneo_id>/vista-previa-asignacion/', views.vista_previa_asignacion, name='vista_previa_asignacion'),
    path('torneos/<int:torneo_id>/vista-previa-asignacion-pagina/', views.vista_previa_asignacion_pagina, name='vista_previa_asignacion_pagina'),
]
