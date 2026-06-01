# -*- coding: utf-8 -*-
# =============================================================================
# SIMULACIÓN BANCO DE COLOMBIA - OPTIMIZACIÓN DE CAJEROS
# Materia: Simulación | Ingeniería de Software y Datos
# Modelo: M/M/1 por cajero (colas independientes)
# Jornada: 8 horas/día | 10 réplicas mínimo
# =============================================================================
#
# INSTRUCCIONES PARA GOOGLE COLAB:
#   1. Sube este archivo a Colab o copia el contenido en celdas.
#   2. Ejecuta la celda de instalación de dependencias primero.
#   3. Ejecuta las celdas en orden secuencial.
#
# Para instalar dependencias en Colab, ejecuta:
#   !pip install numpy pandas matplotlib seaborn scipy openpyxl python-docx
# =============================================================================

# -----------------------------------------------------------------------------
# SECCIÓN 1: IMPORTACIONES Y CONFIGURACIÓN
# -----------------------------------------------------------------------------

import sys
import io
# Forzar salida UTF-8 en Windows para evitar UnicodeEncodeError
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from scipy import stats
import warnings

warnings.filterwarnings('ignore')

# Estilo visual para las gráficas
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = '#f8f9fa'
plt.rcParams['axes.grid'] = True
plt.rcParams['grid.alpha'] = 0.4
sns.set_palette("husl")

print("Librerías importadas correctamente.")

# -----------------------------------------------------------------------------
# SECCIÓN 2: PARÁMETROS DEL MODELO
# Fuente: Tabla 1 y Tabla 2 del enunciado
# -----------------------------------------------------------------------------

# --- Probabilidad de tipo de acción ---
# 70% de los usuarios hacen retiros, 30% consignaciones o pagos
PROB_RETIRO = 0.70
PROB_PAGO   = 0.30

# --- Probabilidades de subtipo de usuario (Tabla 2) ---
# Orden: [Rápido, Normal, Lento, Muy lento]
PROB_TIPO_RETIRO = [0.23, 0.40, 0.17, 0.20]
PROB_TIPO_PAGO   = [0.10, 0.20, 0.30, 0.40]

# --- Tiempos de servicio: media exponencial en minutos (Tabla 1) ---
# Orden: [Rápido, Normal, Lento, Muy lento]
SERVICIO_RETIRO = [1, 2, 3, 4]   # Retiro
SERVICIO_PAGO   = [3, 3, 5, 7]   # Consignación/Pago

# --- Tiempos de llegada: media exponencial en minutos (Tabla 1) ---
# Representa el tiempo medio entre llegadas de ese tipo de usuario
LLEGADA_RETIRO = [1, 2, 3, 3]    # Retiro
LLEGADA_PAGO   = [1, 2, 3, 4]    # Consignación/Pago

# --- Nombres descriptivos de los subtipos ---
NOMBRES_TIPO = ['Rápido', 'Normal', 'Lento', 'Muy lento']

# --- Parámetros de la simulación ---
HORAS_OPERACION   = 8                    # Horas de funcionamiento diario
TIEMPO_SIMULACION = HORAS_OPERACION * 60 # Minutos totales (480 min)
NUM_REPLICAS      = 10                   # Número de réplicas a ejecutar
NUM_CAJEROS       = 3                    # Total de cajeros disponibles

print(f"Parámetros cargados: {HORAS_OPERACION}h/día | {NUM_CAJEROS} cajeros | {NUM_REPLICAS} réplicas")


# -----------------------------------------------------------------------------
# SECCIÓN 3: CLASE CAJERO (Modelo M/M/1)
# Cada cajero es una cola independiente con un único servidor (M/M/1).
# Mantiene su propia lista de espera y registro de clientes atendidos.
# -----------------------------------------------------------------------------

class Cajero:
    """
    Representa un cajero bancario como modelo M/M/1 independiente.

    Atributos
    ----------
    cajero_id      : Identificador numérico del cajero.
    tipo_atencion  : 'retiro', 'pago', o 'mixto' (sirve ambos tipos).
    libre_en       : Instante (en minutos) en que el cajero queda desocupado.
    cola           : Lista FIFO de clientes esperando turno.
    clientes_atendidos : Registro de todos los clientes servidos por este cajero.
    """

    def __init__(self, cajero_id: int, tipo_atencion: str = 'mixto'):
        self.cajero_id      = cajero_id
        self.tipo_atencion  = tipo_atencion
        self.libre_en       = 0.0   # El cajero comienza libre en t=0
        self.cola           = []    # Tuplas: (t_llegada, tipo_accion, tipo_usuario)
        self.clientes_atendidos = []

    def esta_libre(self, tiempo_actual: float) -> bool:
        """Retorna True si el cajero no tiene cliente en servicio."""
        return self.libre_en <= tiempo_actual

    def longitud_cola(self) -> int:
        """Número de clientes esperando (sin contar al que se atiende)."""
        return len(self.cola)

    def atender(self, tiempo_actual: float, tipo_accion: str,
                tipo_usuario: int, tiempo_espera: float = 0.0) -> float:
        """
        Registra la atención de un cliente y calcula el fin del servicio.

        Parámetros
        ----------
        tiempo_actual : Momento en que inicia la atención.
        tipo_accion   : 'retiro' o 'pago'.
        tipo_usuario  : Índice 0-3 (Rápido, Normal, Lento, Muy lento).
        tiempo_espera : Minutos que esperó en cola (0 si fue directo).

        Retorna
        -------
        float : Instante en que termina el servicio (libre_en actualizado).
        """
        # Generar tiempo de servicio exponencial según tipo de usuario
        if tipo_accion == 'retiro':
            media_servicio = SERVICIO_RETIRO[tipo_usuario]
        else:
            media_servicio = SERVICIO_PAGO[tipo_usuario]

        tiempo_servicio = np.random.exponential(media_servicio)

        # El servicio inicia cuando el cajero queda libre (o ahora, si ya está libre)
        inicio_servicio = max(self.libre_en, tiempo_actual)
        self.libre_en   = inicio_servicio + tiempo_servicio

        # Guardar registro del cliente
        self.clientes_atendidos.append({
            'cajero'              : self.cajero_id,
            'tipo_atencion_cajero': self.tipo_atencion,
            'tipo_accion'         : tipo_accion,
            'tipo_usuario'        : tipo_usuario,
            'nombre_tipo'         : NOMBRES_TIPO[tipo_usuario],
            'tiempo_llegada'      : tiempo_actual - tiempo_espera,
            'tiempo_espera'       : tiempo_espera,
            'tiempo_servicio'     : tiempo_servicio,
            'tiempo_sistema'      : tiempo_espera + tiempo_servicio,
        })

        return self.libre_en


# -----------------------------------------------------------------------------
# SECCIÓN 4: FUNCIÓN DE GENERACIÓN DE CLIENTES
# Determina el tipo de acción y subtipo de cada cliente entrante.
# -----------------------------------------------------------------------------

def generar_cliente() -> tuple:
    """
    Genera un cliente con tipo de acción y subtipo aleatorios.

    El proceso sigue la cadena de decisión del enunciado:
      1. Elegir acción: retiro (70%) o pago (30%).
      2. Elegir subtipo: Rápido/Normal/Lento/Muy lento según probabilidades de Tabla 2.
      3. El tiempo hasta el siguiente cliente es exponencial con media de Tabla 1.

    Retorna
    -------
    tuple: (tipo_accion, tipo_usuario, media_llegada)
        tipo_accion  : 'retiro' o 'pago'
        tipo_usuario : 0=Rápido, 1=Normal, 2=Lento, 3=Muy lento
        media_llegada: media del tiempo hasta la siguiente llegada (min)
    """
    tipo_accion = 'retiro' if np.random.random() < PROB_RETIRO else 'pago'

    if tipo_accion == 'retiro':
        tipo_usuario  = np.random.choice([0, 1, 2, 3], p=PROB_TIPO_RETIRO)
        media_llegada = LLEGADA_RETIRO[tipo_usuario]
    else:
        tipo_usuario  = np.random.choice([0, 1, 2, 3], p=PROB_TIPO_PAGO)
        media_llegada = LLEGADA_PAGO[tipo_usuario]

    return tipo_accion, tipo_usuario, media_llegada


# -----------------------------------------------------------------------------
# SECCIÓN 5: MOTOR DE SIMULACIÓN (Orientado a Eventos Discretos)
# Implementa la lógica de simulación de un día bancario completo.
# -----------------------------------------------------------------------------

def simular_dia(cajeros_retiro_ids: list, cajeros_pago_ids: list,
                semilla: int = None) -> pd.DataFrame:
    """
    Simula un día completo de operación del banco con simulación de eventos discretos.

    Lógica principal:
    -----------------
    1. Se genera la primera llegada y se agenda como evento.
    2. En cada iteración se procesa el evento más próximo en el tiempo:
       - Si es 'llegada': se asigna al cajero apropiado (libre o cola más corta).
       - Si es 'fin_servicio': el cajero queda libre y atiende al siguiente en cola.
    3. El proceso continúa hasta superar TIEMPO_SIMULACION.

    Parámetros
    ----------
    cajeros_retiro_ids : Lista de IDs de cajeros dedicados a retiros.
    cajeros_pago_ids   : Lista de IDs de cajeros dedicados a pagos.
                         Si coincide con cajeros_retiro_ids, los cajeros son mixtos.
    semilla            : Semilla para reproducibilidad.

    Retorna
    -------
    pd.DataFrame con un registro por cada cliente atendido.
    """
    if semilla is not None:
        np.random.seed(semilla)

    # --- Crear instancias de cajeros ---
    # Se determina el tipo de atención según la asignación del escenario
    es_mixto = set(cajeros_retiro_ids) == set(cajeros_pago_ids)

    todos_cajeros = {}
    ids_unicos = set(cajeros_retiro_ids) | set(cajeros_pago_ids)

    for cid in ids_unicos:
        if es_mixto:
            tipo_at = 'mixto'
        elif cid in cajeros_retiro_ids and cid in cajeros_pago_ids:
            tipo_at = 'mixto'
        elif cid in cajeros_retiro_ids:
            tipo_at = 'retiro'
        else:
            tipo_at = 'pago'
        todos_cajeros[cid] = Cajero(cid, tipo_atencion=tipo_at)

    # --- Lista de eventos futuros ---
    # Formato de cada evento: (tiempo, tipo_evento, tipo_accion, tipo_usuario, cajero_id)
    # tipo_evento: 'llegada' | 'fin_servicio'
    eventos = []

    # --- Generar la primera llegada ---
    tipo_accion0, tipo_usuario0, media_llegada0 = generar_cliente()
    t_primera_llegada = np.random.exponential(media_llegada0)
    eventos.append((t_primera_llegada, 'llegada', tipo_accion0, tipo_usuario0, None))

    tiempo_actual = 0.0

    # --- Bucle principal de simulación ---
    while eventos:
        # Ordenar eventos por tiempo (próximo primero) y extraer el primero
        eventos.sort(key=lambda x: x[0])
        evento = eventos.pop(0)
        tiempo_actual = evento[0]

        # Detener si superamos el horario bancario
        if tiempo_actual > TIEMPO_SIMULACION:
            break

        tipo_evento  = evento[1]
        tipo_accion  = evento[2]
        tipo_usuario = evento[3]

        # ----------------------------------------------------------------
        # EVENTO: LLEGADA DE CLIENTE
        # ----------------------------------------------------------------
        if tipo_evento == 'llegada':

            # Determinar qué cajeros pueden atender este tipo de cliente
            if tipo_accion == 'retiro':
                ids_validos = cajeros_retiro_ids
            else:
                ids_validos = cajeros_pago_ids

            cajeros_validos = [todos_cajeros[i] for i in ids_validos]

            # Buscar un cajero libre
            cajero_elegido = None
            for c in cajeros_validos:
                if c.esta_libre(tiempo_actual):
                    cajero_elegido = c
                    break  # Primer cajero libre encontrado

            if cajero_elegido is not None:
                # Atender sin espera
                fin_servicio = cajero_elegido.atender(
                    tiempo_actual, tipo_accion, tipo_usuario, tiempo_espera=0.0
                )
                # Programar el fin del servicio
                eventos.append((fin_servicio, 'fin_servicio',
                                tipo_accion, tipo_usuario, cajero_elegido.cajero_id))
            else:
                # Todos ocupados: ir a la cola del cajero con menos clientes esperando
                cajero_elegido = min(cajeros_validos, key=lambda c: c.longitud_cola())
                cajero_elegido.cola.append((tiempo_actual, tipo_accion, tipo_usuario))

            # Generar la próxima llegada independientemente de la asignación
            tipo_accion_sig, tipo_usuario_sig, media_sig = generar_cliente()
            t_prox = tiempo_actual + np.random.exponential(media_sig)
            eventos.append((t_prox, 'llegada', tipo_accion_sig, tipo_usuario_sig, None))

        # ----------------------------------------------------------------
        # EVENTO: FIN DE SERVICIO
        # ----------------------------------------------------------------
        elif tipo_evento == 'fin_servicio':
            cajero_id = evento[4]
            cajero    = todos_cajeros[cajero_id]

            # Resetear disponibilidad del cajero
            cajero.libre_en = tiempo_actual

            # Si hay clientes en cola, atender al primero (FIFO)
            if cajero.cola:
                t_llegada_cola, ta_cola, tu_cola = cajero.cola.pop(0)
                tiempo_espera_cola = tiempo_actual - t_llegada_cola

                fin_servicio = cajero.atender(
                    tiempo_actual, ta_cola, tu_cola,
                    tiempo_espera=tiempo_espera_cola
                )
                eventos.append((fin_servicio, 'fin_servicio',
                                ta_cola, tu_cola, cajero.cajero_id))

    # --- Consolidar registros de todos los cajeros ---
    todos_registros = []
    for cajero in todos_cajeros.values():
        todos_registros.extend(cajero.clientes_atendidos)

    df = pd.DataFrame(todos_registros)
    return df


# -----------------------------------------------------------------------------
# SECCIÓN 6: EJECUTOR DE RÉPLICAS
# Corre múltiples simulaciones del mismo escenario para obtener estadísticas.
# -----------------------------------------------------------------------------

def ejecutar_replicas(cajeros_retiro_ids: list, cajeros_pago_ids: list,
                      num_replicas: int = 10,
                      nombre_escenario: str = '') -> pd.DataFrame:
    """
    Ejecuta múltiples réplicas independientes de la simulación.

    Cada réplica usa una semilla diferente para garantizar independencia
    estadística entre corridas manteniendo reproducibilidad.

    Parámetros
    ----------
    cajeros_retiro_ids : IDs de cajeros para retiros.
    cajeros_pago_ids   : IDs de cajeros para pagos.
    num_replicas       : Cantidad de réplicas a ejecutar (mínimo 10).
    nombre_escenario   : Etiqueta descriptiva del escenario.

    Retorna
    -------
    pd.DataFrame consolidado con columnas 'replica' y 'escenario'.
    """
    resultados = []

    for i in range(num_replicas):
        semilla = (i + 1) * 7  # Semillas reproducibles y distintas entre sí
        df_replica = simular_dia(cajeros_retiro_ids, cajeros_pago_ids, semilla=semilla)
        df_replica['replica']   = i + 1
        df_replica['escenario'] = nombre_escenario
        resultados.append(df_replica)
        print(f"  Réplica {i+1:02d}/{num_replicas} | Escenario: {nombre_escenario} | "
              f"Clientes: {len(df_replica)}")

    return pd.concat(resultados, ignore_index=True)


# -----------------------------------------------------------------------------
# SECCIÓN 7: ANÁLISIS DE RESULTADOS (5 puntos del enunciado)
# -----------------------------------------------------------------------------

def analizar_resultados(df: pd.DataFrame, nombre_escenario: str) -> dict:
    """
    Calcula las estadísticas requeridas para responder los 5 puntos del enunciado.

    Parámetros
    ----------
    df               : DataFrame con datos de todas las réplicas del escenario.
    nombre_escenario : Nombre para identificar el escenario en los reportes.

    Retorna
    -------
    dict con las métricas clave del escenario.
    """
    sep = "=" * 72
    print(f"\n{sep}")
    print(f"  ESCENARIO: {nombre_escenario}")
    print(sep)

    # ------------------------------------------------------------------
    # PUNTO 1: Cajero con menor y mayor tiempo promedio de atención
    # No se requiere segregar usuarios: se calcula sobre todos los clientes.
    # ------------------------------------------------------------------
    print("\n[PUNTO 1] Tiempo promedio de ATENCIÓN (servicio) por cajero")
    print("-" * 60)

    resumen_cajero = df.groupby('cajero').agg(
        Clientes_Atendidos=('tiempo_servicio', 'count'),
        T_Servicio_Prom=('tiempo_servicio', 'mean'),
        T_Espera_Prom=('tiempo_espera', 'mean'),
        T_Sistema_Prom=('tiempo_sistema', 'mean'),
        T_Servicio_Desv=('tiempo_servicio', 'std'),
    ).round(4)

    print(resumen_cajero.to_string())

    cajero_min_serv = resumen_cajero['T_Servicio_Prom'].idxmin()
    cajero_max_serv = resumen_cajero['T_Servicio_Prom'].idxmax()
    val_min = resumen_cajero.loc[cajero_min_serv, 'T_Servicio_Prom']
    val_max = resumen_cajero.loc[cajero_max_serv, 'T_Servicio_Prom']

    print(f"\n  >> Cajero con MENOR tiempo promedio de atención: "
          f"Cajero {cajero_min_serv} ({val_min:.4f} min)")
    print(f"  >> Cajero con MAYOR tiempo promedio de atención: "
          f"Cajero {cajero_max_serv} ({val_max:.4f} min)")

    # ------------------------------------------------------------------
    # PUNTO 2: Promedio de usuarios de cada tipo en la totalidad de cajeros
    # Se calcula el promedio entre réplicas del número de clientes por tipo.
    # ------------------------------------------------------------------
    print("\n[PUNTO 2] Promedio de usuarios por tipo (todos los cajeros, todas las réplicas)")
    print("-" * 60)

    conteo_por_rep = (df.groupby(['replica', 'tipo_accion', 'nombre_tipo'])
                        .size()
                        .reset_index(name='conteo'))

    promedio_tipo = (conteo_por_rep
                     .groupby(['tipo_accion', 'nombre_tipo'])['conteo']
                     .agg(['mean', 'std', 'min', 'max'])
                     .round(2))
    promedio_tipo.columns = ['Promedio', 'Desv_Std', 'Min', 'Max']

    print(promedio_tipo.to_string())

    # ------------------------------------------------------------------
    # PUNTO 3: Total de usuarios por tipo en cada réplica +
    #          Réplica con menor cantidad de usuarios
    # ------------------------------------------------------------------
    print("\n[PUNTO 3] Total de usuarios por tipo en cada réplica")
    print("-" * 60)

    pivot = (df.groupby(['replica', 'tipo_accion', 'nombre_tipo'])
               .size()
               .unstack(level=['tipo_accion', 'nombre_tipo'], fill_value=0))

    # Aplanar nombres de columnas multi-índice
    pivot.columns = [f"{a} - {t}" for a, t in pivot.columns]
    pivot['TOTAL_REPLICA'] = pivot.sum(axis=1)
    pivot = pivot.sort_index()

    print(pivot.to_string())

    replica_menos_usuarios = pivot['TOTAL_REPLICA'].idxmin()
    replica_mas_usuarios   = pivot['TOTAL_REPLICA'].idxmax()
    print(f"\n  >> Réplica con MENOR cantidad de usuarios: "
          f"Réplica {replica_menos_usuarios} "
          f"({pivot.loc[replica_menos_usuarios, 'TOTAL_REPLICA']} usuarios)")
    print(f"  >> Réplica con MAYOR cantidad de usuarios: "
          f"Réplica {replica_mas_usuarios} "
          f"({pivot.loc[replica_mas_usuarios, 'TOTAL_REPLICA']} usuarios)")

    # Detalle de la réplica con menor cantidad
    df_replica_min = df[df['replica'] == replica_menos_usuarios]
    print(f"\n  Detalle de la réplica {replica_menos_usuarios} (menor carga):")
    detalle_min = (df_replica_min.groupby(['tipo_accion', 'nombre_tipo'])
                                 .agg(Usuarios=('tipo_usuario','count'),
                                      T_Servicio_Prom=('tiempo_servicio','mean'),
                                      T_Espera_Prom=('tiempo_espera','mean'))
                                 .round(4))
    print(detalle_min.to_string())

    # ------------------------------------------------------------------
    # PUNTO 4: Necesidad de nuevo cajero
    # Criterios basados en teoría de colas M/M/c:
    #   - Tiempo de espera promedio global > 5 min: señal de congestión
    #   - Proporción de clientes con espera > 10 min > 15%
    #   - Factor de utilización ρ > 0.85 por cajero
    # ------------------------------------------------------------------
    print("\n[PUNTO 4] ¿Es necesario un nuevo cajero?")
    print("-" * 60)

    t_espera_global = df['tiempo_espera'].mean()
    t_espera_retiro = df[df['tipo_accion'] == 'retiro']['tiempo_espera'].mean()
    t_espera_pago   = df[df['tipo_accion'] == 'pago']['tiempo_espera'].mean()
    p_sin_espera    = (df['tiempo_espera'] == 0).mean() * 100
    p_espera_alta   = (df['tiempo_espera'] > 10).mean() * 100
    t_espera_p95    = df['tiempo_espera'].quantile(0.95)

    print(f"  T. espera promedio global  : {t_espera_global:.4f} min")
    print(f"  T. espera promedio retiros : {t_espera_retiro:.4f} min")
    print(f"  T. espera promedio pagos   : {t_espera_pago:.4f} min")
    print(f"  % clientes SIN espera      : {p_sin_espera:.2f}%")
    print(f"  % clientes con espera >10m : {p_espera_alta:.2f}%")
    print(f"  Percentil 95 de espera     : {t_espera_p95:.4f} min")

    print("\n  Tiempo de espera promedio por cajero:")
    print(resumen_cajero[['T_Espera_Prom']].round(4).to_string())

    # Decisión basada en criterios múltiples
    criterio1 = t_espera_global > 5
    criterio2 = p_espera_alta > 15
    criterio3 = t_espera_p95 > 15

    necesita_cajero = criterio1 or criterio2 or criterio3

    print(f"\n  Criterio 1 (T_espera > 5 min)  : {'SUPERA' if criterio1 else 'OK'} "
          f"({t_espera_global:.4f} min)")
    print(f"  Criterio 2 (>15% espera >10min): {'SUPERA' if criterio2 else 'OK'} "
          f"({p_espera_alta:.2f}%)")
    print(f"  Criterio 3 (P95 espera >15 min): {'SUPERA' if criterio3 else 'OK'} "
          f"({t_espera_p95:.4f} min)")
    print(f"\n  >> ¿Se necesita cajero adicional?: {'SÍ' if necesita_cajero else 'NO'}")

    return {
        'resumen_cajero'       : resumen_cajero,
        'promedio_tipo'        : promedio_tipo,
        'pivot_replicas'       : pivot,
        'replica_min'          : replica_menos_usuarios,
        't_espera_global'      : t_espera_global,
        't_espera_retiro'      : t_espera_retiro,
        't_espera_pago'        : t_espera_pago,
        'p_sin_espera'         : p_sin_espera,
        'p_espera_alta'        : p_espera_alta,
        'necesita_cajero'      : necesita_cajero,
    }


# -----------------------------------------------------------------------------
# SECCIÓN 8: VISUALIZACIONES
# Genera 6 gráficas para el análisis visual de los resultados.
# -----------------------------------------------------------------------------

def generar_graficas(df_base: pd.DataFrame, df_A: pd.DataFrame,
                     df_B: pd.DataFrame, comparacion: pd.DataFrame,
                     stats_base: dict, stats_A: dict, stats_B: dict) -> None:
    """
    Genera y guarda un panel de 6 gráficas con los resultados clave.

    Gráficas incluidas:
    -------------------
    1. Boxplot del tiempo de espera por escenario.
    2. Barras comparativas de espera por tipo de acción y escenario.
    3. Clientes atendidos por réplica (escenario base).
    4. Distribución de subtipos de usuario (escenario base).
    5. Tiempo de servicio promedio por cajero (escenarios A y B).
    6. Comparación de métricas globales por escenario.
    """
    fig, axes = plt.subplots(2, 3, figsize=(20, 13))
    fig.suptitle('Simulación Banco de Colombia\nAnálisis de Optimización de Cajeros',
                 fontsize=16, fontweight='bold', y=1.01)

    # --- Gráfica 1: Boxplot tiempo de espera por escenario ---
    ax1 = axes[0, 0]
    datos_box = [df_base['tiempo_espera'].values,
                 df_A['tiempo_espera'].values,
                 df_B['tiempo_espera'].values]
    bp = ax1.boxplot(datos_box, labels=['Base\n(3 Mixtos)', 'A: 1R+2P', 'B: 2R+1P'],
                     patch_artist=True, notch=False)
    colores_box = ['#4CAF50', '#2196F3', '#FF5722']
    for patch, color in zip(bp['boxes'], colores_box):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    ax1.axhline(y=5, color='red', linestyle='--', linewidth=1.5, label='Umbral 5 min')
    ax1.set_title('Distribución del Tiempo de Espera\npor Escenario', fontsize=11)
    ax1.set_ylabel('Tiempo de espera (min)')
    ax1.set_xlabel('Escenario')
    ax1.legend(fontsize=9)

    # --- Gráfica 2: Barras comparativas espera por tipo de acción ---
    ax2 = axes[0, 1]
    escenarios_names = ['Base\n(3 Mixtos)', 'A: 1R+2P', 'B: 2R+1P']
    t_retiro = [
        df_base[df_base.tipo_accion == 'retiro']['tiempo_espera'].mean(),
        df_A[df_A.tipo_accion == 'retiro']['tiempo_espera'].mean(),
        df_B[df_B.tipo_accion == 'retiro']['tiempo_espera'].mean()
    ]
    t_pago = [
        df_base[df_base.tipo_accion == 'pago']['tiempo_espera'].mean(),
        df_A[df_A.tipo_accion == 'pago']['tiempo_espera'].mean(),
        df_B[df_B.tipo_accion == 'pago']['tiempo_espera'].mean()
    ]
    x    = np.arange(len(escenarios_names))
    ancho = 0.35
    ax2.bar(x - ancho/2, t_retiro, ancho, label='Retiro',        color='#2196F3', alpha=0.85)
    ax2.bar(x + ancho/2, t_pago,   ancho, label='Pago/Consig.',  color='#FF7043', alpha=0.85)
    ax2.set_title('Tiempo Promedio de Espera\npor Tipo de Acción y Escenario', fontsize=11)
    ax2.set_ylabel('Tiempo promedio (min)')
    ax2.set_xticks(x)
    ax2.set_xticklabels(escenarios_names)
    ax2.legend()
    for bars, vals in [(ax2.containers[0], t_retiro), (ax2.containers[1], t_pago)]:
        for bar, v in zip(bars, vals):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                     f'{v:.2f}', ha='center', va='bottom', fontsize=8)

    # --- Gráfica 3: Clientes por réplica (escenario base) ---
    ax3 = axes[0, 2]
    clientes_rep = df_base.groupby('replica').size()
    colores_bars = ['#4CAF50' if v == clientes_rep.min()
                    else '#F44336' if v == clientes_rep.max()
                    else '#78909C' for v in clientes_rep.values]
    ax3.bar(clientes_rep.index, clientes_rep.values, color=colores_bars, edgecolor='white')
    ax3.axhline(y=clientes_rep.mean(), color='navy', linestyle='--', linewidth=1.5,
                label=f'Promedio: {clientes_rep.mean():.1f}')
    ax3.set_title('Clientes Atendidos por Réplica\n(Escenario Base - 3 Cajeros Mixtos)',
                  fontsize=11)
    ax3.set_xlabel('Réplica')
    ax3.set_ylabel('Número de clientes')
    ax3.set_xticks(clientes_rep.index)
    ax3.legend()
    min_patch = mpatches.Patch(color='#4CAF50', label=f'Mínimo (R{clientes_rep.idxmin()})')
    max_patch = mpatches.Patch(color='#F44336', label=f'Máximo (R{clientes_rep.idxmax()})')
    ax3.legend(handles=[ax3.get_legend_handles_labels()[0][0], min_patch, max_patch],
               fontsize=8)

    # --- Gráfica 4: Distribución de subtipos de usuario ---
    ax4 = axes[1, 0]
    dist_tipos = (df_base.groupby(['tipo_accion', 'nombre_tipo'])
                         .size()
                         .reset_index(name='n'))
    dist_tipos['etiqueta'] = dist_tipos['tipo_accion'].str.capitalize() + '\n' + dist_tipos['nombre_tipo']
    paleta = ['#1565C0', '#42A5F5', '#90CAF9', '#BBDEFB',
              '#B71C1C', '#EF5350', '#EF9A9A', '#FFCDD2']
    bars4 = ax4.bar(range(len(dist_tipos)), dist_tipos['n'].values,
                    color=paleta[:len(dist_tipos)], edgecolor='white', linewidth=0.8)
    ax4.set_xticks(range(len(dist_tipos)))
    ax4.set_xticklabels(dist_tipos['etiqueta'].values, fontsize=8)
    ax4.set_title('Total Usuarios por Subtipo\n(Escenario Base - Todas las Réplicas)', fontsize=11)
    ax4.set_ylabel('Total de usuarios')
    for bar in bars4:
        ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                 str(int(bar.get_height())), ha='center', va='bottom', fontsize=8)

    # --- Gráfica 5: Tiempo de servicio por cajero (escenarios A y B) ---
    ax5 = axes[1, 1]
    t_serv_A = df_A.groupby('cajero')['tiempo_servicio'].mean()
    t_serv_B = df_B.groupby('cajero')['tiempo_servicio'].mean()
    t_esp_A  = df_A.groupby('cajero')['tiempo_espera'].mean()
    t_esp_B  = df_B.groupby('cajero')['tiempo_espera'].mean()

    ax5.plot(t_serv_A.index, t_serv_A.values, 'o-',  label='Servicio Esc. A', color='#2196F3', lw=2, ms=8)
    ax5.plot(t_serv_B.index, t_serv_B.values, 's--', label='Servicio Esc. B', color='#FF5722', lw=2, ms=8)
    ax5.plot(t_esp_A.index,  t_esp_A.values,  'o:',  label='Espera Esc. A',   color='#90CAF9', lw=1.5, ms=6)
    ax5.plot(t_esp_B.index,  t_esp_B.values,  's:',  label='Espera Esc. B',   color='#FFAB91', lw=1.5, ms=6)
    ax5.set_title('Tiempo Promedio de Servicio y Espera\npor Cajero', fontsize=11)
    ax5.set_xlabel('ID Cajero')
    ax5.set_ylabel('Tiempo promedio (min)')
    ax5.set_xticks([0, 1, 2])
    ax5.legend(fontsize=8)

    # --- Gráfica 6: Comparación global de escenarios ---
    ax6 = axes[1, 2]
    metricas_labels = ['T. Espera\nRetiro', 'T. Espera\nPago', 'T. Espera\nGlobal']
    metricas_cols   = ['T_Espera_Retiro', 'T_Espera_Pago', 'T_Espera_Global']
    colores_esc = ['#4CAF50', '#2196F3', '#FF5722']
    esc_labels  = comparacion['Escenario'].tolist()
    x6 = np.arange(len(metricas_labels))
    ancho6 = 0.25
    for i, (esc, color) in enumerate(zip(esc_labels, colores_esc)):
        vals = comparacion.loc[i, metricas_cols].values.astype(float)
        ax6.bar(x6 + i*ancho6, vals, ancho6, label=esc, color=color, alpha=0.85)
    ax6.set_title('Comparación de Tiempos de Espera\npor Escenario', fontsize=11)
    ax6.set_ylabel('Tiempo promedio (min)')
    ax6.set_xticks(x6 + ancho6)
    ax6.set_xticklabels(metricas_labels, fontsize=9)
    ax6.legend(fontsize=8)

    plt.tight_layout()
    nombre_archivo = 'graficas_simulacion_banco.png'
    plt.savefig(nombre_archivo, dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.show()
    print(f"\nGráficas guardadas en '{nombre_archivo}'")


# -----------------------------------------------------------------------------
# SECCIÓN 9: FUNCIÓN PRINCIPAL
# Orquesta los tres escenarios, analiza resultados y toma la decisión final.
# -----------------------------------------------------------------------------

def main():
    """
    Punto de entrada de la simulación.

    Escenarios evaluados:
    ---------------------
    - Base  : 3 cajeros mixtos (atienden retiros y pagos).
    - Esc. A: 1 cajero exclusivo para retiros + 2 cajeros para pagos.
    - Esc. B: 2 cajeros exclusivos para retiros + 1 cajero para pagos.
    """
    sep_doble = "=" * 72
    print(sep_doble)
    print("  SIMULACIÓN BANCO DE COLOMBIA")
    print("  Optimización de Asignación de Cajeros - Modelo M/M/1")
    print(sep_doble)
    print(f"\n  Configuración: {NUM_REPLICAS} réplicas | "
          f"{HORAS_OPERACION}h/día ({TIEMPO_SIMULACION} min) | "
          f"{NUM_CAJEROS} cajeros\n")

    # ------------------------------------------------------------------
    # ESCENARIO BASE: 3 cajeros mixtos (sirven retiros y pagos)
    # Los tres cajeros atienden cualquier tipo de cliente.
    # ------------------------------------------------------------------
    print(">>> ESCENARIO BASE: 3 cajeros mixtos")
    df_base = ejecutar_replicas(
        cajeros_retiro_ids=[0, 1, 2],
        cajeros_pago_ids  =[0, 1, 2],
        num_replicas=NUM_REPLICAS,
        nombre_escenario='Base: 3 Cajeros Mixtos'
    )
    stats_base = analizar_resultados(df_base, 'Base: 3 Cajeros Mixtos')

    # ------------------------------------------------------------------
    # ESCENARIO A: 1 cajero retiros + 2 cajeros pagos
    # Cajero 0 atiende exclusivamente retiros.
    # Cajeros 1 y 2 atienden exclusivamente pagos/consignaciones.
    # ------------------------------------------------------------------
    print("\n\n>>> ESCENARIO A: 1 cajero retiros | 2 cajeros pagos")
    df_A = ejecutar_replicas(
        cajeros_retiro_ids=[0],
        cajeros_pago_ids  =[1, 2],
        num_replicas=NUM_REPLICAS,
        nombre_escenario='A: 1 Retiro + 2 Pagos'
    )
    stats_A = analizar_resultados(df_A, 'A: 1 Retiro + 2 Pagos')

    # ------------------------------------------------------------------
    # ESCENARIO B: 2 cajeros retiros + 1 cajero pagos
    # Cajeros 0 y 1 atienden exclusivamente retiros.
    # Cajero 2 atiende exclusivamente pagos/consignaciones.
    # ------------------------------------------------------------------
    print("\n\n>>> ESCENARIO B: 2 cajeros retiros | 1 cajero pagos")
    df_B = ejecutar_replicas(
        cajeros_retiro_ids=[0, 1],
        cajeros_pago_ids  =[2],
        num_replicas=NUM_REPLICAS,
        nombre_escenario='B: 2 Retiros + 1 Pago'
    )
    stats_B = analizar_resultados(df_B, 'B: 2 Retiros + 1 Pago')

    # ------------------------------------------------------------------
    # PUNTO 5: DECISIÓN FINAL - Comparación de escenarios
    # Se escoge el escenario que minimiza el tiempo de espera global,
    # ponderando también el desempeño por tipo de acción.
    # ------------------------------------------------------------------
    print(f"\n\n{sep_doble}")
    print("  PUNTO 5: COMPARACIÓN FINAL Y DECISIÓN DE ASIGNACIÓN DE CAJEROS")
    print(sep_doble)

    comparacion = pd.DataFrame({
        'Escenario': [
            'Base (3 Mixtos)',
            'A: 1 Retiro + 2 Pagos',
            'B: 2 Retiros + 1 Pago'
        ],
        'T_Espera_Retiro': [
            stats_base['t_espera_retiro'],
            stats_A['t_espera_retiro'],
            stats_B['t_espera_retiro']
        ],
        'T_Espera_Pago': [
            stats_base['t_espera_pago'],
            stats_A['t_espera_pago'],
            stats_B['t_espera_pago']
        ],
        'T_Espera_Global': [
            stats_base['t_espera_global'],
            stats_A['t_espera_global'],
            stats_B['t_espera_global']
        ],
        'Pct_Sin_Espera': [
            stats_base['p_sin_espera'],
            stats_A['p_sin_espera'],
            stats_B['p_sin_espera']
        ],
        'Pct_Espera_Alta': [
            stats_base['p_espera_alta'],
            stats_A['p_espera_alta'],
            stats_B['p_espera_alta']
        ],
        'Necesita_Cajero_Extra': [
            stats_base['necesita_cajero'],
            stats_A['necesita_cajero'],
            stats_B['necesita_cajero']
        ],
        'Clientes_Prom_Dia': [
            len(df_base) / NUM_REPLICAS,
            len(df_A)    / NUM_REPLICAS,
            len(df_B)    / NUM_REPLICAS
        ]
    })

    print("\nTabla comparativa de escenarios:")
    print(comparacion.round(4).to_string(index=False))

    # Selección del mejor escenario
    idx_mejor = comparacion['T_Espera_Global'].idxmin()
    mejor_esc  = comparacion.loc[idx_mejor, 'Escenario']

    t_A = comparacion.loc[1, 'T_Espera_Global']
    t_B = comparacion.loc[2, 'T_Espera_Global']

    print(f"\n{'-'*60}")
    print("  RECOMENDACIÓN FINAL PARA EL BANCO")
    print(f"{'-'*60}")
    print(f"\n  Mejor escenario: {mejor_esc}")
    print(f"  (Tiempo de espera global mínimo: "
          f"{comparacion.loc[idx_mejor, 'T_Espera_Global']:.4f} min)\n")

    if t_B < t_A:
        print("  DECISIÓN: Asignar 2 cajeros para RETIROS y 1 cajero para PAGOS.")
        print("\n  Justificación:")
        print("  - El 70% de los clientes realizan retiros -> mayor demanda.")
        print("  - Los retiros tienen tiempos de servicio más cortos (1-4 min)")
        print("    versus pagos (3-7 min), generando mayor rotación en cajeros")
        print("    de retiro y acumulación de cola en el cajero de pagos.")
        print("  - Dedicar 2 cajeros a retiros absorbe el volumen mayoritario")
        print("    y reduce el tiempo de espera total del sistema.")
    else:
        print("  DECISIÓN: Asignar 1 cajero para RETIROS y 2 cajeros para PAGOS.")
        print("\n  Justificación:")
        print("  - Los tiempos de servicio de pagos (3-7 min) son significativamente")
        print("    mayores que los de retiros (1-4 min).")
        print("  - Aunque los pagos representan solo el 30% de usuarios, su mayor")
        print("    tiempo de servicio genera cuellos de botella que requieren más")
        print("    capacidad de atención para mantener tiempos de espera razonables.")

    if stats_base['necesita_cajero'] or stats_A['necesita_cajero'] or stats_B['necesita_cajero']:
        print("\n  ALERTA: Al menos un escenario supera los umbrales de espera.")
        print("  Se recomienda evaluar la incorporación de un 4to cajero en horas pico.")
    else:
        print("\n  Los 3 cajeros actuales son suficientes bajo las condiciones simuladas.")

    # ------------------------------------------------------------------
    # GENERAR GRÁFICAS
    # ------------------------------------------------------------------
    print("\n\nGenerando panel de gráficas...")
    generar_graficas(df_base, df_A, df_B, comparacion, stats_base, stats_A, stats_B)

    # ------------------------------------------------------------------
    # EXPORTAR RESULTADOS A EXCEL
    # ------------------------------------------------------------------
    nombre_excel = 'resultados_banco_colombia.xlsx'
    print(f"\nExportando resultados a '{nombre_excel}'...")

    with pd.ExcelWriter(nombre_excel, engine='openpyxl') as writer:
        # Datos crudos
        df_base.to_excel(writer, sheet_name='Base_Datos', index=False)
        df_A.to_excel(writer,    sheet_name='EscA_Datos', index=False)
        df_B.to_excel(writer,    sheet_name='EscB_Datos', index=False)
        # Comparación de escenarios
        comparacion.to_excel(writer, sheet_name='Comparacion', index=False)
        # Resúmenes por cajero
        stats_base['resumen_cajero'].to_excel(writer, sheet_name='Base_x_Cajero')
        stats_A['resumen_cajero'].to_excel(writer,    sheet_name='EscA_x_Cajero')
        stats_B['resumen_cajero'].to_excel(writer,    sheet_name='EscB_x_Cajero')
        # Promedios por tipo de usuario
        stats_base['promedio_tipo'].to_excel(writer, sheet_name='Base_x_Tipo')
        stats_A['promedio_tipo'].to_excel(writer,    sheet_name='EscA_x_Tipo')
        stats_B['promedio_tipo'].to_excel(writer,    sheet_name='EscB_x_Tipo')
        # Totales por réplica
        stats_base['pivot_replicas'].to_excel(writer, sheet_name='Base_x_Replica')
        stats_A['pivot_replicas'].to_excel(writer,    sheet_name='EscA_x_Replica')
        stats_B['pivot_replicas'].to_excel(writer,    sheet_name='EscB_x_Replica')

    print(f"Resultados exportados correctamente.")
    print("\n" + sep_doble)
    print("  SIMULACIÓN COMPLETADA")
    print(sep_doble)

    return df_base, df_A, df_B, comparacion, stats_base, stats_A, stats_B


# =============================================================================
# PUNTO DE ENTRADA
# =============================================================================
if __name__ == '__main__':
    df_base, df_A, df_B, comparacion, stats_base, stats_A, stats_B = main()
