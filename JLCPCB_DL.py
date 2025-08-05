import json
import time
import os
import sys
from itertools import product
import pandas as pd

# --- Importar Rich ---
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.panel import Panel
from rich.console import Console
from rich.table import Table

# --- Importar Scraper ---
from JLCPCB_scrape import JLCPCB_Scrape

# --- Configuración ---
PAGE_SIZE = 1000
MIN_COMPONENTS_FOR_TASK = 500
MAX_COMPONENTS_FOR_API_LIMIT = 100000

# --- Nombres de Archivos para Checkpointing ---
OUTPUT_FILENAME = "jlcpcb_components.jsonl"
PROGRESS_FILENAME = "jlcpcb_progress.json"

# --- Consola Rich ---
console = Console()

# --- Funciones de Ayuda para la Gestión de Archivos ---

def load_progress():
    if not os.path.exists(PROGRESS_FILENAME):
        return {"completed_tasks": [], "processed_ids": []}
    try:
        with open(PROGRESS_FILENAME, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        console.print(f"[bold red]Error al leer {PROGRESS_FILENAME}. Se creará uno nuevo.[/]")
        return {"completed_tasks": [], "processed_ids": []}

def save_progress(progress_data):
    temp_filename = PROGRESS_FILENAME + ".tmp"
    try:
        with open(temp_filename, "w", encoding="utf-8") as f:
            json.dump(progress_data, f, indent=2)
        os.replace(temp_filename, PROGRESS_FILENAME)
    except IOError as e:
        console.print(f"[bold red]Error al guardar el progreso: {e}[/]")

def append_components_to_file(components):
    try:
        with open(OUTPUT_FILENAME, "a", encoding="utf-8") as f:
            for component in components:
                f.write(json.dumps(component, ensure_ascii=False) + "\n")
    except IOError as e:
        console.print(f"[bold red]Error al escribir componentes en {OUTPUT_FILENAME}: {e}[/]")
        

def validate_task(task_params, completed_tasks_set):
    task_tuple = tuple(sorted(task_params.items()))
    if task_tuple in completed_tasks_set:
        return False
    return True

# --- Función Principal ---

def download_sequentially_rich():
    api = JLCPCB_Scrape()

    # --- 1. Cargar Progreso Anterior ---
    progress_data = load_progress()
    completed_tasks_set = set(tuple(sorted(t.items())) for t in progress_data["completed_tasks"])
    processed_ids_set = set(progress_data["processed_ids"])

    console.print(Panel(
        f"Cargado progreso anterior:\n"
        f"- [bold cyan]{len(completed_tasks_set)}[/] tareas completadas.\n"
        f"- [bold cyan]{len(processed_ids_set)}[/] componentes únicos encontrados.",
        title="[bold green]Estado de Reanudación[/]",
        expand=False
    ))

    # --- 2. Definir Combinaciones de Parámetros ---
    keywords = [
        None, "resistor", "capacitor", "inductor", "diode", "transistor",
        "crystal", "led","microcontroller", "fpga", "mosfet", "igbt", "opamp", "LDO", "TVS", "STM32",
        "electrolytic", "ceramic", "tantalum"
    ]
    stock_flags = [None, True]
    #preferred_flags = [None, True]
    #library_types = [None,"base", "expand"]
    presale_types = ["stock", "buy"]
    #pcba_types = [None,1, 2]
    
    #combinación 
    # preferred_flags
    # library_types
    # pcba_types
    # presale_types
    over_len_combinations = [
        (None, "base", None, None),  
        (None, "expand", None, None), 
        (None, "expand", 1, None), 
        (None, "expand", 2, None), 
        (True, "expand", None, None),
        
        (None, "expand", None, "stock"), 
        (None, "expand", 1, "stock"), 
        (None, "expand", 2, "stock"), 
        
        (None, "expand", None, "buy"), 
        (None, "expand", 1, "buy"), 
        (None, "expand", 2, "buy"), 
        
        (None, None, None, "stock"), 
        (None, None, 1, "stock"), 
        (None, None, 2, "stock"), 
        
        (None, None, None, "buy"), 
        (None, None, 1, "buy"), 
        (None, None, 2, "buy"), 
    ]

    sort_combinations = [
        (None, None), ("ASC", "STOCK_SORT"), ("DESC", "STOCK_SORT"),
        ("ASC", "PRICE_SORT"), ("DESC", "PRICE_SORT")
    ]
    
    # --- Estructura de Progreso ---
    progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>5.1f}%"),
        TextColumn("({task.completed}/{task.total})"),
        TimeRemainingColumn(),
        console=console,
        transient=False, # Mantiene las barras visibles al final
    )

    with progress:
        # --- 3. Generar y Filtrar Tareas ---
        console.print("\n[bold yellow]Generando y verificando combinaciones de búsqueda...[/]")
        
        potential_tasks = list(product(keywords, stock_flags))
        
        valid_tasks = []

        check_task_id = progress.add_task("[cyan]Verificando tareas...", total=len(potential_tasks))
        
        for kw, sf in potential_tasks:
            base_params = {"keyword": kw, "stockFlag": sf}

            try:
                count = api.get_jlcpcb_total_count(**base_params)
                
                if valid_tasks:
                    if valid_tasks[-1]["count"] == count:
                        if kw is None:
                            if valid_tasks[-1]["params"]["keyword"] is None:
                                continue
                            
                        elif valid_tasks[-1]["params"]["keyword"] == kw:
                            continue

                if count >= MIN_COMPONENTS_FOR_TASK:
                    if validate_task(base_params, completed_tasks_set):
                        valid_tasks.append({"params": base_params, "count": count})
                        progress.log(f"[blue]INFO: Tarea validada: {base_params} -> {count} comps[/]")
                        
                    if count >= MAX_COMPONENTS_FOR_API_LIMIT:
                        for pref, lib, pcba, presale in over_len_combinations:
                            expanded_params = base_params.copy()
                            expanded_params.update({
                                "preferredComponentFlag": pref,
                                "componentLibraryType": lib,
                                "pcbAType": pcba,
                                "presaleType": presale
                            })
                            
                            if not validate_task(expanded_params, completed_tasks_set):
                                continue

                            expanded_count = api.get_jlcpcb_total_count(**expanded_params)
                            
                            if expanded_count >= MIN_COMPONENTS_FOR_TASK:
                                if expanded_count >= MAX_COMPONENTS_FOR_API_LIMIT:
                                    for asc, mode in sort_combinations:
                                        sort_params = expanded_params.copy()
                                        sort_params.update({"sortASC": asc, "sortMode": mode})
                                        
                                        if validate_task(sort_params, completed_tasks_set):
                                            valid_tasks.append({"params": sort_params, "count": expanded_count})
                                            progress.log(f"[blue]INFO: Tarea validada (expandida, sort): {sort_params} -> ~{expanded_count} comps[/]")
                                else:
                                    valid_tasks.append({"params": expanded_params, "count": expanded_count})
                                    progress.log(f"[blue]INFO: Tarea validada (expandida): {expanded_params} -> {expanded_count} comps[/]")
                    else:
                        for presale in presale_types:
                            pres_params = base_params.copy()
                            pres_params.update({"presaleType": presale})
                            
                            if not validate_task(pres_params, completed_tasks_set):
                                continue
                            
                            pres_count = api.get_jlcpcb_total_count(**pres_params)
                            
                            if pres_count >= MIN_COMPONENTS_FOR_TASK:
                                if pres_count >= MAX_COMPONENTS_FOR_API_LIMIT:
                                    for asc, mode in sort_combinations:
                                        sort_params = pres_params.copy()
                                        sort_params.update({"sortASC": asc, "sortMode": mode})
                                        
                                        if validate_task(sort_params, completed_tasks_set):
                                            valid_tasks.append({"params": sort_params, "count": pres_count})
                                            progress.log(f"[blue]INFO: Tarea validada (presale, sort): {sort_params} -> ~{pres_count} comps[/]")
                                else:
                                    valid_tasks.append({"params": pres_params, "count": pres_count})
                                    progress.log(f"[blue]INFO: Tarea validada (presale): {pres_params} -> {pres_count} comps[/]")
                        
                
                time.sleep(0.05)
            except Exception as e:
                if "sort_params" in locals():
                    progress.log(f"[red]ERROR: Falló verificación para {sort_params}: {e}[/]")
                elif "expanded_params" in locals():
                    progress.log(f"[yellow]WARN: Falló verificación para {expanded_params}: {e}[/]")
                else:
                    progress.log(f"[red]ERROR: Falló verificación para {base_params}: {e}[/]")
                time.sleep(0.2)
            
            progress.update(check_task_id, advance=1)
        
        progress.stop_task(check_task_id)
        progress.update(check_task_id, visible=False) # Ocultar barra de verificación

        # --- Resumen y Ejecución ---
        valid_tasks.sort(key=lambda x: x["count"], reverse=True)
        total_tasks_to_run = len(valid_tasks)

        summary_table = Table(title="Resumen de Plan de Descarga")
        summary_table.add_column("Concepto", style="cyan")
        summary_table.add_column("Cantidad", style="magenta")
        summary_table.add_row("Tareas potenciales", str(len(potential_tasks)))
        summary_table.add_row("Tareas nuevas válidas a ejecutar", f"[bold green]{total_tasks_to_run}[/]")
        console.print(summary_table)

        if not valid_tasks:
            console.print("\n[bold green]¡No hay nuevas tareas para ejecutar! El trabajo está completo.[/]")
            return

        console.print("\n[bold yellow]Iniciando descarga de tareas...[/]")
        
        # Barra para el progreso general de las tareas
        overall_task = progress.add_task("[bold blue]Progreso General", total=total_tasks_to_run)
        # Barra para la descarga de páginas de la tarea actual
        page_download_task = progress.add_task("[bold green]Descarga de Páginas", total=1, start=False)

        for i, task_info in enumerate(valid_tasks):
            params = task_info["params"]
            
            # --- 5. Descargar Componentes ---
            scraper_progress_args = {"progress": progress, "task_id": page_download_task}
            
            # Resetear y hacer visible la barra de descarga de páginas
            progress.reset(page_download_task, total=1, description="[bold green]Descarga de Páginas", visible=True)
            progress.start_task(page_download_task)

            df = api.get_jlcpcb_components(
                **params,
                pageSize=PAGE_SIZE,
                progress_mode="rich",
                progress_args=scraper_progress_args,
            )

            # Ocultar la barra de descarga de páginas una vez terminada
            progress.stop_task(page_download_task)
            progress.update(page_download_task, visible=False)

            # --- 6. Procesar y Guardar Resultados ---
            if df is not None:
                newly_added_components = []
                initial_id_count = len(processed_ids_set)
                
                components_list = df.to_dict(orient="records")

                for comp in components_list:
                    comp_id = comp.get("JLCPCB Part")
                    if comp_id and comp_id not in processed_ids_set:
                        newly_added_components.append(comp)
                        processed_ids_set.add(comp_id)
                
                if newly_added_components:
                    append_components_to_file(newly_added_components)
                
                task_tuple_to_save = tuple(sorted(params.items()))
                progress_data["completed_tasks"].append(dict(task_tuple_to_save))
                progress_data["processed_ids"] = list(processed_ids_set)
                save_progress(progress_data)

                # Log de tarea completada (similar al original)
                new_count = len(processed_ids_set) - initial_id_count
                log_msg = (
                    f"[green]✓ Tarea {i+1}/{total_tasks_to_run}:[/] "
                    f"{params} | "
                    f"Descargados: {len(df)} | Nuevos: {new_count} | Total Únicos: {len(processed_ids_set)}"
                )
                progress.log(log_msg)

            else:
                log_msg = (
                    f"[red]✗ Tarea {i+1}/{total_tasks_to_run} FAILED:[/]"
                    f" Parámetros: {params}"
                )
                progress.log(log_msg)

            progress.update(overall_task, advance=1)
    
    # --- 7. Finalización ---
    console.print("\n" + "="*60)
    console.print(f"[bold green]Proceso de descarga secuencial completado.[/]")
    console.print(f"Total de componentes únicos guardados en '{OUTPUT_FILENAME}': [bold cyan]{len(processed_ids_set)}[/]")
    console.print("="*60)


if __name__ == "__main__":
    start_time = time.time()
    try:
        download_sequentially_rich()
    except KeyboardInterrupt:
        console.print("\n\n[bold yellow]Descarga interrumpida por el usuario. El progreso ha sido guardado.[/]")
        sys.exit(0)
    finally:
        end_time = time.time()
        total_seconds = end_time - start_time
        minutes, seconds = divmod(total_seconds, 60)
        console.print(f"Tiempo total de ejecución: {int(minutes)} minutos y {seconds:.2f} segundos.")