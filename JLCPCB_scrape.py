import requests
import time

import pandas as pd
import numpy as np

from util import *



class JLCPCB_Scrape:
    """
    Clase que encapsula la lógica de interacción con la API interna de JLCPCB
    para buscar componentes electrónicos. Internamente almacenará los resultados
    en un DataFrame (self._df) para manipularlos con Pandas.
    """

    def __init__(
        self,
        url=None,
        cookie=None,
        secretkey=None,
        xsrf_token=None,
        user_agent=None,
        referer=None,
    ):
        """
        Constructor de la clase JLCPCB_Scrape, con soporte para parámetros avanzados.

        Parámetros opcionales:
        ----------------------
        url         : str  (Endpoint de la API)
        cookie      : str  (Cookies para la cabecera)
        secretkey   : str  (Valor de 'secretkey' en la cabecera)
        xsrf_token  : str  (Valor de 'x-xsrf-token')
        user_agent  : str  (User-Agent a enviar en las peticiones)
        referer     : str  (Referer a enviar en las peticiones)
        """

        # DataFrame donde almacenaremos todos los componentes.
        self._df = None

        if url is None:
            url = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList/v2"
        self.url = url

        if user_agent is None:
            user_agent = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            )
        if referer is None:
            referer = "https://jlcpcb.com/parts/all-electronic-components"

        self.headers = {
            "authority": "jlcpcb.com",
            "method": "POST",
            "path": "/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList/v2",
            "scheme": "https",
            "accept": "application/json, text/plain, */*",
            "accept-language": "es-419,es;q=0.9,en;q=0.8",
            "content-type": "application/json",
            "origin": "https://jlcpcb.com",
            "referer": referer,
            "user-agent": user_agent,
        }

        if cookie is not None:
            self.headers["cookie"] = cookie
        if secretkey is not None:
            self.headers["secretkey"] = secretkey
        if xsrf_token is not None:
            self.headers["x-xsrf-token"] = xsrf_token

    def _print_progress(self, current, total, bar_length=50):
        fraction = current / total if total else 1
        filled = int(bar_length * fraction)
        bar = "█" * filled + "-" * (bar_length - filled)
        print(
            f"\rDescargando páginas: |{bar}| {fraction*100:.1f}% ({current}/{total})",
            end="",
        )
        if current == total:
            print()

    def JLCPCB_API_query(
        self,
        keyword=None,
        currentPage=1,
        pageSize=25,
        presaleType="stock",
        pcbAType=None,
        photo=None,
        dateSheet=None,
        searchType=2,
        componentLibraryType=None,
        sortASC=None,
        sortMode=None,
        stockFlag=True,
        stockSort=None,
        preferredComponentFlag=None,
        startStockNumber=None,
        endStockNumber=None,
        searchSource="search",
    ) -> dict:
        """
        Realiza una consulta directa a la API de JLCPCB con un payload detallado.

        Args:
            --- Búsqueda y Paginación ---
            keyword (str, optional): Término de búsqueda principal (MPN, descripción, etc.).
            currentPage (int, optional): Número de la página de resultados. Defaults to 1.
            pageSize (int, optional): Cantidad de resultados por página (máx 100). Defaults to 25.
            searchSource (str, optional): Origen de la búsqueda, usualmente "search".

            --- Filtros Principales (Nuevos) ---
            presaleType (str, optional): Tipo de disponibilidad del componente.
                - "stock": (Default) Partes en stock.
                - "buy": Partes bajo pre-orden.
                - "post": Partes consignadas.
            pcbAType (int, optional): Filtra por el tipo de tarifa de ensamblaje (PCBA).
                - 1: "Economic"
                - 2: "Standard"
                - 3: "Economic" y "Standard"
                - None: (Default) Sin filtro.
            photo (bool, optional): Si es True, filtra componentes que tienen foto. Defaults to None.
            dateSheet (bool, optional): Si es True, filtra componentes con datasheet. (Nótese el typo en el nombre). Defaults to None.
            searchType (int, optional): Tipo de búsqueda interna. Usar 2 para obtener listas de componentes. Defaults to 2.

            --- Filtros Originales y Ordenación ---
            componentLibraryType (str, optional): Filtra por tipo de librería.
                - "base": Componentes de la librería básica.
                - "expand": Componentes de la librería extendida.
                - None: (Default) Ambas.
            preferredComponentFlag (bool, optional): Filtra por componentes "Preferidos".
                - True: Solo preferidos.
                - False: Solo no preferidos.
                - None: (Default) Sin filtro.
            stockFlag (bool, optional): Si es True, muestra solo componentes con stock > 0. Defaults to True.
            sortMode (str, optional): Criterio principal de ordenación.
                - "STOCK_SORT": Ordenar por cantidad en stock.
                - "PRICE_SORT": Ordenar por precio.
                - None: (Default) Ordenar por relevancia.
            sortASC (str, optional): Dirección de la ordenación ("ASC" o "DESC").
            stockSort (str, optional): Parámetro de ordenación de stock, usualmente se deja en None.
            startStockNumber (int, optional): Cantidad mínima de stock para filtrar.
            endStockNumber (int, optional): Cantidad máxima de stock para filtrar.

        Returns:
            dict: La respuesta JSON de la API o None si hay un error.
        """
        payload = {
            "keyword": keyword,
            "currentPage": currentPage,
            "pageSize": pageSize,
            "searchSource": searchSource,
            "presaleType": presaleType,
            "searchType": searchType,
            "pcbAType": pcbAType,
            "componentLibraryType": componentLibraryType,
            "preferredComponentFlag": preferredComponentFlag,
            "stockFlag": stockFlag,
            "stockSort": stockSort,
            "startStockNumber": startStockNumber,
            "endStockNumber": endStockNumber,
            "sortASC": sortASC,
            "sortMode": sortMode,
            # Parámetros que suelen estar vacíos en búsquedas generales
            "firstSortName": "",
            "secondSortName": "",
            "componentBrandList": [],
            "componentSpecificationList": [],
            "componentAttributeList": [],
            "firstSortNameList": [],
        }

        # Añadir filtros booleanos solo si son True, como hace el navegador
        if photo:
            payload['photo'] = True
        if dateSheet:
            payload['dateSheet'] = True

        try:
            resp = requests.post(self.url, headers=self.headers, json=payload)
            resp.raise_for_status()  # Lanza una excepción para errores HTTP (4xx o 5xx)
            data_json = resp.json()
            if data_json.get("code") == 200:
                return data_json
            else:
                print(f"Error en la respuesta de la API: {data_json.get('msg', 'Sin mensaje')}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Error en la petición a la API: {e}")
            return None

    def get_jlcpcb_total_count(self, **kwargs) -> int:
        """
        Obtiene el número total de componentes para una consulta dada.
        Acepta los mismos argumentos de filtrado que get_jlcpcb_components.
        """
        # Se establece una página y tamaño pequeños para optimizar
        kwargs['currentPage'] = 1
        kwargs['pageSize'] = 1

        data_json = self.JLCPCB_API_query(**kwargs)
        if data_json is None:
            return 0

        page_info = data_json.get("data", {}).get("componentPageInfo", {})
        return page_info.get("total", 0)

    def get_jlcpcb_components(
        self,
        keyword=None,
        pageSize=100,
        # --- Nuevos Parámetros con valores por defecto ---
        presaleType="stock",
        pcbAType=None,
        photo=None,
        dateSheet=None,
        # --- Parámetros Originales ---
        componentLibraryType=None,
        sortASC=None,
        sortMode=None,
        stockFlag=True,
        stockSort=None,
        preferredComponentFlag=None,
        startStockNumber=None,
        endStockNumber=None,
        searchSource="search",
        progress_mode: str = "rich",
        progress_args: dict = None,
    ) -> pd.DataFrame:
        """
        Descarga la lista completa de componentes desde la API de JLCPCB.
        Acepta todos los parámetros de filtrado y los pasa a la API.
        """
        current_page = 1
        query_params = {
            "keyword": keyword, "pageSize": pageSize, "presaleType": presaleType,
            "pcbAType": pcbAType, "photo": photo, "dateSheet": dateSheet,
            "componentLibraryType": componentLibraryType, "sortASC": sortASC, "sortMode": sortMode,
            "stockFlag": stockFlag, "stockSort": stockSort,
            "preferredComponentFlag": preferredComponentFlag, "startStockNumber": startStockNumber,
            "endStockNumber": endStockNumber, "searchSource": searchSource
        }

        data_json = self.JLCPCB_API_query(currentPage=current_page, **query_params)
        if data_json is None:
            return None

        page_info = data_json["data"]["componentPageInfo"]
        pages = page_info.get("pages", 1)
        raw_components = page_info.get("list", [])

        # Configuración de barra de progreso
        rich_progress = None
        if progress_mode == "rich" and progress_args:
            rich_progress = progress_args.get("progress")
            rich_task_id = progress_args.get("task_id")
            if rich_progress and rich_task_id is not None:
                rich_progress.update(rich_task_id, total=pages, completed=1)
                rich_progress.start_task(rich_task_id)
            else:
                progress_mode = "terminal" # Fallback a terminal
        
        if progress_mode == "terminal":
            self._print_progress(current_page, pages)

        # Descarga de páginas restantes
        if pages > 1:
            for p in range(2, pages + 1):
                data_p = self.JLCPCB_API_query(currentPage=p, **query_params)
                
                if data_p is None:
                    break
                
                page_info_p = data_p.get("data", {}).get("componentPageInfo")
                if page_info_p is None:
                    break
                
                raw_components.extend(page_info_p.get("list", []))


                # Actualizar progreso
                if progress_mode == 'rich':
                    try:
                        rich_progress.update(rich_task_id, advance=1)
                    except Exception as e:
                        print(f"Error actualizando progreso: {e}")
                        progress_mode = 'terminal'
                elif progress_mode == 'terminal':
                    self._print_progress(p, pages)
                
                time.sleep(0.1)

        # --- Procesamiento de datos en DataFrame ---
        if not raw_components:
            self._df = pd.DataFrame()
            return self._df
            
        df_raw = pd.DataFrame(raw_components)

        rename_map = {
            "componentModelEn": "Model", "componentBrandEn": "Manufacturer",
            "componentCode": "JLCPCB Part", "attributes": "Specifications",
            "componentSpecificationEn": "Package", "stockCount": "Stock",
            "componentPrices": "Price Tiers", "leastPatchNumber": "Min Assembly Qty",
            "dataManualUrl": "Datasheet URL", "allowPostFlag": "Assembly Available",
            "componentLibraryType": "Library Type", "preferredComponentFlag": "Preferred",
            "componentTypeEn": "Category", "describe": "Description",
            "minPurchaseNum": "Min Purchase Qty", "encapsulationNumber": "Reel Quantity",
            "lcscGoodsUrl": "Product URL", "componentId": "Component ID",
            "componentName": "Component Name", "erpComponentName": "Short Description",
        }

        original_cols_to_keep = [col for col in rename_map.keys() if col in df_raw.columns]
        if not original_cols_to_keep:
            self._df = pd.DataFrame()
            return None

        df_processed = df_raw[original_cols_to_keep].copy()
        rename_dict = {orig: new for orig, new in rename_map.items() if orig in df_processed.columns}
        df_processed.rename(columns=rename_dict, inplace=True)

        if "Assembly Available" in df_processed.columns:
            assembly_bool_map = {True: True, "true": True, 1: True, False: False, "false": False, 0: False}
            assembly_available_bool = df_processed["Assembly Available"].map(assembly_bool_map).fillna(False)
            df_processed = df_processed[assembly_available_bool].copy()
            df_processed.drop(columns=["Assembly Available"], inplace=True)

        if "Library Type" in df_processed.columns and "Preferred" in df_processed.columns:
            cond_base = df_processed["Library Type"] == "base"
            preferred_bool_map = {True: True, "true": True, 1: True, False: False, "false": False, 0: False}
            preferred_bool = df_processed["Preferred"].map(preferred_bool_map).fillna(False)
            cond_expand_pref = (df_processed["Library Type"] == "expand") & (preferred_bool == True)
            cond_expand_not_pref = (df_processed["Library Type"] == "expand") & (preferred_bool == False)
            choices = [0, 1, 2]
            df_processed["Preference Level"] = np.select([cond_base, cond_expand_pref, cond_expand_not_pref], choices, default=2)

        for col in df_processed.columns:
            if df_processed[col].dtype == "object":
                first_non_null = df_processed[col].dropna().iloc[0] if not df_processed[col].dropna().empty else None
                if isinstance(first_non_null, str):
                    df_processed[col] = df_processed[col].apply(clean_text_value)
                elif col == "Specifications" and isinstance(first_non_null, list):
                    def clean_specs(spec_list):
                        if not isinstance(spec_list, list): return spec_list
                        return [{clean_text_value(k): clean_text_value(v) for k, v in spec_dict.items()} if isinstance(spec_dict, dict) else spec_dict for spec_dict in spec_list]
                    df_processed[col] = df_processed[col].apply(clean_specs)
        
        self._df = df_processed
        return self._df



if __name__ == "__main__":
    # Ejemplo de uso
    api = JLCPCB_Scrape()

    print("--- Ejemplo 1: Consulta básica a la API (primeros 5 componentes en stock) ---")
    res = api.JLCPCB_API_query(pageSize=5, stockFlag=True)
    if res:
        print("Consulta exitosa:\n")
        # Imprime solo algunos campos clave para mayor claridad
        for item in res["data"]["componentPageInfo"]["list"]:
            print(f"  - {item.get('componentModelEn', 'N/A')} ({item.get('componentCode', 'N/A')})")
        print("\n" + "="*50 + "\n")
    else:
        print("Error en la consulta.")

    print("--- Ejemplo 2: Descargar componentes 'Pre-order' con datasheet ---")
    # Usando los nuevos parámetros: presaleType="buy" y dateSheet=True
    df = api.get_jlcpcb_components(
        keyword="stm32",
        presaleType="buy",  # Busca en "Pre-order Parts"
        dateSheet=True,     # Filtra los que tienen datasheet
        pageSize=50,        # Limita la descarga para el ejemplo
        progress_mode="terminal",
    )