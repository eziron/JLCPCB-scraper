from JLCPCB_scrape_pandas import JLCPCB_Scrape

def main():
    # Instanciamos la clase.
    api = JLCPCB_Scrape()

    # Cargamos el archivo JSON (ya descargado previamente).
    # Esto internamente lo almacenará en un DataFrame en api._df
    api.load_json_from_file("jlcpcb_parts_combined.json")
    print("Archivo JSON cargado con éxito.\n")

    while True:
        query_text = input("Ingresa la búsqueda (o 'exit' para salir): ")

        # Opción para salir
        if query_text.strip().lower() == "exit":
            print("Saliendo del programa.")
            break

        # Ejemplo de uso: Buscamos con min_stock=100 como en tu código original
        found_df = api.search_components(query_text=query_text, min_stock=100)

        # Convertimos el DataFrame en una lista de diccionarios (registros)
        found_records = found_df.to_dict(orient="records")

        print(f"Encontrados {len(found_records)} componentes con '{query_text}'.\n")

        if not found_records:
            # Si la lista de resultados está vacía, no imprimimos nada más
            print("No se encontraron resultados con esa búsqueda.\n")
            continue

        # Definimos las columnas que queremos mostrar
        columns = [
            "JLCPCB Part",
            "Component Type",
            "Preferred Component",
            "Product Type",
            "Stock Count",
            "Model",
            "Category",
            "Package",
            "Description",
        ]

        # Calculamos el ancho máximo de cada columna
        # (entre el nombre de la columna y los valores, ambos convertidos a string)
        widths = {}
        for col in columns:
            max_width_in_column = len(col)  # considerar ancho del título de la columna
            for rec in found_records:
                val = rec.get(col, "")
                val_width = len(str(val))
                if val_width > max_width_in_column:
                    max_width_in_column = val_width
            widths[col] = max_width_in_column

        # Imprimimos la cabecera, ajustando cada columna a su ancho
        header_row = " | ".join(col.ljust(widths[col]) for col in columns)
        print(header_row)
        print("-" * len(header_row))  # separador

        # Imprimimos cada fila
        for rec in reversed(found_records):
            row = " | ".join(str(rec.get(col, "")).ljust(widths[col]) for col in columns)
            print(row)

        print("\n")  # Espacio adicional entre búsquedas

if __name__ == "__main__":
    main()
