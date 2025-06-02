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
]