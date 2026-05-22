# Histórico BCB — Contexto do Projeto

## O que é este projeto

Aplicação web estática (um único `index.html`) que exibe o histórico de atas e comunicados do COPOM (Banco Central do Brasil). Hospedada no GitHub Pages em `nathaliadali/Historico-BCB`.

Funcionalidades principais:
- Visualização de atas e comunicados individuais
- **Comparativo entre reuniões** (diff palavra a palavra, estilo Word track-changes)
- **Busca por palavra-chave** em todas as reuniões
- Gráfico histórico da taxa Selic com marcação de ocorrências

---

## Arquitetura

```
index.html          — todo o frontend (HTML + CSS + JS em um arquivo)
baixar-dados.py     — script Python que baixa dados do BCB e gera os JSONs
data/
  meta.json         — lista de reuniões com datas (carregado na inicialização)
  search-index.json — texto completo de todas as reuniões (busca instantânea)
  selic.json        — série histórica da Selic
  docs/
    ata_NNN.json    — ata individual (tem campo "paragrafos" pré-extraído)
    com_NNN.json    — comunicado individual (tem campo "paragrafos" pré-extraído)
```

**GitHub Actions** (`.github/workflows/atualizar-dados.yml`): roda `baixar-dados.py` automaticamente toda terça 08:15 e quarta 19:00 (horário de Brasília), commita e faz push dos dados novos.

---

## Decisões técnicas importantes

### Diff (comparativo entre reuniões)

O diff usa **SequenceMatcher de dois níveis**, replicando o comportamento do Word track-changes:

1. **Nível parágrafo**: LCS (`getParaOpcodes`) alinha parágrafos por similaridade mínima de 0.55
2. **Nível palavra**: `diffParagrafo` faz LCS palavra a palavra dentro de cada par de parágrafos alinhados

Regras críticas:
- `tokenize()` usa **apenas palavras** (`\S+`), **sem tokens de espaço**. Se incluir espaços, o `groupOps` não consegue juntar palavras e aparecem "palavras soltas" no diff.
- `groupOps()` agrupa tokens consecutivos do mesmo tipo separando com `' '`
- **Change-ratio guard**: se >65% das palavras mudaram, retorna `null` → caller usa formato bloco (del parágrafo inteiro + ins parágrafo inteiro)
- **LCS tie-breaking**: usa `>` (não `>=`) para que DEL apareça antes de INS após o `reverse()` do backtracking

### Extração de parágrafos (tabelas)

`htmlToParagraphs()` no frontend usa o seletor `'p, li, h1, h2, h3, h4, h5, h6, tr'`. Para `<tr>`, junta as células com `'  '` (dois espaços) em vez de criar um parágrafo por célula — isso evita que a tabela de projeções de inflação apareça fragmentada.

O mesmo comportamento está replicado em `html_to_paragraphs()` no `baixar-dados.py` (classe `_ParagraphExtractor`).

### Campo `paragrafos` nos JSONs

Cada `ata_NNN.json` e `com_NNN.json` tem um campo `paragrafos` pré-extraído (array de strings). O frontend usa esse campo quando disponível, evitando re-parsear o HTML a cada comparação. Se o campo estiver ausente (arquivos antigos), extrai na hora via `htmlToParagraphs()`.

### Busca por palavra-chave

- Carrega `search-index.json` uma vez por sessão de página
- Busca in-memory com `indexOf` (case-insensitive)
- Resultados exibidos em **duas seções separadas**: Atas e Comunicados (o comunicado pode aparecer sem ata correspondente)
- Se o browser tiver cache antigo do `search-index.json`, fazer **Ctrl+Shift+R** para forçar reload

---

## APIs do BCB

```
Ata:        https://www.bcb.gov.br/api/servico/sitebcb/copom/atas_detalhes?nro_reuniao=NNN
Comunicado: https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=NNN
Selic:      https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados?formato=json&dataInicial=DD/MM/YYYY&dataFinal=DD/MM/YYYY
```

Reuniões numeradas sequencialmente. A mais recente no momento desta escrita é a **278** (comunicado de 29/04/2026, ata ainda não publicada).

---

## Como atualizar os dados

**Automático**: GitHub Actions roda terça e quarta — não precisa fazer nada.

**Manual** (forçar agora): GitHub → Actions → "Atualizar Dados BCB" → "Run workflow".

**Local**: `py baixar-dados.py` (apenas se necessário; o Actions cuida disso).

---

## Dívidas técnicas / coisas a saber

- `baixar-dados.js` existe na raiz mas não é usado — pode ser ignorado
- O campo `paragrafos` usa `len(text) > 0` no `_flush()` para capturar valores curtos de tabela (ex: "3,9")
- Alguns textos do BCB começam com zero-width space (U+200B) — isso é normal, não afeta a busca
