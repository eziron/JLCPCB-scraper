import pandas as pd
import tkinter as tk
from tkinter import filedialog
import sys
import numpy as np

# --- Importar Rich ---
from rich.console import Console
from rich.table import Table

from util import *
from JLCPCB_search import JLCPCB_Search

# --- Consola Rich ---
console = Console()


def main():
    try:
        root = tk.Tk()
        root.withdraw()  # Ocultar ventana principal de Tkinter
        filename = filedialog.askopenfilename(
            title="Selecciona el archivo JSON de componentes JLCPCB",
            filetypes=[("JSON files", "*.json, *.jsonl"), ("All files", "*.*")],
        )
        if not filename:
            console.print("[bold red]No se seleccionó ningún archivo. Saliendo.[/]")
            sys.exit()

        console.print(f"Cargando componentes desde '[cyan]{filename}[/cyan]'...")
        api = JLCPCB_Search(filename,100000, console=console)
        if api.elements_count == 0:
            console.print("[bold red]Error: El archivo no contiene componentes o está vacío.[/]")
            sys.exit()
            
        console.print(f"Cargados [bold green]{api.elements_count}[/] componentes iniciales.\n")
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[bold red]Error al cargar el archivo: {e}[/]")
        sys.exit()

    # --- Bucle de Búsqueda Interactivo ---
    while True:
        console.print("-" * 30, style="dim")
        console.print("Introduce criterios de búsqueda (deja en blanco para omitir):")

        # 1. Texto General
        query_text = console.input("  [cyan]Texto Búsqueda (o 'exit'):[/cyan] ")
        if not query_text.strip():
            query_text = None
        elif query_text.strip().lower() == "exit":
            console.print("Saliendo del programa.")
            break

        # 2. Stock Mínimo
        min_stock_str = console.input("  [cyan]Stock Mínimo:[/cyan] ")
        min_stock = None
        if min_stock_str.strip():
            try:
                min_stock = int(min_stock_str)
                if min_stock < 0:
                    min_stock = 0
            except ValueError:
                console.print("  [yellow]Entrada inválida para Stock Mínimo, se ignorará.[/]")

        # 3. Nivel de Preferencia Máximo
        pref_level_str = console.input("  [cyan]PL Máximo (0=Base, 1=ExpPref, 2=ExpNP):[/cyan] ")
        max_preference_level = None
        if pref_level_str.strip():
            try:
                max_preference_level = int(pref_level_str)
                if max_preference_level not in [0, 1, 2]:
                    console.print("  [yellow]PL inválido (debe ser 0, 1, o 2), se ignorará.[/]")
                    max_preference_level = None
            except ValueError:
                console.print("  [yellow]Entrada inválida para PL Máximo, se ignorará.[/]")

        # 4. Package
        package = console.input("  [cyan]Package (ej: 0603):[/cyan] ")
        if not package.strip():
            package = None

        console.print("\nBuscando...", style="dim")

        # --- Ejecutar Búsqueda ---
        try:
            found_df = api.search_components(
                query_text=query_text,
                min_stock=min_stock,
                max_preference_level=max_preference_level,
                package=package,
                manufacturer=None,
                specifications=None,
            )
        except Exception as e:
            console.print(f"[bold red]Error durante la búsqueda: {e}[/]")
            continue

        # --- Procesar y Mostrar Resultados ---
        if found_df.empty:
            console.print("\n[yellow]No se encontraron componentes que coincidan con los criterios.[/]\n")
            continue

        total_found_pre_sort = len(found_df)
        console.print(f"\nEncontrados [bold green]{total_found_pre_sort}[/] componentes.")
        console.print("Calculando precios y aplicando ordenación invertida para visualización...",style="dim")

        try:
            # Copiar para evitar modificar el DataFrame original de la búsqueda
            df_to_process = found_df.copy()

            # --- Añadir Columnas para Ordenación ---
            # Precio Unitario
            if "Price Tiers" in df_to_process.columns:
                df_to_process["Unit Price"] = df_to_process["Price Tiers"].apply(get_unit_price)
                # Para ordenar descendente (más barato al final), reemplazar NaN con -infinito
                # ya que NaN no se ordena bien en descendente directamente
                df_to_process["_sort_price_temp"] = df_to_process["Unit Price"].fillna(-np.inf)
            else:
                console.print("[yellow]Advertencia: Columna 'Price Tiers' no encontrada, no se puede calcular/ordenar por precio unitario.[/]")
                df_to_process["Unit Price"] = None
                df_to_process["_sort_price_temp"] = -np.inf # Valor muy bajo

            # Preference Level (manejar NaN si existe)
            if "Preference Level" in df_to_process.columns:
                 # Para ordenar descendente (PL 0 al final), reemplazar NaN con -1 (o un valor bajo)
                df_to_process["_sort_pl_temp"] = df_to_process["Preference Level"].fillna(-1)
            else:
                console.print("[yellow]Advertencia: Columna 'Preference Level' no encontrada, no se puede ordenar por PL.[/]")
                df_to_process["_sort_pl_temp"] = -1 # Valor bajo por defecto

            # Stock (manejar NaN si existe)
            if "Stock" in df_to_process.columns:
                # Para ordenar ascendente (Stock más alto al final), reemplazar NaN con -1 (o valor bajo)
                df_to_process["_sort_stock_temp"] = df_to_process["Stock"].fillna(-1)
            else:
                console.print("[yellow]Advertencia: Columna 'Stock' no encontrada, no se puede ordenar por Stock.[/]")
                df_to_process["_sort_stock_temp"] = -1 # Valor bajo por defecto


            # --- Definir Criterios de Ordenación Invertida ---
            # Prioridad: PL (0 al final), Precio (bajo al final), Stock (alto al final)
            sort_by_columns = [
                "_sort_pl_temp",
                "_sort_price_temp",
                "_sort_stock_temp",
            ]
            # PL DESC (2, 1, 0), Precio DESC (alto a bajo), Stock ASC (bajo a alto)
            sort_by_ascending = [False, False, True]

            # --- Aplicar Ordenación Invertida ---
            found_df_sorted_inverted = df_to_process.sort_values(
                by=sort_by_columns,
                ascending=sort_by_ascending,
                na_position='first' # Poner los NaN/rellenos al principio (menos relevantes)
            )

            # Eliminar columnas temporales DESPUÉS de ordenar
            columns_to_drop = [col for col in ['_sort_pl_temp', '_sort_price_temp', '_sort_stock_temp'] if col in found_df_sorted_inverted.columns]
            if columns_to_drop:
                found_df_sorted_inverted = found_df_sorted_inverted.drop(columns=columns_to_drop)

        except Exception as e:
            console.print(f"[bold red]Error al calcular precios o aplicar ordenación invertida: {e}[/]")
            console.print("[yellow]Mostrando resultados con ordenación por defecto.[/]")
            # Usar el DF original sin ordenación específica si falla
            found_df_sorted_inverted = found_df

        # --- Recortar para Mostrar (Tomar los Últimos N = Los Más Relevantes) ---
        total_found_sorted = len(found_df_sorted_inverted)
        max_rows_to_display = 1000  # Límite de filas a mostrar

        # Seleccionar las últimas 'max_rows_to_display' filas
        df_to_display = found_df_sorted_inverted.tail(max_rows_to_display)
        rows_in_final_table = len(df_to_display)

        # --- Crear Tabla Rich ---
        table = Table(
            title=f"Resultados de Búsqueda (Mostrando los {rows_in_final_table} más relevantes de {total_found_sorted})",
            show_header=True,
            header_style="bold magenta",
            show_edge=True,
            # box=box.ROUNDED # Descomentar si quieres bordes redondeados (necesita importar box de rich)
        )

        # Añadir columnas con "JLCPCB Part" primero
        table.add_column("JLCPCB Part", style="bold white", width=12)
        table.add_column("PL", style="dim", width=3, justify="center")  # Preference Level
        table.add_column("Unit Price", justify="right", style="green", width=10)
        table.add_column("Stock", justify="right", style="cyan", width=8)
        table.add_column("Model (MPN)", style="bold yellow", no_wrap=False, min_width=20)
        table.add_column("Package", style="blue", width=10)
        table.add_column("Category", style="italic dim", min_width=15)
        table.add_column("Description", style="default", min_width=30)


        # --- Poblar Tabla (Iterando sobre el DataFrame RECORTADO) ---
        # Añadir mensaje si se omitieron resultados menos relevantes
        if total_found_sorted > rows_in_final_table:
             table.add_row(
                 f"[dim]({total_found_sorted - rows_in_final_table} resultados menos relevantes omitidos)",
                 "[dim]...",
                 "...",
                 "...",
                 "...",
                 "...",
                 "...",
                 "...",
                 style="dim"
             )

        # Iterar sobre las filas del DataFrame recortado (df_to_display)
        for index, row in df_to_display.iterrows():
            # Formatear datos para mostrar
            jlc_part = str(row.get("JLCPCB Part", "")) # <-- Primero
            pl = str(row.get("Preference Level", "-"))
            price = row.get("Unit Price")
            unit_price_str = (f"${price:.5f}" if pd.notna(price) and price != -np.inf else "-") # Comprobar si no es NaN o -inf
            stock_val = row.get("Stock")
            stock_str = str(int(stock_val)) if pd.notna(stock_val) and stock_val != -1 else "-" # Mostrar como entero si es número válido
            model = str(row.get("Model", ""))
            package_val = str(row.get("Package", ""))
            category = str(row.get("Category", ""))
            description = str(row.get("Description", ""))


            # Añadir fila a la tabla rich (en el nuevo orden)
            table.add_row(
                jlc_part,      # <-- Primero
                pl,
                unit_price_str,
                stock_str,
                model,
                package_val,
                category,
                description,
            )

        # --- Imprimir Tabla ---
        console.print(table)
        # El número de resultados mostrados ya está en el título de la tabla

        console.print("\n" + "=" * 40 + "\n") # Separador


if __name__ == "__main__":
    main()

# --- END OF FILE Gemini_rish_SR.py (Corrected for Inverted Sorting and Display) ---