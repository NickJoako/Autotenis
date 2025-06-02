from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import RegistroPersonalizadoForm
from .forms import *
# Create your views here.

@login_required
def mi_vista_restringida(request):
    return render(request, 'pagina_restringida.html')

@login_required
def home(request):
    user = request.user
    # Si el tipo de usuario está en el modelo User
    if hasattr(user, 'tipo_usuario'):
        if user.tipo_usuario == 'organizador':
            return render(request, 'home_organizador.html')
        elif user.tipo_usuario == 'jugador':
            return render(request, 'home_jugador.html')
        elif user.tipo_usuario == 'arbitro':
            return render(request, 'home_arbitro.html')
    return render(request, 'home.html')

def registro(request):
    if request.method == 'POST':
        form = RegistroPersonalizadoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = RegistroPersonalizadoForm()

    return render(request, 'registro.html', {'form': form})

@login_required
def crear_torneo(request):
    if request.method == 'POST':
        form = TorneoForm(request.POST)
        if form.is_valid():
            torneo = form.save(commit=False)
            torneo.organizador = request.user
            torneo.save()
            return redirect('lista_torneos')
    else:
        form = TorneoForm()
    return render(request, 'crear_torneo.html', {'form': form})

@login_required
def lista_torneos(request):
    torneos = Torneo.objects.filter(organizador=request.user)
    return render(request, 'lista_torneos.html', {'torneos': torneos})

@login_required
def lista_clubes(request):
    clubes = Club.objects.filter(organizador=request.user)
    if request.method == 'POST':
        if 'agregar' in request.POST:
            form = ClubForm(request.POST, organizador=request.user)
            if form.is_valid():
                club = form.save(commit=False)
                club.organizador = request.user
                club.save()
                return redirect('lista_clubes')
        elif 'eliminar' in request.POST:
            club_id = request.POST.get('club_id')
            Club.objects.filter(id=club_id, organizador=request.user).delete()
            return redirect('lista_clubes')
    else:
        form = ClubForm(organizador=request.user)
    return render(request, 'lista_clubes.html', {'clubes': clubes, 'form': form})

@login_required
def lista_categorias(request):
    categorias = Categoria.objects.all()
    if request.method == 'POST':
        if 'agregar' in request.POST:
            form = CategoriaForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('lista_categorias')
        elif 'eliminar' in request.POST:
            categoria_id = request.POST.get('categoria_id')
            Categoria.objects.filter(id=categoria_id).delete()
            return redirect('lista_categorias')
    else:
        form = CategoriaForm()
    return render(request, 'lista_categorias.html', {'categorias': categorias, 'form': form})

@login_required
def lista_jugadores(request):
    jugadores = Jugador.objects.filter(organizador=request.user)
    if request.method == 'POST':
        if 'agregar' in request.POST:
            form = JugadorForm(request.POST, organizador=request.user)
            if form.is_valid():
                jugador = form.save(commit=False)
                jugador.organizador = request.user
                jugador.save()
                return redirect('lista_jugadores')
        elif 'eliminar' in request.POST:
            jugador_id = request.POST.get('jugador_id')
            Jugador.objects.filter(id=jugador_id, organizador=request.user).delete()
            return redirect('lista_jugadores')
    else:
        form = JugadorForm(organizador=request.user)
    return render(request, 'lista_jugadores.html', {'jugadores': jugadores, 'form': form})

