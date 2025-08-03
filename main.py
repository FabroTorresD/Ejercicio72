# -*- coding: utf-8 -*-
"""
Simulador discreto – Centro de Salud (Ejercicio 72) - VERSIÓN MEJORADA
------------------------------------------------------------------
• Paciente → llega con distribución Exponencial(µ = 3 min)
• Mesa de turnos (servidor 1) → Uniforme(1,3 min)
    – Al paciente SIN obra social le informa (0.1667 min = 10 seg) y lo envía a Cooperadora
• Cooperadora (servidor 2) → Uniforme(0.8, 2.4 min)
    – Al terminar vuelve a Mesa de turnos (sin volver a la cola original)
• Llamadas → arriban cada 3 minutos (constante)
    – Duración Uniforme(0.5, 1.5 min)
    – Si la línea está ocupada la llamada se pierde

Lógica de Atención:
- Con obra social: t ~ U(1,3 min) → abandona el sistema
- Sin obra social (1ª vez): 10 seg → va a Cooperadora  
- Sin obra social (retorno): t ~ U(1,3 min) → abandona el sistema

Objetivos
---------
a) Cantidad de llamadas perdidas  
b) Tiempo promedio de espera en cola  

"""

import random
from itertools import count
import streamlit as st
import pandas as pd
import numpy as np

# -----------------------------------------------------------
# 1) Generadores de números aleatorios
# -----------------------------------------------------------

def gen_exponencial(media: float) -> tuple[float, float]:
    u = random.random()
    intervalo = -media * np.log(1 - u)
    return u, intervalo

def gen_uniforme(a: float, b: float) -> tuple[float, float]:
    u = random.random()
    valor = a + (b - a) * u
    return u, valor

# -----------------------------------------------------------
# 2) Definición de la clase Paciente
# -----------------------------------------------------------

class Paciente:
    def __init__(self, id: str, tiene_obra_social: bool, t_llegada: float):
        self.id = id
        self.tiene_obra_social = tiene_obra_social
        self.tiempo_inicio_espera = t_llegada
        self.primera_vez = True  # para identificar si ya pasó por cooperadora

# -----------------------------------------------------------
# 4) Simulación
# -----------------------------------------------------------

def simular_dia(media_llegada: float, a1: float, b1: float, a2: float, b2: float,
                p_sin_obra: float, tiempo_informe: float, t_llamada: float, c1: float, c2: float,
                ini_mesa: int, ini_coop: int, falta_llamada: float, t_limite: float):
    """Devuelve df, tiempo_promedio_espera, llamadas_perdidas"""

    # ── Variables reloj y eventos ────────────────────────────
    reloj: float = 0.0

    # Generar primera llegada de paciente
    rnd_llegada, tiempo_entre = gen_exponencial(media_llegada)
    prox_llegada_pac: float = tiempo_entre

    # Programar primera llamada
    prox_llamada: float = falta_llamada
    fin_llamada: float = float('inf')

    # Eventos de atención - SEPARADOS PARA MAYOR CLARIDAD
    fin_atencion_completa: float = float('inf')  # Para pacientes con obra social o retorno
    fin_informe_obra_social: float = float('inf')  # Para informar a pacientes sin obra social
    fin_pago: float = float('inf')

    # ── Variables para rastrear la atención en mesa ──
    rnd_att_actual: float | None = None
    t_att_actual: float | None = None
    tipo_atencion_actual: str = ""  # "completa", "informe"

    # ── Colas & servidores ──────────────────────────────────
    cola_mesa: list[Paciente] = []
    cola_retorno: list[Paciente] = []  # Pacientes que vuelven de cooperadora
    cola_pago: list[Paciente] = []

    # Inicializar con pacientes en cola de mesa
    for i in range(ini_mesa):
        pac = Paciente(f"P{i+1}", random.random() >= p_sin_obra, 0.0)
        pac.tiempo_inicio_espera = 0.0
        cola_mesa.append(pac)

    # Inicializar con pacientes en cooperadora (pagan)
    for i in range(ini_coop):
        pac = Paciente(f"CP{i+1}", False, 0.0)
        pac.primera_vez = False
        cola_pago.append(pac)

    mesa_ocupada: bool = False
    coop_ocupada: bool = False
    linea_ocupada: bool = False

    # Si hay alguien en cooperadora al inicio, arranca el servicio
    paciente_en_pago = None
    if cola_pago:
        coop_ocupada = True
        paciente_en_pago = cola_pago.pop(0)
        rnd_pago, tiempo_pago = gen_uniforme(a2, b2)
        fin_pago = tiempo_pago

    llamadas_perdidas = 0
    espera_total = 0.0
    cnt_esperas = 0
    pacientes_atendidos = 0

    paciente_en_atencion = None
    next_id = count(start=100)
    filas = []

    def formatear_valor(valor):
        if valor in (float('inf'), float('-inf')):
            return ""
        return f"{valor:.3f}" if isinstance(valor, (int, float)) else str(valor)

    def registrar(evento: str, extra: dict = None):
        # Construcción de la fila
        objetos_temporales = []
        for pac in cola_mesa:
            objetos_temporales.append({'id': pac.id, 'estado': 'En cola mesa', 'hora_inicio': pac.tiempo_inicio_espera})
        for pac in cola_retorno:
            objetos_temporales.append({'id': pac.id, 'estado': 'Esperando retorno (prioridad)', 'hora_inicio': None})
        for pac in cola_pago:
            objetos_temporales.append({'id': pac.id, 'estado': 'En cola cooperadora', 'hora_inicio': None})

        row_data = {
            'Evento': evento,
            'Reloj': formatear_valor(reloj),
            'RND_llegada_paciente': formatear_valor(extra.get('rnd_llegada', '')) if extra else '',
            'Tiempo_entre_llegadas': formatear_valor(extra.get('tiempo_entre', '')) if extra else '',
            'Proxima_llegada': formatear_valor(prox_llegada_pac),
            'RND_obra_social': formatear_valor(extra.get('rnd_obra_social', '')) if extra else '',
            'Obra_Social': extra.get('obra_social', '') if extra else '',
            # ── COLUMNAS DE ATENCIÓN MEJORADAS ──
            'RND_tiempo_atencion': formatear_valor(extra.get('rnd_tiempo_atencion', '')) if extra else '',
            'Tiempo_de_atencion': formatear_valor(extra.get('tiempo_atencion', '')) if extra else '',
            'Tipo_atencion': extra.get('tipo_atencion', '') if extra else '',
            'fin_atencion_completa': formatear_valor(fin_atencion_completa),
            'fin_informe_obra_social': formatear_valor(fin_informe_obra_social),
            'Destino_paciente': extra.get('destino_paciente', '') if extra else '',
            # ── COLUMNAS EXISTENTES ──────────────────────────────
            'fin_abono_consulta': formatear_valor(fin_pago),
            'Proxima_llegada_llamada': formatear_valor(prox_llamada),
            'fin_llamada': formatear_valor(fin_llamada),
            'RND_abono_consulta': formatear_valor(extra.get('rnd_pago', '')) if extra else '',
            'Tiempo_de_abono_de_consulta': formatear_valor(extra.get('tiempo_pago', '')) if extra else '',
            'RND_llamada': formatear_valor(extra.get('rnd_llamada', '')) if extra else '',
            'Tiempo_de_llamada': formatear_valor(extra.get('tiempo_llamada', '')) if extra else '',
            # Servidores
            ('Empleado mesa de turno','Estado'): 'Ocupado' if mesa_ocupada else 'Libre',
            ('Cooperadora','Estado'): 'Ocupado' if coop_ocupada else 'Libre',
            ('Línea telefónica','Estado'): 'Ocupada' if linea_ocupada else 'Libre',
        }

        # Estadísticas
        row_data['Cantidad_de_llamadas_perdidas_por_tener_la_linea_ocupada'] = llamadas_perdidas
        row_data['Acum_tiempo_de_espera'] = formatear_valor(espera_total)
        row_data['Cantidad_de_personas_que_esperan'] = cnt_esperas
        row_data['Pacientes_atendidos_completamente'] = pacientes_atendidos

        # Objetos temporales
        for i_obj, obj in enumerate(objetos_temporales, 1):
            row_data[(f'{i_obj}', 'Estado')] = obj['estado']
            row_data[(f'{i_obj}', 'Hora inicio de espera en cola')] = formatear_valor(obj['hora_inicio']) if obj['hora_inicio'] is not None else ''

        filas.append(row_data)

    # Estado inicial
    registrar("Inicializacion")

    # ── Motor de eventos discretos ──────────────────────────
    while reloj < t_limite:
        eventos = [
            ("llegada_paciente", prox_llegada_pac),
            ("llegada_llamada", prox_llamada),
            ("fin_atencion_completa", fin_atencion_completa),
            ("fin_informe_obra_social", fin_informe_obra_social),
            ("fin_abono_consulta", fin_pago),
            ("fin_llamada", fin_llamada),
        ]
        evento, momento = min(eventos, key=lambda x: x[1])
        if momento == float('inf'):
            break
        reloj = momento

        # ── Procesar evento ──────────────────────────────────
        if evento == "llegada_paciente":
            rnd_llegada, tiempo_entre = gen_exponencial(media_llegada)
            prox_llegada_pac = reloj + tiempo_entre
            rnd_os = random.random()
            tiene_obra = rnd_os >= p_sin_obra
            pid = f"P{next(next_id)}"
            nuevo_paciente = Paciente(pid, tiene_obra, reloj)
            nuevo_paciente.tiempo_inicio_espera = reloj
            cola_mesa.append(nuevo_paciente)

            extra = {
                "rnd_llegada": rnd_llegada,
                "tiempo_entre": tiempo_entre,
                "rnd_obra_social": rnd_os,
                "obra_social": "Con obra social" if tiene_obra else "Sin obra social"
            }
            registrar("llegada_paciente", extra)

        elif evento == "llegada_llamada":
            prox_llamada = reloj + t_llamada
            if linea_ocupada:
                llamadas_perdidas += 1
                registrar("llegada_llamada_perdida")
            else:
                linea_ocupada = True
                rnd_call, dur_call = gen_uniforme(c1, c2)
                fin_llamada = reloj + dur_call
                extra = {"rnd_llamada": rnd_call, "tiempo_llamada": dur_call}
                registrar("llegada_llamada", extra)

        elif evento == "fin_llamada":
            linea_ocupada = False
            fin_llamada = float('inf')
            registrar("fin_llamada")

        elif evento == "fin_abono_consulta":
            coop_ocupada = False
            fin_pago = float('inf')
            if paciente_en_pago:
                # El paciente termina de pagar y va a cola de retorno (prioridad)
                paciente_en_pago.primera_vez = False
                cola_retorno.append(paciente_en_pago)
                paciente_en_pago = None
            registrar("fin_abono_consulta", {"destino_paciente": "Retorna a mesa (prioridad)"})

        elif evento == "fin_atencion_completa":
            # Paciente con obra social o sin obra social (retorno) - ABANDONA EL SISTEMA
            mesa_ocupada = False
            fin_atencion_completa = float('inf')
            destino = "Abandona el sistema (atendido)"
            if paciente_en_atencion:
                pacientes_atendidos += 1
                paciente_en_atencion = None
            
            registrar("fin_atencion_completa", {
                "rnd_tiempo_atencion": rnd_att_actual or '',
                "tiempo_atencion": t_att_actual or '',
                "tipo_atencion": tipo_atencion_actual,
                "destino_paciente": destino
            })
            rnd_att_actual = None
            t_att_actual = None
            tipo_atencion_actual = ""

        elif evento == "fin_informe_obra_social":
            # Paciente sin obra social (primera vez) - VA A COOPERADORA
            mesa_ocupada = False
            fin_informe_obra_social = float('inf')
            if paciente_en_atencion:
                cola_pago.append(paciente_en_atencion)
                paciente_en_atencion = None
            
            registrar("fin_informe_obra_social", {
                "tipo_atencion": "Informe (10 seg)",
                "destino_paciente": "Va a Cooperadora"
            })

        # ── LÓGICA DE PRIORIDADES PARA ATENDER ──
        paciente_a_atender = None
        if not mesa_ocupada:
            # Prioridad 1: Llamadas telefónicas (si hay línea libre y llegó una)
            # Prioridad 2: Pacientes de retorno (ya pagaron)
            # Prioridad 3: Pacientes normales de la cola
            
            if cola_retorno:
                paciente_a_atender = cola_retorno.pop(0)
            elif cola_mesa:
                paciente_a_atender = cola_mesa.pop(0)
                # Solo contamos espera para pacientes nuevos
                tiempo_espera = reloj - paciente_a_atender.tiempo_inicio_espera
                espera_total += tiempo_espera
                cnt_esperas += 1

        if paciente_a_atender:
            mesa_ocupada = True
            paciente_en_atencion = paciente_a_atender

            # Decidir tipo de atención según el caso
            if paciente_a_atender.tiene_obra_social:
                # Caso 1: CON obra social → atención completa U(1,3) → abandona
                rnd_att, t_att = gen_uniforme(a1, b1)
                fin_atencion_completa = reloj + t_att
                rnd_att_actual = rnd_att
                t_att_actual = t_att
                tipo_atencion_actual = "Completa (con obra social)"
                
            elif not paciente_a_atender.primera_vez:
                # Caso 2: SIN obra social (RETORNO) → atención completa U(1,3) → abandona
                rnd_att, t_att = gen_uniforme(a1, b1)
                fin_atencion_completa = reloj + t_att
                rnd_att_actual = rnd_att
                t_att_actual = t_att
                tipo_atencion_actual = "Completa (retorno sin obra social)"
                
            else:
                # Caso 3: SIN obra social (PRIMERA VEZ) → informe 10 seg → cooperadora
                fin_informe_obra_social = reloj + tiempo_informe
                tipo_atencion_actual = "Informe (primera vez sin obra social)"

            extra_inicio = {
                "rnd_tiempo_atencion": rnd_att_actual if rnd_att_actual else '',
                "tiempo_atencion": t_att_actual if t_att_actual else tiempo_informe,
                "tipo_atencion": tipo_atencion_actual
            }
            registrar("inicio_atencion", extra_inicio)

        # ── Si cooperadora está libre y hay cola, inicia pago ──
        if not coop_ocupada and cola_pago:
            coop_ocupada = True
            paciente_en_pago = cola_pago.pop(0)
            rnd_pago, tiempo_pago = gen_uniforme(a2, b2)
            fin_pago = reloj + tiempo_pago
            extra = {"rnd_pago": rnd_pago, "tiempo_pago": tiempo_pago}
            registrar("inicio_abono_consulta", extra)

    # ── Construcción de DataFrame y MultiIndex de columnas ──
    df = pd.DataFrame(filas)
    
    # Columnas principales con orden fijo
    columnas_principales = [
        'Evento','Reloj','RND_llegada_paciente','Tiempo_entre_llegadas',
        'Proxima_llegada','RND_obra_social','Obra_Social',
        'RND_tiempo_atencion','Tiempo_de_atencion','Tipo_atencion',
        'fin_atencion_completa','fin_informe_obra_social','Destino_paciente',
        'fin_abono_consulta','Proxima_llegada_llamada','fin_llamada',
        'RND_abono_consulta','Tiempo_de_abono_de_consulta',
        'RND_llamada','Tiempo_de_llamada'
    ]
    
    estadisticas = [
        'Cantidad_de_llamadas_perdidas_por_tener_la_linea_ocupada',
        'Acum_tiempo_de_espera','Cantidad_de_personas_que_esperan',
        'Pacientes_atendidos_completamente'
    ]

    # Generar MultiIndex
    nuevas_columnas = []
    for col in columnas_principales:
        if col in df.columns:
            nuevas_columnas.append(('Variables','',col))
    
    # Servidores
    servidores = [('Empleado mesa de turno','Estado'), ('Cooperadora','Estado'), ('Línea telefónica','Estado')]
    for col in servidores:
        if col in df.columns:
            nuevas_columnas.append(('Servidores',col[0],col[1]))
    
    for est in estadisticas:
        if est in df.columns:
            nuevas_columnas.append(('Estadisticas','',est))
    
    objetos_cols = [c for c in df.columns if isinstance(c, tuple) and len(c) == 2 and c[0].isdigit()]
    for col in sorted(objetos_cols, key=lambda x: int(x[0])):
        nuevas_columnas.append(('Objetos temporales',col[0],col[1]))

    df.columns = pd.MultiIndex.from_tuples(nuevas_columnas)
    prom_esp = espera_total / cnt_esperas if cnt_esperas else 0.0
    return df, prom_esp, llamadas_perdidas, pacientes_atendidos

# -----------------------------------------------------------
# Interfaz con Streamlit
# -----------------------------------------------------------

st.title("Centro de Salud – Simulación (Ej. 72) - LÓGICA MEJORADA")

st.info("""
**Lógica de Atención Implementada:**
- **Con obra social**: Atención completa U(1,3 min) → Abandona el sistema
- **Sin obra social (1ª vez)**: Informe 10 seg → Va a Cooperadora  
- **Sin obra social (retorno)**: Atención completa U(1,3 min) → Abandona el sistema

**Prioridades**: Llamadas > Pacientes de retorno > Pacientes nuevos
""")

st.sidebar.markdown("**Parámetros básicos**")
media_llegada = st.sidebar.number_input("Media entre llegadas (min)", 0.5, 30.0, 3.0)
a1, b1 = st.sidebar.slider("Atención mesa (min)", 0.5, 10.0, (1.0,3.0))
p_sin_obra = st.sidebar.slider("Proporción SIN obra social",0.0,1.0,0.45,0.05)
tiempo_informe = st.sidebar.number_input("Tiempo informe (min)",0.1,1.0,0.1667)
a2, b2 = st.sidebar.slider("Abono cooperadora (min)",0.1,10.0,(0.8,2.4))

st.sidebar.markdown("**Llamadas telefónicas**")
t_llamada = st.sidebar.number_input("Intervalo entre llamadas (min)",0.5,10.0,3.0)
c1, c2 = st.sidebar.slider("Duración llamada (min)",0.1,5.0,(0.5,1.5))

st.sidebar.markdown("**Escenario inicial**")
ini_pacientes_mesa = st.sidebar.number_input("Pacientes en cola de mesa",0,20,4)
ini_pacientes_coop = st.sidebar.number_input("Pacientes en coop. (pago)",0,20,2)
ini_t_llamada = st.sidebar.number_input("Faltan min para 1ª llamada",0.0,5.0,2.0)
tiempo_simulacion = st.sidebar.number_input("Duración simulación (min)",10,1000,60)

if st.sidebar.button("Iniciar simulación"):
    df, prom_espera, perdidas, atendidos = simular_dia(
        media_llegada, a1, b1, a2, b2, p_sin_obra, tiempo_informe,
        t_llamada, c1, c2, ini_pacientes_mesa, ini_pacientes_coop,
        ini_t_llamada, tiempo_simulacion,
    )

    st.subheader("Vector de Estado")
    st.dataframe(df, use_container_width=True, height=500)

    st.subheader("Estadísticas Finales")
    col1, col2, col3 = st.columns(3)
    col1.metric("Llamadas perdidas", perdidas)
    col2.metric("Tiempo prom. espera (min)", f"{prom_espera:.3f}")
    col3.metric("Pacientes atendidos", atendidos)

    # Resumen de lógica implementada
    with st.expander("Ver detalles de la lógica implementada"):
        st.markdown("""
        ### Casos de Atención Implementados:
        
        1. **Paciente CON obra social**:
           - Tiempo de atención: U(1,3 min) 
           - Destino: Abandona el sistema
           
        2. **Paciente SIN obra social (primera vez)**:
           - Tiempo de informe: 10 segundos (0.1667 min)
           - Destino: Va a Cooperadora
           
        3. **Paciente SIN obra social (retorno de Cooperadora)**:
           - Tiempo de atención: U(1,3 min)
           - Destino: Abandona el sistema
           
        ### Prioridades de Atención:
        1. Llamadas telefónicas (si línea libre)
        2. Pacientes que retornan de Cooperadora
        3. Pacientes nuevos en cola normal
        """)