import requests
import json
import time
import unicodedata
import pandas as pd
import numpy as np


def strip_accents_and_lower(text: str) -> str:
    """
    Elimina diacríticos (tildes) y pasa la cadena a minúsculas.
    """
    if not text:
        return ""
    text_nfd = unicodedata.normalize("NFD", text)
    text_without_accents = "".join(
        c for c in text_nfd if unicodedata.category(c) != "Mn"
    )
    return text_without_accents.lower()


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

        # Variable para almacenar metadatos de la descarga.
        self.metadata = {}

        # 1) URL por defecto
        if url is None:
            url = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList/v2"
        self.url = url

        # 2) Definir user-agent y referer por defecto, si no se especifican.
        if user_agent is None:
            user_agent = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            )
        if referer is None:
            referer = "https://jlcpcb.com/parts/all-electronic-components"

        # 3) Construir cabeceras mínimas necesarias.
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

        # 4) Agregar parámetros opcionales (si no son None).
        if cookie is not None:
            self.headers["cookie"] = cookie

        if secretkey is not None:
            self.headers["secretkey"] = secretkey

        if xsrf_token is not None:
            self.headers["x-xsrf-token"] = xsrf_token

    def _print_progress(self, current, total, bar_length=50):
        """
        Método interno para imprimir una barra de progreso simple en la terminal.
        current: página actual
        total  : total de páginas
        """
        fraction = current / total if total else 1
        filled = int(bar_length * fraction)
        bar = "█" * filled + "-" * (bar_length - filled)
        print(
            f"\rDescargando páginas: |{bar}| {fraction*100:.1f}% ({current}/{total})",
            end="",
        )
        if current == total:
            print()

    def get_jlcpcb_total_count(
        self,
        keyword=None,
        componentLibraryType=None,
        preferredComponentFlag=None,
        stockFlag=True,
        stockSort=None,
        startStockNumber=None,
        endStockNumber=None,
        firstSortName=None,
        secondSortName=None,
        componentBrand=None,
        componentSpecification=None,
        componentAttributes=None,
        sortASC=None,  # "ASC" o "DESC"
        sortMode=None,  # "STOCK_SORT" o "PRICE_SORT"
        pageSize=25,
        searchSource="search",
    ) -> int:
        """
        Retorna la cantidad total de componentes encontrados según los parámetros indicados,
        sin descargar todas las páginas.
        """
        payload = {
            "pageSize": pageSize,
            "keyword": keyword,
            "componentLibraryType": componentLibraryType,
            "preferredComponentFlag": preferredComponentFlag,
            "stockFlag": stockFlag,
            "stockSort": stockSort,
            "startStockNumber": startStockNumber,
            "endStockNumber": endStockNumber,
            "firstSortName": firstSortName,
            "secondSortName": secondSortName,
            "componentBrand": componentBrand,
            "componentSpecification": componentSpecification,
            "componentAttributes": componentAttributes or [],
            "searchSource": searchSource,
            "currentPage": 1,
            "sortASC": sortASC,
            "sortMode": sortMode,
        }

        resp = requests.post(self.url, headers=self.headers, json=payload)
        if resp.status_code != 200:
            raise RuntimeError(
                f"[get_jlcpcb_total_count] Respuesta HTTP no exitosa: {resp.status_code}"
            )

        data_json = resp.json()
        if data_json.get("code") != 200:
            raise RuntimeError(
                f"[get_jlcpcb_total_count] code != 200. Mensaje: {data_json.get('message','Desconocido')}"
            )

        page_info = data_json["data"]["componentPageInfo"]
        total = page_info.get("total", 0)
        return total

    def get_jlcpcb_components(
        self,
        keyword=None,
        componentLibraryType=None,
        preferredComponentFlag=None,
        stockFlag=True,
        stockSort=None,
        startStockNumber=None,
        endStockNumber=None,
        firstSortName=None,
        secondSortName=None,
        componentBrand=None,
        componentSpecification=None,
        componentAttributes=None,
        sortASC=None,  # "ASC" o "DESC"
        sortMode=None,  # "STOCK_SORT" o "PRICE_SORT"
        pageSize=25,
        searchSource="search",
    ) -> pd.DataFrame:
        """
        Descarga la lista completa de componentes desde la API de JLCPCB
        (todas las páginas) y los almacena en un DataFrame (self._df).
        También retorna dicho DataFrame.
        """

        # Petición inicial (página 1) para extraer metadatos
        base_payload = {
            "pageSize": pageSize,
            "keyword": keyword,
            "componentLibraryType": componentLibraryType,
            "preferredComponentFlag": preferredComponentFlag,
            "stockFlag": stockFlag,
            "stockSort": stockSort,
            "startStockNumber": startStockNumber,
            "endStockNumber": endStockNumber,
            "firstSortName": firstSortName,
            "secondSortName": secondSortName,
            "componentBrand": componentBrand,
            "componentSpecification": componentSpecification,
            "componentAttributes": componentAttributes or [],
            "searchSource": searchSource,
            "sortASC": sortASC,
            "sortMode": sortMode,
        }

        current_page = 1
        payload = base_payload.copy()
        payload["currentPage"] = current_page

        resp = requests.post(self.url, headers=self.headers, json=payload)
        if resp.status_code != 200:
            raise RuntimeError(
                f"[get_jlcpcb_components] Error HTTP {resp.status_code} en página 1."
            )

        data_json = resp.json()
        if data_json.get("code") != 200:
            raise RuntimeError(
                f"[get_jlcpcb_components] code != 200 en página 1. Mensaje: {data_json.get('message','Desconocido')}"
            )

        page_info = data_json["data"]["componentPageInfo"]
        pages = page_info.get("pages", 1)
        total = page_info.get("total", 0)
        page_size = page_info.get("pageSize", pageSize)

        raw_components = page_info.get("list", [])
        self._print_progress(current_page, pages)

        # 2) Iterar por las demás páginas
        for p in range(2, pages + 1):
            payload["currentPage"] = p
            r = requests.post(self.url, headers=self.headers, json=payload)
            if r.status_code != 200:
                print(
                    f"[get_jlcpcb_components] Advertencia: HTTP {r.status_code} al pedir la página {p}. Se detiene."
                )
                break

            data_p = r.json()
            if data_p.get("code") != 200:
                print(
                    f"[get_jlcpcb_components] Advertencia: code != 200 en página {p}. Se detiene."
                )
                print(data_json)
                break

            page_info_p = data_p.get("data", {}).get("componentPageInfo")
            if page_info_p is None:
                print(f"[get_jlcpcb_components] page_info_p es None en página {p}")
                break

            raw_components.extend(page_info_p.get("list", []))
            self._print_progress(p, pages)
            time.sleep(0.2)

        # Convertir a DataFrame
        df = pd.DataFrame(raw_components)

        # Mapeo de campos [nombre_original] -> [nuevo_nombre]
        # Observa que aquí invertimos el dict que tenías en tu código para renombrar.
        rename_map = {
            "componentCode": "JLCPCB Part",
            "componentId": "Component ID",
            "componentName": "Component Name",
            "componentModelEn": "Model",
            "componentTypeEn": "Category",
            "firstSortName": "Primary Classification",
            "secondSortName": "Secondary Classification",
            "componentSpecificationEn": "Package",
            "describe": "Description",
            "componentBrandEn": "Manufacturer",
            "stockCount": "Stock Count",
            "componentPrices": "Price Tiers",
            "componentLibraryType": "Component Type",
            "preferredComponentFlag": "Preferred Component",
            "componentProductType": "Product Type",
            "allowPostFlag": "Allows Purchase",
            "componentAlternativesCode": "Alternatives",
            "lcscGoodsUrl": "Product Page URL",
            "dataManualUrl": "Datasheet URL",
        }

        # Renombramos las columnas existentes
        common_cols = set(rename_map.keys()).intersection(df.columns)
        rename_dict = {k: rename_map[k] for k in common_cols}
        df.rename(columns=rename_dict, inplace=True)

        # Guardar el DataFrame en la instancia
        self._df = df

        # Guardamos metadata
        self.metadata = {
            "payload_parameters": base_payload,
            "pages": pages,
            "total": len(df),
            "pageSize": page_size,
        }

        return self._df

    def load_json_from_file(self, filename: str):
        """
        Carga un archivo JSON (exportado previamente)
        y lo asigna a self._df para reutilizarlo en las búsquedas.
        """
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Asumimos que el JSON tiene la estructura: {"metadata": {...}, "components": [...]} 
        # según tu código original. Ajustamos para cargar en un DataFrame.
        if "components" in data:
            df = pd.DataFrame(data["components"])
            self._df = df
            self.metadata = data.get("metadata", {})
        else:
            # En caso de que el JSON sea directamente una lista de componentes
            self._df = pd.DataFrame(data)
            self.metadata = {}

    def _get_min_price(self, price_tiers) -> float:
        """
        Retorna el menor precio dentro de 'Price Tiers' de un componente,
        o un valor grande (999999) si no existe.
        """
        if not isinstance(price_tiers, list) or len(price_tiers) == 0:
            return 999999
        min_price = 999999
        for tier in price_tiers:
            if tier and isinstance(tier, dict):
                p = tier.get("productPrice", 999999)
                if p < min_price:
                    min_price = p
        return min_price

    def search_components(
        self,
        query_text: str = None,
        component_type: str = None,  # 'base', 'expand', etc.
        preferred: bool = None,      # True/False
        allows_purchase: bool = None,# True/False
        min_stock: int = None,       # stock mínimo
    ) -> pd.DataFrame:
        """
        Realiza la búsqueda y filtrado sobre self._df (DataFrame).

        Filtros:
           - query_text: busca en varios campos (sin tildes, case-insensitive).
           - component_type: Filtra por "Component Type" => 'base', 'expand', etc.
           - preferred: Filtra por "Preferred Component" => True/False
           - allows_purchase: Filtra por "Allows Purchase" => True/False
           - min_stock: Filtra componentes con "Stock Count" >= min_stock

        Orden final (ascendente):
          1) stock>0 primero  (is_stock_zero = 0 para stock>0, 1 para stock=0)
          2) "Component Type": 'base' primero (is_expand = 0 si base, 1 si no-base)
          3) "Preferred Component": True primero (is_not_preferred=0 si True, 1 si False)
          4) precio asc (min_price)

        Retorna un DataFrame con los resultados filtrados y ordenados.
        """

        if self._df is None or self._df.empty:
            print("[search_components] No hay datos en self._df. Carga u obtiene datos primero.")
            return pd.DataFrame()

        df = self._df.copy()

        # ---- 1) APLICACIÓN DE FILTROS ----

        # Filtro por component_type
        if component_type is not None:
            df = df[df["Component Type"] == component_type]

        # Filtro por preferred
        if preferred is not None:
            df = df[df["Preferred Component"] == preferred]

        # Filtro por allows_purchase
        if allows_purchase is not None:
            df = df[df["Allows Purchase"] == allows_purchase]

        # Filtro por min_stock
        if min_stock is not None:
            df = df[df["Stock Count"].fillna(0) >= min_stock]

        # Filtro texto: se buscan todas las palabras en varios campos
        if query_text:
            query_words = [
                strip_accents_and_lower(word) for word in query_text.split() if word.strip()
            ]
            if query_words:
                text_fields = [
                    "JLCPCB Part",
                    "Component Name",
                    "Model",
                    "Category",
                    "Primary Classification",
                    "Secondary Classification",
                    "Package",
                    "Description",
                    "Manufacturer",
                ]
                # Asegurarnos de que existan esas columnas en df
                text_fields = [f for f in text_fields if f in df.columns]

                # Creamos una sola columna con la concatenación de texto normalizado
                def normalize_row(row):
                    vals = []
                    for col in text_fields:
                        val = row[col] if pd.notnull(row[col]) else ""
                        vals.append(strip_accents_and_lower(str(val)))
                    return " ".join(vals)

                # Generamos la columna 'search_concat'
                df["search_concat"] = df.apply(normalize_row, axis=1)

                # Para filtrar, requerimos que cada palabra de query_words esté presente
                for w in query_words:
                    df = df[df["search_concat"].str.contains(w)]

                # Eliminamos la columna auxiliar
                df.drop(columns=["search_concat"], inplace=True)

        # ---- 2) ORDENAMIENTO ----
        # Definimos columnas auxiliares para replicar la lógica:
        # stock>0 => is_stock_zero=0, si stock=0 => 1
        df["is_stock_zero"] = np.where(df["Stock Count"].fillna(0) > 0, 0, 1)

        # 'base' => is_expand=0, caso contrario => 1
        # OJO: si no existe la columna "Component Type", se asume 1
        df["is_expand"] = np.where(df["Component Type"] == "base", 0, 1)

        # True => is_not_preferred=0, False => 1
        df["is_not_preferred"] = np.where(df["Preferred Component"] == True, 0, 1)

        # min_price => calculamos con la misma lógica de _get_min_price
        # (si en tu DataFrame "Price Tiers" ya tiene la estructura, podrías vectorizar;
        #  por simplicidad hacemos un apply para cada fila).
        df["min_price"] = df["Price Tiers"].apply(self._get_min_price)

        # Ordenamos con sort_values ascendente en todas las columnas
        df.sort_values(
            by=["is_stock_zero", "is_expand", "is_not_preferred", "min_price"],
            ascending=[True, True, True, True],
            inplace=True
        )

        # Limpiamos columnas auxiliares antes de retornar
        df.drop(
            columns=["is_stock_zero", "is_expand", "is_not_preferred", "min_price"],
            inplace=True
        )

        return df
