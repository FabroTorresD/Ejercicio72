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
p_sin_obra         = st.sidebar.slider("Proporción SIN obra social", 0.0, 1.0, 0.45, 0.05)  # 45% sin obra social
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

    # Eventos de atención
    fin_atencion: float = float('inf')
    fin_pago: float = float('inf')

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
        pac = Paciente(f"CP{i+1}", False, 0.0)  # Sin obra social
        cola_pago.append(pac)

    # Estados de servidores
    mesa_ocupada: bool = False
    coop_ocupada: bool = len(cola_pago) > 0
    linea_ocupada: bool = False

    # Si hay pacientes esperando pago, calcular fin_pago inicial
    if coop_ocupada:
        rnd_pago, tiempo_pago = gen_uniforme(a2, b2)
        fin_pago = tiempo_pago

    # Variables estadísticas
    llamadas_perdidas = 0
    espera_total = 0.0
    cnt_esperas = 0
    
    # Pacientes actualmente siendo atendidos
    paciente_en_atencion = None
    paciente_en_pago = None
    if cola_pago:
        paciente_en_pago = cola_pago.pop(0)

    # Para generar IDs únicos
    next_id = count(start=100)
    
    # Listas para almacenar datos
    filas = []

    def formatear_valor(valor):
        """Formatea valores para mostrar, evitando infinitos"""
        if valor == float('inf') or valor == float('-inf'):
            return ""
        return f"{valor:.3f}" if isinstance(valor, (int, float)) else str(valor)

    def registrar(evento: str, extra: dict = None):
        """Registra el estado actual del sistema"""
        
        # Todos los objetos temporales (pacientes en el sistema)
        objetos_temporales = []
        
        # Pacientes en cola mesa
        for pac in cola_mesa:
            objetos_temporales.append({
                'id': pac.id,
                'estado': 'En cola mesa',
                'hora_inicio': pac.tiempo_inicio_espera
            })
        
        # Paciente en atención mesa
        if paciente_en_atencion:
            objetos_temporales.append({
                'id': paciente_en_atencion.id,
                'estado': 'En atención mesa',
                'hora_inicio': None
            })
        
        # Pacientes en cola pago
        for pac in cola_pago:
            objetos_temporales.append({
                'id': pac.id,
                'estado': 'En cola cooperadora',
                'hora_inicio': None
            })
        
        # Paciente en pago
        if paciente_en_pago:
            objetos_temporales.append({
                'id': paciente_en_pago.id,
                'estado': 'En pago cooperadora',
                'hora_inicio': None
            })
        
        # Pacientes esperando retorno
        for pac in cola_retorno:
            objetos_temporales.append({
                'id': pac.id,
                'estado': 'Esperando retorno',
                'hora_inicio': None
            })

        # Crear fila base
        row_data = {
            'Evento': evento,
            'Reloj': formatear_valor(reloj),
            'RND_llegada_paciente': formatear_valor(extra.get('rnd_llegada', '')) if extra else '',
            'Tiempo_entre_llegadas': formatear_valor(extra.get('tiempo_entre', '')) if extra else '',
            'Proxima_llegada': formatear_valor(prox_llegada_pac),
            'RND_obra_social': formatear_valor(extra.get('rnd_obra_social', '')) if extra else '',
            'Obra_Social': extra.get('obra_social', '') if extra else '',
            'fin_informe_obra_social': formatear_valor(tiempo_informe) if evento == 'Inicializacion' else '',
            'fin_abono_consulta': formatear_valor(fin_pago),
            'Proxima_llegada_llamada': formatear_valor(prox_llamada),
            'fin_llamada': formatear_valor(fin_llamada),
            'RND_abono_consulta': formatear_valor(extra.get('rnd_pago', '')) if extra else '',
            'Tiempo_de_abono_de_consulta': formatear_valor(extra.get('tiempo_pago', '')) if extra else '',
            'RND_llamada': formatear_valor(extra.get('rnd_llamada', '')) if extra else '',
            'Tiempo_de_llamada': formatear_valor(extra.get('tiempo_llamada', '')) if extra else '',
        }

        # Agregar servidores
        row_data[('Empleado mesa de turno', 'Estado')] = 'Ocupado' if mesa_ocupada else 'Libre'
        row_data[('Empleado mesa de turno', 'Cola')] = str([p.id for p in cola_mesa]) if cola_mesa else ''
        
        row_data[('Empleado cooperadora', 'Estado')] = 'Ocupado' if coop_ocupada else 'Libre' 
        row_data[('Empleado cooperadora', 'Cola')] = str([p.id for p in cola_pago]) if cola_pago else ''
        
        row_data[('Linea telefonica', 'Estado')] = 'Ocupado' if linea_ocupada else 'Libre'
        row_data[('Linea telefonica', 'Cola')] = ''

        # Estadísticas
        row_data['Cantidad_de_llamadas_perdidas_por_tener_la_linea_ocupada'] = llamadas_perdidas
        row_data['Acum_tiempo_de_espera'] = formatear_valor(espera_total)
        row_data['Cantidad_de_personas_que_esperan'] = cnt_esperas

        # Agregar objetos temporales dinámicamente
        for i, obj in enumerate(objetos_temporales, 1):
            row_data[(f'{i}', 'Estado')] = obj['estado']
            row_data[(f'{i}', 'Hora inicio de espera en cola')] = formatear_valor(obj['hora_inicio']) if obj['hora_inicio'] is not None else ''

        filas.append(row_data)

    # Registrar estado inicial
    registrar("Inicializacion")

    # ── Motor de eventos discretos ──────────────────────────
    while reloj < t_limite:
        
        # Encontrar próximo evento
        eventos = [
            ("llegada_paciente", prox_llegada_pac),
            ("llegada_llamada", prox_llamada),
            ("fin_atencion", fin_atencion),
            ("fin_abono_consulta", fin_pago),
            ("fin_llamada", fin_llamada),
        ]
        
        evento, momento = min(eventos, key=lambda x: x[1])
        
        if momento == float('inf'):
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
            tiene_obra = rnd_os > p_sin_obra  # 45% SIN obra social
            
            # Crear paciente
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
            # Programar próxima llamada
            prox_llamada = reloj + t_llamada
            
            # Verificar si la línea está disponible
            if linea_ocupada:
                llamadas_perdidas += 1
                registrar("llegada_llamada")
            else:
                # Iniciar llamada
                rnd_call, dur_call = gen_uniforme(c1, c2)
                fin_llamada = reloj + dur_call
                linea_ocupada = True
                
                extra = {
                    "rnd_llamada": rnd_call,
                    "tiempo_llamada": dur_call
                }
                registrar("llegada_llamada", extra)
                
        elif evento == "fin_llamada":
            linea_ocupada = False
            fin_llamada = float('inf')
            registrar("fin_llamada")
            
        elif evento == "fin_atencion":
            mesa_ocupada = False
            fin_atencion = float('inf')
            
            # El paciente actual termina su atención
            if paciente_en_atencion:
                if not paciente_en_atencion.tiene_obra_social:
                    # Enviar a cooperadora
                    cola_pago.append(paciente_en_atencion)
                # Si tiene obra social, sale del sistema
                paciente_en_atencion = None
                
            registrar("fin_atencion")
            
        elif evento == "fin_abono_consulta":
            coop_ocupada = False
            fin_pago = float('inf')
            
            # El paciente vuelve a mesa de turnos sin hacer cola
            if paciente_en_pago:
                cola_retorno.append(paciente_en_pago)
                paciente_en_pago = None
                
            registrar("fin_abono_consulta")
        
        # ── Despachar nuevos servicios ──────────────────────────
        
        # Atender en mesa de turnos (prioridad: llamadas > retorno > cola normal)
        if not mesa_ocupada and not linea_ocupada:
            paciente_a_atender = None
            
            if cola_retorno:
                paciente_a_atender = cola_retorno.pop(0)
                # Los pacientes de retorno no esperan (ya esperaron antes)
            elif cola_mesa:
                paciente_a_atender = cola_mesa.pop(0)
                # Calcular tiempo de espera
                if paciente_a_atender.tiempo_inicio_espera is not None:
                    tiempo_espera = reloj - paciente_a_atender.tiempo_inicio_espera
                    espera_total += tiempo_espera
                    cnt_esperas += 1
            
            if paciente_a_atender:
                mesa_ocupada = True
                paciente_en_atencion = paciente_a_atender
                
                if paciente_a_atender.tiene_obra_social:
                    # Atención normal
                    rnd_att, t_att = gen_uniforme(a1, b1)
                    fin_atencion = reloj + t_att
                else:
                    # Solo informar (tiempo_informe)
                    fin_atencion = reloj + tiempo_informe
        
        # Atender en cooperadora
        if not coop_ocupada and cola_pago:
            paciente_en_pago = cola_pago.pop(0)
            coop_ocupada = True
            
            rnd_pago, t_pago = gen_uniforme(a2, b2)
            fin_pago = reloj + t_pago

    # ── Crear DataFrame con MultiIndex ──
    df = pd.DataFrame(filas)
    
    # Obtener todas las columnas únicas para objetos temporales
    objetos_cols = []
    for col in df.columns:
        if isinstance(col, tuple) and col[0].isdigit():
            objetos_cols.append(col)
    
    # Crear estructura de columnas para MultiIndex
    nuevas_columnas = []
    
    # Columnas principales (nivel simple)
    columnas_principales = [
        'Evento', 'Reloj', 'RND_llegada_paciente', 'Tiempo_entre_llegadas', 
        'Proxima_llegada', 'RND_obra_social', 'Obra_Social', 
        'fin_informe_obra_social', 'fin_abono_consulta', 'Proxima_llegada_llamada',
        'fin_llamada', 'RND_abono_consulta', 'Tiempo_de_abono_de_consulta',
        'RND_llamada', 'Tiempo_de_llamada'
    ]
    
    for col in columnas_principales:
        if col in df.columns:
            nuevas_columnas.append(('', '', col))
    
    # Objetos permanentes (servidores)
    servidores = [
        ('Empleado mesa de turno', 'Estado'),
        ('Empleado mesa de turno', 'Cola'),
        ('Empleado cooperadora', 'Estado'), 
        ('Empleado cooperadora', 'Cola'),
        ('Linea telefonica', 'Estado'),
        ('Linea telefonica', 'Cola')
    ]
    
    for servidor in servidores:
        if servidor in df.columns:
            nuevas_columnas.append(('Objetos permanentes', servidor[0], servidor[1]))
    
    # Estadísticas
    estadisticas = [
        'Cantidad_de_llamadas_perdidas_por_tener_la_linea_ocupada',
        'Acum_tiempo_de_espera', 
        'Cantidad_de_personas_que_esperan'
    ]
    
    for est in estadisticas:
        if est in df.columns:
            nuevas_columnas.append(('Estadisticas', '', est))
    
    # Objetos temporales
    for col in sorted(objetos_cols, key=lambda x: int(x[0])):
        nuevas_columnas.append(('Objetos temporales', col[0], col[1]))
    
    # Reordenar DataFrame según nuevas columnas
    columnas_existentes = [col for col in [orig for _, _, orig in nuevas_columnas if not isinstance(orig, tuple)] + 
                          [orig for orig in df.columns if isinstance(orig, tuple)] 
                          if col in df.columns]
    
    df_ordenado = df[columnas_existentes]
    
    # Aplicar MultiIndex
    df_ordenado.columns = pd.MultiIndex.from_tuples(nuevas_columnas)
    
    prom_espera = espera_total / cnt_esperas if cnt_esperas else 0.0

    return df_ordenado, prom_espera, llamadas_perdidas

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