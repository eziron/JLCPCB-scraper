from JLCPCB_scrape import JLCPCB_Scrape
import json

def download_with_various_sorts():
    api = JLCPCB_Scrape()
    
    n = api.get_jlcpcb_total_count(
        stockFlag=True,
    )
    print(f"Componentes encontrados: {n}")

    # --- Opciones de sort que queremos usar ---
    sort_combinations = [
        (None,  None),
        ("ASC",  "STOCK_SORT"),
        ("DESC", "STOCK_SORT"),
        ("ASC",  "PRICE_SORT"),
        ("DESC", "PRICE_SORT"),
    ]

    # Diccionario para acumular los componentes sin duplicados
    # Clave: "JLCPCB Part", Valor: diccionario completo del componente
    combined_components = {}

    for (asc, mode) in sort_combinations:
        print(f"\n>>> Descargando con sortASC='{asc}' y sortMode='{mode}' ...")

        # Llamamos a get_jlcpcb_components con los parámetros deseados
        data = api.get_jlcpcb_components(
            pageSize=1000,
            stockFlag=True,
            sortASC=asc,
            sortMode=mode
        )
        # data es un diccionario con "metadata" y "components"
        comps_list = data.get("components", [])
        print(f"  -> Se obtuvieron {len(comps_list)} componentes en esta descarga.")

        # Insertar en nuestro dict para evitar duplicados
        for comp in comps_list:
            jlcpcb_part = comp.get("JLCPCB Part")
            if jlcpcb_part:
                combined_components[jlcpcb_part] = comp

        # Si deseas pausar un poco entre descargas
        # import time
        # time.sleep(2)

    # Al final de todas las descargas, tenemos un dict sin duplicados
    final_list = list(combined_components.values())
    print(f"\nTotal de componentes únicos combinados: {len(final_list)}")

    # Podrías guardarlos en un JSON, igual que antes
    result_data = {
        "metadata": {
            "downloadMode": "sortASC/sortMode combined",
            "uniqueCount": len(final_list),
        },
        "components": final_list
    }

    with open("jlcpcb_parts_combined.json", "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    print("Archivo 'jlcpcb_parts_combined.json' guardado correctamente.\n")


if __name__ == "__main__":
    download_with_various_sorts()
