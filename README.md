# JLCPCB Component Scraper & Local Search Engine

Este repositorio contiene un conjunto de herramientas de Python para descargar la base de datos completa de componentes de ensamblaje (SMT) de JLCPCB y realizar búsquedas locales potentes y rápidas sobre los datos descargados.

El proyecto se divide en dos herramientas principales:
1.  **`JLCPCB_DL.py`**: Un scraper inteligente y resumible que descarga los datos.
2.  **`JLCPCB_SR.py`**: Una interfaz de línea de comandos interactiva para buscar en la base de datos local.

 <!-- Reemplaza esto con una captura o GIF de tu herramienta en acción -->

## 🚀 Características Principales

-   **Scraper Inteligente y Resumible**: El proceso de descarga puede tardar horas. La herramienta guarda el progreso y puede ser interrumpida y reanudada en cualquier momento, evitando la pérdida de trabajo.
-   **Superación de Límites de API**: Desglosa automáticamente búsquedas masivas en sub-búsquedas más pequeñas para garantizar la descarga completa del catálogo, superando el límite de 100,000 componentes por consulta de la API.
-   **Motor de Búsqueda de Bajo Consumo de RAM**: Utiliza un sistema de lectura por "chunks" para procesar bases de datos de millones de componentes (`.jsonl`) sin necesidad de cargarlas por completo en memoria, permitiendo su uso en máquinas con recursos limitados.
-   **Búsqueda Paramétrica Avanzada**: Realiza búsquedas complejas directamente desde el texto, como `resistor 10k <1%`, `capacitor >=10uF 16V`, o `led 0603`.
-   **Interfaz de Usuario Enriquecida**: Utiliza la librería `rich` para ofrecer una experiencia de usuario clara y agradable, con barras de progreso, tablas formateadas y resaltado de color.
-   **Ordenación Inteligente**: Los resultados se ordenan por relevancia, priorizando componentes en stock y de la librería básica (Base/Preferred).

## 📂 Estructura del Proyecto

```
.
├── JLCPCB_DL.py          # --> Herramienta de Descarga (Usuario Final)
├── JLCPCB_SR.py          # --> Herramienta de Búsqueda (Usuario Final)
|
├── JLCPCB_scrape.py      # <-- Librería de bajo nivel (Comunicación API)
├── JLCPCB_search.py      # <-- Librería de bajo nivel (Motor de Búsqueda)
└── util.py               # <-- Funciones de utilidad comunes
```

## ⚙️ Instalación y Configuración

1.  **Clona el repositorio:**
    ```bash
    git clone https://github.com/tu_usuario/tu_repositorio.git
    cd tu_repositorio
    ```

2.  **Crea un entorno virtual (recomendado):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # En Windows: venv\Scripts\activate
    ```

3.  **Instala las dependencias:**
    ```bash
    pip install pandas requests rich numpy
    ```

## 📖 Guía de Uso

El flujo de trabajo consta de dos pasos: primero descargar la base de datos y luego buscar en ella.

### Paso 1: Descargar la Base de Datos con `JLCPCB_DL.py`

Esta herramienta se conecta a la API de JLCPCB y descarga la lista de componentes.

**Ejecución:**
Abre una terminal en la carpeta del proyecto y ejecuta:
```bash
python JLCPCB_DL.py
```

**¿Qué hace?**
-   Creará dos archivos:
    -   `jlcpcb_components.jsonl`: La base de datos de componentes, donde cada línea es un JSON.
    -   `jlcpcb_progress.json`: Un archivo para guardar el progreso. **No lo borres si quieres poder reanudar la descarga.**
-   Mostrará barras de progreso detalladas sobre el estado de la descarga.
-   Puedes detener el script en cualquier momento (`Ctrl+C`). Al volver a ejecutarlo, leerá el archivo de progreso y continuará desde donde se quedó.

### Paso 2: Buscar Componentes con `JLCPCB_SR.py`

Una vez que tengas el archivo `jlcpcb_components.jsonl`, puedes usar esta herramienta para realizar búsquedas interactivas.

**Ejecución:**
```bash
python JLCPCB_SR.py
```

**¿Qué hace?**
1.  Te pedirá que selecciones el archivo de base de datos (`.jsonl` o `.json`).
2.  Iniciará un bucle de búsqueda interactivo donde podrás introducir tus criterios.
3.  Mostrará los resultados en una tabla clara y ordenada.

**Ejemplos de Búsqueda:**

-   **Búsqueda simple:** `stm32f407`
-   **Búsqueda con encapsulado:** `resistor 0402`
-   **Búsqueda paramétrica:**
    -   `capacitor 100nF 50V` (busca un condensador de 100nF y 50V)
    -   `resistor >=10k <1%` (resistencia mayor o igual a 10kΩ y tolerancia menor al 1%)
    -   `led verde 0805` (led verde en encapsulado 0805)
-   **Filtrar por stock:** Introduce un número cuando se te pregunte por "Stock Mínimo".
-   **Filtrar por preferencia:** `PL Máximo: 0` (solo componentes de la librería Base), `1` (Base + Extended Preferred), `2` (Todos).

---

## 🛠️ Documentación de las Librerías (para Desarrolladores)

Si deseas utilizar las clases de este proyecto en tu propio código, aquí tienes un resumen de su funcionamiento.

### `JLCPCB_scrape.py` - El Comunicador con la API

Esta librería encapsula toda la interacción directa con el endpoint de la API de JLCPCB.

-   **Clase `JLCPCB_Scrape`**:
    -   **`__init__(...)`**: Inicializa la sesión con las cabeceras (`headers`) necesarias para las peticiones.
    -   **`JLCPCB_API_query(**kwargs)`**: Realiza una única petición POST a la API con un conjunto de parámetros detallados (filtros, paginación, etc.). Devuelve el JSON de la respuesta.
    -   **`get_jlcpcb_components(**kwargs)`**: Orquesta la descarga de *todas* las páginas para una consulta dada, gestionando la paginación y devolviendo un DataFrame de Pandas con todos los resultados.

### `JLCPCB_search.py` - El Motor de Búsqueda Local

Contiene la lógica para filtrar eficientemente la base de datos local.

-   **Clase `JLCPCB_Search`**:
    -   **`__init__(filename, chunk_size, ...)`**: Constructor inteligente. Si el `filename` es `.json`, carga todo el archivo en memoria. Si es `.jsonl`, activa el **modo de bajo consumo de RAM**, procesando el archivo en fragmentos (`chunks`) del tamaño especificado.
    -   **`search_components(**kwargs)`**: La función principal de búsqueda. Orquesta el proceso de filtrado (ya sea en memoria o por chunks) y aplica la ordenación final a los resultados.
    -   **Métodos internos (`_parse_parametric_query`, `_perform_search_on_df`, etc.)**: Contienen la lógica para interpretar búsquedas de texto paramétricas y aplicar los diferentes filtros de manera eficiente sobre un DataFrame de Pandas.

## Contribuciones

Las contribuciones son bienvenidas. Si tienes alguna idea o encuentras un error, por favor, abre un "issue" o envía un "pull request".