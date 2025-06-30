"""
Vistas principales del sistema de gestión de torneos de tenis.

Este módulo contiene todas las vistas para la gestión de torneos, jugadores,
partidos, resultados y sistema de autenticación personalizado.
"""

import random
import pandas as pd
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth import authenticate, login
from .forms import *
from django.db.models import Q
from django.db import models
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as DjangoValidationError
import re
from datetime import datetime
import math
import unicodedata
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse, JsonResponse
from .models import GrupoTorneo, ParticipanteGrupo, LlaveTorneo, JugadorBye, UsuarioPersonalizado, ArbitroTorneo
from django.db import transaction
from .decorators import require_organizador, require_jugador, require_arbitro, require_user_type


def login_personalizado(request):
    """
    Vista personalizada para autenticación de usuarios.
    
    Permite autenticación basada en email y tipo de usuario específico,
    soportando diferentes tipos: organizador, árbitro y jugador.
    
    Args:
        request (HttpRequest): Objeto de petición HTTP
        
    Returns:
        HttpResponse: Redirección a home si login exitoso, o template de login con errores
    """
    if request.method == 'POST':
        email = request.POST.get('username')  # El campo se llama username pero contiene el email
        password = request.POST.get('password')
        tipo_usuario = request.POST.get('tipo_usuario')
        
        # Buscar usuario por email y tipo
        try:
            user = UsuarioPersonalizado.objects.get(email=email, tipo_usuario=tipo_usuario)
            # Verificar la contraseña
            if user.check_password(password) and user.activo:
                # Especificar el backend para evitar el error
                backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user, backend=backend)
                # Redirigir según tipo de usuario (ya tienes la lógica en home)
                return redirect('home')
            else:
                messages.error(request, 'Credenciales incorrectas o usuario inactivo')
        except UsuarioPersonalizado.DoesNotExist:
            messages.error(request, 'No existe un usuario con ese email y tipo de usuario')
        
        return render(request, 'login.html', {'form': {'errors': True}})
    
    return render(request, 'login.html')

def rut_valido(rut):
    return bool(re.match(r'^\d{7,8}-[\dkK]$', str(rut)))

def normalizar_rut(rut):
    return str(rut).replace('.', '').replace(' ', '').upper()

def limpiar_texto_estricto(texto):
    if pd.isna(texto) or texto is None:
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
    if pd.isna(email) or email is None:
        return ''
    
    email = str(email).strip().lower()
    
    email = email.replace('\r', '').replace('\n', '').replace('\t', '')
    email = email.replace('_x000D_', '').replace('_x000A_', '')
    email = email.replace('x000D', '').replace('x000A', '')
    
    email = unicodedata.normalize('NFC', email)
    
    email = re.sub(r"[^a-z0-9@.\-_]", "", email)
    
    return email.strip()

def fecha_valida(fecha):
    if isinstance(fecha, datetime):
        return True
    formatos = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"]
    for fmt in formatos:
        try:
            datetime.strptime(str(fecha), fmt)
            return True
        except ValueError:
            continue
    return False

def correo_valido(correo):
    if not correo:
        return True
    try:
        validate_email(str(correo))
        return True
    except DjangoValidationError:
        return False

@login_required
def mi_vista_restringida(request):
    return render(request, 'pagina_restringida.html')

@login_required
def home(request):
    user = request.user
    if hasattr(user, 'tipo_usuario'):
        if user.tipo_usuario == 'organizador':
            return render(request, 'home_organizador.html')
        elif user.tipo_usuario == 'jugador':
            return render(request, 'home_jugador.html')
        elif user.tipo_usuario == 'arbitro':
            return redirect('arbitros:panel')
    return render(request, 'home.html')

def registro(request):
    if request.method == 'POST':
        form = RegistroPersonalizadoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "¡Registro exitoso! Ahora puedes iniciar sesión.")
            return redirect('registro')
    else:
        form = RegistroPersonalizadoForm()

    return render(request, 'registro.html', {'form': form})

@require_organizador
def crear_torneo(request):
    if request.method == 'POST':
        form = TorneoForm(request.POST)
        if form.is_valid():
            torneo = form.save(commit=False)
            torneo.organizador = request.user
            torneo.save()
            messages.success(request, f"Torneo {torneo.nombre} creado exitosamente.")
            return redirect('lista_torneos')
    else:
        form = TorneoForm()
    return render(request, 'crear_torneo.html', {'form': form})

@require_organizador
def lista_torneos(request):
    # Ordenar por ID descendente (más recientes primero, ya que el ID es incremental)
    torneos = Torneo.objects.filter(organizador=request.user).order_by('-id')
    
    # Agregar información sobre si cada torneo tiene partidos creados
    for torneo in torneos:
        if torneo.modalidad == 'llaves':
            # Verificar si el torneo tiene partidos creados
            torneo.tiene_partidos = torneo.partidos.exists()
        else:
            torneo.tiene_partidos = False
    
    return render(request, 'lista_torneos.html', {'torneos': torneos})

@require_organizador
def lista_clubes(request):
    clubes = Club.objects.all()
    return render(request, 'lista_clubes.html', {'clubes': clubes})

@require_organizador
def lista_categorias(request):
    categorias = Categoria.objects.all().order_by('edad_minima')
    
    if request.method == 'POST':
        if 'agregar' in request.POST:
            form = CategoriaForm(request.POST)
            if form.is_valid():
                try:
                    categoria = form.save()
                    messages.success(request, f"✅ Categoría '{categoria.nombre}' agregada correctamente.")
                    return redirect('lista_categorias')
                except Exception as e:
                    messages.error(request, f"❌ Error al guardar la categoría: {str(e)}")
            else:
                # Mostrar errores del formulario
                for field, errors in form.errors.items():
                    for error in errors:
                        if field == '__all__':
                            messages.error(request, f"❌ {error}")
                        else:
                            field_name = form.fields[field].label or field
                            messages.error(request, f"❌ {field_name}: {error}")
        
        elif 'eliminar' in request.POST:
            categoria_id = request.POST.get('categoria_id')
            try:
                categoria = Categoria.objects.get(id=categoria_id)
                categoria_nombre = categoria.nombre
                
                # Verificar si la categoría está siendo usada por algún torneo
                torneos_usando_categoria = Torneo.objects.filter(categoria=categoria).count()
                
                if torneos_usando_categoria > 0:
                    messages.warning(request, f"⚠️ No se puede eliminar la categoría '{categoria_nombre}' porque está siendo usada en {torneos_usando_categoria} torneo(s).")
                else:
                    categoria.delete()
                    messages.success(request, f"✅ Categoría '{categoria_nombre}' eliminada correctamente.")
                    
            except Categoria.DoesNotExist:
                messages.error(request, "❌ La categoría seleccionada no existe.")
            except Exception as e:
                messages.error(request, f"❌ Error al eliminar la categoría: {str(e)}")
            
            return redirect('lista_categorias')
    else:
        form = CategoriaForm()
    
    context = {
        'categorias': categorias, 
        'form': form,
        'total_categorias': categorias.count()
    }
    
    return render(request, 'lista_categorias.html', context)

@require_organizador
def lista_jugadores(request):
    query = request.GET.get('q', '').strip()
    if query:
        rut_normalizado = normalizar_rut(query)
        jugadores = Jugador.objects.filter(rut__icontains=rut_normalizado)
    else:
        jugadores = Jugador.objects.all()
    if request.method == 'POST':
        if 'agregar' in request.POST:
            form = JugadorForm(request.POST)
            if form.is_valid():
                jugador = form.save()
                messages.success(request, f"Jugador {jugador.nombre} ingresado exitosamente.")
                return redirect('lista_jugadores')
    else:
        form = JugadorForm()
    return render(request, 'lista_jugadores.html', {'jugadores': jugadores, 'form': form, 'query': query})

@require_organizador
def importar_jugadores(request):
    if request.method == "POST" and request.FILES.get("archivo"):
        archivo = request.FILES["archivo"]
        df = pd.read_excel(archivo)
        df.columns = [col.strip().lower() for col in df.columns]
        errores = []
        emails_en_archivo = set()
        ruts_en_archivo = set()
        
        for i, row in df.iterrows():
            rut = normalizar_rut(row.get('rut', ''))
            nombre = limpiar_texto_estricto(row.get('nombre', ''))
            apellido = limpiar_texto_estricto(row.get('apellido', ''))
            fecha_nacimiento = row.get('fecha de nacimiento', '')
            genero = limpiar_texto_estricto(row.get('genero', '')).upper()
            club_nombre = limpiar_texto_estricto(row.get('club', ''))
            
            correo_raw = row.get('correo', '')
            if pd.isna(correo_raw) or correo_raw is None or str(correo_raw).strip().lower() in ('', 'nan'):
                correo = ''
            else:
                correo = limpiar_email_estricto(correo_raw)

            if not club_nombre or club_nombre.lower() in ('', 'nan'):
                club = None
            else:
                club, _ = Club.objects.get_or_create(nombre=club_nombre)

            if not nombre:
                errores.append(f"Fila {i+2}: Nombre vacío o inválido")
                continue
            if not apellido:
                errores.append(f"Fila {i+2}: Apellido vacío o inválido")
                continue

            if not rut_valido(rut):
                errores.append(f"Fila {i+2}: RUT inválido ({rut})")
                continue
            if rut in ruts_en_archivo:
                errores.append(f"Fila {i+2}: RUT duplicado en el archivo ({rut})")
                continue
            if Jugador.objects.filter(rut=rut).exists():
                errores.append(f"Fila {i+2}: RUT ya existe en la base de datos ({rut})")
                continue
            ruts_en_archivo.add(rut)

            if isinstance(fecha_nacimiento, datetime):
                fecha_nac = fecha_nacimiento.date()
            else:
                fecha_nac = None
                for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"]:
                    try:
                        fecha_nac = datetime.strptime(str(fecha_nacimiento), fmt).date()
                        break
                    except ValueError:
                        continue
                if not fecha_nac:
                    errores.append(f"Fila {i+2}: Fecha de nacimiento inválida ({fecha_nacimiento})")
                    continue

            if genero not in ("M", "F"):
                errores.append(f"Fila {i+2}: Género inválido ({genero}). Debe ser 'M' o 'F'.")
                continue

            if correo:
                if not correo_valido(correo):
                    errores.append(f"Fila {i+2}: Correo inválido ({correo})")
                    continue
                if correo in emails_en_archivo:
                    errores.append(f"Fila {i+2}: Correo duplicado en el archivo ({correo})")
                    continue
                if Jugador.objects.filter(email=correo).exists():
                    errores.append(f"Fila {i+2}: Correo ya existe in la base de datos ({correo})")
                    continue
                emails_en_archivo.add(correo)
            else:
                correo = None

            club, _ = Club.objects.get_or_create(nombre=club_nombre) if club_nombre else (None, None)

            Jugador.objects.create(
                rut=rut,
                nombre=nombre,
                apellido=apellido,
                fecha_nacimiento=fecha_nac,
                genero=genero,
                club=club,
                email=correo
            )

        if errores:
            for error in errores:
                messages.error(request, error)
        else:
            messages.success(request, "Jugadores importados exitosamente.")
        return redirect('lista_jugadores')
    return render(request, 'importar_jugadores.html', {'form': ImportarJugadoresForm()})

@require_organizador
def anadir_correo_jugador(request, jugador_id):
    jugador = get_object_or_404(Jugador, id=jugador_id)
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        if not email:
            messages.error(request, "Debes ingresar un correo.")
        elif Jugador.objects.filter(email=email).exclude(id=jugador.id).exists():
            messages.error(request, "Ya existe un jugador con ese correo.")
        else:
            jugador.email = email
            jugador.save()
            messages.success(request, "Correo añadido correctamente.")
            return redirect(f"{reverse('lista_jugadores')}?q={jugador.rut}")
    return render(request, "anadir_correo.html", {"jugador": jugador})

@require_organizador
def gestionar_torneo(request, torneo_id):
    torneo = Torneo.objects.get(id=torneo_id, organizador=request.user)
    return render(request, 'gestionar_torneo.html', {'torneo': torneo})

@require_organizador
def gestionar_torneo_federado(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id, organizador=request.user)
    return render(request, 'gestionar_torneo_federado.html', {'torneo': torneo})

@require_organizador
def ingresar_participantes(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id, organizador=request.user)
    
    # Verificar si las inscripciones están cerradas
    if torneo.inscripciones_cerradas:
        messages.error(request, "Las inscripciones están cerradas. No se pueden agregar más participantes.")
        return redirect('listado_participantes', torneo_id=torneo.id)
    
    query_raw = request.GET.get('q', '').strip()
    query = limpiar_texto_estricto(query_raw).lower()

    participantes_confirmados_ruts = set(
        Jugador.objects.filter(
            id__in=torneo.participaciones.values_list('jugador_id', flat=True)
        ).values_list('rut', flat=True)
    )

    session_key = f'participantes_temp_{torneo_id}'
    participantes_temp = set(request.session.get(session_key, []))
    
    seleccionados_visuales = participantes_temp.copy()
    
    if request.method == "GET" and 'selected' in request.GET:
        seleccionados_visuales = set(request.GET.getlist('selected'))

    if torneo.todo_competidor:
        jugadores = Jugador.objects.exclude(rut__in=participantes_confirmados_ruts | participantes_temp)
    elif torneo.categoria:
        jugadores = [
            j for j in Jugador.objects.exclude(rut__in=participantes_confirmados_ruts | participantes_temp)
            if j.calcular_categoria() == torneo.categoria.nombre
        ]
    else:
        jugadores = []

    if query:
        if query in ['m', 'f']:
            jugadores = [j for j in jugadores if j.genero.lower() == query]
        else:
            jugadores = [
                j for j in jugadores if
                query in j.rut.lower() or
                query in limpiar_texto_estricto(j.nombre).lower() or
                query in limpiar_texto_estricto(j.apellido).lower() or
                query in str(j.fecha_nacimiento) or
                query in j.calcular_categoria().lower() or
                (j.club and query in limpiar_texto_estricto(j.club.nombre).lower()) or (j.email and query in limpiar_email_estricto(j.email).lower())
            ]

    if request.method == "POST" and "agregar" in request.POST:
        seleccionados_ruts = request.POST.getlist("jugadores")
        participantes_temp.update(seleccionados_ruts)
        request.session[session_key] = list(participantes_temp)
        request.session.modified = True
        return HttpResponseRedirect(request.path_info)
    
    if request.method == "POST" and request.FILES.get("archivo_participantes"):
        archivo = request.FILES["archivo_participantes"]
        try:
            df = pd.read_excel(archivo)
            df.columns = [col.strip().lower() for col in df.columns]
            errores = []
            ruts_en_archivo = set()
            jugadores_agregados = 0
            
            participantes_confirmados_ruts = set(
                Jugador.objects.filter(
                    id__in=torneo.participaciones.values_list('jugador_id', flat=True)
                ).values_list('rut', flat=True)
            )
            participantes_temp_ruts = participantes_temp.copy()
            
            for i, row in df.iterrows():
                rut = normalizar_rut(row.get('rut', ''))
                
                if not rut:
                    errores.append(f"Fila {i+2}: RUT vacío")
                    continue
                    
                if not rut_valido(rut):
                    errores.append(f"Fila {i+2:}: RUT inválido ({rut})")
                    continue
                    
                if rut in ruts_en_archivo:
                    errores.append(f"Fila {i+2}: RUT duplicado en el archivo ({rut})")
                    continue

                try:
                    jugador = Jugador.objects.get(rut=rut)
                except Jugador.DoesNotExist:
                    errores.append(f"Fila {i+2}: Jugador con RUT {rut} no existe en la base de datos")
                    continue
                
                if rut in participantes_confirmados_ruts:
                    errores.append(f"Fila {i+2}: Jugador con RUT {rut} ya está confirmado en el torneo")
                    continue
                
                if rut in participantes_temp_ruts:
                    errores.append(f"Fila {i+2}: Jugador con RUT {rut} ya está seleccionado para agregar")
                    continue
                
                if not torneo.todo_competidor and torneo.categoria:
                    if jugador.calcular_categoria() != torneo.categoria.nombre:
                        errores.append(f"Fila {i+2}: Jugador {jugador.nombre} {jugador.apellido} (RUT: {rut}) no pertenece a la categoría {torneo.categoria.nombre}")
                        continue
                
                participantes_temp.add(rut)
                participantes_temp_ruts.add(rut)
                ruts_en_archivo.add(rut)
                jugadores_agregados += 1
            
            request.session[session_key] = list(participantes_temp)
            request.session.modified = True            
            if errores:
                for error in errores:
                    messages.error(request, error)
            
            if jugadores_agregados > 0:
                messages.success(request, f"Se agregaron {jugadores_agregados} jugador(es) a la lista de participantes.")
            
            return HttpResponseRedirect(request.path_info)
            
        except Exception as e:
            messages.error(request, f"Error al procesar el archivo: {str(e)}")
            return HttpResponseRedirect(request.path_info)
    
    if request.method == "POST" and "quitar" in request.POST:
        quitar_rut = request.POST.get("quitar")
        participantes_temp.discard(quitar_rut)
        seleccionados_visuales.discard(quitar_rut)
        request.session[session_key] = list(participantes_temp)
        request.session.modified = True
        return HttpResponseRedirect(request.path_info)

    if request.method == "POST" and "confirmar" in request.POST:
        for rut in participantes_temp:
            try:
                jugador = Jugador.objects.get(rut=rut)
                Participacion.objects.get_or_create(torneo=torneo, jugador=jugador)
            except Jugador.DoesNotExist:
                messages.error(request, f"Jugador con RUT {rut} no encontrado. Se ha omitido.")
        request.session[session_key] = []
        request.session.modified = True
        messages.success(request, "Participantes confirmados correctamente.")
        return redirect('listado_participantes', torneo_id=torneo.id)

    jugadores_seleccionados = Jugador.objects.filter(rut__in=participantes_temp)

    return render(request, "ingresar_participantes.html", {
        "torneo": torneo,
        "jugadores": jugadores,
        "jugadores_seleccionados": jugadores_seleccionados,
        "seleccionados_ids": seleccionados_visuales, 
        "query": query_raw,
        "form_importar": ImportarParticipantesForm(),
    })

@require_organizador
def listado_participantes(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id, organizador=request.user)
    participantes = [p.jugador for p in torneo.participaciones.select_related('jugador')]

    # Manejar el cerrar inscripciones
    if request.method == "POST" and "cerrar_inscripciones" in request.POST and not torneo.inscripciones_cerradas:
        if len(participantes) < 3:
            messages.error(request, "No puedes cerrar las inscripciones. Debe haber al menos 3 jugadores inscritos.")
            return redirect('listado_participantes', torneo_id=torneo.id)
        
        torneo.inscripciones_cerradas = True
        torneo.save()
        messages.success(request, "Las inscripciones han sido cerradas. Ya no se pueden agregar o eliminar participantes.")
        return redirect('listado_participantes', torneo_id=torneo.id)

    return render(request, "listado_participantes.html", {"torneo": torneo, "participantes": participantes})

@require_organizador
def eliminar_participante(request, torneo_id, participante_rut):
    torneo = get_object_or_404(Torneo, id=torneo_id, organizador=request.user)
    
    # Verificar si las inscripciones están cerradas
    if torneo.inscripciones_cerradas:
        messages.error(request, "Las inscripciones están cerradas. No se pueden eliminar participantes.")
        return redirect('listado_participantes', torneo_id=torneo.id)
    
    try:
        jugador = get_object_or_404(Jugador, rut=participante_rut)
        participacion = get_object_or_404(Participacion, torneo=torneo, jugador=jugador)
        
        participacion.delete()
        messages.success(request, f"Participante {jugador.nombre} {jugador.apellido} (RUT: {jugador.rut}) eliminado del torneo correctamente.")
        
    except Jugador.DoesNotExist:
        messages.error(request, f"Jugador con RUT {participante_rut} no encontrado.")
    except Participacion.DoesNotExist:
        messages.error(request, "El jugador no está registrado en este torneo.")
    
    return redirect('listado_participantes', torneo_id=torneo.id)

@require_organizador
def configurar_sets_llaves(request, torneo_id):
    """Vista para configurar la cantidad de sets antes de iniciar el torneo con llaves"""
    torneo = get_object_or_404(Torneo, id=torneo_id, organizador=request.user)
    
    if not torneo.inscripciones_cerradas:
        messages.error(request, "Debes cerrar las inscripciones antes de configurar el torneo.")
        return redirect('gestionar_torneo', torneo_id=torneo.id)
    
    if torneo.torneo_iniciado:
        messages.warning(request, "El torneo ya ha sido iniciado.")
        return redirect('gestionar_torneo', torneo_id=torneo.id)
    
    if request.method == 'POST':
        form = ConfigurarSetsForm(request.POST)
        if form.is_valid():
            # Guardar la configuración de sets
            torneo.mejor_de_sets = int(form.cleaned_data['mejor_de_sets'])
            torneo.mejor_de_sets_final = int(form.cleaned_data['mejor_de_sets_final'])
            torneo.modalidad = 'llaves'
            torneo.torneo_iniciado = True
            torneo.save()
            
            messages.success(request, f"¡Torneo configurado! Mejor de {torneo.mejor_de_sets} sets (normal) y {torneo.mejor_de_sets_final} sets (final).")
            return redirect('organizar_llaves', torneo_id=torneo.id)
    else:
        # Inicializar el formulario con los valores actuales del torneo
        form = ConfigurarSetsForm(initial={
            'mejor_de_sets': torneo.mejor_de_sets,
            'mejor_de_sets_final': torneo.mejor_de_sets_final,
        })
    
    # Calcular datos del bracket para mostrar información
    num_participantes = torneo.participaciones.count()
    potencia_2_siguiente = 2 ** math.ceil(math.log2(max(num_participantes, 2)))
    byes_necesarias = potencia_2_siguiente - num_participantes if num_participantes > 0 else 0
    rondas_necesarias = math.ceil(math.log2(potencia_2_siguiente)) if num_participantes > 1 else 1
    
    context = {
        'torneo': torneo,
        'form': form,
        'num_participantes': num_participantes,
        'potencia_2_siguiente': potencia_2_siguiente,
        'byes_necesarias': byes_necesarias,
        'rondas_necesarias': rondas_necesarias,
    }
    
    return render(request, 'configurar_sets_llaves.html', context)

@require_organizador
def modalidad_llaves(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id, organizador=request.user)
    
    if not torneo.inscripciones_cerradas:
        messages.error(request, "Debes cerrar las inscripciones antes de seleccionar una modalidad.")
        return redirect('gestionar_torneo', torneo_id=torneo.id)
    
    # Si el torneo ya ha iniciado, redirigir a la gestión de llaves
    if torneo.torneo_iniciado and torneo.modalidad == 'llaves':
        return redirect('organizar_llaves', torneo_id=torneo.id)
        
    # Manejar el inicio del torneo por llaves
    if request.method == 'POST' and 'iniciar_llaves' in request.POST:
        torneo.modalidad = 'llaves'
        torneo.torneo_iniciado = True
        torneo.save()
        messages.success(request, "¡Torneo iniciado en modalidad de llaves! Ahora puedes organizar las llaves.")
        return redirect('organizar_llaves', torneo_id=torneo.id)
    
    # Calcular datos del bracket dinámicamente
    num_participantes = torneo.participaciones.count()
    
    # Calcular la potencia de 2 más cercana (hacia arriba)
    potencia_2_siguiente = 2 ** math.ceil(math.log2(max(num_participantes, 2)))
    
    # Calcular BYE necesarias
    byes_necesarias = potencia_2_siguiente - num_participantes if num_participantes > 0 else 0
    
    # Calcular número de rondas
    rondas_necesarias = math.ceil(math.log2(potencia_2_siguiente)) if num_participantes > 1 else 1
    
    # Determinar si es un bracket perfecto (potencia de 2)
    es_bracket_perfecto = num_participantes > 0 and (num_participantes & (num_participantes - 1)) == 0
    
    context = {
        'torneo': torneo,
        'num_participantes': num_participantes,
        'potencia_2_siguiente': potencia_2_siguiente,
        'byes_necesarias': byes_necesarias,
        'rondas_necesarias': rondas_necesarias,
        'es_bracket_perfecto': es_bracket_perfecto,
    }
    
    return render(request, 'modalidad_llaves.html', context)

@require_organizador
def modalidad_grupos(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id, organizador=request.user)
    
    if not torneo.inscripciones_cerradas:
        messages.error(request, "Debes cerrar las inscripciones antes de seleccionar una modalidad.")
        return redirect('gestionar_torneo', torneo_id=torneo.id)
    
    # Si el torneo ya ha iniciado, redirigir a la gestión de grupos
    if torneo.torneo_iniciado and torneo.modalidad == 'grupos':
        return redirect('organizar_grupos', torneo_id=torneo.id)
    
    # Manejar el inicio del torneo por grupos
    if request.method == 'POST' and 'iniciar_grupos' in request.POST:
        torneo.modalidad = 'grupos'
        torneo.torneo_iniciado = True
        torneo.save()
        messages.success(request, "¡Torneo iniciado en modalidad de grupos! Ahora puedes organizar los grupos.")
        return redirect('organizar_grupos', torneo_id=torneo.id)
    
    # Calcular distribución de grupos según reglas de tenis de mesa
    num_participantes = torneo.participaciones.count()
    
    def calcular_grupos_tenis_mesa(participantes):
        """
        Calcula la distribución óptima de grupos para tenis de mesa.
        Reglas: Máximo 2 grupos de 4, el resto de 3. Clasifican 2 por grupo.
        """
        if participantes < 3:
            return {'error': 'Se necesitan mínimo 3 participantes para fases de grupos'}
        
        # Calcular distribución óptima
        grupos_de_4 = 0
        grupos_de_3 = 0
        
        # Intentar primero solo grupos de 3
        if participantes % 3 == 0:
            grupos_de_3 = participantes // 3
        elif participantes % 3 == 1:
            # Si sobra 1, necesitamos convertir un grupo de 3 en uno de 4
            if participantes >= 4:
                grupos_de_4 = 1
                grupos_de_3 = (participantes - 4) // 3
        elif participantes % 3 == 2:
            # Si sobran 2, necesitamos 2 grupos de 4
            if participantes >= 8:
                grupos_de_4 = 2
                grupos_de_3 = (participantes - 8) // 3
            else:
                # Caso especial para números pequeños
                grupos_de_4 = 0
                grupos_de_3 = participantes // 3
        
        total_grupos = grupos_de_3 + grupos_de_4
        clasificados = total_grupos * 2  # 2 clasificados por grupo
        
        # Calcular bracket para fase eliminatoria
        potencia_2_siguiente = 2 ** math.ceil(math.log2(max(clasificados, 2)))
        byes_eliminatoria = potencia_2_siguiente - clasificados if clasificados > 0 else 0
        rondas_eliminatoria = math.ceil(math.log2(potencia_2_siguiente)) if clasificados > 1 else 1
        
        return {
            'grupos_de_3': grupos_de_3,
            'grupos_de_4': grupos_de_4,
            'total_grupos': total_grupos,
            'clasificados': clasificados,
            'potencia_2_siguiente': potencia_2_siguiente,
            'byes_eliminatoria': byes_eliminatoria,
            'rondas_eliminatoria': rondas_eliminatoria,
            'es_bracket_perfecto': clasificados > 0 and (clasificados & (clasificados - 1)) == 0
        }
    
    grupos_info = calcular_grupos_tenis_mesa(num_participantes)
    
    context = {
        'torneo': torneo,
        'num_participantes': num_participantes,
        'grupos_info': grupos_info,
    }
    
    return render(request, 'modalidad_grupos.html', context)

@require_organizador
def organizar_grupos(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id, organizador=request.user)
      # Verificar que el torneo esté en modalidad grupos
    if torneo.modalidad != 'grupos' or not torneo.torneo_iniciado:
        messages.error(request, "El torneo no está en modalidad de grupos o no ha sido iniciado.")
        return redirect('gestionar_torneo', torneo_id=torneo.id)
    

    
    participantes = list(torneo.participaciones.select_related('jugador').all())
    num_participantes = len(participantes)
      # Calcular distribución de grupos
    def calcular_distribucion_grupos(participantes_count):
        grupos_de_4 = 0
        grupos_de_3 = 0
        
        if participantes_count % 3 == 0:
            grupos_de_3 = participantes_count // 3
        elif participantes_count % 3 == 1:
            if participantes_count >= 4:
                grupos_de_4 = 1
                grupos_de_3 = (participantes_count - 4) // 3
        elif participantes_count % 3 == 2:
            if participantes_count >= 8:
                grupos_de_4 = 2
                grupos_de_3 = (participantes_count - 8) // 3
            else:
                grupos_de_4 = 0
                grupos_de_3 = participantes_count // 3
        
        return grupos_de_3, grupos_de_4
    
    grupos_de_3, grupos_de_4 = calcular_distribucion_grupos(num_participantes)
    total_grupos = grupos_de_3 + grupos_de_4
    clasificados_total = total_grupos * 2
    
    # Manejar asignación de grupos
    if request.method == 'POST':
        if 'asignar_automatico' in request.POST:
            # Limpiar grupos existentes
            GrupoTorneo.objects.filter(torneo=torneo).delete()
            
            # Mezclar participantes aleatoriamente
            participantes_mezclados = participantes.copy()
            random.shuffle(participantes_mezclados)
            
            # Crear grupos y asignar participantes usando serpenteo
            grupos_creados = []
            for i in range(total_grupos):
                grupo = GrupoTorneo.objects.create(
                    torneo=torneo,
                    nombre=str(i + 1),  # Grupo 1, 2, 3, etc.
                    numero=i + 1
                )
                grupos_creados.append(grupo)
            
            # Distribución serpenteo secuencial
            participante_idx = 0
            
            # Crear una lista de todas las posiciones disponibles en orden serpenteo
            posiciones_serpenteo = []
            max_participantes = 4  # Máximo posible
            
            for posicion in range(1, max_participantes + 1):  # Posiciones 1, 2, 3, 4
                # TODOS los grupos pueden tener hasta 4 participantes durante el serpenteo
                # La regla del torneo (máximo 2 grupos de 4) se aplica naturalmente
                grupos_disponibles = list(range(total_grupos))  # Todos los grupos están disponibles
                
                # Aplicar patrón serpenteo según la posición
                if (posicion - 1) % 2 == 1:  # Posiciones 2, 4, 6... (reverso)
                    orden_grupos = list(reversed(grupos_disponibles))
                else:  # Posiciones 1, 3, 5... (normal)
                    orden_grupos = grupos_disponibles
                
                # Agregar todas las asignaciones de esta posición a la lista
                for grupo_idx in orden_grupos:
                    posiciones_serpenteo.append((grupo_idx, posicion))
            
            # Asignar participantes siguiendo el orden serpenteo secuencial
            for i, (grupo_idx, posicion) in enumerate(posiciones_serpenteo):
                if participante_idx < len(participantes_mezclados):
                    ParticipanteGrupo.objects.create(
                        grupo=grupos_creados[grupo_idx],
                        jugador=participantes_mezclados[participante_idx].jugador,
                        posicion_grupo=posicion,
                        es_cabeza_serie=False
                    )
                    participante_idx += 1
            
            messages.success(request, "¡Grupos asignados automáticamente!")
            return redirect('organizar_grupos', torneo_id=torneo.id)
        
        elif 'reorganizar_grupos' in request.POST:
            # Verificar si hay grupos existentes y cabezas de serie
            grupos_existentes = GrupoTorneo.objects.filter(torneo=torneo).prefetch_related('participantes')
            
            if grupos_existentes.exists():
                # Obtener cabezas de serie existentes por posición (mantener orden por grupo)
                cabezas_serie_primera_linea = []  # Posición 1
                cabezas_serie_segunda_linea = []  # Posición 2
                
                for grupo in grupos_existentes.order_by('numero'):
                    # Cabezas de serie de primera línea (posición 1)
                    cabeza_primera = grupo.participantes.filter(es_cabeza_serie=True, posicion_grupo=1).first()
                    if cabeza_primera:
                        cabezas_serie_primera_linea.append((grupo.numero - 1, cabeza_primera))  # (índice_grupo, participante)
                    
                    # Cabezas de serie de segunda línea (posición 2)
                    cabeza_segunda = grupo.participantes.filter(es_cabeza_serie=True, posicion_grupo=2).first()
                    if cabeza_segunda:
                        cabezas_serie_segunda_linea.append((grupo.numero - 1, cabeza_segunda))  # (índice_grupo, participante)
                
                # Obtener cabezas de serie de primera línea en el orden correcto
                cabezas_serie_primera_linea = sorted(cabezas_serie_primera_linea, key=lambda x: x[0])
                # Obtener cabezas de serie de segunda línea en el orden correcto
                cabezas_serie_segunda_linea = sorted(cabezas_serie_segunda_linea, key=lambda x: x[0])
                
                # Obtener IDs de jugadores que son cabezas de serie (ambas líneas)
                ids_cabezas_serie = set()
                for _, cabeza in cabezas_serie_primera_linea:
                    ids_cabezas_serie.add(cabeza.jugador.id)
                for _, cabeza in cabezas_serie_segunda_linea:
                    ids_cabezas_serie.add(cabeza.jugador.id)
                
                # Obtener participantes que NO son cabezas de serie
                participantes_sin_cabezas = []
                for participacion in participantes:
                    if participacion.jugador.id not in ids_cabezas_serie:
                        participantes_sin_cabezas.append(participacion)
                
                # Limpiar grupos existentes
                GrupoTorneo.objects.filter(torneo=torneo).delete()
                
                # Mezclar solo los participantes que NO son cabezas de serie
                random.shuffle(participantes_sin_cabezas)
                
                # Crear grupos
                grupos_creados = []
                for i in range(total_grupos):
                    grupo = GrupoTorneo.objects.create(
                        torneo=torneo,
                        nombre=str(i + 1),  # 1, 2, 3, etc.
                        numero=i + 1
                    )
                    grupos_creados.append(grupo)
                
                # Re-asignar cabezas de serie de primera línea EN EL MISMO ORDEN Y GRUPO
                for grupo_idx, cabeza_serie in cabezas_serie_primera_linea:
                    if grupo_idx < len(grupos_creados):
                        ParticipanteGrupo.objects.create(
                            grupo=grupos_creados[grupo_idx],
                            jugador=cabeza_serie.jugador,
                            posicion_grupo=1,
                            es_cabeza_serie=True
                        )
                
                # Re-asignar cabezas de serie de segunda línea EN EL MISMO ORDEN Y GRUPO
                for grupo_idx, cabeza_serie in cabezas_serie_segunda_linea:
                    if grupo_idx < len(grupos_creados):
                        ParticipanteGrupo.objects.create(
                            grupo=grupos_creados[grupo_idx],
                            jugador=cabeza_serie.jugador,
                            posicion_grupo=2,
                            es_cabeza_serie=True
                        )
                
                # Distribuir el resto de participantes usando serpenteo corregido
                participante_idx = 0
                num_cabezas_primera = len(cabezas_serie_primera_linea)
                num_cabezas_segunda = len(cabezas_serie_segunda_linea)
                
                # Crear lista de posiciones disponibles para serpenteo
                posiciones_serpenteo = []
                max_participantes = 4
                
                # Crear un mapa de posiciones ocupadas por cabezas de serie
                posiciones_ocupadas = set()
                for grupo_idx, _ in cabezas_serie_primera_linea:
                    posiciones_ocupadas.add((grupo_idx, 1))
                for grupo_idx, _ in cabezas_serie_segunda_linea:
                    posiciones_ocupadas.add((grupo_idx, 2))
                
                # Llenar posiciones disponibles considerando cabezas de serie ya asignadas
                for posicion in range(1, max_participantes + 1):
                    grupos_disponibles = list(range(total_grupos))
                    
                    # Aplicar patrón serpenteo según la posición
                    if (posicion - 1) % 2 == 1:  # Posiciones 2, 4, 6... (reverso)
                        orden_grupos = list(reversed(grupos_disponibles))
                    else:  # Posiciones 1, 3, 5... (normal)
                        orden_grupos = grupos_disponibles
                    
                    # Agregar todas las asignaciones de esta posición a la lista
                    for grupo_idx in orden_grupos:
                        if (grupo_idx, posicion) not in posiciones_ocupadas:
                            posiciones_serpenteo.append((grupo_idx, posicion))
                
                # Asignar participantes siguiendo el orden serpenteo secuencial
                for i, (grupo_idx, posicion) in enumerate(posiciones_serpenteo):
                    if participante_idx < len(participantes_sin_cabezas):
                        ParticipanteGrupo.objects.create(
                            grupo=grupos_creados[grupo_idx],
                            jugador=participantes_sin_cabezas[participante_idx].jugador,
                            posicion_grupo=posicion,
                            es_cabeza_serie=False
                        )
                        participante_idx += 1
                
                mensaje = "¡Grupos reorganizados manteniendo las cabezas de serie!"
                if num_cabezas_segunda > 0:
                    mensaje = f"¡Grupos reorganizados manteniendo {num_cabezas_primera} cabezas de serie y {num_cabezas_segunda} de segunda línea!"
                messages.success(request, mensaje)
            else:
                # Si no hay grupos existentes, hacer reorganización completa normal
                # Mezclar participantes aleatoriamente
                participantes_mezclados = participantes.copy()
                random.shuffle(participantes_mezclados)
                
                # Crear grupos y asignar participantes usando serpenteo
                grupos_creados = []
                for i in range(total_grupos):
                    grupo = GrupoTorneo.objects.create(
                        torneo=torneo,
                        nombre=str(i + 1),  # 1, 2, 3, etc.
                        numero=i + 1
                    )
                    grupos_creados.append(grupo)
                
                # Distribución serpenteo secuencial
                participante_idx = 0
                
                # Crear una lista de todas las posiciones disponibles en orden serpenteo
                posiciones_serpenteo = []
                max_participantes = 4  # Máximo posible
                
                for posicion in range(1, max_participantes + 1):  # Posiciones 1, 2, 3, 4
                    grupos_disponibles = list(range(total_grupos))
                    
                    # Aplicar patrón serpenteo según la posición
                    if (posicion - 1) % 2 == 1:  # Posiciones 2, 4, 6... (reverso)
                        orden_grupos = list(reversed(grupos_disponibles))
                    else:  # Posiciones 1, 3, 5... (normal)
                        orden_grupos = grupos_disponibles
                    
                    # Agregar todas las asignaciones de esta posición a la lista
                    for grupo_idx in orden_grupos:
                        posiciones_serpenteo.append((grupo_idx, posicion))
                
                # Asignar participantes siguiendo el orden serpenteo secuencial
                for i, (grupo_idx, posicion) in enumerate(posiciones_serpenteo):
                    if participante_idx < len(participantes_mezclados):
                        ParticipanteGrupo.objects.create(
                            grupo=grupos_creados[grupo_idx],
                            jugador=participantes_mezclados[participante_idx].jugador,
                            posicion_grupo=posicion,
                            es_cabeza_serie=False
                        )
                        participante_idx += 1
                
                messages.success(request, "¡Grupos reorganizados exitosamente!")
            
            return redirect('organizar_grupos', torneo_id=torneo.id)
        
        elif 'resetear_grupos' in request.POST:
            # Limpiar grupos existentes
            GrupoTorneo.objects.filter(torneo=torneo).delete()
            
            messages.success(request, "¡Grupos reseteados! Ahora puedes reorganizar los participantes.")
            return redirect('organizar_grupos', torneo_id=torneo.id)
        
        elif 'definir_cabezas' in request.POST:
            return redirect('definir_cabezas_serie', torneo_id=torneo.id)
      # Obtener grupos existentes
    grupos_existentes = GrupoTorneo.objects.filter(torneo=torneo).prefetch_related('participantes__jugador')
    
    context = {
        'torneo': torneo,
        'participantes': participantes,
        'num_participantes': num_participantes,
        'grupos_de_3': grupos_de_3,
        'grupos_de_4': grupos_de_4,
        'total_grupos': total_grupos,
        'clasificados_total': clasificados_total,
        'grupos_existentes': grupos_existentes,
    }
    
    return render(request, 'organizar_grupos.html', context)

@require_organizador
def definir_cabezas_serie(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id, organizador=request.user)
    
    # Verificar que el torneo esté en modalidad grupos
    if torneo.modalidad != 'grupos' or not torneo.torneo_iniciado:
        messages.error(request, "El torneo no está en modalidad de grupos o no ha sido iniciado.")
        return redirect('gestionar_torneo', torneo_id=torneo.id)
    
    participantes = list(torneo.participaciones.select_related('jugador').all())
    num_participantes = len(participantes)
    
    # Calcular número de cabezas de serie (igual al número de grupos)
    def calcular_distribucion_grupos(participantes_count):
        grupos_de_4 = 0
        grupos_de_3 = 0
        
        if participantes_count % 3 == 0:
            grupos_de_3 = participantes_count // 3
        elif participantes_count % 3 == 1:
            if participantes_count >= 4:
                grupos_de_4 = 1
                grupos_de_3 = (participantes_count - 4) // 3
        elif participantes_count % 3 == 2:
            if participantes_count >= 8:
                grupos_de_4 = 2
                grupos_de_3 = (participantes_count - 8) // 3
            else:
                grupos_de_4 = 0
                grupos_de_3 = participantes_count // 3
        
        return grupos_de_3, grupos_de_4
    
    grupos_de_3, grupos_de_4 = calcular_distribucion_grupos(num_participantes)
    total_grupos = grupos_de_3 + grupos_de_4
    
    # Calcular el total de clasificados (típicamente 2 por grupo para fase de llaves)
    clasificados_total = total_grupos * 2
    
    if request.method == 'POST':
        if 'asignar_con_cabezas' in request.POST:
            # Obtener las cabezas de serie de primera línea seleccionadas EN ORDEN
            cabezas_serie_ids = []
            cabezas_serie_continuas = True
            
            for i in range(total_grupos):
                cabeza_id = request.POST.get(f'cabeza_{i}')
                if cabeza_id:
                    if not cabezas_serie_continuas:
                        messages.error(request, f"Error: No puedes saltar grupos. Si seleccionas un grupo debes llenar todos los anteriores en orden secuencial (A, B, C, etc.).")
                        return redirect('definir_cabezas_serie', torneo_id=torneo.id)
                    cabezas_serie_ids.append(int(cabeza_id))
                else:
                    # Una vez que encontramos un vacío, todos los siguientes deben estar vacíos
                    cabezas_serie_continuas = False
            
            # Obtener las cabezas de serie de segunda línea
            segunda_linea_ids = []
            segunda_linea_continuas = True
            
            for i in range(total_grupos):
                segunda_id = request.POST.get(f'segunda_{i}')
                if segunda_id:
                    if not segunda_linea_continuas:
                        messages.error(request, f"Error en segunda línea: No puedes saltar posiciones. Debes llenar en orden secuencial.")
                        return redirect('definir_cabezas_serie', torneo_id=torneo.id)
                    segunda_linea_ids.append(int(segunda_id))
                else:
                    segunda_linea_continuas = False
            
            # Verificar que haya al menos una cabeza de serie
            if len(cabezas_serie_ids) == 0:
                messages.error(request, "Debes seleccionar al menos una cabeza de serie.")
                return redirect('definir_cabezas_serie', torneo_id=torneo.id)
            
            # Verificar que no se repitan jugadores entre primera y segunda línea
            all_selected_ids = cabezas_serie_ids + segunda_linea_ids
            if len(set(all_selected_ids)) != len(all_selected_ids):
                messages.error(request, "No puedes seleccionar el mismo jugador más de una vez.")
                return redirect('definir_cabezas_serie', torneo_id=torneo.id)
            
            # Limpiar grupos existentes
            GrupoTorneo.objects.filter(torneo=torneo).delete()
            
            # Separar participantes
            cabezas_serie_ordenadas = []
            segunda_linea_ordenadas = []
            resto_participantes = []
            
            # Crear un diccionario para mapear id de jugador a participación
            participaciones_map = {p.jugador.id: p for p in participantes}
            
            # Ordenar cabezas de serie según el orden de selección
            for cabeza_id in cabezas_serie_ids:
                if cabeza_id in participaciones_map:
                    cabezas_serie_ordenadas.append(participaciones_map[cabeza_id])
            
            # Ordenar segunda línea según el orden de selección (pero serán asignadas en serpenteo)
            for segunda_id in segunda_linea_ids:
                if segunda_id in participaciones_map:
                    segunda_linea_ordenadas.append(participaciones_map[segunda_id])
            
            # Agregar resto de participantes (excluyendo las seleccionadas)
            for participacion in participantes:
                if participacion.jugador.id not in all_selected_ids:
                    resto_participantes.append(participacion)
            
            # Mezclar el resto de participantes
            random.shuffle(resto_participantes)
            
            # Crear grupos
            grupos_creados = []
            for i in range(total_grupos):
                grupo = GrupoTorneo.objects.create(
                    torneo=torneo,
                    nombre=str(i + 1),  # 1, 2, 3, etc.
                    numero=i + 1
                )
                grupos_creados.append(grupo)
            
            # Asignar cabezas de serie de primera línea EN EL ORDEN CORRECTO
            for i, cabeza_serie in enumerate(cabezas_serie_ordenadas):
                ParticipanteGrupo.objects.create(
                    grupo=grupos_creados[i],
                    jugador=cabeza_serie.jugador,
                    posicion_grupo=1,
                    es_cabeza_serie=True
                )
            
            # Asignar cabezas de serie de segunda línea en orden serpenteo (reverso)
            if segunda_linea_ordenadas:
                # Segunda línea va en posición 2, comenzando desde el último grupo hacia atrás
                for i, segunda in enumerate(segunda_linea_ordenadas):
                    grupo_idx = total_grupos - 1 - i  # Último grupo hacia atrás
                    if grupo_idx >= 0:  # Asegurar que no salga del rango
                        ParticipanteGrupo.objects.create(
                            grupo=grupos_creados[grupo_idx],
                            jugador=segunda.jugador,
                            posicion_grupo=2,
                            es_cabeza_serie=True
                        )
            
            # Ahora distribuir el resto de participantes usando serpenteo
            participante_idx = 0
            
            # Crear lista de posiciones disponibles para serpenteo
            posiciones_serpenteo = []
            max_participantes = 4
            
            # Crear información de cabezas de serie para cálculos
            cabezas_serie_primera_linea = [(i, cabeza) for i, cabeza in enumerate(cabezas_serie_ordenadas)]
            cabezas_serie_segunda_linea = [(total_grupos - 1 - i, segunda) for i, segunda in enumerate(segunda_linea_ordenadas)]
            
            num_cabezas_primera = len(cabezas_serie_primera_linea)
            num_cabezas_segunda = len(cabezas_serie_segunda_linea)
            
            # Crear un mapa de posiciones ocupadas por cabezas de serie
            posiciones_ocupadas = set()
            for grupo_idx, _ in cabezas_serie_primera_linea:
                posiciones_ocupadas.add((grupo_idx, 1))
            for grupo_idx, _ in cabezas_serie_segunda_linea:
                posiciones_ocupadas.add((grupo_idx, 2))
            
            # Llenar posiciones disponibles considerando cabezas de serie ya asignadas
            for posicion in range(1, max_participantes + 1):
                grupos_disponibles = list(range(total_grupos))
                
                # Aplicar patrón serpenteo según la posición
                if (posicion - 1) % 2 == 1:  # Posiciones 2, 4, 6... (reverso)
                    orden_grupos = list(reversed(grupos_disponibles))
                else:  # Posiciones 1, 3, 5... (normal)
                    orden_grupos = grupos_disponibles
                
                # Agregar todas las asignaciones de esta posición a la lista
                for grupo_idx in orden_grupos:
                    if (grupo_idx, posicion) not in posiciones_ocupadas:
                        posiciones_serpenteo.append((grupo_idx, posicion))
            
            # Asignar participantes siguiendo el orden serpenteo secuencial
            for i, (grupo_idx, posicion) in enumerate(posiciones_serpenteo):
                if participante_idx < len(resto_participantes):
                    ParticipanteGrupo.objects.create(
                        grupo=grupos_creados[grupo_idx],
                        jugador=resto_participantes[participante_idx].jugador,
                        posicion_grupo=posicion,
                        es_cabeza_serie=False
                    )
                    participante_idx += 1
            
            messages.success(request, "Grupos organizados correctamente con cabezas de serie asignadas.")
            return redirect('organizar_grupos', torneo_id=torneo.id)
    
    context = {
        'torneo': torneo,
        'participantes': participantes,
        'num_participantes': num_participantes,
        'total_grupos': total_grupos,
        'grupos_de_3': grupos_de_3,
        'grupos_de_4': grupos_de_4,
        'clasificados_total': clasificados_total,
    }
    
    return render(request, 'definir_cabezas_serie.html', context)

@login_required
def organizar_llaves(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id, organizador=request.user)
    
    # Verificar que el torneo esté en modalidad llaves
    if torneo.modalidad != 'llaves' or not torneo.torneo_iniciado:
        messages.error(request, "El torneo no está en modalidad de llaves o no ha sido iniciado.")
        return redirect('gestionar_torneo', torneo_id=torneo.id)
    
    participantes = list(torneo.participaciones.select_related('jugador').all())
    num_participantes = len(participantes)
    
    # Calcular la potencia de 2 más cercana (hacia arriba)
    potencia_2_siguiente = 2 ** math.ceil(math.log2(max(num_participantes, 2)))
    
    # Calcular BYE necesarias
    byes_necesarias = potencia_2_siguiente - num_participantes if num_participantes > 0 else 0
    
    # Calcular número de rondas
    rondas_necesarias = math.ceil(math.log2(potencia_2_siguiente)) if num_participantes > 1 else 1
    
    # Determinar si es un bracket perfecto (potencia de 2)
    es_bracket_perfecto = num_participantes > 0 and (num_participantes & (num_participantes - 1)) == 0
    
    # Verificar si ya existen llaves asignadas
    llaves_asignadas = torneo.llaves.filter(ronda=1).exists()
    llaves_primera_ronda = torneo.llaves.filter(ronda=1).select_related('jugador1', 'jugador2', 'bye1', 'bye2') if llaves_asignadas else []
    
    # Obtener árbitros del torneo
    arbitros_torneo = UsuarioPersonalizado.objects.filter(
        torneos_asignados__torneo=torneo,
        torneos_asignados__activo=True
    ).distinct()
    
    # CORREGIDO: Mostrar árbitros disponibles por defecto
    # Solo excluir árbitros que están ACTIVOS en el torneo
    arbitros_activos_en_torneo = ArbitroTorneo.objects.filter(
        torneo=torneo,
        activo=True
    ).values_list('arbitro_id', flat=True)
    
    arbitros_disponibles = UsuarioPersonalizado.objects.filter(
        tipo_usuario='arbitro',
        activo=True
    ).exclude(
        id__in=arbitros_activos_en_torneo
    ).distinct()
    
    # Manejar solicitudes POST
    if request.method == 'POST':
        # Gestión de llaves
        if 'definir_llaves_manual' in request.POST:
            return redirect('definir_llaves', torneo_id=torneo.id)
        elif 'asignar_automatico' in request.POST:
            return asignar_llaves_automatico(request, torneo, participantes, potencia_2_siguiente, byes_necesarias)
        elif 'reconfigurar_llaves' in request.POST:
            # Limpiar todas las llaves existentes
            torneo.llaves.all().delete()
            torneo.byes.all().delete()
            messages.info(request, "Las llaves han sido eliminadas. Puedes asignar nuevamente.")
            return redirect('organizar_llaves', torneo_id=torneo.id)
        
        # Gestión de árbitros
        elif 'buscar_arbitros' in request.POST:
            buscar_termino = request.POST.get('buscar_arbitro', '').strip()
            if buscar_termino:
                # CORREGIDO: Solo excluir árbitros ACTIVOS en el torneo
                arbitros_activos_en_torneo = ArbitroTorneo.objects.filter(
                    torneo=torneo,
                    activo=True
                ).values_list('arbitro_id', flat=True)
                
                # Buscar árbitros por email, nombre o apellido
                arbitros_disponibles = UsuarioPersonalizado.objects.filter(
                    tipo_usuario='arbitro',
                    activo=True
                ).filter(
                    Q(email__icontains=buscar_termino) |
                    Q(first_name__icontains=buscar_termino) |
                    Q(last_name__icontains=buscar_termino)
                ).exclude(
                    id__in=arbitros_activos_en_torneo
                ).distinct()
                
                if not arbitros_disponibles:
                    messages.info(request, f"No se encontraron árbitros disponibles con '{buscar_termino}'.")
            else:
                messages.warning(request, "Por favor, ingresa un término de búsqueda.")
        
        elif 'mostrar_todos_arbitros' in request.POST:
            # CORREGIDO: Solo excluir árbitros ACTIVOS en el torneo
            arbitros_activos_en_torneo = ArbitroTorneo.objects.filter(
                torneo=torneo,
                activo=True
            ).values_list('arbitro_id', flat=True)
            
            # Mostrar todos los árbitros disponibles (no asignados activamente al torneo)
            arbitros_disponibles = UsuarioPersonalizado.objects.filter(
                tipo_usuario='arbitro',
                activo=True
            ).exclude(
                id__in=arbitros_activos_en_torneo
            ).distinct()
            
            if not arbitros_disponibles:
                messages.info(request, "No hay árbitros disponibles para asignar.")
        
        elif 'agregar_arbitro' in request.POST:
            arbitro_id = request.POST.get('arbitro_id')
            if arbitro_id:
                try:
                    arbitro = UsuarioPersonalizado.objects.get(
                        id=arbitro_id,
                        tipo_usuario='arbitro',
                        activo=True
                    )
                    
                    # CORREGIDO: Verificar si ya existe una relación (activa o inactiva)
                    try:
                        arbitro_torneo = ArbitroTorneo.objects.get(torneo=torneo, arbitro=arbitro)
                        
                        if arbitro_torneo.activo:
                            # Ya está activo
                            messages.warning(request, f"El árbitro {arbitro.first_name} {arbitro.last_name} ya está asignado a este torneo.")
                        else:
                            # Está inactivo, reactivarlo
                            arbitro_torneo.activo = True
                            arbitro_torneo.save()
                            messages.success(request, f"Árbitro {arbitro.first_name} {arbitro.last_name} reasignado al torneo exitosamente.")
                            
                    except ArbitroTorneo.DoesNotExist:
                        # No existe, crear nuevo
                        ArbitroTorneo.objects.create(torneo=torneo, arbitro=arbitro)
                        messages.success(request, f"Árbitro {arbitro.first_name} {arbitro.last_name} agregado al torneo exitosamente.")
                        
                except UsuarioPersonalizado.DoesNotExist:
                    messages.error(request, "Árbitro no encontrado.")
            
            return redirect('organizar_llaves', torneo_id=torneo.id)
        
        elif 'remover_arbitro' in request.POST:
            arbitro_id = request.POST.get('arbitro_id')
            if arbitro_id:
                try:
                    arbitro_torneo = ArbitroTorneo.objects.get(
                        torneo=torneo,
                        arbitro_id=arbitro_id,
                        activo=True
                    )
                    arbitro_torneo.activo = False
                    arbitro_torneo.save()
                    messages.success(request, f"Árbitro {arbitro_torneo.arbitro.first_name} {arbitro_torneo.arbitro.last_name} removido del torneo.")
                    
                except ArbitroTorneo.DoesNotExist:
                    messages.error(request, "Asignación de árbitro no encontrada.")
            
            return redirect('organizar_llaves', torneo_id=torneo.id)
    
    context = {
        'torneo': torneo,
        'participantes': participantes,
        'num_participantes': num_participantes,
        'potencia_2_siguiente': potencia_2_siguiente,
        'byes_necesarias': byes_necesarias,
        'rondas_necesarias': rondas_necesarias,
        'es_bracket_perfecto': es_bracket_perfecto,
        'llaves_asignadas': llaves_asignadas,
        'llaves_primera_ronda': llaves_primera_ronda,
        'arbitros_torneo': arbitros_torneo,
        'arbitros_disponibles': arbitros_disponibles,
    }
    
    return render(request, 'organizar_llaves.html', context)

@require_organizador
def definir_llaves(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id, organizador=request.user)
    
    # Verificar que el torneo esté en modalidad llaves
    if torneo.modalidad != 'llaves' or not torneo.torneo_iniciado:
        messages.error(request, "El torneo no está en modalidad llaves o no ha sido iniciado.")
        return redirect('gestionar_torneo', torneo_id=torneo.id)
    
    # Obtener participantes
    participantes = list(torneo.participaciones.select_related('jugador').all())
    num_participantes = len(participantes)
    
    # Calcular la potencia de 2 más cercana (hacia arriba)
    potencia_2_siguiente = 2 ** math.ceil(math.log2(max(num_participantes, 2)))
    
    # Calcular BYE necesarias
    byes_necesarias = potencia_2_siguiente - num_participantes if num_participantes > 0 else 0
    
    # Calcular número de rondas
    rondas_necesarias = math.ceil(math.log2(potencia_2_siguiente)) if num_participantes > 1 else 1
    
    # Determinar si es un bracket perfecto (potencia de 2)
    es_bracket_perfecto = num_participantes > 0 and (num_participantes & (num_participantes - 1)) == 0
    
    # Calcular número de enfrentamientos en la primera ronda
    num_enfrentamientos = potencia_2_siguiente // 2
    
    # Crear estructura de enfrentamientos para el formulario
    enfrentamientos = []
    for i in range(num_enfrentamientos):
        enfrentamientos.append({
            'numero': i + 1,  # Cambio: usar 'numero' en lugar de 'posicion'
            'jugador1': None,
            'jugador2': None,
            'es_bye1': False,  # Cambio: usar 'es_bye1' en lugar de 'bye1'
            'es_bye2': False   # Cambio: usar 'es_bye2' en lugar de 'bye2'
        })
    
    try:
        # Lógica para cargar llaves existentes si las hay
        llaves_existentes = torneo.llaves.filter(ronda=1).order_by('posicion')
        if llaves_existentes.exists():
            for llave in llaves_existentes:
                if llave.posicion <= len(enfrentamientos):
                    enfrentamientos[llave.posicion - 1] = {
                        'numero': llave.posicion,  # Cambio: usar 'numero'
                        'jugador1': llave.jugador1,
                        'jugador2': llave.jugador2,
                        'es_bye1': bool(llave.bye1),  # Cambio: usar 'es_bye1' y convertir a bool
                        'es_bye2': bool(llave.bye2)   # Cambio: usar 'es_bye2' y convertir a bool
                    }
    except Exception as e:
        # Si hay un problema con la tabla, simplemente continuar sin cargar llaves existentes
        print(f"Error al cargar llaves existentes: {e}")
        pass
    
    if request.method == 'POST':
        if 'guardar_asignacion' in request.POST:
            import random  # Import aquí para uso en esta función
            try:
                # Limpiar asignaciones previas de la primera ronda
                torneo.llaves.filter(ronda=1).delete()
                torneo.byes.all().delete()
                
                # Recopilar jugadores ya asignados
                jugadores_asignados = set()
                asignaciones_manuales = {}
                
                # Primero, procesar las asignaciones manuales del formulario
                for i in range(num_enfrentamientos):
                    posicion = i + 1
                    jugador1_id = request.POST.get(f'jugador1_posicion_{posicion}')
                    jugador2_id = request.POST.get(f'jugador2_posicion_{posicion}')
                    es_bye1 = request.POST.get(f'bye1_posicion_{posicion}')
                    es_bye2 = request.POST.get(f'bye2_posicion_{posicion}')
                    
                    # Debug: imprimir qué datos estamos recibiendo
                    print(f"🔍 Enfrentamiento {posicion}:")
                    print(f"   - jugador1_id: {jugador1_id}")
                    print(f"   - jugador2_id: {jugador2_id}")
                    print(f"   - es_bye1: {es_bye1}")
                    print(f"   - es_bye2: {es_bye2}")
                    
                    asignaciones_manuales[posicion] = {
                        'jugador1_id': jugador1_id,
                        'jugador2_id': jugador2_id,
                        'es_bye1': es_bye1,
                        'es_bye2': es_bye2
                    }
                    
                    # Agregar jugadores asignados al set
                    if jugador1_id:
                        jugadores_asignados.add(int(jugador1_id))
                        print(f"   ✅ Jugador 1 asignado manualmente")
                    if jugador2_id:
                        jugadores_asignados.add(int(jugador2_id))
                        print(f"   ✅ Jugador 2 asignado manualmente")
                
                # Obtener jugadores disponibles para asignación automática
                todas_participaciones = list(torneo.participaciones.all())
                participaciones_disponibles = [p for p in todas_participaciones if p.id not in jugadores_asignados]
                
                # Mezclar para asignación aleatoria
                import random
                random.shuffle(participaciones_disponibles)
                
                # Contar BYEs ya asignados manualmente
                byes_asignados_manualmente = 0
                for pos_data in asignaciones_manuales.values():
                    if pos_data['es_bye1']:
                        byes_asignados_manualmente += 1
                    if pos_data['es_bye2']:
                        byes_asignados_manualmente += 1
                
                # Calcular BYEs restantes necesarios
                byes_restantes = max(0, byes_necesarias - byes_asignados_manualmente)
                
                # Crear una estrategia de distribución inteligente para BYEs
                # 1. Primero identificar todas las posiciones vacías
                posiciones_vacias = []
                for i in range(num_enfrentamientos):
                    posicion = i + 1
                    asignacion = asignaciones_manuales[posicion]
                    
                    # Verificar qué posiciones están vacías en cada enfrentamiento
                    if not asignacion['jugador1_id'] and not asignacion['es_bye1']:
                        posiciones_vacias.append((posicion, 1))  # (enfrentamiento, posición_en_enfrentamiento)
                    if not asignacion['jugador2_id'] and not asignacion['es_bye2']:
                        posiciones_vacias.append((posicion, 2))
                
                # 2. Mezclar posiciones vacías para distribución aleatoria
                random.shuffle(posiciones_vacias)
                
                # 3. Crear lista de asignaciones automáticas
                elementos_automaticos = {}
                
                # Agregar jugadores disponibles
                for participacion in participaciones_disponibles:
                    elementos_automaticos[participacion.id] = ('jugador', participacion)
                
                # Agregar BYEs necesarios
                for i in range(1, byes_restantes + 1):
                    elementos_automaticos[f'bye_{i}'] = ('bye', None)
                
                # 4. Mezclar elementos
                keys_mezcladas = list(elementos_automaticos.keys())
                random.shuffle(keys_mezcladas)
                
                # 5. Distribuir elementos de forma inteligente evitando BYE vs BYE
                asignaciones_automaticas = {}
                elementos_index = 0
                
                # Primero, asignar jugadores y BYEs de forma que se evite BYE vs BYE
                for posicion_info in posiciones_vacias:
                    enfrentamiento, pos_en_enfrentamiento = posicion_info;
                    
                    if elementos_index >= len(keys_mezcladas):
                        break;
                    
                    clave_elemento = keys_mezcladas[elementos_index]
                    tipo, elemento = elementos_automaticos[clave_elemento]
                    
                    # Verificar si crear BYE vs BYE
                    if tipo == 'bye':
                        # Buscar si ya hay un BYE asignado en este enfrentamiento
                        asignacion_actual = asignaciones_manuales[enfrentamiento]
                        otra_posicion = 1 if pos_en_enfrentamiento == 2 else 2;
                        
                        # Verificar asignaciones manuales
                        hay_bye_manual = (asignacion_actual['es_bye1'] if otra_posicion == 1 else asignacion_actual['es_bye2'])
                        
                        # Verificar asignaciones automáticas previas
                        hay_bye_automatico = False
                        if enfrentamiento in asignaciones_automaticas:
                            hay_bye_automatico = asignaciones_automaticas[enfrentamiento].get(otra_posicion, {}).get('tipo') == 'bye'
                        
                        if hay_bye_manual or hay_bye_automatico:
                            # Ya hay un BYE, buscar un jugador en su lugar
                            jugador_encontrado = False
                            for j in range(elementos_index + 1, len(keys_mezcladas)):
                                clave_busqueda = keys_mezcladas[j]
                                if elementos_automaticos[clave_busqueda][0] == 'jugador':
                                    # Intercambiar posiciones
                                    keys_mezcladas[elementos_index], keys_mezcladas[j] = keys_mezcladas[j], keys_mezcladas[elementos_index]
                                    clave_elemento = keys_mezcladas[elementos_index]
                                    tipo, elemento = elementos_automaticos[clave_elemento]
                                    jugador_encontrado = True
                                    break
                            
                            # Si no se encontró jugador, mantener el BYE pero marcarlo para revisión posterior
                            if not jugador_encontrado:
                                pass  # Mantener el BYE, se manejará después
                    
                    # Guardar asignación automática
                    if enfrentamiento not in asignaciones_automaticas:
                        asignaciones_automaticas[enfrentamiento] = {}
                    
                    asignaciones_automaticas[enfrentamiento][pos_en_enfrentamiento] = {
                        'tipo': tipo,
                        'elemento': elemento
                    }
                    
                    elementos_index += 1
                
                # Guardar nuevas asignaciones con la nueva estrategia
                byes_creados = 0
                
                for i in range(num_enfrentamientos):
                    posicion = i + 1
                    asignacion = asignaciones_manuales[posicion]
                    
                    # Preparar objetos para la llave
                    jugador1_obj = None
                    jugador2_obj = None
                    bye1_obj = None
                    bye2_obj = None
                    
                    # Procesar jugador 1 (manual o automático)
                    if asignacion['jugador1_id']:
                        # Asignación manual
                        try:
                            participacion = torneo.participaciones.get(id=asignacion['jugador1_id'])
                            jugador1_obj = participacion.jugador
                        except:
                            pass
                    elif asignacion['es_bye1']:
                        # BYE manual
                        byes_creados += 1
                        bye1_obj = JugadorBye.objects.create(
                            nombre="BYE",
                            posicion_bye=byes_creados,
                            torneo=torneo
                        )
                    else:
                        # Asignación automática para posición vacía
                        if posicion in asignaciones_automaticas and 1 in asignaciones_automaticas[posicion]:
                            auto_data = asignaciones_automaticas[posicion][1]
                            
                            if auto_data['tipo'] == 'jugador':
                                jugador1_obj = auto_data['elemento'].jugador
                            elif auto_data['tipo'] == 'bye':
                                byes_creados += 1
                                bye1_obj = JugadorBye.objects.create(
                                    nombre="BYE",
                                    posicion_bye=byes_creados,
                                    torneo=torneo
                                )
                    
                    # Procesar jugador 2 (manual o automático)
                    if asignacion['jugador2_id']:
                        # Asignación manual
                        try:
                            participacion = torneo.participaciones.get(id=asignacion['jugador2_id'])
                            jugador2_obj = participacion.jugador
                        except:
                            pass
                    elif asignacion['es_bye2']:
                        # BYE manual
                        byes_creados += 1
                        bye2_obj = JugadorBye.objects.create(
                            nombre="BYE",
                            posicion_bye=byes_creados,
                            torneo=torneo
                        )
                    else:
                        # Asignación automática para posición vacía
                        if posicion in asignaciones_automaticas and 2 in asignaciones_automaticas[posicion]:
                            auto_data = asignaciones_automaticas[posicion][2]
                            
                            if auto_data['tipo'] == 'jugador':
                                jugador2_obj = auto_data['elemento'].jugador
                            elif auto_data['tipo'] == 'bye':
                                byes_creados += 1
                                bye2_obj = JugadorBye.objects.create(
                                    nombre="BYE",
                                    posicion_bye=byes_creados,
                                    torneo=torneo
                                )
                    
                    # Crear la llave (siempre crear, aunque esté vacía)
                    llave = LlaveTorneo.objects.create(
                        torneo=torneo,
                        ronda=1,
                        posicion=posicion,
                        jugador1=jugador1_obj,
                        jugador2=jugador2_obj,
                        bye1=bye1_obj,
                        bye2=bye2_obj
                    )
                    
                    print(f"✅ Llave {posicion} creada: {llave.jugador1_nombre} vs {llave.jugador2_nombre}")
            
                # Crear todas las rondas siguientes (vacías) para completar el bracket
                total_rondas = crear_bracket_completo(torneo, len(participantes))
                
                messages.success(request, f"Las llaves han sido definidas correctamente. Se crearon {total_rondas} rondas en total. Los espacios vacíos fueron completados automáticamente.")
                return redirect('organizar_llaves', torneo_id=torneo.id)
            except Exception as e:
                messages.error(request, f"Error al guardar las llaves: {str(e)}")
                print(f"Error al guardar llaves: {e}")
    
    context = {
        'torneo': torneo,
        'participantes': participantes,
        'num_participantes': num_participantes,
        'potencia_2_siguiente': potencia_2_siguiente,
        'byes_necesarias': byes_necesarias,
        'rondas_necesarias': rondas_necesarias,
        'es_bracket_perfecto': es_bracket_perfecto,
        'enfrentamientos': enfrentamientos,
        'num_enfrentamientos': num_enfrentamientos,
    }
    
    return render(request, 'definir_llaves.html', context)

@login_required
def vista_previa_asignacion(request, torneo_id):
    """
    Vista que devuelve el proceso paso a paso de cómo se asignaron los grupos REALMENTE
    """
    torneo = get_object_or_404(Torneo, id=torneo_id, organizador=request.user)
    
    # Obtener grupos existentes ordenados correctamente
    grupos_existentes = GrupoTorneo.objects.filter(torneo=torneo).prefetch_related('participantes__jugador').order_by('numero')
    
    if not grupos_existentes.exists():
        # Si es una petición AJAX, devolver JSON con error
        if (request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 
            'application/json' in request.headers.get('Accept', '') or
            request.GET.get('format') == 'json' or
            'json' in request.path.lower()):
            return JsonResponse({'error': 'No hay grupos asignados para mostrar la vista previa.'}, status=404)
        messages.error(request, "No hay grupos asignados para mostrar la vista previa.")
        return redirect('organizar_grupos', torneo_id=torneo.id)
    
    # Obtener participantes originales en orden de inscripción
    participantes_originales = list(torneo.participaciones.select_related('jugador').order_by('id'))
    
    # Verificar si hay cabezas de serie
    tiene_cabezas_serie = grupos_existentes.filter(participantes__es_cabeza_serie=True).exists()
    
    # Si es una petición AJAX/JSON, devolver los datos en formato JSON
    if (request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 
        'application/json' in request.headers.get('Accept', '') or
        request.GET.get('format') == 'json' or
        'json' in request.path.lower()):
        
        # Función para convertir participante a dict
        def participante_to_dict(p):
            return {
                'id': p.jugador.id,
                'nombre': f"{p.jugador.nombre} {p.jugador.apellido}",
                'categoria': p.jugador.calcular_categoria()
            }
        
        pasos = []
        
        # Paso 1: Lista original de participantes
        pasos.append({
            'titulo': 'Lista Original de Participantes',
            'descripcion': 'Participantes registrados en el torneo en orden de inscripción',
            'tipo': 'lista_original',
            'participantes': [participante_to_dict(p) for p in participantes_originales]
        })
        
        if tiene_cabezas_serie:
            # PROCESO CON CABEZAS DE SERIE - RECONSTRUIR EL PROCESO REAL
            
            # Obtener las cabezas de serie de primera línea (posición 1) en el orden correcto de los grupos
            cabezas_serie_primera_linea = []
            for grupo in grupos_existentes.order_by('numero'):
                cabeza_primera = grupo.participantes.filter(es_cabeza_serie=True, posicion_grupo=1).first()
                if cabeza_primera:
                    cabezas_serie_primera_linea.append({
                        'id': cabeza_primera.jugador.id,
                        'nombre': f"{cabeza_primera.jugador.nombre} {cabeza_primera.jugador.apellido}",
                        'categoria': cabeza_primera.jugador.calcular_categoria(),
                        'grupo': str(grupo.numero),  # 1, 2, 3, etc.
                        'numero_grupo': grupo.numero - 1,
                        'posicion': 1
                    })
            
            # Obtener las cabezas de serie de segunda línea (posición 2) en el orden correcto de los grupos
            cabezas_serie_segunda_linea = []
            for grupo in grupos_existentes.order_by('numero'):
                cabeza_segunda = grupo.participantes.filter(es_cabeza_serie=True, posicion_grupo=2).first()
                if cabeza_segunda:
                    cabezas_serie_segunda_linea.append({
                        'id': cabeza_segunda.jugador.id,
                        'nombre': f"{cabeza_segunda.jugador.nombre} {cabeza_segunda.jugador.apellido}",
                        'categoria': cabeza_segunda.jugador.calcular_categoria(),
                        'grupo': str(grupo.numero),  # 1, 2, 3, etc.
                        'numero_grupo': grupo.numero - 1,
                        'posicion': 2           
                    })
            
            # Combinar todas las cabezas de serie para mostrar en el paso
            todas_cabezas_serie = cabezas_serie_primera_linea + cabezas_serie_segunda_linea
            
            # Paso 2: Mostrar cabezas de serie seleccionadas
            descripcion_cabezas = 'Jugadores seleccionados como cabezas de serie'
            if cabezas_serie_primera_linea and cabezas_serie_segunda_linea:
                descripcion_cabezas += f': {len(cabezas_serie_primera_linea)} de primera línea (posición 1) y {len(cabezas_serie_segunda_linea)} de segunda línea (posición 2)'
            elif cabezas_serie_primera_linea:
                descripcion_cabezas += f': {len(cabezas_serie_primera_linea)} de primera línea (posición 1)'
            
            pasos.append({
                'titulo': 'Cabezas de Serie Seleccionadas',
                'descripcion': descripcion_cabezas,
                'tipo': 'cabezas_serie',
                'cabezas': todas_cabezas_serie,
                'primera_linea': cabezas_serie_primera_linea,
                'segunda_linea': cabezas_serie_segunda_linea
            })
            
            # Obtener todos los participantes que NO son cabezas de serie
            cabezas_ids = [c['id'] for c in todas_cabezas_serie]
            resto_participantes = [p for p in participantes_originales if p.jugador.id not in cabezas_ids]
            
            # RECONSTRUIR la lista shuffle que se usó realmente
            # Necesitamos obtener el orden exacto en que fueron asignados
            resto_orden_real = []
            num_grupos = len(grupos_existentes)
            
            # Crear un conjunto de posiciones ocupadas por cabezas de serie
            posiciones_ocupadas = set()
            for cabeza in cabezas_serie_primera_linea:
                posiciones_ocupadas.add((cabeza['numero_grupo'], 1))
            for cabeza in cabezas_serie_segunda_linea:
                posiciones_ocupadas.add((cabeza['numero_grupo'], 2))
            
            # Reconstruir el orden siguiendo el patrón de serpenteo pero excluyendo posiciones ocupadas
            for posicion in range(1, 5):  # Posiciones 1, 2, 3, 4
                grupos_disponibles = list(range(num_grupos))
                
                # Aplicar patrón serpenteo según la posición
                if (posicion - 1) % 2 == 1:  # Posiciones 2, 4, 6... (reverso)
                    orden_grupos = list(reversed(grupos_disponibles))
                else:  # Posiciones 1, 3, 5... (normal)
                    orden_grupos = grupos_disponibles
                
                # Obtener participantes en esta posición siguiendo el orden serpenteo
                for grupo_idx in orden_grupos:
                    # Skip si esta posición está ocupada por cabezas de serie
                    if (grupo_idx, posicion) not in posiciones_ocupadas:
                        grupo = grupos_existentes[grupo_idx]
                        participante_en_posicion = grupo.participantes.filter(posicion_grupo=posicion, es_cabeza_serie=False).first()
                        if participante_en_posicion:
                            resto_orden_real.append(participante_en_posicion.jugador)
            
            # Paso 3: Lista randomizada (el orden real que se usó)
            pasos.append({
                'titulo': 'Participantes Restantes Aleatorizados',
                'descripcion': 'Los participantes restantes (sin cabezas de serie) fueron mezclados aleatoriamente antes de la asignación',
                'tipo': 'lista_randomizada',
                'participantes': [
                    {
                        'id': jugador.id,
                        'nombre': f"{jugador.nombre} {jugador.apellido}",
                        'categoria': jugador.calcular_categoria()
                    }
                    for jugador in resto_orden_real
                ]
            })
            
            # Paso 4: Asignación de cabezas de serie a sus grupos
            grupos_simulados = [[] for _ in range(num_grupos)]
            
            # Primero asignar las cabezas de serie de primera línea a sus grupos correspondientes
            for cabeza_info in cabezas_serie_primera_linea:
                grupo_idx = cabeza_info['numero_grupo']
                grupos_simulados[grupo_idx].append({
                    'id': cabeza_info['id'],
                    'nombre': cabeza_info['nombre'],
                    'categoria': cabeza_info['categoria'],
                    'es_cabeza_serie': True,
                    'posicion': 1
                })
            
            # Luego asignar las cabezas de serie de segunda línea a sus grupos correspondientes
            for cabeza_info in cabezas_serie_segunda_linea:
                grupo_idx = cabeza_info['numero_grupo']
                # Insertar en la segunda posición del grupo
                grupos_simulados[grupo_idx].insert(1, {
                    'id': cabeza_info['id'],
                    'nombre': cabeza_info['nombre'],
                    'categoria': cabeza_info['categoria'],
                    'es_cabeza_serie': True,
                    'posicion': 2
                })
            
            pasos.append({
                'titulo': 'Asignación de Cabezas de Serie',
                'descripcion': 'Las cabezas de serie fueron asignadas a sus grupos correspondientes (1→A, 2→B, 3→C, etc.)',
                'tipo': 'asignacion_serpenteo',
                'grupos': [grupo.copy() for grupo in grupos_simulados],
                'jugador_actual': None,
                'grupo_actual': None
            })
            
            # Paso 5: Asignación serpenteo del resto usando la nueva lógica
            if resto_orden_real:
                lote_size = min(5, max(3, len(resto_orden_real) // 3))
                
                # Crear la secuencia de asignaciones que se usó realmente
                asignaciones_reales = []
                
                # Usar el mismo método de posiciones ocupadas que arriba
                posiciones_ocupadas_sim = set()
                for cabeza in cabezas_serie_primera_linea:
                    posiciones_ocupadas_sim.add((cabeza['numero_grupo'], 1))
                for cabeza in cabezas_serie_segunda_linea:
                    posiciones_ocupadas_sim.add((cabeza['numero_grupo'], 2))
                
                # Crear lista de asignaciones disponibles siguiendo serpenteo
                for posicion in range(1, 5):  # Posiciones 1, 2, 3, 4
                    grupos_disponibles = list(range(num_grupos))
                    
                    # Aplicar patrón serpenteo según la posición
                    if (posicion - 1) % 2 == 1:  # Posiciones 2, 4, 6... (reverso)
                        orden_grupos = list(reversed(grupos_disponibles))
                    else:  # Posiciones 1, 3, 5... (normal)
                        orden_grupos = grupos_disponibles
                    
                    # Agregar asignaciones disponibles
                    for grupo_idx in orden_grupos:
                        if (grupo_idx, posicion) not in posiciones_ocupadas_sim:
                            asignaciones_reales.append((grupo_idx, posicion))
                
                # Simular la asignación usando el patrón secuencial correcto
                participante_idx = 0
                
                for lote_inicio in range(0, len(resto_orden_real), lote_size):
                    lote_fin = min(lote_inicio + lote_size, len(resto_orden_real))
                    
                    for i in range(lote_inicio, lote_fin):
                        if i < len(asignaciones_reales) and participante_idx < len(resto_orden_real):
                            jugador = resto_orden_real[participante_idx]
                            grupo_destino, posicion = asignaciones_reales[i]
                            
                            jugador_data = {
                                'id': jugador.id,
                                'nombre': f"{jugador.nombre} {jugador.apellido}",
                                'categoria': jugador.calcular_categoria(),
                                'es_cabeza_serie': False
                            }
                            grupos_simulados[grupo_destino].append(jugador_data)
                            participante_idx += 1
                    
                    # Agregar paso de asignación agrupada
                    if lote_fin > 0 and (lote_fin - 1) < len(resto_orden_real):
                        ultimo_jugador = resto_orden_real[lote_fin - 1]
                        ultimo_i = lote_fin - 1
                        if ultimo_i < len(asignaciones_reales):
                            ultimo_grupo, ultimo_posicion = asignaciones_reales[ultimo_i]
                        else:
                            ultimo_grupo = 0
                            ultimo_posicion = 2
                        
                        pasos.append({
                            'titulo': f'Asignación Serpenteo - Jugadores {lote_inicio + 1}-{lote_fin}',
                            'descripcion': f'Asignando jugadores {lote_inicio + 1} al {lote_fin} de {len(resto_orden_real)} usando el patrón serpenteo corregido',
                            'tipo': 'asignacion_serpenteo',
                            'grupos': [grupo.copy() for grupo in grupos_simulados],
                            'jugador_actual': {
                                'id': ultimo_jugador.id,
                                'nombre': f"{ultimo_jugador.nombre} {ultimo_jugador.apellido}",
                                'categoria': ultimo_jugador.calcular_categoria(),
                                'es_cabeza_serie': False
                            },
                            'grupo_actual': ultimo_grupo
                        })
        
        else:
            # PROCESO AUTOMÁTICO SIN CABEZAS DE SERIE
            # Reconstruir el orden real de los participantes basado en sus posiciones actuales
            participantes_orden_real = []
            num_grupos = len(grupos_existentes)
            
            # Crear la misma lista de posiciones serpenteo que se usó en la asignación real
            posiciones_serpenteo = []
            
            for posicion in range(1, 5):  # Posiciones 1, 2, 3, 4
                # TODOS los grupos pueden tener hasta 4 participantes durante el serpenteo
                # La regla del torneo (máximo 2 grupos de 4) se aplica naturalmente
                grupos_disponibles = list(range(num_grupos))  # Todos los grupos están disponibles
                
                if grupos_disponibles:  # Solo si hay grupos con esta posición
                    # Aplicar patrón serpenteo según la posición
                    if (posicion - 1) % 2 == 1:  # Posiciones 2, 4, 6... (reverso)
                        orden_grupos = list(reversed(grupos_disponibles))
                    else:  # Posiciones 1, 3, 5... (normal)
                        orden_grupos = grupos_disponibles
                    
                    # Agregar todas las asignaciones de esta posición a la lista
                    for grupo_idx in orden_grupos:
                        posiciones_serpenteo.append((grupo_idx, posicion))
            
            # Reconstruir el orden de los participantes siguiendo las posiciones serpenteo
            for grupo_idx, posicion in posiciones_serpenteo:
                grupo = grupos_existentes[grupo_idx]
                participante_en_posicion = grupo.participantes.filter(posicion_grupo=posicion).first()
                if participante_en_posicion:
                    participantes_orden_real.append(participante_en_posicion.jugador)
            
            pasos.append({
                'titulo': 'Lista Aleatorizada (Shuffle)',
                'descripcion': 'Todos los participantes fueron mezclados aleatoriamente para la asignación',
                'tipo': 'lista_randomizada',
                'participantes': [
                    {
                        'id': jugador.id,
                        'nombre': f"{jugador.nombre} {jugador.apellido}",
                        'categoria': jugador.calcular_categoria()
                    }
                    for jugador in participantes_orden_real
                ]
            })
            
            # Simular asignación serpenteo para proceso automático
            grupos_simulados = [[] for _ in range(num_grupos)]
            
            # Agregar pasos de asignación agrupada
            if participantes_orden_real:
                lote_size = min(5, max(3, len(participantes_orden_real) // 3))
                
                participante_idx = 0
                for lote_inicio in range(0, len(participantes_orden_real), lote_size):
                    lote_fin = min(lote_inicio + lote_size, len(participantes_orden_real))
                    
                    for i in range(lote_inicio, lote_fin):
                        if i < len(posiciones_serpenteo) and participante_idx < len(participantes_orden_real):
                            jugador = participantes_orden_real[participante_idx]
                            grupo_destino, posicion = posiciones_serpenteo[i]
                            
                            jugador_data = {
                                'id': jugador.id,
                                'nombre': f"{jugador.nombre} {jugador.apellido}",
                                'categoria': jugador.calcular_categoria(),
                                'es_cabeza_serie': False
                            }
                            grupos_simulados[grupo_destino].append(jugador_data)
                            participante_idx += 1
                    
                    # Agregar paso de asignación agrupada
                    if lote_fin > 0 and (lote_fin - 1) < len(participantes_orden_real):
                        ultimo_jugador = participantes_orden_real[lote_fin - 1]
                        ultimo_i = lote_fin - 1
                        if ultimo_i < len(posiciones_serpenteo):
                            ultimo_grupo, ultimo_posicion = posiciones_serpenteo[ultimo_i]
                        else:
                            ultimo_grupo = 0
                            ultimo_posicion = 1
                        
                        pasos.append({
                            'titulo': f'Asignación Serpenteo - Jugadores {lote_inicio + 1}-{lote_fin}',
                            'descripcion': f'Asignando jugadores {lote_inicio + 1} al {lote_fin} de {len(participantes_orden_real)} usando el patrón serpenteo secuencial',
                            'tipo': 'asignacion_serpenteo',
                            'grupos': [grupo.copy() for grupo in grupos_simulados],
                            'jugador_actual': {
                                'id': ultimo_jugador.id,
                                'nombre': f"{ultimo_jugador.nombre} {ultimo_jugador.apellido}",
                                'categoria': ultimo_jugador.calcular_categoria(),
                                'es_cabeza_serie': False
                            },
                            'grupo_actual': ultimo_grupo
                        })
        
        # Paso final: Grupos completados (usando los datos REALES)
        grupos_finales = []
        for grupo in grupos_existentes.order_by('numero'):
            participantes_grupo = []
            for participante_grupo in grupo.participantes.all().order_by('posicion_grupo'):
                participantes_grupo.append({
                    'id': participante_grupo.jugador.id,
                    'nombre': f"{participante_grupo.jugador.nombre} {participante_grupo.jugador.apellido}",
                    'categoria': participante_grupo.jugador.calcular_categoria(),
                    'es_cabeza_serie': participante_grupo.es_cabeza_serie
                })
            grupos_finales.append(participantes_grupo)
        
        pasos.append({
            'titulo': 'Asignación Completada',
            'descripcion': 'Todos los participantes han sido asignados a sus grupos correspondientes',
            'tipo': 'grupos_finales',
            'grupos': grupos_finales
        })
        
        return JsonResponse({'pasos': pasos})
    
    # Si es una petición normal, devolver HTML
    context = {
        'torneo': torneo,
        'grupos_existentes': grupos_existentes,
        'participantes': participantes_originales,
        'tiene_cabezas_serie': tiene_cabezas_serie,
        'num_participantes': len(participantes_originales),
        'total_grupos': grupos_existentes.count(),
    }
    
    return render(request, 'vista_previa_asignacion.html', context)

@login_required
def vista_previa_asignacion_pagina(request, torneo_id):
    """Vista para la página de vista previa de asignación"""
    return vista_previa_asignacion(request, torneo_id)

def crear_bracket_completo(torneo, num_participantes):
    """Crear todas las rondas del bracket con jugadores vacíos en las rondas superiores"""
    import math
    
    # Calcular la potencia de 2 más cercana para obtener el tamaño real del bracket
    potencia_2_siguiente = 2 ** math.ceil(math.log2(max(num_participantes, 2)))
    
    # Calcular número total de rondas necesarias basado en la potencia de 2
    total_rondas = math.ceil(math.log2(potencia_2_siguiente))
    
    print(f"📊 Creando bracket completo:")
    print(f"   - Participantes: {num_participantes}")
    print(f"   - Tamaño bracket: {potencia_2_siguiente}")
    print(f"   - Rondas totales: {total_rondas}")
    
    # Ya tenemos la ronda 1 creada, ahora crear las rondas 2, 3, etc.
    for ronda in range(2, total_rondas + 1):
        # Calcular cuántos enfrentamientos hay en esta ronda
        # En cada ronda, el número de enfrentamientos se divide por 2
        enfrentamientos_en_ronda = potencia_2_siguiente // (2 ** ronda)
        
        print(f"   - Ronda {ronda}: {enfrentamientos_en_ronda} enfrentamientos")
        
        # Crear las llaves vacías para esta ronda
        for posicion in range(1, enfrentamientos_en_ronda + 1):
            llave = LlaveTorneo.objects.create(
                torneo=torneo,
                ronda=ronda,
                posicion=posicion,
                jugador1=None,  # Se llenará cuando se definan los ganadores
                jugador2=None,  # Se llenará cuando se definan los ganadores
                bye1=None,
                bye2=None
            )
            print(f"     ✅ Llave creada: Ronda {ronda}, Posición {posicion}")
    
    return total_rondas

def asignar_llaves_automatico(request, torneo, participantes, potencia_2_siguiente, byes_necesarias):
    """
    Asigna automáticamente los jugadores y BYEs a las llaves del torneo
    Garantiza que los BYEs no se enfrenten entre sí
    """
    import random
    
    try:
        # Limpiar asignaciones previas
        torneo.llaves.filter(ronda=1).delete()
        torneo.byes.all().delete()
        
        # Crear una lista mezclada de participantes
        jugadores_mezclados = [p.jugador for p in participantes]
        random.shuffle(jugadores_mezclados)
        
        # Crear BYEs necesarios
        byes_objetos = []
        for i in range(byes_necesarias):
            bye_obj = JugadorBye.objects.create(
                nombre="BYE",
                posicion_bye=i + 1,
                torneo=torneo
            )
            byes_objetos.append(bye_obj)
        
        # Calcular número de enfrentamientos en la primera ronda
        num_enfrentamientos = potencia_2_siguiente // 2
        
        # ESTRATEGIA MEJORADA: Distribuir BYEs aleatoriamente evitando enfrentamientos BYE vs BYE
        enfrentamientos = []
        
        # Crear estructura de enfrentamientos vacía
        for i in range(num_enfrentamientos):
            enfrentamientos.append({
                'posicion': i + 1,
                'jugador1': None,
                'jugador2': None,
                'bye1': None,
                'bye2': None
            })
        
        # Crear lista de todas las posiciones disponibles para BYEs
        posiciones_disponibles = []
        for i in range(num_enfrentamientos):
            posiciones_disponibles.append((i, 1))  # (enfrentamiento_index, posicion_en_enfrentamiento)
            posiciones_disponibles.append((i, 2))
        
        # Mezclar posiciones para distribución aleatoria
        random.shuffle(posiciones_disponibles)
        
        # Asignar BYEs de forma que no haya BYE vs BYE
        byes_asignados = 0
        enfrentamientos_con_bye = set()
        
        for enfrentamiento_idx, posicion_en_enfrentamiento in posiciones_disponibles:
            if byes_asignados >= len(byes_objetos):
                break
                
            # Solo asignar BYE si este enfrentamiento no tiene ya un BYE
            if enfrentamiento_idx not in enfrentamientos_con_bye:
                if posicion_en_enfrentamiento == 1:
                    enfrentamientos[enfrentamiento_idx]['bye1'] = byes_objetos[byes_asignados]
                else:
                    enfrentamientos[enfrentamiento_idx]['bye2'] = byes_objetos[byes_asignados]
                
                enfrentamientos_con_bye.add(enfrentamiento_idx)
                byes_asignados += 1
        
        # Asignar jugadores a las posiciones restantes
        jugador_index = 0
        for enfrentamiento in enfrentamientos:
            # Asignar jugador1 si no hay BYE1
            if enfrentamiento['bye1'] is None and jugador_index < len(jugadores_mezclados):
                enfrentamiento['jugador1'] = jugadores_mezclados[jugador_index]
                jugador_index += 1
            
            # Asignar jugador2 si no hay BYE2
            if enfrentamiento['bye2'] is None and jugador_index < len(jugadores_mezclados):
                enfrentamiento['jugador2'] = jugadores_mezclados[jugador_index]
                jugador_index += 1
        # Crear las llaves en la base de datos
        for enfrentamiento in enfrentamientos:
            # Validación adicional: Verificar que no hay BYE vs BYE
            if enfrentamiento['bye1'] and enfrentamiento['bye2']:
                # Si ocurre esto (no debería), mover un BYE a otro enfrentamiento
                for otro_enfrentamiento in enfrentamientos:
                    if otro_enfrentamiento != enfrentamiento and not otro_enfrentamiento['bye1'] and not otro_enfrentamiento['bye2']:
                        # Mover BYE2 a este enfrentamiento vacío
                        otro_enfrentamiento['bye1'] = enfrentamiento['bye2']
                        enfrentamiento['bye2'] = None
                        break
            
            LlaveTorneo.objects.create(
                torneo=torneo,
                ronda=1,
                posicion=enfrentamiento['posicion'],
                jugador1=enfrentamiento['jugador1'],
                jugador2=enfrentamiento['jugador2'],
                bye1=enfrentamiento['bye1'],
                bye2=enfrentamiento['bye2'],
                estado_partido='pendiente'
            )
        
        # Crear todas las rondas siguientes (vacías) para completar el bracket
        total_rondas = crear_bracket_completo(torneo, len(participantes))
        
        messages.success(request, f"¡Asignación automática completada! Se han creado {num_enfrentamientos} enfrentamientos en la primera ronda y {total_rondas} rondas totales con {byes_necesarias} BYEs distribuidos aleatoriamente (sin enfrentamientos BYE vs BYE).")
        return redirect('organizar_llaves', torneo_id=torneo.id)
        
    except Exception as e:
        messages.error(request, f"Error en la asignación automática: {str(e)}")
        return redirect('organizar_llaves', torneo_id=torneo.id)

def sincronizar_estados_automatico(torneo):
    """
    Sincroniza automáticamente estados de partidos SOLO cuando:
    - Un partido está en 'pendiente' 
    - Tiene ambos jugadores asignados
    - NO es BYE
    - NO está finalizado
    - NO tiene ganador asignado
    """
    partidos_actualizados = 0
    
    # SOLO partidos pendientes que no estén finalizados y sin ganador
    partidos_pendientes = Partido.objects.filter(
        torneo=torneo,
        estado_partido='pendiente',  # SOLO pendientes
        finalizado=False,  # NO tocar los finalizados
        ganador__isnull=True  # NO tocar los que ya tienen ganador
    )
    
    for partido in partidos_pendientes:
        # Si tiene ambos jugadores y no es BYE, cambiar a "en_curso"
        if (partido.jugador1 and partido.jugador2 and 
            not partido.bye1 and not partido.bye2):
            
            partido.estado_partido = 'en_curso'
            partido.save()
            partidos_actualizados += 1
            
            # Crear resultado si no existe
            try:
                partido.resultado_detallado
            except:
                from .models import Resultado
                Resultado.objects.create(partido=partido)
    
    return partidos_actualizados

@login_required
def iniciar_partidos(request, torneo_id):
    """Vista para iniciar todos los partidos del torneo y mostrar enfrentamientos"""
    torneo = get_object_or_404(Torneo, id=torneo_id, organizador=request.user)
    
    # Verificar que el torneo esté en modalidad llaves y ya iniciado
    if torneo.modalidad != 'llaves' or not torneo.torneo_iniciado:
        messages.error(request, "El torneo no está en modalidad llaves o no ha sido iniciado.")
        return redirect('gestionar_torneo', torneo_id=torneo.id)
    
    # Verificar que haya llaves asignadas
    llaves_primera_ronda = torneo.llaves.filter(ronda=1).order_by('posicion')
    if not llaves_primera_ronda.exists():
        messages.error(request, "Primero debes asignar las llaves del torneo.")
        return redirect('organizar_llaves', torneo_id=torneo.id)
    
    # Crear partidos automáticamente si no existen
    partidos_creados = 0
    resultados_creados = 0
    partidos_bye_procesados = 0
    
    for llave in llaves_primera_ronda:
        # Verificar si ya existe un partido para esta llave
        partido_existente = Partido.objects.filter(torneo=torneo, llave_torneo=llave).first()
        
        if not partido_existente:
            # Determinar estado inicial del partido
            if llave.jugador1 and llave.jugador2 and not llave.bye1 and not llave.bye2:
                estado_inicial = 'en_curso'
            else:
                estado_inicial = 'pendiente'
            
            # Crear el partido
            partido = Partido.objects.create(
                torneo=torneo,
                llave_torneo=llave,
                jugador1=llave.jugador1,
                jugador2=llave.jugador2,
                bye1=llave.bye1,
                bye2=llave.bye2,
                estado_partido=estado_inicial,
                organizador=request.user
            )
            partidos_creados += 1
            
            # Crear el resultado automáticamente with default values
            Resultado.objects.create(
                partido=partido
                # Los campos del resultado se inicializan automáticamente en 0
            )
            resultados_creados += 1
            
            # Procesar automáticamente si es un partido con BYE
            if partido.es_partido_bye():
                exito, mensaje = partido.procesar_partido_bye()
                if exito:
                    partidos_bye_procesados += 1
        else:
            # Si ya existe, actualizar estado si es necesario (solo si está pendiente y no finalizado)
            if (partido_existente.jugador1 and partido_existente.jugador2 and 
                not partido_existente.bye1 and not partido_existente.bye2 and
                partido_existente.estado_partido == 'pendiente' and
                not partido_existente.finalizado):
                partido_existente.estado_partido = 'en_curso'
                partido_existente.save()
            
            # Crear resultado si no existe
            try:
                partido_existente.resultado_detallado
            except Resultado.DoesNotExist:
                Resultado.objects.create(
                    partido=partido_existente
                    # Los campos del resultado se inicializan automáticamente en 0
                )
                resultados_creados += 1
            
            # Procesar automáticamente si es un partido con BYE y aún no está jugado
            if partido_existente.es_partido_bye() and partido_existente.estado_partido != 'jugado':
                exito, mensaje = partido_existente.procesar_partido_bye()
                if exito:
                    partidos_bye_procesados += 1
    
    if partidos_creados > 0:
        mensaje_principal = f"¡{partidos_creados} partidos y {resultados_creados} resultados creados!"
        if partidos_bye_procesados > 0:
            mensaje_principal += f" {partidos_bye_procesados} partidos con BYE fueron cerrados automáticamente."
        messages.success(request, mensaje_principal)
    elif partidos_bye_procesados > 0:
        messages.success(request, f"¡{partidos_bye_procesados} partidos con BYE fueron cerrados automáticamente!")
    
    # Obtener todos los partidos de todas las rondas
    partidos = Partido.objects.filter(
        torneo=torneo
    ).select_related('jugador1', 'jugador2', 'bye1', 'bye2', 'llave_torneo').order_by('llave_torneo__ronda', 'llave_torneo__posicion')
    
    # Crear partidos para rondas siguientes si hay llaves con ganadores asignados
    llaves_todas_rondas = torneo.llaves.all().order_by('ronda', 'posicion')
    for llave in llaves_todas_rondas:
        if llave.ronda > 1:  # Para rondas después de la primera
            # Solo crear partido si hay al menos un jugador asignado
            if llave.jugador1 or llave.jugador2:
                partido_existente = Partido.objects.filter(torneo=torneo, llave_torneo=llave).first()
                if not partido_existente:
                    # Determinar estado del partido
                    if llave.jugador1 and llave.jugador2:
                        estado = 'en_curso'
                    elif llave.jugador1 or llave.jugador2:
                        estado = 'pendiente'  # Falta un jugador
                    else:
                        estado = 'pendiente'
                    
                    partido = Partido.objects.create(
                        torneo=torneo,
                        llave_torneo=llave,
                        jugador1=llave.jugador1,
                        jugador2=llave.jugador2,
                        bye1=llave.bye1,
                        bye2=llave.bye2,
                        estado_partido=estado,
                        organizador=request.user
                    )
                    
                    # Crear resultado si ambos jugadores están asignados
                    if llave.jugador1 and llave.jugador2:
                        Resultado.objects.create(partido=partido)
                        
                        # Procesar BYE si aplica
                        if partido.es_partido_bye():
                            partido.procesar_partido_bye()
                else:
                    # Actualizar partido existente para asegurar sincronización
                    actualizado = False
                    if partido_existente.jugador1 != llave.jugador1:
                        partido_existente.jugador1 = llave.jugador1
                        actualizado = True
                    if partido_existente.jugador2 != llave.jugador2:
                        partido_existente.jugador2 = llave.jugador2
                        actualizado = True
                    if partido_existente.bye1 != llave.bye1:
                        partido_existente.bye1 = llave.bye1
                        actualizado = True
                    if partido_existente.bye2 != llave.bye2:
                        partido_existente.bye2 = llave.bye2
                        actualizado = True
                    
                    if actualizado:
                        # Actualizar estado según jugadores asignados - solo si está pendiente y no finalizado
                        if (partido_existente.jugador1 and partido_existente.jugador2 and 
                            not partido_existente.bye1 and not partido_existente.bye2 and
                            partido_existente.estado_partido == 'pendiente' and 
                            not partido_existente.finalizado):
                            partido_existente.estado_partido = 'en_curso'
                        partido_existente.save()
                        
                        # Crear resultado si no existe y ambos jugadores están asignados
                        if partido_existente.jugador1 and partido_existente.jugador2:
                            try:
                                partido_existente.resultado_detallado
                            except Resultado.DoesNotExist:
                                Resultado.objects.create(partido=partido_existente)
    
    # Refrescar la consulta de partidos después de crear nuevos
    partidos = Partido.objects.filter(
        torneo=torneo
    ).select_related('jugador1', 'jugador2', 'bye1', 'bye2', 'llave_torneo').order_by('llave_torneo__ronda', 'llave_torneo__posicion')
    
    # Agrupar partidos por ronda
    partidos_por_ronda = {}
    partidos_tercer_lugar = []
    
    for partido in partidos:
        ronda = partido.llave_torneo.ronda
        # Separar partidos de tercer lugar
        if partido.llave_torneo.tipo_llave == 'tercer_lugar':
            partidos_tercer_lugar.append(partido)
        else:
            if ronda not in partidos_por_ronda:
                partidos_por_ronda[ronda] = []
            partidos_por_ronda[ronda].append(partido)

    # Calcular el total de rondas teóricas basado en el número de participantes
    # Para una llave de 8 participantes: 3 rondas (4->2->1)
    import math
    total_participantes = torneo.llaves.filter(ronda=1).count() * 2  # Cada llave de primera ronda tiene 2 participantes
    if total_participantes > 0:
        total_rondas = int(math.log2(total_participantes))
    else:
        total_rondas = torneo.llaves.aggregate(max_ronda=models.Max('ronda'))['max_ronda'] or 1

    # Asegurarse de que todas las rondas estén representadas, aunque estén vacías
    for r in range(1, total_rondas + 1):
        if r not in partidos_por_ronda:
            partidos_por_ronda[r] = []

    # Verificar si se puede crear la siguiente ronda
    ronda_actual = 1
    if partidos_por_ronda:
        # Encontrar la ronda más alta que tiene partidos
        rondas_con_partidos = [r for r in partidos_por_ronda.keys() if partidos_por_ronda[r]]
        if rondas_con_partidos:
            ronda_actual = max(rondas_con_partidos)
    
    puede_crear_siguiente = False
    if ronda_actual in partidos_por_ronda:
        puede_crear_siguiente = all(p.ganador for p in partidos_por_ronda[ronda_actual])

    # Obtener árbitros disponibles para este torneo
    arbitros_disponibles = ArbitroTorneo.objects.filter(
        torneo=torneo, 
        activo=True
    ).select_related('arbitro')

    # 🔄 SINCRONIZACIÓN AUTOMÁTICA DE ESTADOS
    # Aplicar sincronización final de estados después de todas las operaciones
    try:
        partidos_sincronizados = sincronizar_estados_automatico(torneo)
        if partidos_sincronizados > 0:
            messages.success(request, f"✅ {partidos_sincronizados} partidos sincronizados automáticamente a estado 'en_curso'.")
    except Exception as e:
        messages.warning(request, f"⚠️ Error en sincronización automática: {str(e)}")

    torneo_completado = verificar_torneo_completado(torneo)

    # Actualizar automáticamente el estado finalizado del torneo
    if torneo_completado and not torneo.finalizado:
        torneo.finalizado = True
        torneo.save()
        print(f"🏆 Torneo '{torneo.nombre}' marcado como FINALIZADO automáticamente")
    elif not torneo_completado and torneo.finalizado:
        # Si por alguna razón el torneo no está completado pero está marcado como finalizado, corregir
        torneo.finalizado = False
        torneo.save()
        print(f"⚠️ Torneo '{torneo.nombre}' desmarcado como finalizado (corrección automática)")

    # Siempre generar clasificación (parcial o completa)
    clasificacion_final = generar_clasificacion_final(torneo)

    context = {
        'torneo': torneo,
        'partidos_por_ronda': partidos_por_ronda,
        'partidos_tercer_lugar': partidos_tercer_lugar,
        'puede_crear_siguiente': puede_crear_siguiente,
        'ronda_actual': ronda_actual,
        'total_rondas': total_rondas,
        'arbitros_disponibles': arbitros_disponibles,
        'es_organizador': request.user == torneo.organizador,
        # Información de depuración
        'debug_partidos_count': partidos.count(),
        'debug_llaves_count': torneo.llaves.count(),
        'torneo_completado': torneo_completado,
        'clasificacion_final': clasificacion_final,
    }
    
    return render(request, 'enfrentamientos.html', context)

@require_organizador
def cerrar_partido_organizador(request, torneo_id, partido_id):
    """Vista para que el organizador cierre un partido manualmente"""
    torneo = get_object_or_404(Torneo, id=torneo_id, organizador=request.user)
    partido = get_object_or_404(Partido, id=partido_id, torneo=torneo)
    
    if partido.estado_partido == 'jugado':
        messages.info(request, "El partido ya está cerrado.")
        return redirect('iniciar_partidos', torneo_id=torneo.id)
    
    # Verificar y cerrar el partido
    cerrado, mensaje = partido.verificar_y_cerrar_partido()
    
    if cerrado:
        messages.success(request, f"¡Partido cerrado exitosamente! {mensaje}")
    else:
        messages.error(request, f"No se pudo cerrar el partido: {mensaje}")
    
    return redirect('iniciar_partidos', torneo_id=torneo.id)

@require_organizador

def procesar_partidos_bye_masivo(request, torneo_id):
    """Vista auxiliar para procesar automáticamente todos los partidos con BYE de un torneo"""
    torneo = get_object_or_404(Torneo, id=torneo_id, organizador=request.user)
    
    # Buscar todos los partidos con BYE que no estén ya jugados
    partidos_con_bye = Partido.objects.filter(
        torneo=torneo,
        estado_partido__in=['pendiente', 'en_curso']
    ).filter(
        models.Q(bye1__isnull=False) | models.Q(bye2__isnull=False)
    )
    
    partidos_procesados = 0
    errores = []
    
    for partido in partidos_con_bye:
        if partido.es_partido_bye():
            exito, mensaje = partido.procesar_partido_bye()
            if exito:
                partidos_procesados += 1
            else:
                errores.append(f"Partido {partido.id}: {mensaje}")
    
    if partidos_procesados > 0:
        messages.success(request, f"¡Se procesaron automáticamente {partidos_procesados} partidos con BYE!")
    
    if errores:
        for error in errores:
            messages.error(request, error)
    
    if partidos_procesados == 0 and not errores:
        messages.info(request, "No se encontraron partidos con BYE pendientes de procesar.")
    
    # Regresar a la vista de enfrentamientos
    return redirect('iniciar_partidos', torneo_id=torneo.id)

@login_required
def registrar_resultado(request, torneo_id, partido_id):
    """Vista para registrar los puntos de cada set en un partido"""
    torneo = get_object_or_404(Torneo, id=torneo_id, organizador=request.user)
    partido = get_object_or_404(Partido, id=partido_id, torneo=torneo)
    
    # Verificar que el partido esté en curso
    if partido.estado_partido != 'en_curso':
        messages.error(request, "Solo se pueden registrar resultados de partidos en curso.")
        return redirect('iniciar_partidos', torneo_id=torneo.id)
    
    # Obtener el resultado del partido
    try:
        resultado = partido.resultado_detallado
    except Resultado.DoesNotExist:
        # Si no existe, crearlo
        resultado = Resultado.objects.create(partido=partido)
    
    if request.method == 'POST':
        try:
            # Determinar si es un partido final
            total_rondas = torneo.llaves.aggregate(max_ronda=models.Max('ronda'))['max_ronda'] or 1
            es_partido_final = partido.llave_torneo.ronda == total_rondas
            
            # Obtener los puntos de cada set usando la modalidad correcta
            mejor_de_sets = torneo.mejor_de_sets_final if es_partido_final else torneo.mejor_de_sets
            sets_para_ganar = (mejor_de_sets // 2) + 1
            
            # Verificar qué sets ya están guardados antes de procesar
            sets_guardados = resultado.obtener_sets_guardados()
            
            # Obtener puntos de los sets obligatorios (1, 2, 3)
            # Solo permitir cambios en sets no guardados
            if sets_guardados['set1']:
                # Set 1 ya está guardado, mantener valores actuales
                set1_j1 = resultado.set1_jugador1
                set1_j2 = resultado.set1_jugador2
            else:
                # Set 1 puede modificarse
                set1_j1 = int(request.POST.get('set1_jugador1', 0))
                set1_j2 = int(request.POST.get('set1_jugador2', 0))
                
            if sets_guardados['set2']:
                # Set 2 ya está guardado, mantener valores actuales
                set2_j1 = resultado.set2_jugador1
                set2_j2 = resultado.set2_jugador2
            else:
                # Set 2 puede modificarse
                set2_j1 = int(request.POST.get('set2_jugador1', 0))
                set2_j2 = int(request.POST.get('set2_jugador2', 0))
                
            if sets_guardados['set3']:
                # Set 3 ya está guardado, mantener valores actuales
                set3_j1 = resultado.set3_jugador1
                set3_j2 = resultado.set3_jugador2
            else:
                # Set 3 puede modificarse
                set3_j1 = int(request.POST.get('set3_jugador1', 0))
                set3_j2 = int(request.POST.get('set3_jugador2', 0))
            
            # Función para validar puntos de un set según reglas de tenis de mesa
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
            
            # Validar cada set (solo los que no están guardados)
            errores = []
            
            # Validar sets obligatorios solo si no están guardados
            if not sets_guardados['set1']:
                error_set1 = validar_set(set1_j1, set1_j2, "Set 1")
                if error_set1:
                    errores.append(error_set1)
            
            if not sets_guardados['set2']:        
                error_set2 = validar_set(set2_j1, set2_j2, "Set 2")
                if error_set2:
                    errores.append(error_set2)
            
            if not sets_guardados['set3']:
                error_set3 = validar_set(set3_j1, set3_j2, "Set 3")
                if error_set3:
                    errores.append(error_set3)
            
            # Variables para sets opcionales
            set4_j1_val = None
            set4_j2_val = None
            set5_j1_val = None
            set5_j2_val = None
            set6_j1_val = None
            set6_j2_val = None
            set7_j1_val = None
            set7_j2_val = None
            set8_j1_val = None
            set8_j2_val = None
            set9_j1_val = None
            set9_j2_val = None
            
            # Validar sets adicionales dinámicamente según mejor_de_sets
            for set_num in range(4, mejor_de_sets + 1):
                set_j1 = request.POST.get(f'set{set_num}_jugador1')
                set_j2 = request.POST.get(f'set{set_num}_jugador2')
                
                # Validar si se ingresaron valores y no está guardado
                if set_j1 and set_j2 and not sets_guardados[f'set{set_num}']:
                    try:
                        set_j1_val = int(set_j1)
                        set_j2_val = int(set_j2)
                        error_set = validar_set(set_j1_val, set_j2_val, f"Set {set_num}")
                        if error_set:
                            errores.append(error_set)
                        else:
                            # Asignar los valores a las variables correspondientes
                            if set_num == 4:
                                set4_j1_val, set4_j2_val = set_j1_val, set_j2_val
                            elif set_num == 5:
                                set5_j1_val, set5_j2_val = set_j1_val, set_j2_val
                            elif set_num == 6:
                                set6_j1_val, set6_j2_val = set_j1_val, set_j2_val
                            elif set_num == 7:
                                set7_j1_val, set7_j2_val = set_j1_val, set_j2_val
                            elif set_num == 8:
                                set8_j1_val, set8_j2_val = set_j1_val, set_j2_val
                            elif set_num == 9:
                                set9_j1_val, set9_j2_val = set_j1_val, set_j2_val
                    except ValueError:
                        errores.append(f"Error: Los valores del Set {set_num} deben ser números válidos.")
                elif sets_guardados[f'set{set_num}']:
                    # Set ya está guardado, mantener valores actuales
                    if set_num == 4:
                        set4_j1_val = resultado.set4_jugador1
                        set4_j2_val = resultado.set4_jugador2
                    elif set_num == 5:
                        set5_j1_val = resultado.set5_jugador1
                        set5_j2_val = resultado.set5_jugador2
                    elif set_num == 6:
                        set6_j1_val = getattr(resultado, 'set6_jugador1', None)
                        set6_j2_val = getattr(resultado, 'set6_jugador2', None)
                    elif set_num == 7:
                        set7_j1_val = getattr(resultado, 'set7_jugador1', None)
                        set7_j2_val = getattr(resultado, 'set7_jugador2', None)
                    elif set_num == 8:
                        set8_j1_val = getattr(resultado, 'set8_jugador1', None)
                        set8_j2_val = getattr(resultado, 'set8_jugador2', None)
                    elif set_num == 9:
                        set9_j1_val = getattr(resultado, 'set9_jugador1', None)
                        set9_j2_val = getattr(resultado, 'set9_jugador2', None)
            
            # Si hay errores, mostrarlos y no guardar
            if errores:
                for error in errores:
                    messages.error(request, error)
                # Mantener en la misma página para mostrar los errores
                sets = list(range(1, mejor_de_sets + 1))
                sets_values = {}
                for set_num in sets:
                    sets_values[f"set{set_num}_jugador1"] = getattr(resultado, f"set{set_num}_jugador1", "")
                    sets_values[f"set{set_num}_jugador2"] = getattr(resultado, f"set{set_num}_jugador2", "")
                context = {
                    'torneo': torneo,
                    'partido': partido,
                    'resultado': resultado,
                    'mejor_de_sets': mejor_de_sets,
                    'sets_para_ganar': sets_para_ganar,
                    'sets_guardados': resultado.obtener_sets_guardados(),
                    'sets': sets,
                    'sets_values': sets_values,
                    'es_partido_final': es_partido_final,  # Indica si es un partido final
                }
                return render(request, 'registrar_resultado.html', context)

            # Validación extra: impedir guardar si hay empate en sets y ambos están a un set de ganar (ej: 2-2 en mejor de 5)
            # Primero, calcular los sets ganados con los valores actuales (sin guardar aún)
            sets_j1 = 0
            sets_j2 = 0
            sets_totales = []
            # Recolectar los sets jugados
            for set_num in range(1, mejor_de_sets + 1):
                j1 = locals().get(f'set{set_num}_j1', None)
                j2 = locals().get(f'set{set_num}_j2', None)
                if j1 is not None and j2 is not None and (j1 > 0 or j2 > 0) and j1 != j2:
                    if j1 > j2:
                        sets_j1 += 1
                    else:
                        sets_j2 += 1
                    sets_totales.append((j1, j2))

            # Si ambos tienen sets_para_ganar - 1 y están empatados, bloquear guardado
            if sets_j1 == sets_j2 and sets_j1 == sets_para_ganar - 1:
                messages.error(request, f"No puedes guardar el resultado con empate {sets_j1}-{sets_j2}. Debe haber un ganador (por ejemplo, 3-2 en mejor de 5). Ingresa el set definitivo.")
                sets = list(range(1, mejor_de_sets + 1))
                sets_values = {}
                for set_num in sets:
                    sets_values[f"set{set_num}_jugador1"] = locals().get(f'set{set_num}_j1', getattr(resultado, f"set{set_num}_jugador1", ""))
                    sets_values[f"set{set_num}_jugador2"] = locals().get(f'set{set_num}_j2', getattr(resultado, f"set{set_num}_jugador2", ""))
                context = {
                    'torneo': torneo,
                    'partido': partido,
                    'resultado': resultado,
                    'mejor_de_sets': mejor_de_sets,
                    'sets_para_ganar': sets_para_ganar,
                    'sets_guardados': resultado.obtener_sets_guardados(),
                    'sets': sets,
                    'sets_values': sets_values,
                    'es_partido_final': es_partido_final,  # Indica si es un partido final
                }
                return render(request, 'registrar_resultado.html', context)

            # Si todas las validaciones pasaron, actualizar el resultado
            resultado.set1_jugador1 = set1_j1
            resultado.set1_jugador2 = set1_j2
            resultado.set2_jugador1 = set2_j1
            resultado.set2_jugador2 = set2_j2
            resultado.set3_jugador1 = set3_j1
            resultado.set3_jugador2 = set3_j2

            # Actualizar sets opcionales dinámicamente
            for set_num in range(4, mejor_de_sets + 1):
                j1_val = locals().get(f'set{set_num}_j1_val')
                j2_val = locals().get(f'set{set_num}_j2_val')

                if j1_val is not None and j2_val is not None:
                    setattr(resultado, f'set{set_num}_jugador1', j1_val)
                    setattr(resultado, f'set{set_num}_jugador2', j2_val)

            # Guardar y calcular sets ganados automáticamente
            resultado.save()

            # Verificar inmediatamente si el partido debe cerrarse
            cerrado, mensaje = partido.verificar_y_cerrar_partido()

            if cerrado:
                # Auto-confirmar el partido inmediatamente si está marcado como pendiente
                if partido.pendiente_confirmacion:
                    cerrado_final, mensaje_final = partido.confirmar_y_cerrar_partido()
                    if cerrado_final:
                        messages.success(request, f"¡Partido cerrado exitosamente! {mensaje_final}")
                    else:
                        messages.success(request, f"¡{mensaje}!")
                else:
                    messages.success(request, f"¡{mensaje}!")

                # **AGREGADO**: Sincronizar inmediatamente ganador entre partido y llave
                sincronizar_ganador_partido_llave(partido)

                # Si el torneo es de llaves, intentar avanzar ganadores automáticamente
                if torneo.modalidad == 'llaves':
                    avanzado, mensaje_avance = avanzar_ganadores_automaticamente(torneo)
                    if avanzado:
                        messages.info(request, mensaje_avance)
                
                # Verificar si el torneo está completado y marcarlo como finalizado
                if verificar_torneo_completado(torneo) and not torneo.finalizado:
                    torneo.finalizado = True
                    torneo.save()
                    messages.success(request, "🏆 ¡TORNEO FINALIZADO! Todos los partidos principales han sido completados.")

                return redirect('iniciar_partidos', torneo_id=torneo.id)
            else:
                # Resultado parcial guardado correctamente
                sets_guardados_actuales = resultado.obtener_sets_guardados()
                sets_nuevos = []
                if sets_guardados_actuales['set1'] and not sets_guardados.get('set1', False):
                    sets_nuevos.append("Set 1")
                if sets_guardados_actuales['set2'] and not sets_guardados.get('set2', False):
                    sets_nuevos.append("Set 2")
                if sets_guardados_actuales['set3'] and not sets_guardados.get('set3', False):
                    sets_nuevos.append("Set 3")
                if sets_guardados_actuales['set4'] and not sets_guardados.get('set4', False):
                    sets_nuevos.append("Set 4")
                if sets_guardados_actuales['set5'] and not sets_guardados.get('set5', False):
                    sets_nuevos.append("Set 5")

                if sets_nuevos:
                    mensaje = f"Resultado guardado correctamente. Nuevos sets guardados: {', '.join(sets_nuevos)}. Sets actuales: {resultado.sets_ganados_jugador1}-{resultado.sets_ganados_jugador2}"
                else:
                    mensaje = f"Resultado actualizado correctamente. Sets: {resultado.sets_ganados_jugador1}-{resultado.sets_ganados_jugador2}"

                messages.success(request, mensaje)
                return redirect('registrar_resultado', torneo_id=torneo.id, partido_id=partido.id)
        
        except ValueError:
            messages.error(request, "Por favor ingresa números válidos para los puntos.")
            # Mantener en la misma página para mostrar el error
            # Determinar modalidad correcta para mostrar el error
            total_rondas = torneo.llaves.aggregate(max_ronda=models.Max('ronda'))['max_ronda'] or 1
            es_partido_final = partido.llave_torneo.ronda == total_rondas
            mejor_de_sets_error = torneo.mejor_de_sets_final if es_partido_final else torneo.mejor_de_sets
            
            sets = list(range(1, mejor_de_sets_error + 1))
            sets_values = {}
            for set_num in sets:
                sets_values[f"set{set_num}_jugador1"] = getattr(resultado, f"set{set_num}_jugador1", "")
                sets_values[f"set{set_num}_jugador2"] = getattr(resultado, f"set{set_num}_jugador2", "")
            context = {
                'torneo': torneo,
                'partido': partido,
                'resultado': resultado,
                'mejor_de_sets': mejor_de_sets_error,
                'sets_para_ganar': (mejor_de_sets_error // 2) + 1,
                'sets_guardados': resultado.obtener_sets_guardados(),
                'sets': sets,
                'sets_values': sets_values,
                'es_partido_final': es_partido_final,  # Indica si es un partido final
            }
            return render(request, 'registrar_resultado.html', context)
        except Exception as e:
            messages.error(request, f"Error al guardar el resultado: {str(e)}")
            # Mantener en la misma página para mostrar el error
            # Determinar modalidad correcta para mostrar el error
            total_rondas = torneo.llaves.aggregate(max_ronda=models.Max('ronda'))['max_ronda'] or 1
            es_partido_final = partido.llave_torneo.ronda == total_rondas
            mejor_de_sets_error = torneo.mejor_de_sets_final if es_partido_final else torneo.mejor_de_sets
            
            sets = list(range(1, mejor_de_sets_error + 1))
            sets_values = {}
            for set_num in sets:
                sets_values[f"set{set_num}_jugador1"] = getattr(resultado, f"set{set_num}_jugador1", "")
                sets_values[f"set{set_num}_jugador2"] = getattr(resultado, f"set{set_num}_jugador2", "")
            context = {
                'torneo': torneo,
                'partido': partido,
                'resultado': resultado,
                'mejor_de_sets': mejor_de_sets_error,
                'sets_para_ganar': (mejor_de_sets_error // 2) + 1,
                'sets_guardados': resultado.obtener_sets_guardados(),
                'sets': sets,
                'sets_values': sets_values,
                'es_partido_final': es_partido_final,  # Indica si es un partido final
            }
            return render(request, 'registrar_resultado.html', context)
    
    # Determinar si es un partido final para mostrar la modalidad correcta
    total_rondas = torneo.llaves.aggregate(max_ronda=models.Max('ronda'))['max_ronda'] or 1
    es_partido_final = partido.llave_torneo.ronda == total_rondas
    
    # Usar la modalidad correcta según si es final o no
    mejor_de_sets = torneo.mejor_de_sets_final if es_partido_final else torneo.mejor_de_sets
    sets_para_ganar = (mejor_de_sets // 2) + 1
    sets = list(range(1, mejor_de_sets + 1))  # Lista dinámica de sets [1, 2, 3, ..., mejor_de_sets]
    
    # Crear diccionario con valores de sets para facilitar acceso en template
    sets_values = {}
    for set_num in sets:
        sets_values[f"set{set_num}_jugador1"] = getattr(resultado, f"set{set_num}_jugador1", "")
        sets_values[f"set{set_num}_jugador2"] = getattr(resultado, f"set{set_num}_jugador2", "")

    context = {
        'torneo': torneo,
        'partido': partido,
        'resultado': resultado,
        'mejor_de_sets': mejor_de_sets,
        'sets_para_ganar': sets_para_ganar,
        'sets_guardados': resultado.obtener_sets_guardados(),
        'sets': sets,  # Lista dinámica de sets
        'sets_values': sets_values,  # Valores de los sets
        'es_partido_final': es_partido_final,  # Indica si es un partido final
    }
    
    return render(request, 'registrar_resultado.html', context)

def crear_partido_tercer_lugar(torneo, llaves_semifinales):
    """
    Crea automáticamente una llave y partido de tercer lugar después de completar las semifinales.
    """
    try:
        if llaves_semifinales.count() != 2:
            return False, "Se requieren exactamente 2 semifinales"
        
        # Verificar si ya existe
        if LlaveTorneo.objects.filter(torneo=torneo, tipo_llave='tercer_lugar').exists():
            return True, "Llave de tercer lugar ya existe"
        
        # Obtener perdedores
        perdedores = []
        for semifinal in llaves_semifinales:
            if semifinal.ganador:
                if semifinal.jugador1 == semifinal.ganador:
                    perdedor = semifinal.jugador2
                elif semifinal.jugador2 == semifinal.ganador:
                    perdedor = semifinal.jugador1
                
                if perdedor:
                    perdedores.append(perdedor)
        
        if len(perdedores) != 2:
            return False, f"Se necesitan 2 perdedores, se encontraron {len(perdedores)}"
        
        # Calcular la siguiente posición disponible
        ronda_semifinales = llaves_semifinales.first().ronda
        ultima_posicion = LlaveTorneo.objects.filter(
            torneo=torneo, 
            tipo_llave='normal'
        ).aggregate(models.Max('posicion'))['posicion__max'] or 0
        
        # Crear llave de tercer lugar
        llave_tercer_lugar = LlaveTorneo.objects.create(
            torneo=torneo,
            ronda=ronda_semifinales,
            posicion=ultima_posicion + 1,
            tipo_llave='tercer_lugar',
            jugador1=perdedores[0],
            jugador2=perdedores[1],
            estado_partido='en_curso'  # Cambiar a 'en_curso' para permitir registro de resultados
        )
        
        # Crear partido
        partido_tercer_lugar = Partido.objects.create(
            torneo=torneo,
            llave_torneo=llave_tercer_lugar,
            jugador1=perdedores[0],
            jugador2=perdedores[1],
            estado_partido='en_curso',  # Cambiar a 'en_curso' para permitir registro de resultados
            organizador=torneo.organizador
        )
        
        # Crear resultado
        Resultado.objects.create(partido=partido_tercer_lugar)
        
        return True, f"Partido de tercer lugar creado: {perdedores[0].nombre} vs {perdedores[1].nombre}"
        
    except Exception as e:
        return False, f"Error al crear partido de tercer lugar: {str(e)}"

def avanzar_ganadores_automaticamente(torneo):
    """
    Verifica si una ronda está completa y automáticamente avanza a los ganadores 
    a la siguiente ronda para torneos de cualquier tamaño (2, 4, 8, 16, 32, 64, 128, etc.).
    """
    
    try:
        # Obtener todas las rondas del torneo
        total_rondas = LlaveTorneo.objects.filter(torneo=torneo).aggregate(
            max_ronda=models.Max('ronda')
        )['max_ronda']
        
        if not total_rondas:
            return False, "No hay llaves en el torneo"
        
        # Revisar cada ronda de la primera hacia adelante
        for ronda_actual in range(1, total_rondas + 1):
            # Obtener todas las llaves de esta ronda
            llaves_ronda = LlaveTorneo.objects.filter(
                torneo=torneo, 
                ronda=ronda_actual
            ).order_by('posicion')
            
            if not llaves_ronda.exists():
                continue
            
            # CORRECCION: Solo considerar llaves normales para determinar si la ronda está completa
            # Las llaves de tercer lugar no deben bloquear el avance
            llaves_normales_ronda = llaves_ronda.filter(tipo_llave='normal')
            
            # Verificar si todos los partidos NORMALES de esta ronda están completos
            total_partidos = llaves_normales_ronda.count()
            partidos_completados = llaves_normales_ronda.filter(ganador__isnull=False).count()
            
            print(f"📊 Ronda {ronda_actual}: {partidos_completados}/{total_partidos} partidos normales completados")
            
            # Si esta ronda no está completa, detenemos aquí
            if partidos_completados < total_partidos:
                return False, f"Ronda {ronda_actual} incompleta ({partidos_completados}/{total_partidos} partidos normales)"
            
            # Si es la penúltima ronda (semifinales), crear partido de tercer lugar
            if ronda_actual == total_rondas - 1:
                # Usar llaves normales para semifinales (ya filtradas arriba)
                if llaves_normales_ronda.count() == 2:
                    exito, mensaje = crear_partido_tercer_lugar(torneo, llaves_normales_ronda)
                    if exito:
                        print(f"🥉 {mensaje}")
                    else:
                        print(f"⚠️  Tercer lugar: {mensaje}")
            
            # Si es la última ronda y está completa, el torneo terminó
            if ronda_actual == total_rondas:
                ganador_final = llaves_normales_ronda.first().ganador
                if ganador_final:
                    return True, f"🏆 ¡Torneo finalizado! Campeón: {ganador_final.nombre} {ganador_final.apellido}"
                else:
                    return False, "Error: Última ronda completa pero sin ganador"
            
            # Verificar si existe la siguiente ronda
            ronda_siguiente = ronda_actual + 1
            llaves_siguiente_ronda = LlaveTorneo.objects.filter(
                torneo=torneo, 
                ronda=ronda_siguiente,
                tipo_llave='normal'  # Solo considerar llaves normales para el avance
            ).order_by('posicion')
            
            if not llaves_siguiente_ronda.exists():
                return False, f"No existen llaves normales para la ronda {ronda_siguiente}"
            
            # Obtener todos los ganadores de la ronda actual ordenados por posición
            ganadores = []
            for llave in llaves_normales_ronda:  # Solo de llaves normales
                if llave.ganador:
                    ganadores.append(llave.ganador)
                else:
                    return False, f"Llave {llave.posicion} de ronda {ronda_actual} sin ganador"
            
            print(f"🏃 Ganadores de ronda {ronda_actual}: {[f'{g.nombre} {g.apellido}' for g in ganadores]}")
            
            # Avanzar ganadores a la siguiente ronda
            with transaction.atomic():
                ganadores_avanzados = 0
                
                # Cada par de ganadores va a una llave de la siguiente ronda
                for i in range(0, len(ganadores), 2):
                    if i // 2 < llaves_siguiente_ronda.count():
                        llave_destino = llaves_siguiente_ronda[i // 2]
                        
                        # Limpiar la llave primero (en caso de avances previos incorrectos)
                        actualizar_llave = False
                        
                        # Asignar primer ganador
                        if i < len(ganadores):
                            if llave_destino.jugador1 != ganadores[i]:
                                llave_destino.jugador1 = ganadores[i]
                                llave_destino.bye1 = None  # Limpiar BYE si hay
                                actualizar_llave = True
                                ganadores_avanzados += 1
                                print(f"✅ {ganadores[i].nombre} avanza a ronda {ronda_siguiente}, posición {llave_destino.posicion} (jugador1)")
                        
                        # Asignar segundo ganador (si existe)
                        if i + 1 < len(ganadores):
                            if llave_destino.jugador2 != ganadores[i + 1]:
                                llave_destino.jugador2 = ganadores[i + 1]
                                llave_destino.bye2 = None  # Limpiar BYE si hay
                                actualizar_llave = True
                                ganadores_avanzados += 1
                                print(f"✅ {ganadores[i + 1].nombre} avanza a ronda {ronda_siguiente}, posición {llave_destino.posicion} (jugador2)")
                        elif i < len(ganadores):
                            # Solo hay un ganador (número impar), el otro slot queda vacío por ahora
                            # Esto se manejará en la siguiente iteración o queda como BYE
                            pass
                        
                        # Guardar cambios en la llave
                        if actualizar_llave:
                            # Solo resetear estado si no hay partido asociado o si está pendiente
                            partido_llave = Partido.objects.filter(llave_torneo=llave_destino).first()
                            if not partido_llave or partido_llave.estado_partido == 'pendiente':
                                llave_destino.estado_partido = 'pendiente'
                            llave_destino.ganador = None  # Limpiar ganador de ronda anterior
                            llave_destino.save()
                
                # Después de asignar TODOS los jugadores a las llaves, crear/actualizar los partidos
                for llave_destino in llaves_siguiente_ronda:
                    # Solo procesar llaves que tienen al menos un jugador asignado
                    if llave_destino.jugador1 or llave_destino.jugador2:
                        # Buscar si ya existe un partido para esta llave
                        partido_existente = Partido.objects.filter(
                            torneo=torneo, 
                            llave_torneo=llave_destino
                        ).first()
                        
                        if not partido_existente:
                            # Crear nuevo partido con AMBOS jugadores
                            nuevo_partido = Partido.objects.create(
                                torneo=torneo,
                                llave_torneo=llave_destino,
                                jugador1=llave_destino.jugador1,
                                jugador2=llave_destino.jugador2,
                                bye1=llave_destino.bye1,
                                bye2=llave_destino.bye2,
                                estado_partido='pendiente',
                                organizador=torneo.organizador
                            )
                            
                            # Crear resultado automáticamente
                            Resultado.objects.create(partido=nuevo_partido)
                            print(f"🆕 Partido creado para ronda {ronda_siguiente}, posición {llave_destino.posicion} - J1: {nuevo_partido.jugador1}, J2: {nuevo_partido.jugador2}")
                            
                            # Si es un partido con BYE, procesarlo automáticamente
                            if nuevo_partido.es_partido_bye():
                                nuevo_partido.procesar_partido_bye()
                                print(f"🤖 BYE procesado automáticamente en ronda {ronda_siguiente}")
                        
                        else:
                            # Actualizar partido existente con AMBOS jugadores
                            partido_existente.jugador1 = llave_destino.jugador1
                            partido_existente.jugador2 = llave_destino.jugador2
                            partido_existente.bye1 = llave_destino.bye1
                            partido_existente.bye2 = llave_destino.bye2
                            # Solo resetear estado si el partido no está finalizado
                            if partido_existente.estado_partido not in ['jugado'] and not partido_existente.finalizado and not partido_existente.ganador:
                                partido_existente.estado_partido = 'pendiente'
                            partido_existente.save()
                            print(f"🔄 Partido actualizado para ronda {ronda_siguiente}, posición {llave_destino.posicion} - J1: {partido_existente.jugador1}, J2: {partido_existente.jugador2}")
                
                if ganadores_avanzados > 0:
                    print(f"🎯 {ganadores_avanzados} ganadores avanzados de ronda {ronda_actual} a ronda {ronda_siguiente}")
                    # Continuar verificando la siguiente ronda
                    continue
                else:
                    print(f"ℹ️  Ronda {ronda_actual} ya había sido procesada anteriormente")
        
        return True, "✅ Avance automático completado para todas las rondas disponibles"
        
    except Exception as e:
        print(f"❌ Error en avance automático: {str(e)}")
        return False, f"Error al avanzar ganadores: {str(e)}"

def sincronizar_ganador_partido_llave(partido):
    """
    Función de utilidad para asegurar que el ganador del partido 
    se sincronice inmediatamente con la llave correspondiente
    """
    if partido.ganador and partido.llave_torneo:
        if partido.llave_torneo.ganador != partido.ganador:
            partido.llave_torneo.ganador = partido.ganador
            partido.llave_torneo.estado_partido = 'jugado'
            partido.llave_torneo.save()
            print(f"✅ Sincronizado ganador {partido.ganador.nombre} en llave {partido.llave_torneo.id}")

@login_required
def asignar_arbitro_partido(request, torneo_id, partido_id):
    """Vista para asignar un árbitro a un partido específico"""
    torneo = get_object_or_404(Torneo, id=torneo_id, organizador=request.user)
    partido = get_object_or_404(Partido, id=partido_id, torneo=torneo)
    
    if request.method == 'POST':
        arbitro_id = request.POST.get('arbitro_id')
        
        if arbitro_id:
            try:
                # Verificar que el árbitro esté asignado al torneo
                arbitro_torneo = ArbitroTorneo.objects.get(
                    torneo=torneo,
                    arbitro_id=arbitro_id,
                    activo=True
                )
                
                # Asignar el árbitro al partido
                partido.arbitro = arbitro_torneo.arbitro
                partido.save()
                
                messages.success(request, f"Árbitro {arbitro_torneo.arbitro.first_name} {arbitro_torneo.arbitro.last_name} asignado exitosamente al partido.")
                
            except ArbitroTorneo.DoesNotExist:
                messages.error(request, "El árbitro seleccionado no está asignado a este torneo.")
        else:
            # Remover asignación de árbitro
            partido.arbitro = None
            partido.save()
            messages.success(request, "Asignación de árbitro removida del partido.")
    
    return redirect('iniciar_partidos', torneo_id=torneo.id)

@login_required
def ver_puntaje_vivo(request, torneo_id, partido_id):
    """Vista para mostrar el puntaje en vivo de un partido"""
    torneo = get_object_or_404(Torneo, id=torneo_id)
    partido = get_object_or_404(Partido, id=partido_id, torneo=torneo)
    
    # Verificar que el partido tenga árbitro asignado
    if not partido.arbitro:
        messages.error(request, "Este partido no tiene árbitro asignado.")
        return redirect('iniciar_partidos', torneo_id=torneo.id)
    
    # Verificar permisos (organizador, árbitro del partido, o cualquier usuario autenticado para visualizar)
    puede_ver = (
        request.user == torneo.organizador or 
        request.user == partido.arbitro or
        request.user.is_authenticated  # Permitir a cualquier usuario autenticado ver el puntaje
    )
    
    if not puede_ver:
        messages.error(request, "No tienes permisos para ver este partido.")
        return redirect('iniciar_partidos', torneo_id=torneo.id)
    
    # Determinar si el usuario puede controlar el puntaje (solo árbitro del partido)
    puede_controlar = request.user == partido.arbitro
    
    context = {
        'torneo': torneo,
        'partido': partido,
        'puede_controlar': puede_controlar,
        'es_arbitro': request.user == partido.arbitro,
        'es_organizador': request.user == torneo.organizador,
        'pendiente_confirmacion': partido.pendiente_confirmacion,  # NUEVO
    }
    
    return render(request, 'puntaje_vivo.html', context)

@login_required
@require_POST
def confirmar_resultado_partido(request, torneo_id, partido_id):
    """Vista para que el organizador confirme y cierre un partido"""
    torneo = get_object_or_404(Torneo, id=torneo_id, organizador=request.user)
    partido = get_object_or_404(Partido, id=partido_id, torneo=torneo)
    
    if not partido.pendiente_confirmacion:
        messages.error(request, "Este partido no está pendiente de confirmación.")
        return redirect('iniciar_partidos', torneo_id=torneo.id)
    
    # Confirmar y cerrar el partido
    cerrado, mensaje = partido.confirmar_y_cerrar_partido()
    
    if cerrado:
        messages.success(request, f"¡{mensaje}!")
        
        # Si el torneo es de llaves, intentar avanzar ganadores automáticamente
        if torneo.modalidad == 'llaves':
            avanzado, mensaje_avance = avanzar_ganadores_automaticamente(torneo)
            if avanzado:
                messages.info(request, mensaje_avance)
    else:
        messages.error(request, f"Error: {mensaje}")
    
    return redirect('iniciar_partidos', torneo_id=torneo.id)

@login_required
def verificar_estado_partido_ajax(request, torneo_id, partido_id):
    """Vista AJAX para verificar el estado del partido en tiempo real"""
    try:
        torneo = get_object_or_404(Torneo, id=torneo_id)
        partido = get_object_or_404(Partido, id=partido_id, torneo=torneo)
        
        # Verificar permisos
        puede_ver = (
            request.user == torneo.organizador or 
            request.user == partido.arbitro or
            request.user.is_authenticated
        )
        
        if not puede_ver:
            return JsonResponse({'error': 'Sin permisos'}, status=403)
        
        data = {
            'pendiente_confirmacion': partido.pendiente_confirmacion,
            'estado_partido': partido.estado_partido,
            'es_organizador': request.user == torneo.organizador,
            'es_arbitro': request.user == partido.arbitro,
        }
        
        if partido.pendiente_confirmacion and partido.ganador:
            data['ganador_nombre'] = f"{partido.ganador.nombre} {partido.ganador.apellido}"
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
@login_required
@require_organizador
def corregir_estados_partidos(request, torneo_id):
    """Vista para corregir estados de partidos que están mal configurados"""
    torneo = get_object_or_404(Torneo, id=torneo_id, organizador=request.user)
    
    if request.method == 'POST':
        partidos = Partido.objects.filter(torneo=torneo)
        partidos_corregidos = 0
        
        for partido in partidos:
            # Si tiene ambos jugadores y no es BYE, debería estar "en_curso"
            if (partido.jugador1 and partido.jugador2 and 
                not partido.bye1 and not partido.bye2 and 
                partido.estado_partido == 'pendiente'):
                
                partido.estado_partido = 'en_curso'
                partido.save()
                partidos_corregidos += 1
        
        if partidos_corregidos > 0:
            messages.success(request, f"✅ {partidos_corregidos} partidos corregidos a estado 'en curso'")
        else:
            messages.info(request, "✅ No se encontraron partidos que requieran corrección de estado")
    
    return redirect('iniciar_partidos', torneo_id=torneo.id)

@login_required
@require_organizador
def asignar_arbitros_masivo(request, torneo_id):
    """Vista para asignar árbitros de forma masiva a todos los partidos del torneo"""
    torneo = get_object_or_404(Torneo, id=torneo_id, organizador=request.user)
    
    if request.method == 'POST':
        # Obtener árbitros disponibles
        arbitros_torneo = ArbitroTorneo.objects.filter(torneo=torneo, activo=True)
        
        if not arbitros_torneo.exists():
            messages.error(request, "❌ No hay árbitros asignados a este torneo. Primero asigna árbitros.")
            return redirect('gestionar_torneo', torneo_id=torneo.id)
        
        arbitros_lista = list(arbitros_torneo)
        
        # Obtener partidos sin árbitro que estén en curso o pendientes
        partidos_sin_arbitro = Partido.objects.filter(
            torneo=torneo,
            arbitro__isnull=True,
            estado_partido__in=['en_curso', 'pendiente']
        ).order_by('llave_torneo__ronda', 'llave_torneo__posicion')
        
        if not partidos_sin_arbitro.exists():
            messages.info(request, "✅ Todos los partidos ya tienen árbitros asignados")
            return redirect('iniciar_partidos', torneo_id=torneo.id)
        
        partidos_asignados = 0
        arbitro_index = 0
        
        # Asignar árbitros de forma rotativa
        for partido in partidos_sin_arbitro:
            arbitro_asignado = arbitros_lista[arbitro_index % len(arbitros_lista)]
            partido.arbitro = arbitro_asignado.arbitro
            partido.save()
            partidos_asignados += 1
            arbitro_index += 1
        
        messages.success(request, f"🎉 {partidos_asignados} partidos asignados con árbitros de forma automática")
    
    return redirect('iniciar_partidos', torneo_id=torneo.id)

@login_required
@require_organizador
def corregir_torneo_completo(request, torneo_id):

    """Vista para corregir todos los problemas de un torneo de una vez"""
    torneo = get_object_or_404(Torneo, id=torneo_id, organizador=request.user)
    
    if request.method == 'POST':
        problemas_corregidos = []
        
        # 1. Corregir estados de partidos
        partidos = Partido.objects.filter(torneo=torneo)
        partidos_estado_corregidos = 0
        
        for partido in partidos:
            if (partido.jugador1 and partido.jugador2 and 
                not partido.bye1 and not partido.bye2 and 
                partido.estado_partido == 'pendiente'):
                
                partido.estado_partido = 'en_curso'
                partido.save()
                partidos_estado_corregidos += 1
        
        if partidos_estado_corregidos > 0:
            problemas_corregidos.append(f"Estados corregidos: {partidos_estado_corregidos} partidos")
        
        # 2. Asignar árbitros faltantes
        arbitros_torneo = ArbitroTorneo.objects.filter(torneo=torneo, activo=True)
        
        if arbitros_torneo.exists():
            arbitros_lista = list(arbitros_torneo)
            partidos_sin_arbitro = Partido.objects.filter(
                torneo=torneo,
                arbitro__isnull=True,
                estado_partido__in=['en_curso', 'pendiente']
            )
            
            partidos_arbitros_asignados = 0
            arbitro_index = 0
            
            for partido in partidos_sin_arbitro:
                arbitro_asignado = arbitros_lista[arbitro_index % len(arbitros_lista)]
                partido.arbitro = arbitro_asignado.arbitro
                partido.save()
                partidos_arbitros_asignados += 1
                arbitro_index += 1
            
            if partidos_arbitros_asignados > 0:
                problemas_corregidos.append(f"Árbitros asignados: {partidos_arbitros_asignados} partidos")
        
        # 3. Crear resultados faltantes
        partidos_sin_resultado = []
        for partido in partidos:
            if partido.estado_partido == 'en_curso' and partido.jugador1 and partido.jugador2:
                try:
                    partido.resultado_detallado
                except:
                    from .models import Resultado
                    Resultado.objects.create(partido=partido)
                    partidos_sin_resultado.append(partido)
        
        if partidos_sin_resultado:
            problemas_corregidos.append(f"Resultados creados: {len(partidos_sin_resultado)} partidos")
        
        # Mensaje final
        if problemas_corregidos:
            mensaje = "🎉 Corrección completa del torneo:\n" + "\n".join([f"✅ {problema}" for problema in problemas_corregidos])
            messages.success(request, mensaje)
        else:
            messages.info(request, "✅ El torneo ya está correctamente configurado")
    
    return redirect('iniciar_partidos', torneo_id=torneo.id)

def verificar_torneo_completado(torneo):
    """
    Verifica si los partidos esenciales del torneo están completados (Final y Tercer Lugar)
    El torneo se considera completado cuando:
    1. TODOS los partidos Final (ronda 1) están terminados con ganador
    2. TODOS los partidos de Tercer Lugar están terminados con ganador (si existen)
    """
    
    # 1. Verificar si existen y están terminados TODOS los partidos Final (ronda 1)
    partidos_final = Partido.objects.filter(
        torneo=torneo,
        llave_torneo__ronda=1,
        llave_torneo__tipo_llave='normal'
    )
    
    final_completado = False
    if partidos_final.exists():
        # TODOS los partidos finales deben estar jugados con ganador
        final_completado = all(
            partido.estado_partido == 'jugado' and partido.ganador is not None
            for partido in partidos_final
        )
    else:
        # Si no hay partido final, el torneo no puede estar completado
        return False
    
    # 2. Verificar si existen y están terminados TODOS los partidos de Tercer Lugar
    partidos_tercer_lugar = Partido.objects.filter(
        torneo=torneo,
        llave_torneo__tipo_llave='tercer_lugar'
    )
    
    tercer_lugar_completado = True  # Por defecto True para torneos sin tercer lugar
    if partidos_tercer_lugar.exists():
        # TODOS los partidos de tercer lugar deben estar jugados con ganador
        tercer_lugar_completado = all(
            partido.estado_partido == 'jugado' and partido.ganador is not None
            for partido in partidos_tercer_lugar
        )
    
    # El torneo está completado si tanto Final como Tercer Lugar están terminados
    # (o si no hay partido de tercer lugar en torneos pequeños)
    resultado = final_completado and tercer_lugar_completado
    
    # Debug logging para diagnosticar
    print(f"🏆 Verificación torneo completado '{torneo.nombre}':")
    print(f"   - Partidos Final encontrados: {partidos_final.count()}")
    print(f"   - Final completado: {final_completado}")
    print(f"   - Partidos Tercer Lugar encontrados: {partidos_tercer_lugar.count()}")
    print(f"   - Tercer lugar completado: {tercer_lugar_completado}")
    print(f"   - Resultado final: {resultado}")
    
    return resultado    

def generar_clasificacion_final(torneo):
    """
    Genera la clasificación final del torneo basada en las posiciones alcanzadas
    """
    clasificacion = []
    
    # 1. CAMPEÓN - Ganador de la final (ronda más alta)
    ronda_maxima = LlaveTorneo.objects.filter(
        torneo=torneo, 
        tipo_llave='normal'
    ).aggregate(models.Max('ronda'))['ronda__max']
    
    if ronda_maxima:
        partido_final = Partido.objects.filter(
            torneo=torneo,
            llave_torneo__ronda=ronda_maxima,
            llave_torneo__tipo_llave='normal',
            estado_partido='jugado'
        ).first()
        
        if partido_final and partido_final.ganador:
            clasificacion.append({
                'posicion': 1,
                'jugador': partido_final.ganador,
                'titulo': '🏆 Campeón'
            })
            
            # 2. SUBCAMPEÓN - Perdedor de la final
            perdedor_final = partido_final.jugador1 if partido_final.ganador == partido_final.jugador2 else partido_final.jugador2
            if perdedor_final:
                clasificacion.append({
                    'posicion': 2,
                    'jugador': perdedor_final,
                    'titulo': '🥈 Subcampeón'
                })
    
    # 3. TERCER LUGAR - Ganador del partido de tercer lugar
    partido_tercer_lugar = Partido.objects.filter(
        torneo=torneo,
        llave_torneo__tipo_llave='tercer_lugar',
        estado_partido='jugado'
    ).first()
    
    if partido_tercer_lugar and partido_tercer_lugar.ganador:
        clasificacion.append({
            'posicion': 3,
            'jugador': partido_tercer_lugar.ganador,
            'titulo': '🥉 Tercer Lugar'
        })
        
        # 4. CUARTO LUGAR - Perdedor del partido de tercer lugar
        perdedor_tercer_lugar = (
            partido_tercer_lugar.jugador1 
            if partido_tercer_lugar.ganador == partido_tercer_lugar.jugador2 
            else partido_tercer_lugar.jugador2
        )
        if perdedor_tercer_lugar:
            clasificacion.append({
                'posicion': 4,
                'jugador': perdedor_tercer_lugar,
                'titulo': '4º Lugar'
            })
    
    # 5. SEMIFINALISTAS - Perdedores de semifinales (si no están en tercer lugar)
    if ronda_maxima and ronda_maxima > 1:
        ronda_semifinales = ronda_maxima - 1
        partidos_semifinales = Partido.objects.filter(
            torneo=torneo,
            llave_torneo__ronda=ronda_semifinales,
            llave_torneo__tipo_llave='normal',
            estado_partido='jugado'
        )
        
        posicion_actual = 5
        jugadores_ya_clasificados = [c['jugador'] for c in clasificacion]
        
        for partido in partidos_semifinales:
            if partido.ganador:
                perdedor = (
                    partido.jugador1 
                    if partido.ganador == partido.jugador2 
                    else partido.jugador2
                )
                
                # Solo agregar si no está ya en la clasificación (tercer/cuarto lugar)
                if perdedor and perdedor not in jugadores_ya_clasificados:
                    clasificacion.append({
                        'posicion': posicion_actual,
                        'jugador': perdedor,
                        'titulo': f'{posicion_actual}º Lugar (Semifinalista)'
                    })
                    posicion_actual += 1
    
    # 6. RESTO DE JUGADORES - Por ronda de eliminación
    # Obtener todos los jugadores únicos que participaron en el torneo
    jugadores_en_partidos = set()
    todos_partidos = Partido.objects.filter(torneo=torneo)
    for partido in todos_partidos:
        if partido.jugador1:
            jugadores_en_partidos.add(partido.jugador1)
        if partido.jugador2:
            jugadores_en_partidos.add(partido.jugador2)

    jugadores_ya_clasificados = [c['jugador'] for c in clasificacion]
    
    # Clasificar el resto por ronda de eliminación (ronda más alta alcanzada)
    resto_jugadores = []
    for jugador in jugadores_en_partidos:
        if jugador not in jugadores_ya_clasificados:
            # Encontrar la ronda más alta donde este jugador fue eliminado
            partidos_perdidos = Partido.objects.filter(
                torneo=torneo,
                estado_partido='jugado'
            ).filter(
                models.Q(jugador1=jugador) | models.Q(jugador2=jugador)
            ).exclude(
                ganador=jugador
            ).order_by('-llave_torneo__ronda')
            
            ronda_eliminacion = 1
            if partidos_perdidos.exists():
                ronda_eliminacion = partidos_perdidos.first().llave_torneo.ronda
            
            resto_jugadores.append({
                'jugador': jugador,
                'titulo': f'Eliminado en Ronda {ronda_eliminacion}',
                'ronda_eliminacion': ronda_eliminacion
            })
    
    # Ordenar resto por ronda de eliminación (mayor ronda = mejor posición)
    resto_jugadores.sort(key=lambda x: -x['ronda_eliminacion'])
    
    # Agregar a la clasificación con posiciones consecutivas
    posicion_actual = len(clasificacion) + 1
    for jugador_info in resto_jugadores:
        jugador_info['posicion'] = posicion_actual
        clasificacion.append(jugador_info)
        posicion_actual += 1
    
    return clasificacion
    
@login_required
def resultados_torneo(request, torneo_id):
    """Vista para mostrar la clasificación final del torneo"""
    torneo = get_object_or_404(Torneo, id=torneo_id)
    
    # Generar clasificación (parcial o completa)
    clasificacion_final = generar_clasificacion_final(torneo)
    torneo_completado = verificar_torneo_completado(torneo)
    
    context = {
        'torneo': torneo,
        'clasificacion_final': clasificacion_final,
        'torneo_completado': torneo_completado,
        'es_organizador': request.user == torneo.organizador,
    }
    
    return render(request, 'resultados_torneo.html', context)