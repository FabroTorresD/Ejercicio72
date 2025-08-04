# Ejercicio72

Este proyecto simula el proceso de atención de pacientes en un centro de salud utilizando un enfoque de simulación de eventos discretos. La aplicación está desarrollada en **Python**, y hace uso de **Streamlit** para la interfaz interactiva y **Pandas** para la manipulación y presentación de datos.

## Descripción

* Los pacientes llegan con un tiempo entre llegadas distribuido exponencialmente (media configurable).
* Un solo empleado en la mesa de turnos atiende a los pacientes con tiempos uniformes.
* El 45% de los pacientes sin obra social debe pasar por la cooperadora para abonar la consulta.
* El sistema gestiona también las reservas por llamada telefónica, con llamadas que arriban cada 3 minutos y tienen duración uniforme.

## Tecnologías

* **Python 3.9+**
* **Streamlit** para la interfaz web interactiva
* **Pandas** para estructuras de datos y reporte de resultados
* **Math** y **random** para generación de números aleatorios

## Instalación

1. Clonar el repositorio:

   ```bash
   git clone <URL-del-repositorio>
   cd Ejercicio72
   ```
2. Crear un entorno virtual e instalar dependencias:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # En macOS/Linux
   # o .\.venv\Scripts\activate en Windows
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

## Uso

Para ejecutar la simulación y ver el vector de estado en tiempo real:

```bash
streamlit run main.py
```

En la barra lateral podrás configurar:

* Media entre llegadas de pacientes
* Rangos de tiempo para atención en mesa y cooperadora
* Proporción de pacientes sin obra social
* Parámetros de llamadas telefónicas
* Escenario inicial (pacientes en espera)
* Duración de la simulación

Los resultados se mostrarán en una tabla con el vector de estado y métricas finales (llamadas perdidas y tiempo promedio de espera).

## Estructura de directorios

```text
Ejercicio72/
├── main.py             # Código principal de la simulación
├── requirements.txt    # Dependencias del proyecto
├── README.md           # Documentación del proyecto
└── data/               # (Opcional) Carpeta para datos de entrada o resultados
```

## Contribuciones

Si deseas mejorar o ampliar este simulador, ¡eres bienvenido! Haz un fork, crea una rama con tu mejora y envía un Pull Request.

## Licencia

Este proyecto está bajo la licencia MIT. Consulta el archivo `LICENSE` para más detalles.
