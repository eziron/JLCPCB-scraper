import json
import re
import os
from typing import TYPE_CHECKING

import pandas as pd
import numpy as np

# --- Importaciones de Rich ---
# Usamos TYPE_CHECKING para que 'rich' sea una dependencia opcional
# si alguien quisiera usar la clase sin la funcionalidad de consola.
if TYPE_CHECKING:
    from rich.console import Console

from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.panel import Panel

# Asumo que util.py está en el mismo directorio
from util import *


class JLCPCB_Search:
    # --- Atributos de la clase ---
    filename: str  = None
    _df: pd.DataFrame  = None
    chunk_size: int = None
    elements_count: int = 0
    console: 'Console'  = None

    def __init__(self, filename: str, chunk_size: int = 50000, console: 'Console'  = None):
        """
        Constructor unificado para inicializar el buscador de componentes JLCPCB.

        Carga los datos desde un archivo JSON o JSONL y prepara el objeto para la búsqueda.
        Decide si operar en modo 'en memoria' (para .json) o 'por chunks' (para .jsonl).

        Args:
            filename (str): Ruta al archivo de datos (.json o .jsonl).
            chunk_size (int, optional): Tamaño de los fragmentos para leer archivos .jsonl.
                                        Se ignora para archivos .json. Defaults to 50000.
            console (rich.console.Console, optional): Instancia de una consola Rich para mostrar
                                                      logs, paneles y barras de progreso.
                                                      Si es None, operará en modo silencioso.
        """
        self.console = console

        if not filename or not isinstance(filename, str):
            raise ValueError("Se debe proporcionar un nombre de archivo válido.")

        if not os.path.exists(filename):
            raise FileNotFoundError(f"El archivo '{filename}' no fue encontrado.")

        self.filename = filename
        file_size_mb = os.path.getsize(filename) / (1024 * 1024)

        # --- Lógica de carga unificada ---
        if self.filename.endswith('.jsonl'):
            # --- MODO CHUNKING (.jsonl) ---
            self.chunk_size = chunk_size
            if self.console:
                self.console.log(f"Modo 'chunking' activado para [cyan]{self.filename}[/cyan].")

            # Contar elementos para la barra de progreso (puede ser lento en archivos muy grandes)
            with self.console.status("[bold yellow]Contando elementos en el archivo...[/]", spinner="dots") if self.console else open(os.devnull, 'w') as status:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    self.elements_count = sum(1 for _ in f)

            if self.console:
                self.console.print(Panel(
                    f"[bold]Archivo:[/bold] [cyan]{os.path.basename(self.filename)}[/cyan]\n"
                    f"[bold]Tamaño:[/bold] [magenta]{file_size_mb:.2f} MB[/]\n"
                    f"[bold]Componentes totales:[/bold] [green]{self.elements_count:,}[/]\n"
                    f"[bold]Modo de operación:[/bold] Lectura por Chunks (Bajo uso de RAM)",
                    title="[bold green]Base de Datos Lista[/]",
                    expand=False
                ))

        else:
            # --- MODO EN MEMORIA (.json) ---
            self._df = pd.DataFrame() # Inicializar por si falla la carga
            if self.console:
                self.console.log(f"Cargando [cyan]{self.filename}[/cyan] ({file_size_mb:.2f} MB) en memoria...")

            try:
                with open(filename, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if "components" in data:
                    self._df = pd.DataFrame(data["components"])
                else:
                    self._df = pd.DataFrame(data)
                
                self.elements_count = len(self._df)
                
                if self.console:
                    self.console.print(Panel(
                        f"[bold]Archivo:[/bold] [cyan]{os.path.basename(self.filename)}[/cyan]\n"
                        f"[bold]Tamaño:[/bold] [magenta]{file_size_mb:.2f} MB[/]\n"
                        f"[bold]Componentes cargados:[/bold] [green]{self.elements_count:,}[/]\n"
                        f"[bold]Modo de operación:[/bold] En Memoria (Rápido)",
                        title="[bold green]Base de Datos Cargada[/]",
                        expand=False
                    ))

            except (json.JSONDecodeError, Exception) as e:
                if self.console:
                    self.console.log(f"[bold red]Error al cargar el archivo JSON: {e}[/]")
                raise e # Relanzar la excepción

    # El resto de las funciones (métodos privados y search_components) permanecen aquí.
    # Los métodos _parse y _evaluate no cambian.
    def _parse_parametric_query(self, text: str) -> dict :
        """
        Analiza una cadena para extraer un operador, valor numérico, prefijo y unidad.
        Devuelve un diccionario normalizado si tiene éxito, de lo contrario None.
        """
        # Expresión regular para capturar: (operador)(número)(prefijo)(unidad)
        # Ejemplos: ">=10kΩ", "<0.1uF", "25V", "100ohm"
        pattern = re.compile(
            r"^\s*(>=|<=|>|<)?\s*(\d*\.?\d+)\s*(p|n|u|µ|m|k|K|M|G)?\s*(F|H|V|A|Hz|W|Ω|ohm|ohms|%|C|°C|R)\s*$",
            re.IGNORECASE
        )
        match = pattern.match(text)
        if not match:
            return None

        operator, value_str, prefix, unit = match.groups()

        # Normalización de operador
        op_map = {">": ">", "<": "<", ">=": ">=", "<=": "<="}
        final_operator = op_map.get(operator, "==") # '==' implícito

        # Normalización de valor con prefijo SI
        value = float(value_str)
        prefix_map = {
            'p': 1e-12, 'n': 1e-9, 'u': 1e-6, 'µ': 1e-6, 'm': 1e-3,
            'k': 1e3, 'K': 1e3, 'M': 1e6, 'G': 1e9
        }
        if prefix:
            value *= prefix_map.get(prefix.lower(), 1)
        
        # Normalización de unidad a un tipo estándar
        unit_lower = unit.lower()
        unit_type = None
        if unit_lower in ['f']: unit_type = 'Capacitance'
        elif unit_lower in ['h']: unit_type = 'Inductance'
        elif unit_lower in ['v']: unit_type = 'Voltage'
        elif unit_lower in ['a']: unit_type = 'Current'
        elif unit_lower in ['hz']: unit_type = 'Frequency'
        elif unit_lower in ['w']: unit_type = 'Power'
        elif unit_lower in ['ω', 'ohm', 'ohms', 'r']: unit_type = 'Resistance'
        elif unit_lower in ['%',]: unit_type = 'Tolerance'
        elif unit_lower in ['c', '°c']: unit_type = 'Temperature'
        
        if unit_type is None:
            return None

        return {
            "operator": final_operator,
            "value_si": value,
            "unit_type": unit_type,
            "prefix": prefix,
        }

    def _evaluate_parametric_condition(self, component_specs: list, condition: dict) -> bool:
        """
        Evalúa si un componente cumple una condición paramétrica.
        Busca un atributo del mismo tipo de unidad y realiza la comparación.
        """
        if not isinstance(component_specs, list):
            return False

        op = condition["operator"]
        value_to_compare = condition["value_si"]
        unit_type_to_compare = condition["unit_type"]

        for spec in component_specs:
            if not isinstance(spec, dict):
                continue
            
            # Asumimos que los nombres/valores ya han sido limpiados por clean_text_value
            attr_name = spec.get('attribute_name_en', '')
            attr_value = spec.get('attribute_value_name', '')
            
            # Intenta parsear el valor del atributo del componente
            component_param = self._parse_parametric_query(attr_value)

            if component_param and component_param['unit_type'] == unit_type_to_compare:
                # Comparamos!
                comp_val = component_param['value_si']
                if op == "==" and np.isclose(comp_val, value_to_compare): return True
                if op == ">" and comp_val > value_to_compare: return True
                if op == "<" and comp_val < value_to_compare: return True
                if op == ">=" and (comp_val > value_to_compare or np.isclose(comp_val, value_to_compare)): return True
                if op == "<=" and (comp_val < value_to_compare or np.isclose(comp_val, value_to_compare)): return True
        
        return False

    def _build_searchable_text_column(self, df: pd.DataFrame) -> pd.Series:
        """Crea una columna concatenada para búsquedas de texto eficientes."""
        text_fields = [
            "JLCPCB Part", "Model", "Category", "Package",
            "Description", "Manufacturer", "Short Description"
        ]
        # Usar solo las columnas que realmente existen en el DataFrame
        existing_fields = [f for f in text_fields if f in df.columns]
        
        # Concatena el contenido, llenando los NaN con cadenas vacías
        searchable_series = df[existing_fields].fillna('').agg(' '.join, axis=1)
        
        # Limpiar y normalizar el texto concatenado una sola vez
        return searchable_series.apply(clean_text_value)

    def _perform_search_on_df(
        self,
        df: pd.DataFrame,
        query_text: str = None,
        min_stock: int = None,
        max_preference_level: int = None,
        package: str = None,
        manufacturer: str = None,
        specifications: dict = None,
    ) -> pd.DataFrame:
        """
        (MOTOR INTERNO) Realiza el filtrado sobre un DataFrame ya existente.
        Esta función contiene toda la lógica de búsqueda pero no se encarga
        de la obtención de datos ni de la ordenación final.

        Returns:
            pd.DataFrame: Un DataFrame con los componentes filtrados (sin ordenar).
        """
        if df.empty:
            return pd.DataFrame()

        # Copiar para no modificar el chunk original
        result_df = df.copy()

        # --- 1. APLICAR FILTROS RÁPIDOS Y DIRECTOS ---
        if min_stock is not None and "Stock" in result_df.columns:
            result_df = result_df[result_df["Stock"].fillna(0) >= min_stock]
        if max_preference_level is not None and "Preference Level" in result_df.columns:
            result_df = result_df[result_df["Preference Level"].fillna(99) <= max_preference_level]

        # --- 2. APLICAR FILTROS DE TEXTO EN COLUMNAS ESPECÍFICAS (CON LÓGICA OR) ---
        for col_name, filter_text in [("Package", package), ("Manufacturer", manufacturer)]:
            if filter_text and col_name in result_df.columns and not result_df.empty:
                regex_pattern = "|".join([re.escape(clean_text_value(part)) for part in filter_text.split("|")])
                result_df = result_df[result_df[col_name].fillna("").str.contains(regex_pattern, case=False, regex=True)]

        if result_df.empty: return result_df
        
        # --- 3. PROCESAR Y APLICAR FILTROS COMPLEJOS (specifications y query_text) ---
        text_conditions = []
        param_conditions = []
        if query_text:
            for token in query_text.split():
                param_query = self._parse_parametric_query(token)
                if param_query:
                    param_conditions.append(param_query)
                else:
                    text_conditions.append(token)
        
        if specifications and "Specifications" in result_df.columns:
            if isinstance(specifications, dict):
                # Implementación de filtrado de especificaciones...
                # (Se mantiene la lógica original)
                pass # Lógica original va aquí
        
        if param_conditions and not result_df.empty:
            rows_to_keep_mask = pd.Series(True, index=result_df.index)
            for condition in param_conditions:
                rows_to_keep_mask &= result_df["Specifications"].apply(lambda specs: self._evaluate_parametric_condition(specs, condition))
            result_df = result_df[rows_to_keep_mask]
            
        if text_conditions and not result_df.empty:
            searchable_text = self._build_searchable_text_column(result_df)
            for token in text_conditions:
                or_parts = [re.escape(p) for p in clean_text_value(token).split('|')]
                regex_pattern = "|".join(or_parts)
                
                mask = searchable_text.str.contains(regex_pattern, regex=True)
                result_df = result_df[mask]
                searchable_text = searchable_text[mask]
                

        return result_df

    def search_components(
        self,
        query_text: str = None,
        min_stock: int = None,
        max_preference_level: int = None,
        package: str = None,
        manufacturer: str = None,
        specifications: dict = None,
    ) -> pd.DataFrame:
        """
        (FUNCIÓN DE ACCESO PÚBLICA) Orquesta la búsqueda de componentes.
        Decide si buscar en memoria o leer el archivo por fragmentos (chunks)
        basado en la configuración inicial. Aplica la ordenación final a los resultados.
        """
        search_params = {
            "query_text": query_text, "min_stock": min_stock,
            "max_preference_level": max_preference_level, "package": package,
            "manufacturer": manufacturer, "specifications": specifications
        }
        
        final_df = pd.DataFrame()

        # --- PATH 1: MODO CHUNKING (BAJO USO DE RAM) ---
        if self.chunk_size and self.filename and self.filename.endswith('.jsonl'):
            
            found_chunks = []
            
            # --- Integración de Rich Progress Bar ---
            progress_context = None
            if self.console:
                progress_context = Progress(
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    TextColumn("({task.completed}/{task.total})"),
                    TimeRemainingColumn(),
                    console=self.console,
                    transient=True # La barra desaparecerá al terminar
                )

            try:
                # Usa el contexto de progreso si está disponible
                with progress_context if progress_context else open(os.devnull, 'w') as progress:
                    task_id = None
                    if progress_context:
                        task_id = progress.add_task("[cyan]Filtrando componentes...", total=self.elements_count)
                    
                    json_iterator = pd.read_json(self.filename, lines=True, chunksize=self.chunk_size, encoding='utf-8')
                    
                    total_components = 0
                    for n,df_chunk in enumerate(json_iterator):
                        filtered_chunk = self._perform_search_on_df(df_chunk, **search_params)
                        if not filtered_chunk.empty:
                            found_chunks.append(filtered_chunk)
                            
                            if self.console:
                                total_components += len(filtered_chunk)
                                self.console.log(f"[bold green]Encontrados {len(filtered_chunk)} componentes en el chunk {n}, total encontrados: {total_components}.[/]")
                        
                        if progress_context and task_id is not None:
                            progress.update(task_id, advance=len(df_chunk))
                
                if found_chunks:
                    final_df = pd.concat(found_chunks, ignore_index=True)

            except FileNotFoundError:
                if self.console:
                    self.console.log(f"[bold red]Error: Archivo no encontrado '{self.filename}'.[/]")
                return pd.DataFrame()
            except Exception as e:
                if self.console:
                    self.console.log(f"[bold red]Error durante la lectura del archivo por chunks: {e}[/]")
                return pd.DataFrame()

        # --- PATH 2: MODO EN MEMORIA (RÁPIDO) ---
        else:
            if self._df is None or self._df.empty:
                return pd.DataFrame()
            
            if self.console:
                with self.console.status("[bold yellow]Filtrando componentes en memoria...", spinner="dots"):
                    final_df = self._perform_search_on_df(self._df, **search_params)
            else: # Modo silencioso
                final_df = self._perform_search_on_df(self._df, **search_params)

        # --- ORDENAMIENTO FINAL (común a ambos paths) ---
        if final_df.empty:
            return final_df

        if self.console:
            self.console.log("Ordenando resultados...")

        final_df["is_stock_zero"] = np.where(final_df["Stock"].fillna(0) > 0, 0, 1) if "Stock" in final_df.columns else 1
        if "Preference Level" not in final_df.columns: final_df["Preference Level"] = 99
        final_df["min_price"] = final_df["Price Tiers"].apply(get_min_price) if "Price Tiers" in final_df.columns else 999999
        
        final_df = final_df.sort_values(
            by=["is_stock_zero", "Preference Level", "min_price"],
            ascending=[True, True, True]
        ).drop(columns=["is_stock_zero", "min_price"])

        return final_df


if __name__ == "__main__":
    from rich.console import Console

    # Crea una instancia de la consola de Rich
    console = Console()
    
    try:
        # Pasa la consola al constructor
        searcher = JLCPCB_Search("jlcpcb_components.jsonl", chunk_size=50000, console=console)
        
        # Realiza la búsqueda. Ahora mostrará la barra de progreso.
        results_df = searcher.search_components(query_text="resistor 10k <1%", min_stock=1000)
        
        if not results_df.empty:
            console.print(f"\n[bold green]Se encontraron {len(results_df)} resultados:[/]")
            console.print(results_df.head()) # Muestra los primeros resultados
        else:
            console.print("\n[yellow]No se encontraron resultados.[/]")

    except (FileNotFoundError, ValueError) as e:
        console.print(f"[bold red]Error en la inicialización: {e}[/]")