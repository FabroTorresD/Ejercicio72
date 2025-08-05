# -*- coding: utf-8 -*-
"""
Simulador discreto – Ejercicio 72 - VERSIÓN MEJORADA
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
    def __init__(self, id: str, reloj_llegada: float):
        self.id = id
        self.tiene_obra_social = None  
        self.tiempo_inicio_espera = reloj_llegada
        self.primera_vez = True
        self.vuelve_de_cooperadora = False
        self.estado_actual = None
        self.finalizado = False  # NUEVO: marca si el paciente terminó completamente
        
    def set_obra_social(self, tiene_obra_social: bool):
        self.tiene_obra_social = tiene_obra_social
        
    def marcar_retorno_cooperadora(self):
        self.primera_vez = False
        self.vuelve_de_cooperadora = True

    def finalizar(self):
        """Marca al paciente como completamente finalizado"""
        self.finalizado = True
        self.estado_actual = 'FINALIZADO'

# -----------------------------------------------------------
# 3) Clase Llamada
# -----------------------------------------------------------

class Llamada:
    def __init__(self, id: str, reloj_llegada: float):
        self.id = id
        self.reloj_llegada = reloj_llegada
        self.estado_actual = 'ESPERANDO'  # ESPERANDO o SIENDO_ATENDIDA

# -----------------------------------------------------------
# 4) Simulación del centro de salud MEJORADA
# -----------------------------------------------------------

def simular_centro_salud(
    media_llegada: float = 3.0,
    a1: float = 1.0, b1: float = 3.0,  # Mesa de turnos
    a2: float = 0.8, b2: float = 2.4,  # Cooperadora
    p_sin_obra: float = 0.45,  # 45% sin obra social
    tiempo_informe: float = 10/60,  # 10 segundos = 0.1667 min
    intervalo_llamadas: float = 3.0,
    c1: float = 0.5, c2: float = 1.5,  # Duración llamadas
    ini_pacientes_mesa: int = 4,
    ini_pacientes_coop: int = 2,
    minutos_proxima_llamada: float = 2.0,
    tiempo_simulacion: float = 60.0
):
    """Simulación MEJORADA del centro de salud"""
    
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
    
    # Estados de servidores MEJORADOS
    mesa_libre = True
    cooperadora_libre = True
    
    # COLAS SEPARADAS - NUEVA ARQUITECTURA
    cola_pacientes_mesa_normal = []    # Pacientes nuevos esperando turno
    cola_pacientes_mesa_retorno = []   # Pacientes que vuelven de cooperadora
    cola_llamadas = []                 # NUEVA: Cola específica para llamadas
    cola_cooperadora = []              # Pacientes esperando pagar
    
    # Objetos siendo atendidos
    paciente_en_mesa = None
    llamada_en_atencion = None  # NUEVO: Llamada siendo atendida
    paciente_en_cooperadora = None
    
    # Lista de TODOS los objetos del sistema (pacientes y llamadas)
    todos_los_objetos = []  # NUEVO: Lista dinámica sin límite
    
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
    
    # CONDICIONES INICIALES MEJORADAS
    
    # 4 pacientes esperando para sacar turno
    pacientes_iniciales = []
    for i in range(ini_pacientes_mesa):
        pac = Paciente(f"P{next(contador_pacientes)}", 0.0)
        pacientes_iniciales.append(pac)
        todos_los_objetos.append(pac)  # Agregar a lista global
    
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
        pac = Paciente(f"CP{next(contador_cooperadora)}", 0.0)
        pac.set_obra_social(False)
        pac.primera_vez = False
        pacientes_cooperadora.append(pac)
        todos_los_objetos.append(pac)  # Agregar a lista global
    
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
    
    # Estadísticas
    llamadas_perdidas = 0
    tiempo_espera_acumulado = 0.0
    cantidad_personas_esperaron = 0
    
    # Vector de estado
    vector_estado = []
    
    def formatear_numero(num):
        if num == float('inf') or num == float('-inf'):
            return ""
        if isinstance(num, (int, float)):
            return f"{num:.4f}" if num != int(num) else f"{int(num)}"
        return str(num)
    
    def obtener_objetos_temporales():
        """NUEVA FUNCIÓN: Obtiene TODOS los objetos dinámicamente"""
        objetos = []
        
        # 1. Paciente siendo atendido en mesa
        if paciente_en_mesa and not paciente_en_mesa.finalizado:
            objetos.append({
                'id': paciente_en_mesa.id,
                'estado': 'SAMT',
                'hora_inicio_espera': formatear_numero(paciente_en_mesa.tiempo_inicio_espera) if paciente_en_mesa.tiempo_inicio_espera != 0 else ""
            })
        
        # 2. Llamada siendo atendida
        if llamada_en_atencion:
            objetos.append({
                'id': llamada_en_atencion.id,
                'estado': 'SIENDO_ATENDIDA',
                'hora_inicio_espera': formatear_numero(llamada_en_atencion.reloj_llegada)
            })
        
        # 3. Llamadas esperando en cola
        for llamada in cola_llamadas:
            objetos.append({
                'id': llamada.id,
                'estado': 'ESPERANDO',
                'hora_inicio_espera': formatear_numero(llamada.reloj_llegada)
            })
        
        # 4. Pacientes en cola mesa (retorno tiene prioridad)
        for pac in cola_pacientes_mesa_retorno:
            if not pac.finalizado:
                objetos.append({
                    'id': pac.id,
                    'estado': 'EAMT',
                    'hora_inicio_espera': formatear_numero(pac.tiempo_inicio_espera)
                })
                
        for pac in cola_pacientes_mesa_normal:
            if not pac.finalizado:
                objetos.append({
                    'id': pac.id,
                    'estado': 'EAMT', 
                    'hora_inicio_espera': formatear_numero(pac.tiempo_inicio_espera)
                })
        
        # 5. Paciente en cooperadora
        if paciente_en_cooperadora and not paciente_en_cooperadora.finalizado:
            objetos.append({
                'id': paciente_en_cooperadora.id,
                'estado': 'AC',
                'hora_inicio_espera': ""
            })
            
        # 6. Pacientes en cola cooperadora
        for pac in cola_cooperadora:
            if not pac.finalizado:
                objetos.append({
                    'id': pac.id,
                    'estado': 'EAC',
                    'hora_inicio_espera': ""
                })
                
        return objetos
    
    def registrar_estado(evento: str):
        objetos = obtener_objetos_temporales()
        
        # Determinar estado de mesa (considerando llamadas)
        estado_mesa = 'Libre'
        if llamada_en_atencion:
            estado_mesa = 'AtendendoLlamada'
        elif not mesa_libre:
            estado_mesa = 'Ocupado'
        
        # Contar colas
        cola_pacientes_count = len(cola_pacientes_mesa_retorno) + len(cola_pacientes_mesa_normal)
        cola_llamadas_count = len(cola_llamadas)
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
            
            # Estados de empleados MEJORADOS
            'Empleado_mesa_estado': estado_mesa,
            'Empleado_mesa_cola_pacientes': cola_pacientes_count,
            'Empleado_mesa_cola_llamadas': cola_llamadas_count,  # NUEVA COLUMNA
            'Empleado_cooperadora_estado': 'Libre' if cooperadora_libre else 'Ocupado',
            'Empleado_cooperadora_cola': cola_coop_count,
            
            'Cantidad_de_llamadas_perdidas_por_tener_la_linea_ocupada': llamadas_perdidas,
            'Acum_tiempo_de_espera': formatear_numero(tiempo_espera_acumulado),
            'Cantidad_de_personas_que_esperan': cantidad_personas_esperaron
        }
        
        # OBJETOS TEMPORALES DINÁMICOS - SIN LÍMITE
        for i, obj in enumerate(objetos):
            fila[f'Objeto_{i+1}_Estado'] = obj['estado']
            fila[f'Objeto_{i+1}_Hora_inicio_espera'] = obj['hora_inicio_espera']
        
        vector_estado.append(fila)
    
    # Registrar estado inicial
    registrar_estado("Inicializacion")
    
    # Función auxiliar para atender siguiente en mesa
    def atender_siguiente_en_mesa():
        """NUEVA LÓGICA: Prioridad Llamadas > Pacientes Retorno > Pacientes Normales"""
        nonlocal mesa_libre, paciente_en_mesa, llamada_en_atencion
        nonlocal ultimo_rnd_obra_social, ultimo_obra_social_str
        nonlocal ultimo_rnd_atencion, ultimo_tiempo_atencion, fin_atencion, fin_informe_obra_social
        nonlocal ultimo_rnd_llamada, ultimo_tiempo_llamada, fin_llamada
        nonlocal tiempo_espera_acumulado, cantidad_personas_esperaron
        
        # PRIORIDAD 1: Llamadas esperando
        if cola_llamadas:
            mesa_libre = False
            llamada_en_atencion = cola_llamadas.pop(0)
            llamada_en_atencion.estado_actual = 'SIENDO_ATENDIDA'
            
            ultimo_rnd_llamada, ultimo_tiempo_llamada = gen_uniforme(c1, c2)
            fin_llamada = reloj + ultimo_tiempo_llamada
            return
        
        # PRIORIDAD 2: Pacientes de retorno
        paciente_a_atender = None
        if cola_pacientes_mesa_retorno:
            paciente_a_atender = cola_pacientes_mesa_retorno.pop(0)
            tiempo_espera = reloj - paciente_a_atender.tiempo_inicio_espera
            tiempo_espera_acumulado += tiempo_espera
            cantidad_personas_esperaron += 1
        # PRIORIDAD 3: Pacientes normales
        elif cola_pacientes_mesa_normal:
            paciente_a_atender = cola_pacientes_mesa_normal.pop(0)
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
    
    # MOTOR DE SIMULACIÓN MEJORADO
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
        
        # PROCESAMIENTO DE EVENTOS MEJORADO
        if proximo_evento == 'llegada_paciente':
            # Generar próxima llegada
            ultimo_rnd_llegada, ultimo_tiempo_entre_llegadas = gen_exponencial(media_llegada)
            prox_llegada_paciente = reloj + ultimo_tiempo_entre_llegadas
            
            # Crear nuevo paciente
            nuevo_pac = Paciente(f"P{next(contador_pacientes)}", reloj)
            nuevo_pac.estado_actual = 'EAMT'
            cola_pacientes_mesa_normal.append(nuevo_pac)
            todos_los_objetos.append(nuevo_pac)  # Agregar a lista global
            
            registrar_estado("llegada_paciente")
            
        elif proximo_evento == 'llegada_llamada':
            # Programar próxima llamada
            prox_llegada_llamada = reloj + intervalo_llamadas
            
            # NUEVA LÓGICA: Llamada espera si mesa ocupada, se pierde solo si hay otra llamada
            if llamada_en_atencion or len(cola_llamadas) > 0:
                # Ya hay llamada siendo atendida O hay llamadas esperando -> se pierde
                llamadas_perdidas += 1
                ultimo_rnd_llamada = None
                ultimo_tiempo_llamada = None
                registrar_estado("llegada_llamada")
            elif not mesa_libre:
                # Mesa ocupada por paciente -> llamada espera en cola
                nueva_llamada = Llamada(f"L{next(contador_llamadas)}", reloj)
                cola_llamadas.append(nueva_llamada)
                todos_los_objetos.append(nueva_llamada)  # Agregar a lista global
                ultimo_rnd_llamada = None
                ultimo_tiempo_llamada = None
                registrar_estado("llegada_llamada")
            else:
                # Mesa libre -> atender llamada inmediatamente
                nueva_llamada = Llamada(f"L{next(contador_llamadas)}", reloj)
                llamada_en_atencion = nueva_llamada
                nueva_llamada.estado_actual = 'SIENDO_ATENDIDA'
                todos_los_objetos.append(nueva_llamada)  # Agregar a lista global
                mesa_libre = False
                
                ultimo_rnd_llamada, ultimo_tiempo_llamada = gen_uniforme(c1, c2)
                fin_llamada = reloj + ultimo_tiempo_llamada
                registrar_estado("llegada_llamada")
                
        elif proximo_evento == 'fin_llamada':
            if llamada_en_atencion:
                # LLAMADA TERMINA COMPLETAMENTE - NO SE REUSA
                llamada_en_atencion = None
            
            fin_llamada = float('inf')
            ultimo_rnd_llamada = None
            ultimo_tiempo_llamada = None
            
            atender_siguiente_en_mesa()
            
            registrar_estado("fin_llamada")
            
        elif proximo_evento == 'fin_atencion':
            if paciente_en_mesa:
                # PACIENTE TERMINA COMPLETAMENTE - NO SE REUSA
                paciente_en_mesa.finalizar()
                paciente_en_mesa = None
            
            fin_atencion = float('inf')
            atender_siguiente_en_mesa()
            registrar_estado("fin_atencion")
            
        elif proximo_evento == 'fin_informe_obra_social':
            if paciente_en_mesa:
                paciente_en_mesa.estado_actual = 'EAC'
                cola_cooperadora.append(paciente_en_mesa)
                paciente_en_mesa = None
            
            fin_informe_obra_social = float('inf')
            atender_siguiente_en_mesa()
            registrar_estado("fin_informe_obra_social")
            
        elif proximo_evento == 'fin_abono_consulta':
            if paciente_en_cooperadora:
                paciente_en_cooperadora.marcar_retorno_cooperadora()
                paciente_en_cooperadora.estado_actual = 'EAMT'
                paciente_en_cooperadora.tiempo_inicio_espera = reloj
                cola_pacientes_mesa_retorno.append(paciente_en_cooperadora)
                paciente_en_cooperadora = None
            
            fin_abono_consulta = float('inf')
            atender_siguiente_paciente_cooperadora()
            registrar_estado("fin_abono_consulta")
    
    # PROCESAMIENTO DE RESULTADOS MEJORADO
    df_vector = pd.DataFrame(vector_estado)
    tiempo_promedio_espera = tiempo_espera_acumulado / cantidad_personas_esperaron if cantidad_personas_esperaron > 0 else 0.0
    
    return df_vector, tiempo_promedio_espera, llamadas_perdidas

# -----------------------------------------------------------
# Interfaz Streamlit MANTENIDA INTACTA
# -----------------------------------------------------------

def main():
    st.set_page_config(page_title="Centro de Salud - Simulación Mejorada", layout="wide")
    
    st.title("🏥 Centro de Salud – Ejercicio 72 (VERSIÓN MEJORADA)")

    # Sidebar con parámetros (MANTENIDO IGUAL)
    st.sidebar.markdown("## ⚙️ Parámetros de Simulación")
    
    # Parámetros básicos
    media_llegada = st.sidebar.number_input("Media entre llegadas (min)", 0.5, 10.0, 3.0, 0.1)
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        a1 = st.sidebar.number_input("Mesa - Mín (min)", 0.1, 5.0, 1.0, 0.1)
        a2 = st.sidebar.number_input("Coop - Mín (min)", 0.1, 5.0, 0.8, 0.1)
        c1 = st.sidebar.number_input("Llamada - Mín (min)", 0.1, 3.0, 0.5, 0.1)
    with col2:
        b1 = st.sidebar.number_input("Mesa - Máx (min)", 0.1, 5.0, 3.0, 0.1)
        b2 = st.sidebar.number_input("Coop - Máx (min)", 0.1, 5.0, 2.4, 0.1)
        c2 = st.sidebar.number_input("Llamada - Máx (min)", 0.1, 3.0, 1.5, 0.1)
    
    p_sin_obra = st.sidebar.slider("% Sin obra social", 0.0, 1.0, 0.45, 0.05)
    intervalo_llamadas = st.sidebar.number_input("Intervalo llamadas (min)", 1.0, 10.0, 3.0, 0.1)
    
    # Condiciones iniciales
    st.sidebar.markdown("### 🎯 Condiciones Iniciales")
    ini_mesa = st.sidebar.number_input("Pacientes esperando turno", 0, 20, 4)
    ini_coop = st.sidebar.number_input("Pacientes esperando pago", 0, 20, 2)
    min_llamada = st.sidebar.number_input("Minutos para próxima llamada", 0.0, 10.0, 2.0, 0.1)
    
    tiempo_sim = st.sidebar.number_input("Tiempo de simulación (min)", 10, 500, 60)
    
    # Botón de simulación
    if st.sidebar.button("Ejecutar Simulación MEJORADA", type="primary"):
        
        # Ejecutar simulación
        with st.spinner("Ejecutando simulación mejorada con colas separadas..."):
            df_resultado, tiempo_promedio, llamadas_perdidas = simular_centro_salud(
                media_llegada=media_llegada,
                a1=a1, b1=b1, a2=a2, b2=b2,
                p_sin_obra=p_sin_obra,
                intervalo_llamadas=intervalo_llamadas,
                c1=c1, c2=c2,
                ini_pacientes_mesa=ini_mesa,
                ini_pacientes_coop=ini_coop,
                minutos_proxima_llamada=min_llamada,
                tiempo_simulacion=tiempo_sim
            )
        
        # Vector de estado (VISUAL MANTENIDO IGUAL)
        st.markdown("## 📊 Simulacion Realizada")

        # Crear DataFrame con multi-índice completo (MANTENIDO IGUAL)
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
        
        # Objetos permanentes MEJORADOS
        nuevas_columnas.extend([
            ('', 'Empleado mesa de turno', 'Estado'),
            ('', 'Empleado mesa de turno', 'Cola Pacientes'),
            ('', 'Empleado mesa de turno', 'Cola Llamadas'),  # NUEVA COLUMNA
            ('', 'Empleado cooperadora', 'Estado'),
            ('', 'Empleado cooperadora', 'Cola')
        ])
        
        # Estadísticas
        nuevas_columnas.extend([
            ('', 'Estadística A)', 'Cantidad de llamadas perdidas por tener la línea ocupada'),
            ('', 'Estadística B)', 'Acum tiempo de espera'),
            ('', 'Estadística B)', 'Cantidad de personas que esperan')
        ])
        
        # Objetos temporales DINÁMICOS - Sin límite fijo
        # Primero determinamos cuántos objetos tenemos como máximo
        max_objetos = 0
        for _, fila in df_multi.iterrows():
            contador = 1
            while f'Objeto_{contador}_Estado' in fila and fila[f'Objeto_{contador}_Estado'] != "":
                contador += 1
            max_objetos = max(max_objetos, contador - 1)
        
        # Crear columnas para todos los objetos necesarios
        for i in range(1, max_objetos + 1):
            if i <= 10:
                etiqueta = f"Paciente/Llamada {i}"  # Cambio de etiqueta para reflejar nueva funcionalidad
            else:
                etiqueta = f"Objeto {i}"
            nuevas_columnas.extend([
                ('', etiqueta, 'Estado'),
                ('', etiqueta, 'Hora inicio espera')
            ])

        # Crear mapeo de columnas antiguas a nuevas
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
        
        # Agregar columnas de objetos temporales dinámicamente
        for i in range(1, max_objetos + 1):
            columnas_originales.extend([
                f'Objeto_{i}_Estado',
                f'Objeto_{i}_Hora_inicio_espera'
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
                help="Llamadas perdidas SOLO cuando ya hay otra llamada en el sistema"
            )
        with col2:
            st.metric(
                "⏱️ B) Tiempo Promedio de Espera", 
                value=f"{tiempo_promedio:.3f} min",
                help="Tiempo promedio de espera de pacientes en colas"
            )
        
        
    

if __name__ == "__main__":
    main()