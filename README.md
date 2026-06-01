# Simulación Banco de Colombia — Optimización de Cajeros

**Modelo:** M/M/1 por cajero (colas independientes)
**Jornada simulada:** 8 horas/día · 10 réplicas mínimo

---

## Descripción del Problema

El Banco de Colombia dispone de **3 cajeros** para atender retiros y pagos/consignaciones. El objetivo es determinar si conviene asignar:

- **Escenario A:** 1 cajero exclusivo para retiros + 2 para pagos, o
- **Escenario B:** 2 cajeros exclusivos para retiros + 1 para pagos.

La simulación usa un modelo de **eventos discretos M/M/1** por cajero, corrida al menos 10 veces, para responder 5 preguntas analíticas sobre el sistema.

---

## Archivos del Proyecto

| Archivo | Descripción |
|---|---|
| `simulacion_banco_colombia.py` | Código principal de la simulación |
| `README.md` | Este archivo |
| `Tabla_1 - Detalles de atención...png` | Tabla de tiempos de servicio y llegada |
| `Tabla_2 - Probabilidades de los tipos...png` | Probabilidades por tipo de usuario |
| `codigo_base.py` | Código base provisto por el docente |

### Archivos generados al ejecutar la simulación

| Archivo generado | Descripción |
|---|---|
| `resultados_banco_colombia.xlsx` | Datos completos de todas las réplicas y escenarios (12 hojas) |
| `graficas_simulacion_banco.png` | Panel de 6 gráficas de análisis |

---

## Dependencias

```
numpy>=1.21
pandas>=1.3
matplotlib>=3.4
seaborn>=0.11
scipy>=1.7
openpyxl>=3.0
python-docx>=0.8.11
```

---

## Instrucciones de Ejecución

### Opción 1 — Google Colab (recomendado)

1. Abre [Google Colab](https://colab.research.google.com).
2. Crea un nuevo notebook.
3. En la primera celda, instala las dependencias:

```python
!pip install numpy pandas matplotlib seaborn scipy openpyxl python-docx
```

4. En la segunda celda, sube y ejecuta el archivo principal:

```python
# Opción A: subir el archivo
from google.colab import files
files.upload()  # Selecciona simulacion_banco_colombia.py

# Opción B: copiar el contenido directamente en celdas del notebook
```

5. Ejecuta la simulación:

```python
exec(open('simulacion_banco_colombia.py').read())
```

6. Descarga los resultados:

```python
files.download('resultados_banco_colombia.xlsx')
files.download('graficas_simulacion_banco.png')
```

---

### Opción 2 — Ejecución local (Python 3.8+)

**Paso 1:** Instalar dependencias

```bash
pip install numpy pandas matplotlib seaborn scipy openpyxl python-docx
```

**Paso 2:** Ejecutar la simulación

```bash
python simulacion_banco_colombia.py
```

---

## Parámetros Configurables

Al inicio del archivo `simulacion_banco_colombia.py` se pueden ajustar:

```python
HORAS_OPERACION   = 8    # Horas de operación diaria
NUM_REPLICAS      = 10   # Número de réplicas (mínimo recomendado: 10)
NUM_CAJEROS       = 3    # Total de cajeros disponibles
```

---

## Estructura del Modelo

```
Llegada de clientes
        │
        ▼
  ¿Retiro (70%) o Pago (30%)?
        │
   ┌────┴────┐
   ▼         ▼
Retiro      Pago/Consignación
   │              │
Subtipo        Subtipo
(Rápido/Normal/(Rápido/Normal/
 Lento/Muy lento) Lento/Muy lento)
   │              │
   ▼              ▼
Cajero(s)    Cajero(s)
exclusivos   exclusivos
  M/M/1        M/M/1
```

### Escenarios simulados

| Escenario | Cajeros Retiro | Cajeros Pago |
|---|---|---|
| **Base** | 0, 1, 2 (mixtos) | 0, 1, 2 (mixtos) |
| **A** | 0 | 1, 2 |
| **B** | 0, 1 | 2 |

---

## Preguntas Respondidas

1. **Cajero con menor/mayor tiempo promedio de atención** → Análisis por cajero sin segregar usuarios.
2. **Promedio de usuarios por tipo** → Conteo promedio entre réplicas por subtipo.
3. **Total de usuarios por réplica** → Tabla pivot + identificación de réplica con menor carga.
4. **Necesidad de cajero adicional** → Criterios: tiempo promedio de espera, percentil 95, porcentaje con espera alta.
5. **Asignación óptima de cajeros** → Comparación de los 3 escenarios; decisión basada en mínimo tiempo de espera global.

---

## Evidencias de Resultados

> Ejecuta la simulación para generar las evidencias. Los archivos de salida contienen:

- **`resultados_banco_colombia.xlsx`** — 12 hojas con datos crudos, resúmenes por cajero, promedios por tipo de usuario, totales por réplica y tabla comparativa de escenarios.
- **`graficas_simulacion_banco.png`** — Panel con:
  - Boxplot de tiempos de espera por escenario.
  - Barras comparativas de espera por tipo de acción.
  - Clientes atendidos por réplica.
  - Distribución de subtipos de usuario.
  - Tiempos de servicio y espera por cajero.
  - Comparación global de métricas.

---

## Supuestos del Modelo

- Los tiempos de servicio y llegada siguen distribución **exponencial** (proceso de Poisson).
- Cada cajero opera como una cola **M/M/1 independiente** con su propia lista de espera.
- La selección de cajero (cuando hay más de uno disponible para el tipo) sigue la política de **cola más corta**.
- El banco cierra a los 480 minutos; los clientes en servicio al cierre son atendidos hasta finalizar.
- Los tiempos de desplazamiento entre colas son despreciables.
- Todos los días son estadísticamente iguales (réplicas i.i.d.).

---
