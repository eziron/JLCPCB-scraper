from JLCPCB_scrape import JLCPCB_Scrape
import json

api = JLCPCB_Scrape()
n = api.get_jlcpcb_total_count(
    stockFlag=True,
    startStockNumber=1000
)
print(f"Componentes encontrados: {n}")

data = api.get_jlcpcb_components(
    pageSize=1000,
    stockFlag=True,
    startStockNumber=1000
)
print(f"\nSe han obtenido {len(data['components'])} componentes en total.\n")

with open("jlcpcb_parts.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print("Archivo 'jlcpcb_parts.json' guardado correctamente.\n")