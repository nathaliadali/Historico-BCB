"""
baixar-dados.py
Baixa todas as atas, comunicados e Selic do BCB e gera:

  data/
    meta.json           - lista de reuniões com datas
    selic.json          - série histórica Selic
    search-index.json   - TODOS os textos em um arquivo (busca instantânea)
    docs/
      ata_NNN.json      - ata individual (para comparativo)
      com_NNN.json      - comunicado individual (para comparativo)

Uso:
  py baixar-dados.py
  py baixar-dados.py --inicio 280   (começa de um número diferente)
  py baixar-dados.py --rebuild      (ignora arquivos existentes e rebaixa tudo)
"""

import urllib.request
import urllib.error
import json
import os
import sys
import time
import html
from html.parser import HTMLParser

# -----------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------
REUNIAO_INICIO = 300
MAX_FALHAS     = 6
DELAY_MS       = 120   # ms entre requests (não sobrecarrega a API)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DOCS_DIR = os.path.join(DATA_DIR, "docs")

API_ATA   = "https://www.bcb.gov.br/api/servico/sitebcb/copom/atas_detalhes?nro_reuniao={}"
API_COM   = "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao={}"
API_SELIC = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados?formato=json"

# -----------------------------------------------------------------------
# HTML → texto puro
# -----------------------------------------------------------------------
class _TextExtractor(HTMLParser):
    BLOCK = {'p','div','h1','h2','h3','h4','h5','h6','li','tr','td','th','blockquote','section','article'}
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data)
    def handle_starttag(self, tag, attrs):
        if tag == 'br':
            self.parts.append('\n')
        elif tag in self.BLOCK:
            self.parts.append('\n\n')
    def handle_endtag(self, tag):
        if tag in self.BLOCK:
            self.parts.append('\n\n')

def html_to_text(raw):
    if not raw:
        return ""
    # decodifica entidades HTML primeiro
    raw = html.unescape(raw)
    p = _TextExtractor()
    p.feed(raw)
    text = "".join(p.parts)
    # normaliza quebras
    import re
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

# -----------------------------------------------------------------------
# HTTP
# -----------------------------------------------------------------------
def fetch_json(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "BCB-Historico/1.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(0.5 * (attempt + 1))
            else:
                return None

# -----------------------------------------------------------------------
# Diretórios
# -----------------------------------------------------------------------
os.makedirs(DOCS_DIR, exist_ok=True)

# -----------------------------------------------------------------------
# Args
# -----------------------------------------------------------------------
rebuild = "--rebuild" in sys.argv
inicio  = REUNIAO_INICIO
for i, arg in enumerate(sys.argv):
    if arg == "--inicio" and i + 1 < len(sys.argv):
        inicio = int(sys.argv[i + 1])

# -----------------------------------------------------------------------
# Download Selic
# -----------------------------------------------------------------------
def baixar_selic():
    print("\nBaixando série histórica da Selic...")
    selic_file = os.path.join(DATA_DIR, "selic.json")
    if os.path.exists(selic_file) and not rebuild:
        data = json.loads(open(selic_file, encoding="utf-8").read())
        print(f"  ✓ já existe ({len(data)} pontos)")
        return data
    data_raw = fetch_json(API_SELIC)
    if not data_raw:
        print("  ✗ erro ao baixar Selic")
        return []
    data = []
    for p in data_raw:
        parts = p["data"].split("/")
        data.append({"x": f"{parts[2]}-{parts[1]}-{parts[0]}", "y": float(p["valor"])})
    with open(selic_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"  ✓ {len(data)} observações → data/selic.json")
    return data

# -----------------------------------------------------------------------
# Download reuniões
# -----------------------------------------------------------------------
def baixar_reunioes():
    print(f"\nBaixando reuniões a partir de {inicio}...\n")
    meta         = []
    search_index = []
    nro          = inicio
    falhas_consec = 0
    total        = 0

    while nro >= 1 and falhas_consec < MAX_FALHAS:
        ata_file = os.path.join(DOCS_DIR, f"ata_{nro}.json")
        com_file = os.path.join(DOCS_DIR, f"com_{nro}.json")

        ata_existe = os.path.exists(ata_file)
        com_existe = os.path.exists(com_file)

        ata_data = None
        com_data = None
        achou    = False

        # Ata
        if ata_existe and not rebuild:
            with open(ata_file, encoding="utf-8") as f:
                ata_data = json.load(f)
            achou = True
        else:
            resp = fetch_json(API_ATA.format(nro))
            if resp and resp.get("conteudo"):
                ata_data = resp["conteudo"][0]
                with open(ata_file, "w", encoding="utf-8") as f:
                    json.dump(ata_data, f, ensure_ascii=False)
                achou = True
            time.sleep(DELAY_MS / 1000)

        # Comunicado
        if com_existe and not rebuild:
            with open(com_file, encoding="utf-8") as f:
                com_data = json.load(f)
            achou = True
        else:
            resp = fetch_json(API_COM.format(nro))
            if resp and resp.get("conteudo"):
                com_data = resp["conteudo"][0]
                with open(com_file, "w", encoding="utf-8") as f:
                    json.dump(com_data, f, ensure_ascii=False)
                achou = True
            time.sleep(DELAY_MS / 1000)

        if achou:
            data_ata = ata_data.get("dataReferencia") or ata_data.get("dataPublicacao") if ata_data else None
            data_com = com_data.get("dataReferencia") if com_data else None

            meta.append({
                "nro":     nro,
                "dataAta": data_ata,
                "dataCom": data_com,
            })

            # Extrai texto puro para o índice de busca
            texto_ata = html_to_text(ata_data.get("textoAta", "")) if ata_data else ""
            texto_com = html_to_text(com_data.get("textoComunicado", "")) if com_data else ""

            search_index.append({
                "nro":     nro,
                "dataAta": data_ata,
                "dataCom": data_com,
                "ata":     texto_ata,
                "com":     texto_com,
            })

            falhas_consec = 0
            total += 1
            status = f"ata={'sim' if ata_data else 'não':3s}  com={'sim' if com_data else 'não':3s}"
            print(f"  Reunião {nro:3d}  {status}  {'(cache)' if (ata_existe and com_existe and not rebuild) else ''}")
        else:
            falhas_consec += 1
            print(f"  Reunião {nro:3d}  não encontrada  ({falhas_consec}/{MAX_FALHAS})")

        nro -= 1

    # Ordena decrescente
    meta.sort(key=lambda x: x["nro"], reverse=True)
    search_index.sort(key=lambda x: x["nro"], reverse=True)

    # Salva meta.json
    with open(os.path.join(DATA_DIR, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # Salva search-index.json (sem indentação para economizar espaço)
    idx_path = os.path.join(DATA_DIR, "search-index.json")
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(search_index, f, ensure_ascii=False)

    idx_kb = os.path.getsize(idx_path) // 1024
    print(f"\n  ✓ {total} reuniões")
    print(f"  ✓ data/meta.json")
    print(f"  ✓ data/search-index.json  ({idx_kb} KB)")
    print(f"  ✓ data/docs/  ({total*2} arquivos individuais)")

    return meta, search_index

# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------
if __name__ == "__main__":
    t0 = time.time()
    print("=" * 50)
    print("  Baixar Dados BCB COPOM")
    print("=" * 50)

    baixar_selic()
    baixar_reunioes()

    elapsed = time.time() - t0
    print(f"\nConcluído em {elapsed:.1f}s")
    print("\nPróximo passo:")
    print('  git add data/')
    print('  git commit -m "data: base local de atas e comunicados"')
    print("  git push\n")
