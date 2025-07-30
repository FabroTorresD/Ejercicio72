# -*- coding: utf-8 -*-
"""
Simulador discreto – Centro de Salud (Ejercicio 72)
------------------------------------------------------------------
• Paciente → llega con distribución Exponencial(µ = 3 min)
• Mesa de turnos (servidor 1) → Uniforme(1,3 min)
    – Al paciente SIN obra social le informa (0.1667 min = 10 seg) y lo envía a Cooperadora
• Cooperadora (servidor 2) → Uniforme(0.8, 2.4 min)
    – Al terminar vuelve a Mesa de turnos (sin volver a la cola original)
• Llamadas → arriban cada 3 minutos (constante)
    – Duración Uniforme(0.5, 1.5 min)
    – Si la línea está ocupada la llamada se pierde
 
Objetivos
---------
a) Cantidad de llamadas perdidas
b) Tiempo promedio de espera en cola de pacientes (todas las veces que esperan en Mesa de turnos)
"""

import streamlit as st
import pandas as pd
import random
import math
from itertools import count

# -----------------------------------------------------------
# 1) Parámetros de entrada – Streamlit sidebar
# -----------------------------------------------------------
st.title("Centro de Salud – Simulación (Ej. 72)")

st.sidebar.markdown("**Parámetros básicos**")
media_llegada      = st.sidebar.number_input("Media entre llegadas de pacientes (min)", 0.5, 30.0, 3.0)
a1, b1             = st.sidebar.slider("Atención mesa de turnos (min)", 0.5, 10.0, (1.0, 3.0))
p_sin_obra         = st.sidebar.slider("Proporción SIN obra social", 0.0, 1.0, 0.55, 0.05)  # Corregido: 55% sin obra
tiempo_informe     = st.sidebar.number_input("Tiempo informe obra social (min)", 0.1, 1.0, 0.1667)
a2, b2             = st.sidebar.slider("Abono cooperadora (min)", 0.1, 10.0, (0.8, 2.4))

st.sidebar.markdown("**Llamadas telefónicas**")
t_llamada          = st.sidebar.number_input("Intervalo entre llamadas (min, fijo)", 0.5, 10.0, 3.0)
c1, c2             = st.sidebar.slider("Duración de llamada (min)", 0.1, 5.0, (0.5, 1.5))

st.sidebar.markdown("**Escenario e inicialización**")
ini_pacientes_mesa = st.sidebar.number_input("Pacientes en cola de mesa (t = 0)", 0, 20, 4)
ini_pacientes_coop = st.sidebar.number_input("Pacientes esperando pago (t = 0)", 0, 20, 2)
ini_t_llamada      = st.sidebar.number_input("Faltan (min) para la próxima llamada", 0.0, t_llamada, 2.0)

tiempo_simulacion  = st.sidebar.number_input("Tiempo a simular (min)", 10, 2880, 480)

# -----------------------------------------------------------
# 2) Auxiliares de generación
# -----------------------------------------------------------

def gen_exponencial(media: float) -> tuple[float, float]:
    rnd = random.random()
    valor = -media * math.log(1 - rnd)
    return rnd, valor

def gen_uniforme(a: float, b: float) -> tuple[float, float]:
    rnd = random.random()
    valor = a + rnd * (b - a)
    return rnd, valor

# -----------------------------------------------------------
# 3) Clase para pacientes
# -----------------------------------------------------------
class Paciente:
    def __init__(self, id_pac, tiene_obra_social, tiempo_llegada):
        self.id = id_pac
        self.tiene_obra_social = tiene_obra_social
        self.tiempo_llegada = tiempo_llegada
        self.tiempo_inicio_espera = None
        self.veces_esperado = 0

# -----------------------------------------------------------
# 4) Simulación mejorada
# -----------------------------------------------------------

def simular_dia(media_llegada: float, a1: float, b1: float, a2: float, b2: float,
                p_sin_obra: float, tiempo_informe: float, t_llamada: float, c1: float, c2: float,
                ini_mesa: int, ini_coop: int, falta_llamada: float, t_limite: float):
    """Devuelve df, tiempo_promedio_espera, llamadas_perdidas, objetos_df"""

    # ── Variables reloj y eventos ────────────────────────────
    reloj: float = 0.0

    # Generar primera llegada de paciente
    rnd_llegada, tiempo_entre = gen_exponencial(media_llegada)
    prox_llegada_pac: float = tiempo_entre

    # Programar primera llamada
    prox_llamada: float = falta_llamada
    fin_llamada: float = math.inf

    # Eventos de atención
    fin_atencion: float = math.inf
    fin_pago: float = math.inf

    # ── Colas & servidores ──────────────────────────────────
    cola_mesa: list[Paciente] = []
    cola_retorno: list[Paciente] = []  # pacientes que vuelven tras pagar
    cola_pago: list[Paciente] = []

    # Inicializar pacientes en cola de mesa
    for i in range(ini_mesa):
        pac = Paciente(f"P{i+1}", random.random() >= p_sin_obra, 0.0)
        pac.tiempo_inicio_espera = 0.0
        cola_mesa.append(pac)

    # Inicializar pacientes en cola de pago
    for i in range(ini_coop):
        pac = Paciente(f"C{i+1}", False, 0.0)  # Sin obra social
        cola_pago.append(pac)

    # Estados de servidores
    mesa_ocupada: bool = False
    coop_ocupada: bool = len(cola_pago) > 0
    linea_ocupada: bool = False

    # Si hay pacientes esperando pago, iniciar el servicio
    if coop_ocupada:
        rnd_pago, tiempo_pago = gen_uniforme(a2, b2)
        fin_pago = tiempo_pago

    # Variables estadísticas
    llamadas_perdidas = 0
    espera_total = 0.0
    cnt_esperas = 0
    
    # Paciente actualmente siendo atendido
    paciente_en_atencion = None
    paciente_en_pago = None
    if cola_pago:
        paciente_en_pago = cola_pago.pop(0)

    # Listas para almacenar datos
    filas = []
    objetos_temporales = []
    next_id = count(start=max(ini_mesa, ini_coop) + 10)

    def registrar(evento: str, extra: dict = None):
        """Crea una fila con la información del vector estado con MultiIndex mejorado."""
        
        # Calcular próximos eventos (sin infinitos)
        prox_llegada_str = f"{prox_llegada_pac:.3f}" if prox_llegada_pac != math.inf else ""
        prox_llamada_str = f"{prox_llamada:.3f}" if prox_llamada != math.inf else ""
        fin_llamada_str = f"{fin_llamada:.3f}" if fin_llamada != math.inf else ""
        fin_atencion_str = f"{fin_atencion:.3f}" if fin_atencion != math.inf else ""
        fin_pago_str = f"{fin_pago:.3f}" if fin_pago != math.inf else ""
        
        # Estados de servidores
        estado_mesa = "Ocupado" if mesa_ocupada else "Libre"
        estado_coop = "Ocupado" if coop_ocupada else "Libre"
        estado_linea = "Ocupado" if linea_ocupada else "Libre"
        
        # Colas
        cola_mesa_ids = [p.id for p in cola_mesa]
        cola_pago_ids = [p.id for p in cola_pago]
        
        # Preparar objetos temporales
        objetos_temp = {}
        obj_num = 1
        
        # Pacientes en cola mesa
        for pac in cola_mesa:
            if obj_num <= 4:
                objetos_temp[obj_num] = {
                    "Estado": "En cola mesa",
                    "Hora_inicio_espera": f"{pac.tiempo_inicio_espera:.3f}" if pac.tiempo_inicio_espera is not None else ""
                }
                obj_num += 1
        
        # Paciente en atención
        if paciente_en_atencion and obj_num <= 4:
            objetos_temp[obj_num] = {
                "Estado": "En atención mesa",
                "Hora_inicio_espera": ""
            }
            obj_num += 1
        
        # Pacientes en cola cooperadora
        for pac in cola_pago:
            if obj_num <= 4:
                objetos_temp[obj_num] = {
                    "Estado": "En cola cooperadora",
                    "Hora_inicio_espera": ""
                }
                obj_num += 1
        
        # Paciente en pago
        if paciente_en_pago and obj_num <= 4:
            objetos_temp[obj_num] = {
                "Estado": "En pago cooperadora",
                "Hora_inicio_espera": ""
            }
            obj_num += 1
        
        # Pacientes en cola retorno
        for pac in cola_retorno:
            if obj_num <= 4:
                objetos_temp[obj_num] = {
                    "Estado": "Esperando retorno",
                    "Hora_inicio_espera": ""
                }
                obj_num += 1
        
        # Completar con objetos vacíos hasta 4
        for i in range(obj_num, 5):
            objetos_temp[i] = {
                "Estado": "",
                "Hora_inicio_espera": ""
            }

        # ESTRUCTURA CON MULTIINDEX MEJORADO
        row = {
            # Columnas simples
            "Evento": evento,
            "Reloj": round(reloj, 3),
            "RND_llegada_paciente": extra.get("rnd_llegada", "") if extra else "",
            "Tiempo_entre_llegadas": extra.get("tiempo_entre", "") if extra else "",
            "Proxima_llegada": prox_llegada_str,
            "RND_obra_social": extra.get("rnd_obra_social", "") if extra else "",
            "Obra_Social": extra.get("obra_social", "") if extra else "",
            "fin_atencion": fin_atencion_str,
            "fin_informe_obra_social": "",  # Constante 0.1667
            "RND_abono_consulta": extra.get("rnd_pago", "") if extra else "",
            "Tiempo_de_abono_consulta": extra.get("tiempo_pago", "") if extra else "",
            "fin_abono_consulta": fin_pago_str,
            "Proxima_llegada_llamada": prox_llamada_str,
            "RND_llamada": extra.get("rnd_llamada", "") if extra else "",
            "Tiempo_de_llamada": extra.get("tiempo_llamada", "") if extra else "",
            "fin_llamada": fin_llamada_str,
            
            # Servidores (MultiIndex nivel 2)
            ("Mesa de Turnos", "Estado"): estado_mesa,
            ("Mesa de Turnos", "Cola"): str(cola_mesa_ids) if cola_mesa_ids else "",
            ("Cooperadora", "Estado"): estado_coop,
            ("Cooperadora", "Cola"): str(cola_pago_ids) if cola_pago_ids else "",
            ("Línea Telefónica", "Estado"): estado_linea,
            ("Línea Telefónica", "Cola"): "",
            
            # Estadísticas
            "Llamadas_perdidas": llamadas_perdidas,
            "Acum_tiempo_espera": round(espera_total, 3),
            "Cantidad_personas_esperaron": cnt_esperas,
            
            # Objetos temporales (MultiIndex nivel 3)
            ("Paciente 1", "Estado"): objetos_temp[1]["Estado"],
            ("Paciente 1", "Hora Inicio Espera"): objetos_temp[1]["Hora_inicio_espera"],
            ("Paciente 2", "Estado"): objetos_temp[2]["Estado"],
            ("Paciente 2", "Hora Inicio Espera"): objetos_temp[2]["Hora_inicio_espera"],
            ("Paciente 3", "Estado"): objetos_temp[3]["Estado"],
            ("Paciente 3", "Hora Inicio Espera"): objetos_temp[3]["Hora_inicio_espera"],
            ("Paciente 4", "Estado"): objetos_temp[4]["Estado"],
            ("Paciente 4", "Hora Inicio Espera"): objetos_temp[4]["Hora_inicio_espera"]
        }
        
        filas.append(row)

    # Registrar estado inicial
    registrar("Inicializacion")

    # ── Motor de eventos discretos ──────────────────────────
    while reloj < t_limite:
        
        # Encontrar próximo evento
        eventos = [
            ("llegada_paciente", prox_llegada_pac),
            ("llegada_llamada", prox_llamada),
            ("fin_atencion", fin_atencion),
            ("fin_pago", fin_pago),
            ("fin_llamada", fin_llamada),
        ]
        
        evento, momento = min(eventos, key=lambda x: x[1])
        
        if momento == math.inf:
            break  # No hay más eventos
        
        # Avanzar reloj
        reloj = momento
        
        # Procesar evento
        if evento == "llegada_paciente":
            # Generar próxima llegada
            rnd_llegada, tiempo_entre = gen_exponencial(media_llegada)
            prox_llegada_pac = reloj + tiempo_entre
            
            # Determinar si tiene obra social
            rnd_os = random.random()
            tiene_obra = rnd_os >= p_sin_obra  # 55% SIN obra social
            
            # Crear paciente
            pid = f"P{next(next_id)}"
            nuevo_paciente = Paciente(pid, tiene_obra, reloj)
            nuevo_paciente.tiempo_inicio_espera = reloj
            cola_mesa.append(nuevo_paciente)
            
            extra = {
                "rnd_llegada": round(rnd_llegada, 3),
                "tiempo_entre": round(tiempo_entre, 3),
                "rnd_obra_social": round(rnd_os, 3),
                "obra_social": "Si" if tiene_obra else "No"
            }
            registrar("llegada_paciente", extra)
            
        elif evento == "llegada_llamada":
            # Programar próxima llamada
            prox_llamada = reloj + t_llamada
            
            # Verificar si la línea está disponible
            if mesa_ocupada or linea_ocupada:
                llamadas_perdidas += 1
                registrar("llamada_perdida")
            else:
                # Iniciar llamada
                rnd_call, dur_call = gen_uniforme(c1, c2)
                fin_llamada = reloj + dur_call
                linea_ocupada = True
                mesa_ocupada = True  # La mesa también se ocupa por la llamada
                
                extra = {
                    "rnd_llamada": round(rnd_call, 3),
                    "tiempo_llamada": round(dur_call, 3)
                }
                registrar("inicio_llamada", extra)
                
        elif evento == "fin_llamada":
            linea_ocupada = False
            mesa_ocupada = False
            fin_llamada = math.inf
            registrar("fin_llamada")
            
        elif evento == "fin_atencion":
            mesa_ocupada = False
            fin_atencion = math.inf
            
            # El paciente actual termina su atención
            if paciente_en_atencion:
                if not paciente_en_atencion.tiene_obra_social:
                    # Enviar a cooperadora
                    cola_pago.append(paciente_en_atencion)
                # Si tiene obra social, sale del sistema
                paciente_en_atencion = None
                
            registrar("fin_atencion")
            
        elif evento == "fin_pago":
            coop_ocupada = False
            fin_pago = math.inf
            
            # El paciente vuelve a mesa de turnos sin hacer cola
            if paciente_en_pago:
                cola_retorno.append(paciente_en_pago)
                paciente_en_pago = None
                
            registrar("fin_pago")
        
        # ── Despachar nuevos servicios ──────────────────────────
        
        # Atender en mesa de turnos (prioridad: retorno > cola normal)
        if not mesa_ocupada and not linea_ocupada:
            paciente_a_atender = None
            rnd_att = 0
            t_att = 0
            
            if cola_retorno:
                paciente_a_atender = cola_retorno.pop(0)
                # Los pacientes de retorno no esperan (ya esperaron antes)
            elif cola_mesa:
                paciente_a_atender = cola_mesa.pop(0)
                # Calcular tiempo de espera
                tiempo_espera = reloj - paciente_a_atender.tiempo_inicio_espera
                espera_total += tiempo_espera
                cnt_esperas += 1
                paciente_a_atender.veces_esperado += 1
            
            if paciente_a_atender:
                mesa_ocupada = True
                paciente_en_atencion = paciente_a_atender
                
                if paciente_a_atender.tiene_obra_social:
                    # Atención normal
                    rnd_att, t_att = gen_uniforme(a1, b1)
                    fin_atencion = reloj + t_att
                else:
                    # Solo informar (10 segundos)
                    fin_atencion = reloj + tiempo_informe
                    t_att = tiempo_informe
                    
                extra = {
                    "rnd_atencion": round(rnd_att, 3),
                    "tiempo_atencion": round(t_att, 3)
                }
                registrar("inicio_atencion", extra)
        
        # Atender en cooperadora
        if not coop_ocupada and cola_pago:
            paciente_en_pago = cola_pago.pop(0)
            coop_ocupada = True
            
            rnd_pago, t_pago = gen_uniforme(a2, b2)
            fin_pago = reloj + t_pago
            
            extra = {
                "rnd_pago": round(rnd_pago, 3),
                "tiempo_pago": round(t_pago, 3)
            }
            registrar("inicio_pago", extra)

    # ── Fin simulación ──
    df = pd.DataFrame(filas)
    
    # Crear MultiIndex mejorado
    # Separar columnas por tipo
    columnas_simples = []
    columnas_servidores = []
    columnas_pacientes = []
    
    for col in df.columns:
        if isinstance(col, tuple):
            if col[0] in ["Mesa de Turnos", "Cooperadora", "Línea Telefónica"]:
                columnas_servidores.append(col)
            elif col[0].startswith("Paciente"):
                columnas_pacientes.append(col)
        else:
            columnas_simples.append(col)
    
    # Reordenar columnas: simples + servidores + pacientes
    columnas_ordenadas = columnas_simples + columnas_servidores + columnas_pacientes
    df = df[columnas_ordenadas]
    
    # Crear multiíndice
    nuevas_columnas = []
    for col in df.columns:
        if isinstance(col, tuple):
            if col[0] in ["Mesa de Turnos", "Cooperadora", "Línea Telefónica"]:
                # Servidores: ("Servidores", "Mesa de Turnos", "Estado")
                nuevas_columnas.append(("Servidores", col[0], col[1]))
            elif col[0].startswith("Paciente"):
                # Pacientes: ("Pacientes", "Paciente 1", "Estado")
                nuevas_columnas.append(("Pacientes", col[0], col[1]))
        else:
            # Columnas simples: ("Variables", "", "Evento")
            nuevas_columnas.append(("Variables", "", col))
    
    # Aplicar multiíndice
    df.columns = pd.MultiIndex.from_tuples(nuevas_columnas)
    
    prom_espera = espera_total / cnt_esperas if cnt_esperas else 0.0

    return df, prom_espera, llamadas_perdidas

# -----------------------------------------------------------
# 5) Ejecución interactiva
# -----------------------------------------------------------
if st.sidebar.button("Iniciar simulación"):
    resultado_df, prom_espera, perdidas = simular_dia(
        media_llegada, a1, b1, a2, b2, p_sin_obra, tiempo_informe,
        t_llamada, c1, c2, ini_pacientes_mesa, ini_pacientes_coop,
        ini_t_llamada, tiempo_simulacion,
    )

    st.subheader("Vector de Estado - Simulación Centro de Salud")
    st.dataframe(resultado_df, use_container_width=True, height=500)

    st.subheader("Estadísticas Finales")
    col1, col2 = st.columns(2)
    col1.metric("a) Llamadas perdidas", perdidas)
    col2.metric("b) Tiempo promedio espera en cola (min)", f"{prom_espera:.3f}")