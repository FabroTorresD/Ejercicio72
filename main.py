# -*- coding: utf-8 -*-
"""
Simulador discreto – Centro de Salud (Ejercicio 72) - FORMATO FINAL
------------------------------------------------------------------
• Paciente → llega con distribución Exponencial(µ = 3 min)
• Mesa de turnos (servidor 1) → Uniforme(1,3 min)
    – Al paciente SIN obra social le informa (0.1667 min = 10 seg) y lo envía a Cooperadora
• Cooperadora (servidor 2) → Uniforme(0.8, 2.4 min)
    – Al terminar vuelve a Mesa de turnos (sin volver a la cola original)
• Llamadas → arriban cada 3 minutos (constante)
    – Duración Uniforme(0.5, 1.5 min)
    – Si la línea está ocupada la llamada se pierde

Estadísticas a calcular:
A) Cantidad de llamadas perdidas por tener la línea ocupada
B) Determinar tiempo promedio de espera en cola

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
# 3) Estados de los pacientes según el documento
# -----------------------------------------------------------
# esperandoAtencionMesaTurno (EAMT)
# siendoAtendidoMesaTurno(SAMT) 
# esperandoAtencionCooperadora (EAC)
# abonandoCooperadora (AC)

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
    prox_llegada_pac: float = reloj + tiempo_entre  # CORREGIDO: desde reloj actual

    # Programar primera llamada
    prox_llegada_llamada: float = falta_llamada  # Correcto: faltan X minutos
    fin_llamada: float = float('inf')

    # Eventos de atención
    fin_atencion: float = float('inf')
    fin_informe_obra_social: float = float('inf') 
    fin_abono_consulta: float = float('inf')

    # ── Variables para rastrear la atención ──
    rnd_att_actual: float | None = None
    t_att_actual: float | None = None
    rnd_abono_actual: float | None = None
    t_abono_actual: float | None = None
    rnd_llamada_actual: float | None = None
    t_llamada_actual: float | None = None

    # ── Colas & servidores según documento ──
    cola_mesa: list[Paciente] = []           # EAMT - esperandoAtencionMesaTurno
    cola_retorno: list[Paciente] = []        # Pacientes que vuelven de cooperadora (prioridad)
    cola_cooperadora: list[Paciente] = []    # EAC - esperandoAtencionCooperadora

    # Inicializar con 4 pacientes esperando para sacar turno
    for i in range(ini_mesa):
        pac = Paciente(f"P{i+1}", random.random() >= p_sin_obra, 0.0)
        pac.tiempo_inicio_espera = 0.0
        cola_mesa.append(pac)

    # Inicializar con 2 pacientes esperando pagar consulta
    for i in range(ini_coop):
        pac = Paciente(f"CP{i+1}", False, 0.0)
        pac.primera_vez = False  # Ya pasaron por mesa antes
        cola_cooperadora.append(pac)

    # Estados de servidores
    mesa_ocupada: bool = False
    cooperadora_ocupada: bool = False
    linea_ocupada: bool = False

    # Si hay alguien en cooperadora al inicio, arranca el servicio inmediatamente
    paciente_en_abono = None
    if cola_cooperadora:
        cooperadora_ocupada = True
        paciente_en_abono = cola_cooperadora.pop(0)
        rnd_abono, tiempo_abono = gen_uniforme(a2, b2)
        fin_abono_consulta = reloj + tiempo_abono  # Desde tiempo 0
        rnd_abono_actual = rnd_abono
        t_abono_actual = tiempo_abono

    # Estadísticas
    llamadas_perdidas = 0
    espera_total = 0.0
    cnt_esperas = 0

    paciente_en_atencion = None
    next_id = count(start=100)
    filas = []

    def formatear_valor(valor):
        if valor in (float('inf'), float('-inf')):
            return ""
        if isinstance(valor, (int, float)):
            return f"{valor:.3f}"
        return str(valor)

    def registrar(evento: str, extra: dict = None):
        # Recopilar objetos temporales según el formato del documento
        objetos_temporales = []
        
        # Pacientes en cola mesa (EAMT)
        for pac in cola_mesa:
            objetos_temporales.append({
                'id': pac.id, 
                'estado': 'EAMT',  # esperandoAtencionMesaTurno
                'hora_inicio': pac.tiempo_inicio_espera
            })
        
        # Pacientes de retorno (también EAMT pero con prioridad)
        for pac in cola_retorno:
            objetos_temporales.append({
                'id': pac.id, 
                'estado': 'EAMT', 
                'hora_inicio': None  # No cuentan tiempo de espera
            })
            
        # Paciente siendo atendido en mesa (SAMT)
        if paciente_en_atencion:
            objetos_temporales.append({
                'id': paciente_en_atencion.id,
                'estado': 'SAMT',  # siendoAtendidoMesaTurno
                'hora_inicio': None
            })
        
        # Pacientes en cola cooperadora (EAC)
        for pac in cola_cooperadora:
            objetos_temporales.append({
                'id': pac.id, 
                'estado': 'EAC',  # esperandoAtencionCooperadora
                'hora_inicio': None
            })
            
        # Paciente abonando en cooperadora (AC)
        if paciente_en_abono:
            objetos_temporales.append({
                'id': paciente_en_abono.id,
                'estado': 'AC',   # abonandoCooperadora
                'hora_inicio': None
            })

        # Construir fila según formato del documento
        row_data = {
            'Evento': evento,
            'Reloj': formatear_valor(reloj),
            'RND_llegada_paciente': formatear_valor(extra.get('rnd_llegada', '')) if extra else '',
            'Tiempo_entre_llegadas': formatear_valor(extra.get('tiempo_entre', '')) if extra else '',
            'Proxima_llegada': formatear_valor(prox_llegada_pac),
            'RND_obra_social': formatear_valor(extra.get('rnd_obra_social', '')) if extra else '',
            'Obra_Social': extra.get('obra_social', '') if extra else '',
            'RND_tiempo_atencion': formatear_valor(extra.get('rnd_tiempo_atencion', '')) if extra else '',
            'Tiempo_de_atencion': formatear_valor(extra.get('tiempo_atencion', '')) if extra else '',
            'fin_atencion': formatear_valor(fin_atencion),
            'fin_informe_obra_social': formatear_valor(fin_informe_obra_social),
            'RND_abono_consulta': formatear_valor(extra.get('rnd_abono_consulta', '')) if extra else '',
            'Tiempo_de_abono_de_consulta': formatear_valor(extra.get('tiempo_abono_consulta', '')) if extra else '',
            'fin_abono_consulta': formatear_valor(fin_abono_consulta),
            'Proxima_llegada_llamada': formatear_valor(prox_llegada_llamada),
            'RND_llamada': formatear_valor(extra.get('rnd_llamada', '')) if extra else '',
            'Tiempo_de_llamada': formatear_valor(extra.get('tiempo_llamada', '')) if extra else '',
            'fin_llamada': formatear_valor(fin_llamada),
            # Estados de servidores
            'Empleado_mesa_de_turno_Estado': 'Ocupado' if mesa_ocupada else 'Libre',
            'Empleado_cooperadora_Estado': 'Ocupado' if cooperadora_ocupada else 'Libre', 
            'Linea_telefonica_Estado': 'Ocupada' if linea_ocupada else 'Libre',
            # Estadísticas
            'Cantidad_de_llamadas_perdidas_por_tener_la_linea_ocupada': llamadas_perdidas,
            'Acum_tiempo_de_espera': formatear_valor(espera_total),
            'Cantidad_de_personas_que_esperan': cnt_esperas,
        }

        # Agregar objetos temporales (máximo 4 según documento)
        for i in range(4):
            if i < len(objetos_temporales):
                obj = objetos_temporales[i]
                row_data[f'Objeto_{i+1}_Estado'] = obj['estado']
                row_data[f'Objeto_{i+1}_Hora_inicio_espera'] = formatear_valor(obj['hora_inicio']) if obj['hora_inicio'] is not None else ''
            else:
                row_data[f'Objeto_{i+1}_Estado'] = ''
                row_data[f'Objeto_{i+1}_Hora_inicio_espera'] = ''

        filas.append(row_data)

    # Estado inicial - Con debug de pacientes iniciales
    # Debug para verificar estado inicial
    print(f"DEBUG INICIAL: Mesa={len(cola_mesa)}, Cooperadora={len(cola_cooperadora)}, Total={len(cola_mesa)+len(cola_cooperadora)}")
    print(f"DEBUG: Próxima llegada en: {prox_llegada_pac:.3f}")
    print(f"DEBUG: Próxima llamada en: {prox_llegada_llamada:.3f}")
    if paciente_en_abono:
        print(f"DEBUG: Cooperadora ocupada hasta: {fin_abono_consulta:.3f}")
    
    registrar("Inicializacion")

    # ── Motor de eventos discretos ──────────────────────────
    while reloj < t_limite:
        eventos = [
            ("llegada_paciente", prox_llegada_pac),
            ("llegada_llamada", prox_llegada_llamada),
            ("fin_atencion", fin_atencion),
            ("fin_informe_obra_social", fin_informe_obra_social),
            ("fin_abono_consulta", fin_abono_consulta),
            ("fin_llamada", fin_llamada),
        ]
        evento, momento = min(eventos, key=lambda x: x[1])
        if momento == float('inf'):
            break
        reloj = momento

        # Debug: mostrar el evento que se está procesando
        print(f"DEBUG: Reloj={reloj:.3f}, Evento={evento}, Próxima llegada={prox_llegada_pac:.3f}")

        # ── Procesar evento ──────────────────────────────────
        if evento == "llegada_paciente":
            # Generar PRÓXIMA llegada ANTES de procesar la actual
            rnd_llegada, tiempo_entre = gen_exponencial(media_llegada)
            prox_llegada_pac = reloj + tiempo_entre
            
            # Procesar llegada actual
            rnd_os = random.random()
            tiene_obra = rnd_os >= p_sin_obra
            pid = f"P{next(next_id)}"
            nuevo_paciente = Paciente(pid, tiene_obra, reloj)
            nuevo_paciente.tiempo_inicio_espera = reloj
            cola_mesa.append(nuevo_paciente)
            
            print(f"DEBUG: Llegó {pid}, próxima llegada en {prox_llegada_pac:.3f}")

            extra = {
                "rnd_llegada": rnd_llegada,
                "tiempo_entre": tiempo_entre,
                "rnd_obra_social": rnd_os,
                "obra_social": "Con obra social" if tiene_obra else "Sin obra social"
            }
            registrar("llegada_paciente", extra)

        elif evento == "llegada_llamada":
            prox_llegada_llamada = reloj + t_llamada
            if linea_ocupada:
                llamadas_perdidas += 1
                registrar("llegada_llamada_perdida")
            else:
                linea_ocupada = True
                rnd_call, dur_call = gen_uniforme(c1, c2)
                fin_llamada = reloj + dur_call
                rnd_llamada_actual = rnd_call
                t_llamada_actual = dur_call
                extra = {"rnd_llamada": rnd_call, "tiempo_llamada": dur_call}
                registrar("llegada_llamada", extra)

        elif evento == "fin_llamada":
            linea_ocupada = False
            fin_llamada = float('inf')
            rnd_llamada_actual = None
            t_llamada_actual = None
            registrar("fin_llamada")

        elif evento == "fin_abono_consulta":
            cooperadora_ocupada = False
            fin_abono_consulta = float('inf')
            if paciente_en_abono:
                paciente_en_abono.primera_vez = False
                cola_retorno.append(paciente_en_abono)
                paciente_en_abono = None
            rnd_abono_actual = None
            t_abono_actual = None
            registrar("fin_abono_consulta")

        elif evento == "fin_atencion":
            mesa_ocupada = False
            fin_atencion = float('inf')
            if paciente_en_atencion:
                # El paciente abandona el sistema después de atención completa
                paciente_en_atencion = None
            rnd_att_actual = None
            t_att_actual = None
            registrar("fin_atencion")

        elif evento == "fin_informe_obra_social":
            mesa_ocupada = False
            fin_informe_obra_social = float('inf')
            if paciente_en_atencion:
                # El paciente va a cooperadora después del informe
                cola_cooperadora.append(paciente_en_atencion)
                paciente_en_atencion = None
            registrar("fin_informe_obra_social")

        # ── Lógica de atención en mesa ──
        if not mesa_ocupada:
            paciente_a_atender = None
            # Prioridad: retorno > cola normal
            if cola_retorno:
                paciente_a_atender = cola_retorno.pop(0)
            elif cola_mesa:
                paciente_a_atender = cola_mesa.pop(0)
                # Solo contar espera para pacientes nuevos
                tiempo_espera = reloj - paciente_a_atender.tiempo_inicio_espera
                espera_total += tiempo_espera
                cnt_esperas += 1

            if paciente_a_atender:
                mesa_ocupada = True
                paciente_en_atencion = paciente_a_atender

                if paciente_a_atender.tiene_obra_social or not paciente_a_atender.primera_vez:
                    # Atención completa
                    rnd_att, t_att = gen_uniforme(a1, b1)
                    fin_atencion = reloj + t_att
                    rnd_att_actual = rnd_att
                    t_att_actual = t_att
                    
                    extra_inicio = {
                        "rnd_tiempo_atencion": rnd_att,
                        "tiempo_atencion": t_att
                    }
                    registrar("inicio_atencion", extra_inicio)
                else:
                    # Solo informe
                    fin_informe_obra_social = reloj + tiempo_informe
                    registrar("inicio_informe")

        # ── Lógica de cooperadora ──
        if not cooperadora_ocupada and cola_cooperadora:
            cooperadora_ocupada = True
            paciente_en_abono = cola_cooperadora.pop(0)
            rnd_abono, tiempo_abono = gen_uniforme(a2, b2)
            fin_abono_consulta = reloj + tiempo_abono
            rnd_abono_actual = rnd_abono
            t_abono_actual = tiempo_abono
            
            extra_cooperadora = {
                "rnd_abono_consulta": rnd_abono,
                "tiempo_abono_consulta": tiempo_abono
            }
            registrar("inicio_abono_consulta", extra_cooperadora)

    # ── Construcción de DataFrame ──
    df = pd.DataFrame(filas)
    
    # Reordenar columnas según el formato del documento
    columnas_ordenadas = [
        'Evento', 'Reloj', 
        'RND_llegada_paciente', 'Tiempo_entre_llegadas', 'Proxima_llegada',
        'RND_obra_social', 'Obra_Social',
        'RND_tiempo_atencion', 'Tiempo_de_atencion', 'fin_atencion',
        'fin_informe_obra_social',
        'RND_abono_consulta', 'Tiempo_de_abono_de_consulta', 'fin_abono_consulta',
        'Proxima_llegada_llamada', 'RND_llamada', 'Tiempo_de_llamada', 'fin_llamada',
        'Empleado_mesa_de_turno_Estado', 'Empleado_cooperadora_Estado', 'Linea_telefonica_Estado',
        'Cantidad_de_llamadas_perdidas_por_tener_la_linea_ocupada',
        'Acum_tiempo_de_espera', 'Cantidad_de_personas_que_esperan',
        'Objeto_1_Estado', 'Objeto_1_Hora_inicio_espera',
        'Objeto_2_Estado', 'Objeto_2_Hora_inicio_espera', 
        'Objeto_3_Estado', 'Objeto_3_Hora_inicio_espera',
        'Objeto_4_Estado', 'Objeto_4_Hora_inicio_espera'
    ]
    
    # Filtrar solo las columnas que existen
    columnas_existentes = [col for col in columnas_ordenadas if col in df.columns]
    df = df[columnas_existentes]
    
    prom_esp = espera_total / cnt_esperas if cnt_esperas else 0.0
    return df, prom_esp, llamadas_perdidas

# -----------------------------------------------------------
# Interfaz con Streamlit
# -----------------------------------------------------------

st.title("Centro de Salud – Simulación (Ejercicio 72) - FORMATO FINAL")

st.info("""
**Estados de Pacientes Implementados:**
- **EAMT**: esperandoAtencionMesaTurno
- **SAMT**: siendoAtendidoMesaTurno  
- **EAC**: esperandoAtencionCooperadora
- **AC**: abonandoCooperadora

**Estadísticas a Calcular:**
- A) Cantidad de llamadas perdidas por tener la línea ocupada
- B) Tiempo promedio de espera en cola
""")

st.sidebar.markdown("**Parámetros básicos**")
media_llegada = st.sidebar.number_input("Media entre llegadas (min)", 0.5, 30.0, 3.0)
a1, b1 = st.sidebar.slider("Atención mesa (min)", 0.5, 10.0, (1.0,3.0))
p_sin_obra = st.sidebar.slider("Proporción SIN obra social",0.0,1.0,0.55,0.05)  # 55% según documento
tiempo_informe = st.sidebar.number_input("Tiempo informe (seg)",1,30,10) / 60  # Convertir a minutos
a2, b2 = st.sidebar.slider("Abono cooperadora (min)",0.1,10.0,(0.8,2.4))

st.sidebar.markdown("**Llamadas telefónicas**")
t_llamada = st.sidebar.number_input("Intervalo entre llamadas (min)",0.5,10.0,3.0)
c1, c2 = st.sidebar.slider("Duración llamada (min)",0.1,5.0,(0.5,1.5))

st.sidebar.markdown("**Escenario inicial (según documento)**")
ini_pacientes_mesa = st.sidebar.number_input("Pacientes esperando sacar turno",0,20,4)
ini_pacientes_coop = st.sidebar.number_input("Pacientes esperando pagar consulta",0,20,2)
ini_t_llamada = st.sidebar.number_input("Faltan min para próxima llamada",0.0,5.0,2.0)
tiempo_simulacion = st.sidebar.number_input("Duración simulación (min)",10,1000,60)

if st.sidebar.button("🚀 Iniciar Simulación"):
    df, prom_espera, perdidas = simular_dia(
        media_llegada, a1, b1, a2, b2, p_sin_obra, tiempo_informe,
        t_llamada, c1, c2, ini_pacientes_mesa, ini_pacientes_coop,
        ini_t_llamada, tiempo_simulacion,
    )

    st.subheader("📊 Vector de Estado")
    st.dataframe(df, use_container_width=True, height=500)

    st.subheader("📈 Estadísticas Finales del Ejercicio 72")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            label="🔴 A) Llamadas Perdidas", 
            value=perdidas,
            help="Cantidad de llamadas perdidas por tener la línea ocupada"
        )
    
    with col2:
        st.metric(
            label="⏱️ B) Tiempo Promedio de Espera", 
            value=f"{prom_espera:.3f} min",
            help="Tiempo promedio de espera en cola (solo pacientes nuevos)"
        )

    # Mostrar resultados finales en formato destacado
    st.success(f"""
    ### 🎯 RESULTADOS FINALES - EJERCICIO 72

    **A) Cantidad de llamadas perdidas por tener la línea ocupada:** `{perdidas}`
    
    **B) Tiempo promedio de espera en cola:** `{prom_espera:.3f} minutos`
    """)

    # Detalles adicionales
    with st.expander("📋 Detalles de la Simulación"):
        ultima_fila = df.iloc[-1]
        st.write(f"**Tiempo total simulado:** {tiempo_simulacion} minutos")
        st.write(f"**Tiempo de espera acumulado:** {ultima_fila['Acum_tiempo_de_espera']} minutos")
        st.write(f"**Cantidad total de personas que esperaron:** {ultima_fila['Cantidad_de_personas_que_esperan']}")
        
        if ultima_fila['Cantidad_de_personas_que_esperan'] > 0:
            st.write(f"**Cálculo promedio:** {ultima_fila['Acum_tiempo_de_espera']} ÷ {ultima_fila['Cantidad_de_personas_que_esperan']} = {prom_espera:.3f} min")