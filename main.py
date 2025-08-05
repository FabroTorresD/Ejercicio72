# -*- coding: utf-8 -*-
"""
Simulador discreto – Ejercicio 72 
------------------------------------------------------------------
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
    """Genera variable aleatoria exponencial negativa"""
    u = random.random()
    intervalo = -media * np.log(1 - u)
    return u, intervalo

def gen_uniforme(a: float, b: float) -> tuple[float, float]:
    """Genera variable aleatoria uniforme"""
    u = random.random()
    valor = a + (b - a) * u
    return u, valor

# -----------------------------------------------------------
# 2) Clase Paciente
# -----------------------------------------------------------

class Paciente:
    def __init__(self, id: str, reloj_llegada: float, es_inicial=False):
        self.id = id
        self.tiene_obra_social = None  
        self.tiempo_inicio_espera = reloj_llegada if not es_inicial else None  # Para pacientes iniciales no sabemos cuándo empezaron
        self.primera_vez = True
        self.vuelve_de_cooperadora = False
        self.estado_actual = None
        self.es_inicial = es_inicial  # Marca si es uno de los 4 pacientes iniciales
        
    def set_obra_social(self, tiene_obra_social: bool):
        self.tiene_obra_social = tiene_obra_social
        
    def marcar_retorno_cooperadora(self):
        self.primera_vez = False
        self.vuelve_de_cooperadora = True

# -----------------------------------------------------------
# 3) Clase Llamada
# -----------------------------------------------------------

class Llamada:
    def __init__(self, id: str, reloj_llegada: float):
        self.id = id
        self.reloj_llegada = reloj_llegada
        self.estado_actual = 'ESPERANDO'  # ESPERANDO o SIENDO_ATENDIDA

# -----------------------------------------------------------
# 4) Simulación del centro de salud   
# -----------------------------------------------------------

def simular_centro_salud(
    media_llegada: float = 3.0,
    a1: float = 1.0, b1: float = 3.0,  # Mesa de turnos
    a2: float = 0.8, b2: float = 2.4,  # Cooperadora
    p_sin_obra: float = 0.45,  # 45% sin obra social
    tiempo_informe: float = 0.1667,  # 10 segundos = 0.1667 min
    intervalo_llamadas: float = 3.0,
    c1: float = 0.5, c2: float = 1.5,  # Duración llamadas
    ini_pacientes_mesa: int = 4,
    ini_pacientes_coop: int = 2,
    minutos_proxima_llamada: float = 2.0,
    tiempo_simulacion: float = 60.0
):
    """Simulación    del centro de salud"""
    
    # INICIALIZACIÓN
    reloj = 0.0
    contador_pacientes = count(start=1)
    contador_cooperadora = count(start=1)
    contador_llamadas = count(start=1)
    
    # Eventos programados
    rnd_primera_llegada, tiempo_primera_llegada = gen_exponencial(media_llegada)
    prox_llegada_paciente = reloj + tiempo_primera_llegada
    prox_llegada_llamada = minutos_proxima_llamada
    fin_atencion = float('inf')
    fin_informe_obra_social = float('inf')
    fin_abono_consulta = float('inf')
    fin_llamada = float('inf')
    
    # Estados de servidores
    mesa_libre = True
    cooperadora_libre = True
    linea_ocupada = False  # NUEVA VARIABLE: indica si la línea telefónica está ocupada
    
    # COLAS SEPARADAS
    cola_pacientes_mesa_normal = []    # Pacientes nuevos esperando turno
    cola_pacientes_mesa_retorno = []   # Pacientes que vuelven de cooperadora
    cola_cooperadora = []              # Pacientes esperando pagar
    
    # Objetos siendo atendidos
    paciente_en_mesa = None
    llamada_esperando = None  # CORREGIDO: Llamada esperando en la línea
    llamada_siendo_atendida = None  # CORREGIDO: Llamada siendo atendida
    paciente_en_cooperadora = None
    
    # Lista DINÁMICA de todos los objetos activos
    objetos_activos = []
    
    # Variables para tracking de RNDs
    ultimo_rnd_llegada = rnd_primera_llegada
    ultimo_tiempo_entre_llegadas = tiempo_primera_llegada
    ultimo_rnd_obra_social = None
    ultimo_obra_social_str = ""
    ultimo_rnd_atencion = None
    ultimo_tiempo_atencion = None
    ultimo_rnd_abono = None
    ultimo_tiempo_abono = None
    ultimo_rnd_llamada = None
    ultimo_tiempo_llamada = None
    
    # CONDICIONES INICIALES CORREGIDAS
    
    # 4 pacientes esperando para sacar turno
    pacientes_iniciales = []
    for i in range(ini_pacientes_mesa):
        pac = Paciente(f"P{next(contador_pacientes)}", 0.0, es_inicial=True)
        pacientes_iniciales.append(pac)
        objetos_activos.append(pac)
    
    # El primer paciente pasa INMEDIATAMENTE a ser atendido
    if pacientes_iniciales:
        primer_paciente = pacientes_iniciales.pop(0)
        primer_paciente.estado_actual = 'SAMT'
        paciente_en_mesa = primer_paciente
        mesa_libre = False
        
        # Calcular obra social y tiempo de atención inmediatamente
        ultimo_rnd_obra_social = random.random()
        tiene_obra_social = ultimo_rnd_obra_social >= p_sin_obra
        primer_paciente.set_obra_social(tiene_obra_social)
        ultimo_obra_social_str = "Con obra social" if tiene_obra_social else "Sin obra social"
        
        if tiene_obra_social:
            ultimo_rnd_atencion, ultimo_tiempo_atencion = gen_uniforme(a1, b1)
            fin_atencion = reloj + ultimo_tiempo_atencion
        else:
            fin_informe_obra_social = reloj + tiempo_informe
    
    # Los otros 3 pacientes van a la cola
    for pac in pacientes_iniciales:
        pac.estado_actual = 'EAMT'
        cola_pacientes_mesa_normal.append(pac)
    
    # 2 pacientes esperando pagar consulta
    pacientes_cooperadora = []
    for i in range(ini_pacientes_coop):
        pac = Paciente(f"CP{next(contador_cooperadora)}", 0.0, es_inicial=True)
        pac.set_obra_social(False)
        pac.primera_vez = False
        pacientes_cooperadora.append(pac)
        objetos_activos.append(pac)
    
    # El primero pasa INMEDIATAMENTE a pagar
    if pacientes_cooperadora:
        primer_coop = pacientes_cooperadora.pop(0)
        primer_coop.estado_actual = 'AC'
        paciente_en_cooperadora = primer_coop
        cooperadora_libre = False
        
        ultimo_rnd_abono, ultimo_tiempo_abono = gen_uniforme(a2, b2)
        fin_abono_consulta = reloj + ultimo_tiempo_abono
    
    # El otro espera en cola
    for pac in pacientes_cooperadora:
        pac.estado_actual = 'EAC'
        cola_cooperadora.append(pac)
    
    # Estadísticas CORREGIDAS
    llamadas_perdidas = 0
    tiempo_espera_acumulado = 0.0
    cantidad_personas_esperaron = 0
    
    # Vector de estado
    vector_estado = []
    
    # Variable para mantener los IDs conocidos
    ids_conocidos = []
    
    def formatear_numero(num):
        if num == float('inf') or num == float('-inf'):
            return ""
        if isinstance(num, (int, float)):
            return f"{num:.4f}" if num != int(num) else f"{int(num)}"
        return str(num)
    
    def obtener_pacientes_activos():
        """Obtiene SOLO los PACIENTES activos con sus posiciones fijas"""
        pacientes = []
        
        # Crear un diccionario para mantener las posiciones de los pacientes
        pacientes_dict = {}
        
        # 1. Paciente siendo atendido en mesa
        if paciente_en_mesa:
            pacientes_dict[paciente_en_mesa.id] = {
                'id': paciente_en_mesa.id,
                'estado': paciente_en_mesa.estado_actual,
                'hora_inicio_espera': formatear_numero(paciente_en_mesa.tiempo_inicio_espera) if paciente_en_mesa.tiempo_inicio_espera is not None else ""
            }
        
        # 2. Pacientes en cola mesa (retorno NO tiene hora inicio porque no esperan)
        for pac in cola_pacientes_mesa_retorno:
            pacientes_dict[pac.id] = {
                'id': pac.id,
                'estado': pac.estado_actual,
                'hora_inicio_espera': ""  # NO ESPERAN - van directo
            }
                
        for pac in cola_pacientes_mesa_normal:
            pacientes_dict[pac.id] = {
                'id': pac.id,
                'estado': pac.estado_actual, 
                'hora_inicio_espera': formatear_numero(pac.tiempo_inicio_espera) if pac.tiempo_inicio_espera is not None else ""
            }
        
        # 3. Paciente en cooperadora
        if paciente_en_cooperadora:
            pacientes_dict[paciente_en_cooperadora.id] = {
                'id': paciente_en_cooperadora.id,
                'estado': paciente_en_cooperadora.estado_actual,
                'hora_inicio_espera': ""  # No esperan en cooperadora
            }
            
        # 4. Pacientes en cola cooperadora
        for pac in cola_cooperadora:
            pacientes_dict[pac.id] = {
                'id': pac.id,
                'estado': pac.estado_actual,
                'hora_inicio_espera': ""  # No esperan en cooperadora
            }
        
        # Convertir a lista ordenada por ID para mantener consistencia
        pacientes = list(pacientes_dict.values())
                
        return pacientes
    
    def registrar_estado(evento: str):
        nonlocal ids_conocidos  # Acceder a la variable del ámbito superior
        
        # OBTENER SOLO PACIENTES ACTIVOS
        pacientes = obtener_pacientes_activos()
        
        # Determinar estado de mesa (CORREGIDO)
        estado_mesa = 'Libre'
        if llamada_siendo_atendida:
            estado_mesa = 'AtendendoLlamada'
        elif not mesa_libre:
            estado_mesa = 'Ocupado'
        
        # Contar colas
        cola_pacientes_count = len(cola_pacientes_mesa_retorno) + len(cola_pacientes_mesa_normal)
        cola_llamadas_count = 1 if llamada_esperando else 0
        cola_coop_count = len(cola_cooperadora)
        
        fila = {
            'Evento': evento,
            'Reloj': formatear_numero(reloj),
            'RND_llegada_paciente': formatear_numero(ultimo_rnd_llegada) if ultimo_rnd_llegada else "",
            'Tiempo_entre_llegadas': formatear_numero(ultimo_tiempo_entre_llegadas) if ultimo_tiempo_entre_llegadas else "",
            'Proxima_llegada': formatear_numero(prox_llegada_paciente),
            'RND_obra_social': formatear_numero(ultimo_rnd_obra_social) if ultimo_rnd_obra_social else "",
            'Obra_Social': ultimo_obra_social_str,
            'fin_informe_obra_social': formatear_numero(fin_informe_obra_social),
            'RND_tiempo_atencion': formatear_numero(ultimo_rnd_atencion) if ultimo_rnd_atencion else "",
            'Tiempo_de_atencion': formatear_numero(ultimo_tiempo_atencion) if ultimo_tiempo_atencion else "",
            'fin_atencion': formatear_numero(fin_atencion),
            'RND_abono_consulta': formatear_numero(ultimo_rnd_abono) if ultimo_rnd_abono else "",
            'Tiempo_de_abono_de_consulta': formatear_numero(ultimo_tiempo_abono) if ultimo_tiempo_abono else "",
            'fin_abono_consulta': formatear_numero(fin_abono_consulta),
            'Proxima_llegada_llamada': formatear_numero(prox_llegada_llamada),
            'RND_llamada': formatear_numero(ultimo_rnd_llamada) if ultimo_rnd_llamada else "",
            'Tiempo_de_llamada': formatear_numero(ultimo_tiempo_llamada) if ultimo_tiempo_llamada else "",
            'fin_llamada': formatear_numero(fin_llamada),
            
            # Estados de empleados
            'Empleado_mesa_estado': estado_mesa,
            'Empleado_mesa_cola_pacientes': cola_pacientes_count,
            'Empleado_mesa_cola_llamadas': cola_llamadas_count,
            'Empleado_cooperadora_estado': 'Libre' if cooperadora_libre else 'Ocupado',
            'Empleado_cooperadora_cola': cola_coop_count,
            
            'Cantidad_de_llamadas_perdidas_por_tener_la_linea_ocupada': llamadas_perdidas,
            'Acum_tiempo_de_espera': formatear_numero(tiempo_espera_acumulado),
            'Cantidad_de_personas_que_esperan': cantidad_personas_esperaron
        }
        
        # CREAR DICCIONARIO DE PACIENTES POR POSICIÓN FIJA
        # Agregar nuevos IDs
        for pac in pacientes:
            if pac['id'] not in ids_conocidos:
                ids_conocidos.append(pac['id'])
        
        # Crear lista ordenada de IDs
        ids_ordenados = ids_conocidos.copy()  # Mantener orden de inserción
        
        # Crear mapeo por posición fija
        pacientes_dict = {pac['id']: pac for pac in pacientes}
        
        # Llenar columnas de pacientes usando posiciones fijas
        for i, id_paciente in enumerate(ids_ordenados, 1):
            if id_paciente in pacientes_dict:
                # Paciente activo
                pac = pacientes_dict[id_paciente]
                fila[f'Paciente_{i}_Estado'] = pac['estado']
                fila[f'Paciente_{i}_Hora_inicio_espera'] = pac['hora_inicio_espera']
            else:
                # Paciente destruido - campos vacíos
                fila[f'Paciente_{i}_Estado'] = ""
                fila[f'Paciente_{i}_Hora_inicio_espera'] = ""
        
        vector_estado.append(fila)
    
    # Registrar estado inicial
    registrar_estado("Inicializacion")
    
    # Función auxiliar para atender siguiente en mesa
    def atender_siguiente_en_mesa():
        """LÓGICA   : Prioridad Llamadas > Pacientes Retorno > Pacientes Normales"""
        nonlocal mesa_libre, paciente_en_mesa, llamada_siendo_atendida, llamada_esperando, linea_ocupada
        nonlocal ultimo_rnd_obra_social, ultimo_obra_social_str
        nonlocal ultimo_rnd_atencion, ultimo_tiempo_atencion, fin_atencion, fin_informe_obra_social
        nonlocal ultimo_rnd_llamada, ultimo_tiempo_llamada, fin_llamada
        nonlocal tiempo_espera_acumulado, cantidad_personas_esperaron
        
        # PRIORIDAD 1: Llamada esperando en línea
        if llamada_esperando:
            mesa_libre = False
            linea_ocupada = True
            llamada_siendo_atendida = llamada_esperando
            llamada_esperando = None
            llamada_siendo_atendida.estado_actual = 'SIENDO_ATENDIDA'
            
            ultimo_rnd_llamada, ultimo_tiempo_llamada = gen_uniforme(c1, c2)
            fin_llamada = reloj + ultimo_tiempo_llamada
            return
        
        # PRIORIDAD 2: Pacientes de retorno (NO ESPERAN - van directo)
        paciente_a_atender = None
        if cola_pacientes_mesa_retorno:
            paciente_a_atender = cola_pacientes_mesa_retorno.pop(0)
            # PACIENTES DE RETORNO NO ESPERAN - no se cuenta tiempo
        # PRIORIDAD 3: Pacientes normales
        elif cola_pacientes_mesa_normal:
            paciente_a_atender = cola_pacientes_mesa_normal.pop(0)
            # CÁLCULO CORREGIDO: Solo si no es paciente inicial
            if not paciente_a_atender.es_inicial and paciente_a_atender.tiempo_inicio_espera is not None:
                tiempo_espera = reloj - paciente_a_atender.tiempo_inicio_espera
                tiempo_espera_acumulado += tiempo_espera
                cantidad_personas_esperaron += 1
        
        if paciente_a_atender:
            mesa_libre = False
            paciente_en_mesa = paciente_a_atender
            paciente_a_atender.estado_actual = 'SAMT'
            
            if paciente_a_atender.tiene_obra_social is None:
                ultimo_rnd_obra_social = random.random()
                tiene_obra_social = ultimo_rnd_obra_social >= p_sin_obra
                paciente_a_atender.set_obra_social(tiene_obra_social)
                ultimo_obra_social_str = "Con obra social" if tiene_obra_social else "Sin obra social"
            
            if paciente_a_atender.tiene_obra_social or paciente_a_atender.vuelve_de_cooperadora:
                ultimo_rnd_atencion, ultimo_tiempo_atencion = gen_uniforme(a1, b1)
                fin_atencion = reloj + ultimo_tiempo_atencion
            else:
                fin_informe_obra_social = reloj + tiempo_informe
                ultimo_rnd_atencion = None
                ultimo_tiempo_atencion = None
        else:
            mesa_libre = True
            ultimo_rnd_obra_social = None
            ultimo_obra_social_str = ""
            ultimo_rnd_atencion = None
            ultimo_tiempo_atencion = None
    
    def atender_siguiente_paciente_cooperadora():
        nonlocal cooperadora_libre, paciente_en_cooperadora, ultimo_rnd_abono, ultimo_tiempo_abono, fin_abono_consulta
        
        if cola_cooperadora:
            cooperadora_libre = False
            paciente_en_cooperadora = cola_cooperadora.pop(0)
            paciente_en_cooperadora.estado_actual = 'AC'
            ultimo_rnd_abono, ultimo_tiempo_abono = gen_uniforme(a2, b2)
            fin_abono_consulta = reloj + ultimo_tiempo_abono
        else:
            cooperadora_libre = True
            ultimo_rnd_abono = None
            ultimo_tiempo_abono = None
    
    # MOTOR DE SIMULACIÓN CORREGIDO
    while reloj < tiempo_simulacion:
        
        # Encontrar próximo evento
        eventos_programados = [
            ('llegada_paciente', prox_llegada_paciente),
            ('llegada_llamada', prox_llegada_llamada),
            ('fin_atencion', fin_atencion),
            ('fin_informe_obra_social', fin_informe_obra_social),
            ('fin_abono_consulta', fin_abono_consulta),
            ('fin_llamada', fin_llamada)
        ]
        
        eventos_validos = [(evento, tiempo) for evento, tiempo in eventos_programados if tiempo < float('inf')]
        
        if not eventos_validos:
            break
            
        proximo_evento, momento_evento = min(eventos_validos, key=lambda x: x[1])
        reloj = momento_evento
        
        # PROCESAMIENTO DE EVENTOS CORREGIDO
        if proximo_evento == 'llegada_paciente':
            # Generar próxima llegada
            ultimo_rnd_llegada, ultimo_tiempo_entre_llegadas = gen_exponencial(media_llegada)
            prox_llegada_paciente = reloj + ultimo_tiempo_entre_llegadas
            
            # Crear nuevo paciente DINÁMICAMENTE
            nuevo_pac = Paciente(f"P{next(contador_pacientes)}", reloj)
            nuevo_pac.estado_actual = 'EAMT'
            cola_pacientes_mesa_normal.append(nuevo_pac)
            objetos_activos.append(nuevo_pac)
            
            registrar_estado("llegada_paciente")
            
        elif proximo_evento == 'llegada_llamada':
            # Programar próxima llamada
            prox_llegada_llamada = reloj + intervalo_llamadas
            
            # LÓGICA    SEGÚN ESPECIFICACIONES:
            if linea_ocupada:
                # La línea YA está ocupada (hay llamada siendo atendida O esperando) -> SE PIERDE
                llamadas_perdidas += 1
                ultimo_rnd_llamada = None
                ultimo_tiempo_llamada = None
                registrar_estado("llegada_llamada")
            elif not mesa_libre:
                # Mesa ocupada por paciente pero línea libre -> llamada ESPERA en la línea
                nueva_llamada = Llamada(f"L{next(contador_llamadas)}", reloj)
                llamada_esperando = nueva_llamada
                nueva_llamada.estado_actual = 'ESPERANDO'
                objetos_activos.append(nueva_llamada)
                linea_ocupada = True
                ultimo_rnd_llamada = None
                ultimo_tiempo_llamada = None
                registrar_estado("llegada_llamada")
            else:
                # Mesa libre -> atender llamada inmediatamente
                nueva_llamada = Llamada(f"L{next(contador_llamadas)}", reloj)
                llamada_siendo_atendida = nueva_llamada
                nueva_llamada.estado_actual = 'SIENDO_ATENDIDA'
                objetos_activos.append(nueva_llamada)
                mesa_libre = False
                linea_ocupada = True
                
                ultimo_rnd_llamada, ultimo_tiempo_llamada = gen_uniforme(c1, c2)
                fin_llamada = reloj + ultimo_tiempo_llamada
                registrar_estado("llegada_llamada")
                
        elif proximo_evento == 'fin_llamada':
            # TERMINA LLAMADA - LIBERAR LÍNEA
            if llamada_siendo_atendida:
                objetos_activos.remove(llamada_siendo_atendida)  # REMOVER de objetos activos
                llamada_siendo_atendida = None
            
            linea_ocupada = False  # LIBERAR LÍNEA
            fin_llamada = float('inf')
            ultimo_rnd_llamada = None
            ultimo_tiempo_llamada = None
            
            atender_siguiente_en_mesa()
            
            registrar_estado("fin_llamada")
            
        elif proximo_evento == 'fin_atencion':
            # TERMINA ATENCIÓN DE PACIENTE - DESTRUIR COMPLETAMENTE
            if paciente_en_mesa:
                # El paciente se DESTRUYE completamente - no se reutiliza
                objetos_activos.remove(paciente_en_mesa)  # REMOVER de objetos activos
                paciente_en_mesa = None
            
            fin_atencion = float('inf')
            atender_siguiente_en_mesa()
            registrar_estado("fin_atencion")
            
        elif proximo_evento == 'fin_informe_obra_social':
            # PACIENTE SIN OBRA SOCIAL VA A COOPERADORA (MANTIENE EL MISMO OBJETO)
            if paciente_en_mesa:
                # El paciente CONTINÚA existiendo pero cambia de lugar
                paciente_en_mesa.estado_actual = 'EAC' if not cooperadora_libre else 'AC'
                
                if cooperadora_libre:
                    # Va directo a ser atendido en cooperadora
                    paciente_en_cooperadora = paciente_en_mesa
                    paciente_en_cooperadora.estado_actual = 'AC'
                    cooperadora_libre = False
                    ultimo_rnd_abono, ultimo_tiempo_abono = gen_uniforme(a2, b2)
                    fin_abono_consulta = reloj + ultimo_tiempo_abono
                else:
                    # Va a cola de cooperadora
                    cola_cooperadora.append(paciente_en_mesa)
                
                paciente_en_mesa = None
            
            fin_informe_obra_social = float('inf')
            atender_siguiente_en_mesa()
            registrar_estado("fin_informe_obra_social")
            
        elif proximo_evento == 'fin_abono_consulta':
            # PACIENTE VUELVE A COLA DE MESA DE TURNOS (MANTIENE EL MISMO OBJETO)
            if paciente_en_cooperadora:
                # El paciente CONTINÚA existiendo pero vuelve a mesa
                paciente_en_cooperadora.marcar_retorno_cooperadora()
                paciente_en_cooperadora.estado_actual = 'EAMT'
                # NO SE ASIGNA tiempo_inicio_espera porque los de retorno NO ESPERAN
                cola_pacientes_mesa_retorno.append(paciente_en_cooperadora)
                paciente_en_cooperadora = None
            
            fin_abono_consulta = float('inf')
            atender_siguiente_paciente_cooperadora()
            registrar_estado("fin_abono_consulta")
    
    # PROCESAMIENTO DE RESULTADOS
    df_vector = pd.DataFrame(vector_estado)
    tiempo_promedio_espera = tiempo_espera_acumulado / cantidad_personas_esperaron if cantidad_personas_esperaron > 0 else 0.0
    
    return df_vector, tiempo_promedio_espera, llamadas_perdidas, len(ids_conocidos)

# -----------------------------------------------------------
# Interfaz Streamlit MANTENIDA INTACTA
# -----------------------------------------------------------

def main():
    st.set_page_config(page_title="Centro de Salud - Simulación ", layout="wide")
    
    st.title("🏥 Centro de Salud – Ejercicio 72 ")

    # Sidebar con parámetros
    st.sidebar.markdown("## ⚙️ Parámetros de Simulación")
    
    
    # Parámetros básicos
    media_llegada = st.sidebar.number_input("Media entre llegadas (min)", 0.5, 10.0, 3.0, 0.1)
    st.sidebar.divider()
    
   # En el sidebar, cada llamada a .columns() crea una nueva fila de 2 columnas
    # Mesa de turnos
    col1, col2 = st.sidebar.columns(2)
    a1 = col1.number_input(
        "Tiempo de atención mesa de turno – Mín (min)",
        min_value=0.1, max_value=5.0, value=1.0, step=0.1
    )
    b1 = col2.number_input(
        "Tiempo de atención mesa de turno – Máx (min)",
        min_value=0.1, max_value=5.0, value=3.0, step=0.1
    )
    st.sidebar.divider()
    # Cooperadora``
    coop_col1, coop_col2 = st.sidebar.columns(2)
    a2 = coop_col1.number_input(
        "Tiempo de atención cooperadora – Mín (min)",
        min_value=0.1, max_value=5.0, value=0.8, step=0.1
    )
    b2 = coop_col2.number_input(
        "Tiempo de atención cooperadora – Máx (min)",
        min_value=0.1, max_value=5.0, value=2.4, step=0.1
    )
    st.sidebar.divider()

    # Llamadas
    llamada_col1, llamada_col2 = st.sidebar.columns(2)
    c1 = llamada_col1.number_input(
        "Duración de llamada – Mín (min)",
        min_value=0.1, max_value=3.0, value=0.5, step=0.1
    )
    c2 = llamada_col2.number_input(
        "Duración de llamada – Máx (min)",
        min_value=0.1, max_value=3.0, value=1.5, step=0.1
    )
    st.sidebar.divider()

    tiempoInforme = st.sidebar.number_input(
        "Tiempo informar sobre obra social (min)",
        min_value=0.01, max_value=2.0, value=0.1667, step=0.0001, format="%.4f"
    )
    st.sidebar.divider()

    p_sin_obra = st.sidebar.slider("% Proporcion sin obra social", 0.0, 1.0, 0.45, 0.05)
    st.sidebar.divider()
    intervalo_llamadas = st.sidebar.number_input("Intervalo llamadas (min)", 1.0, 10.0, 3.0, 0.1)
    st.sidebar.divider()
    
    # Condiciones iniciales
    st.sidebar.markdown("### 🎯 Condiciones Iniciales")
    ini_mesa = st.sidebar.number_input("Pacientes esperando turno", 0, 20, 4)
    ini_coop = st.sidebar.number_input("Pacientes esperando pago", 0, 20, 2)
    min_llamada = st.sidebar.number_input("Minutos para próxima llamada", 0.0, 10.0, 2.0, 0.1)
    
    tiempo_sim = st.sidebar.number_input("Tiempo de simulación (min)", 10, 500, 60)
    
    # Botón de simulación
    if st.sidebar.button("Ejecutar Simulación   ", type="primary"):
        
        # Ejecutar simulación
        with st.spinner("Ejecutando simulación  ..."):
            df_resultado, tiempo_promedio, llamadas_perdidas, max_pacientes = simular_centro_salud(
                media_llegada=media_llegada,
                a1=a1, b1=b1, a2=a2, b2=b2,
                p_sin_obra=p_sin_obra,
                intervalo_llamadas=intervalo_llamadas,
                c1=c1, c2=c2,
                tiempo_informe=tiempoInforme,
                ini_pacientes_mesa=ini_mesa,
                ini_pacientes_coop=ini_coop,
                minutos_proxima_llamada=min_llamada,
                tiempo_simulacion=tiempo_sim
            )
        
        # Vector de estado (VISUAL MANTENIDO IGUAL)
        st.markdown("## 📊 Simulacion Realizada")

        # Crear DataFrame con multi-índice completo
        df_multi = df_resultado.copy()
        
        # Crear las columnas con multi-índice
        nuevas_columnas = []
        
        # Columnas básicas (nivel 1 solo)
        nuevas_columnas.extend([
            ('','', 'Evento'),
            ('','', 'Reloj')
        ])
        
        # Llegada paciente
        nuevas_columnas.extend([
            ('', 'llegada_paciente', 'RND llegada paciente'),
            ('', 'llegada_paciente', 'Tiempo entre llegadas'),
            ('', 'llegada_paciente', 'Proxima llegada')
        ])
        
        # Obra social
        nuevas_columnas.extend([
            ('Obra Social','', 'RND obra social'),
            ('Obra Social','', 'Obra Social'),
            ('','', 'fin_informe_obra_social')
        ])
        
        # Atención
        nuevas_columnas.extend([
            ('', 'fin_atencion', 'RND tiempo atencion'),
            ('','fin_atencion', 'Tiempo de atencion'),
            ('','fin_atencion', 'fin de atencion')
        ])
        
        # Cooperadora
        nuevas_columnas.extend([
            ('','fin_abono_consulta', 'RND abono consulta'),
            ('','fin_abono_consulta', 'Tiempo de abono de consulta'),
            ('','fin_abono_consulta', 'fin abono consulta')
        ])
        
        # Llamadas
        nuevas_columnas.extend([
            ('','', 'Proxima llegada llamada'),
            ('','fin_llamada', 'RND llamada'),
            ('','fin_llamada', 'Tiempo de llamada'),
            ('','fin_llamada', 'fin llamada')
        ])
        
        # Objetos permanentes
        nuevas_columnas.extend([
            ('', 'Empleado mesa de turno', 'Estado'),
            ('', 'Empleado mesa de turno', 'Cola Pacientes'),
            ('', 'Empleado mesa de turno', 'Cola Llamadas'),
            ('', 'Empleado cooperadora', 'Estado'),
            ('', 'Empleado cooperadora', 'Cola')
        ])
        
        # Estadísticas
        nuevas_columnas.extend([
            ('', 'Estadística A)', 'Cantidad de llamadas perdidas por tener la línea ocupada'),
            ('', 'Estadística B)', 'Acum tiempo de espera'),
            ('', 'Estadística B)', 'Cantidad de personas que esperan')
        ])
        
        # Objetos temporales DINÁMICOS - Usar el valor retornado por la simulación
        # Crear columnas para todos los pacientes necesarios
        for i in range(1, max_pacientes + 1):
            etiqueta = f"Paciente {i}"
            nuevas_columnas.extend([
                ('', etiqueta, 'Estado'),
                ('', etiqueta, 'Hora inicio espera')
            ])

        # Crear mapeo de columnas originales a nuevas
        columnas_originales = [
            'Evento', 'Reloj',
            'RND_llegada_paciente', 'Tiempo_entre_llegadas', 'Proxima_llegada',
            'RND_obra_social', 'Obra_Social', 'fin_informe_obra_social',
            'RND_tiempo_atencion', 'Tiempo_de_atencion', 'fin_atencion',
            'RND_abono_consulta', 'Tiempo_de_abono_de_consulta', 'fin_abono_consulta',
            'Proxima_llegada_llamada', 'RND_llamada', 'Tiempo_de_llamada', 'fin_llamada',
            'Empleado_mesa_estado', 'Empleado_mesa_cola_pacientes', 'Empleado_mesa_cola_llamadas',
            'Empleado_cooperadora_estado', 'Empleado_cooperadora_cola',
            'Cantidad_de_llamadas_perdidas_por_tener_la_linea_ocupada',
            'Acum_tiempo_de_espera', 'Cantidad_de_personas_que_esperan'
        ]
        
        # Agregar columnas de pacientes temporales dinámicamente
        for i in range(1, max_pacientes + 1):
            columnas_originales.extend([
                f'Paciente_{i}_Estado',
                f'Paciente_{i}_Hora_inicio_espera'
            ])
        
        # Filtrar solo las columnas que existen
        columnas_existentes = [col for col in columnas_originales if col in df_multi.columns]
        nuevas_columnas_filtradas = nuevas_columnas[:len(columnas_existentes)]
        
        # Crear DataFrame con multi-índice
        df_reordenado = df_multi[columnas_existentes].copy()
        
        # Crear el multi-índice
        multi_index = pd.MultiIndex.from_tuples(nuevas_columnas_filtradas)
        df_reordenado.columns = multi_index
        
        st.dataframe(df_reordenado, use_container_width=True, height=500)

        # Mostrar estadísticas principales
        st.markdown("## 📈 Estadísticas Calculadas")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "🔴 A) Llamadas Perdidas", 
                value=llamadas_perdidas,
                help="Llamadas perdidas SOLO cuando la línea ya está ocupada por otra llamada"
            )
        with col2:
            st.metric(
                "⏱️ B) Tiempo Promedio de Espera", 
                value=f"{tiempo_promedio:.3f} min",
                help="Tiempo promedio de espera de pacientes en colas (excluyendo los 4 iniciales)"
            )
        
        

if __name__ == "__main__":
    main()