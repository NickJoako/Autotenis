import random
import pandas as pd
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
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
from .models import GrupoTorneo, ParticipanteGrupo

# Create your views here.

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
            return render(request, 'home_arbitro.html')
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

@login_required
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

@login_required
def lista_torneos(request):
    torneos = Torneo.objects.filter(organizador=request.user)
    return render(request, 'lista_torneos.html', {'torneos': torneos})

@login_required
def lista_clubes(request):
    clubes = Club.objects.all()
    return render(request, 'lista_clubes.html', {'clubes': clubes})

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
    query = request.GET.get('q', '')
    if query:
        jugadores = Jugador.objects.filter(rut__icontains=query)
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

@login_required
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
                    errores.append(f"Fila {i+2}: Correo ya existe en la base de datos ({correo})")
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

@login_required
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

@login_required
def gestionar_torneo(request, torneo_id):
    torneo = Torneo.objects.get(id=torneo_id, organizador=request.user)
    return render(request, 'gestionar_torneo.html', {'torneo': torneo})

@login_required
def gestionar_torneo_federado(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id, organizador=request.user)
    return render(request, 'gestionar_torneo_federado.html', {'torneo': torneo})

@login_required
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
                    errores.append(f"Fila {i+2}: RUT inválido ({rut})")
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

@login_required
def listado_participantes(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id, organizador=request.user)
    participantes = [p.jugador for p in torneo.participaciones.select_related('jugador')]
    
    # Manejar el cerrar inscripciones
    if request.method == "POST" and "cerrar_inscripciones" in request.POST and not torneo.inscripciones_cerradas:
        torneo.inscripciones_cerradas = True
        torneo.save()
        messages.success(request, "Las inscripciones han sido cerradas. Ya no se pueden agregar o eliminar participantes.")
        return redirect('listado_participantes', torneo_id=torneo.id)
    
    return render(request, "listado_participantes.html", {"torneo": torneo, "participantes": participantes})

@login_required
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

@login_required
def modalidad_llaves(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id, organizador=request.user)
    
    if not torneo.inscripciones_cerradas:
        messages.error(request, "Debes cerrar las inscripciones antes de seleccionar una modalidad.")
        return redirect('gestionar_torneo', torneo_id=torneo.id)
    
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

@login_required
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

@login_required
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
                    
                    # Agregar posiciones disponibles (que no estén ocupadas por cabezas de serie)
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

@login_required
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
            import random
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
            for i, cabeza in enumerate(cabezas_serie_ordenadas):
                ParticipanteGrupo.objects.create(
                    grupo=grupos_creados[i],
                    jugador=cabeza.jugador,
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
                            es_cabeza_serie=True  # También marcar como cabeza de serie
                        )
            
            # Ahora distribuir el resto de participantes usando serpenteo
            participante_idx = 0
            
            # Crear lista de posiciones disponibles para serpenteo
            posiciones_serpenteo = []
            max_participantes = 4
            num_cabezas_serie = len(cabezas_serie_ordenadas)
            num_segunda_linea = len(segunda_linea_ordenadas)
            
            # Llenar posiciones disponibles considerando cabezas de serie ya asignadas
            for posicion in range(1, max_participantes + 1):
                grupos_disponibles = list(range(total_grupos))
                
                # Aplicar patrón serpenteo según la posición
                if (posicion - 1) % 2 == 1:  # Posiciones 2, 4, 6... (reverso)
                    orden_grupos = list(reversed(grupos_disponibles))
                else:  # Posiciones 1, 3, 5... (normal)
                    orden_grupos = grupos_disponibles
                
                # Agregar posiciones disponibles (que no estén ocupadas por cabezas de serie)
                for grupo_idx in orden_grupos:
                    # Verificar si la posición está disponible
                    posicion_ocupada = False
                    
                    # Posición 1 ocupada por cabezas de serie de primera línea
                    if posicion == 1 and grupo_idx < num_cabezas_serie:
                        posicion_ocupada = True
                    
                    # Posición 2 ocupada por cabezas de serie de segunda línea
                    if posicion == 2 and num_segunda_linea > 0:
                        # Verificar si este grupo tiene segunda línea asignada
                        # La segunda línea se asigna desde el último grupo hacia atrás
                        if grupo_idx >= (total_grupos - num_segunda_linea):
                            posicion_ocupada = True
                    
                    if not posicion_ocupada:
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
            
            num_cabezas = len(cabezas_serie_ordenadas)
            num_segunda = len(segunda_linea_ordenadas)
            mensaje = f"¡Grupos asignados con {num_cabezas} cabeza{'s' if num_cabezas != 1 else ''} de serie"
            if num_segunda > 0:
                mensaje += f" y {num_segunda} de segunda línea"
            mensaje += "! Los grupos restantes se llenaron automáticamente."
            
            messages.success(request, mensaje)
            return redirect('organizar_grupos', torneo_id=torneo.id)
    
    context = {
        'torneo': torneo,
        'participantes': participantes,
        'num_participantes': num_participantes,
        'total_grupos': total_grupos,
    }
    
    return render(request, 'definir_cabezas_serie.html', context)

@login_required
def vista_previa_asignacion(request, torneo_id):
    """
    Vista que devuelve el proceso paso a paso de cómo se asignaron los grupos REALMENTE
    """
    torneo = get_object_or_404(Torneo, id=torneo_id, organizador=request.user)
    
    # Obtener grupos existentes ordenados correctamente
    grupos_existentes = GrupoTorneo.objects.filter(torneo=torneo).prefetch_related('participantes__jugador').order_by('numero')
    
    if not grupos_existentes.exists():
        return JsonResponse({'error': 'No hay grupos asignados para mostrar'}, status=400)
    
    # Obtener participantes originales en orden de inscripción
    participantes_originales = list(torneo.participaciones.select_related('jugador').order_by('id'))
    
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
    
    # Verificar si hay cabezas de serie
    tiene_cabezas_serie = grupos_existentes.filter(participantes__es_cabeza_serie=True).exists()
    
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
        num_cabezas_primera_linea = len(cabezas_serie_primera_linea)
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
        max_participantes = max(grupo.participantes.count() for grupo in grupos_existentes)
        num_grupos = len(grupos_existentes)
        
        # Crear la misma lista de posiciones serpenteo que se usó en la asignación real
        posiciones_serpenteo_reales = []
        
        # Determinar cuántos grupos de 4 hay (aproximación basada en distribución)
        total_participantes = sum(grupo.participantes.count() for grupo in grupos_existentes)
        grupos_de_4_aprox = 0
        grupos_de_3_aprox = 0
        
        if total_participantes % 3 == 0:
            grupos_de_3_aprox = total_participantes // 3
        elif total_participantes % 3 == 1:
            if total_participantes >= 4:
                grupos_de_4_aprox = 1
                grupos_de_3_aprox = (total_participantes - 4) // 3
        elif total_participantes % 3 == 2:
            if total_participantes >= 8:
                grupos_de_4_aprox = 2
                grupos_de_3_aprox = (total_participantes - 8) // 3
            else:
                grupos_de_4_aprox = 0
                grupos_de_3_aprox = total_participantes // 3
        
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
                    posiciones_serpenteo_reales.append((grupo_idx, posicion))
        
        # Reconstruir el orden de los participantes siguiendo las posiciones serpenteo
        for grupo_idx, posicion in posiciones_serpenteo_reales:
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
                    if i < len(posiciones_serpenteo_reales) and participante_idx < len(participantes_orden_real):
                        jugador = participantes_orden_real[participante_idx]
                        grupo_destino, posicion = posiciones_serpenteo_reales[i]
                        
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
                    if ultimo_i < len(posiciones_serpenteo_reales):
                        ultimo_grupo, ultimo_posicion = posiciones_serpenteo_reales[ultimo_i]
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


def calcular_grupo_serpenteo(posicion, num_grupos):
    """
    Calcula el grupo destino para una posición dada en el serpenteo
    Posición 1: Grupo 0, Posición 2: Grupo 1, ..., luego serpentea
    """
    if posicion <= num_grupos:
        return posicion - 1
    
    # Calcular en qué "ronda" estamos
    ronda = (posicion - 1) // num_grupos
    posicion_en_ronda = (posicion - 1) % num_grupos
    
    if ronda % 2 == 0:  # Rondas pares: izquierda a derecha
        return posicion_en_ronda
    else:  # Rondas impares: derecha a izquierda
        return num_grupos - 1 - posicion_en_ronda


def calcular_grupo_serpenteo_con_cabezas(posicion, num_grupos):
    """
    Calcula el grupo destino para una posición dada en el serpenteo CON cabezas de serie
    PATRÓN CORRECTO:
    - Ronda 1 (posición 1): A→B→C→D→E (cabezas de serie)
    - Ronda 2 (posición 2): E→D→C→B→A (reverso)
    - Ronda 3 (posición 3): A→B→C→D→E (normal)
    - Ronda 4 (posición 4): E→D→C→B→A (reverso)
    """
    ronda = posicion  # La posición ES la ronda
    
    # Calcular la posición dentro de la ronda (0-indexado)
    # Para ronda 2: posiciones 6,7,8,9,10 → índices 0,1,2,3,4
    # Para ronda 3: posiciones 11,12,13,14,15 → índices 0,1,2,3,4
    
    if (ronda - 1) % 2 == 1:  # Rondas 2, 4, 6... (reverso)
        # E→D→C→B→A
        return num_grupos - 1 - 0  # Siempre empezar desde el último grupo y retroceder
    else:  # Rondas 1, 3, 5... (normal)
        # A→B→C→D→E  
        return 0  # Siempre empezar desde el primer grupo
    
    # Nota: Esta función necesita ser refactorizada porque no maneja correctamente
    # el índice dentro de la ronda. Mejor usar la lógica directa en la vista previa.

@login_required
def vista_previa_asignacion_pagina(request, torneo_id):
    """
    Vista que muestra la página completa de vista previa de asignación
    """
    torneo = get_object_or_404(Torneo, id=torneo_id, organizador=request.user)
    
    # Verificar que el torneo esté en modalidad grupos
    if torneo.modalidad != 'grupos' or not torneo.torneo_iniciado:
        messages.error(request, "El torneo no está en modalidad de grupos o no ha sido iniciado.")
        return redirect('gestionar_torneo', torneo_id=torneo.id)
    
    # Obtener grupos existentes
    grupos_existentes = GrupoTorneo.objects.filter(torneo=torneo).prefetch_related('participantes__jugador').order_by('numero')
    
    if not grupos_existentes.exists():
        messages.error(request, "No hay grupos asignados para mostrar la vista previa.")
        return redirect('organizar_grupos', torneo_id=torneo.id)
    
    # Obtener participantes
    participantes = list(torneo.participaciones.select_related('jugador').all())
    
    # Verificar si hay cabezas de serie
    tiene_cabezas_serie = grupos_existentes.filter(participantes__es_cabeza_serie=True).exists()
    
    context = {
        'torneo': torneo,
        'grupos_existentes': grupos_existentes,
        'participantes': participantes,
        'tiene_cabezas_serie': tiene_cabezas_serie,
        'num_participantes': len(participantes),
        'total_grupos': grupos_existentes.count(),
    }
    
    return render(request, 'vista_previa_asignacion.html', context)

