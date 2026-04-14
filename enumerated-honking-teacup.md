# Plano: Histórico BCB — Atas e Comunicados COPOM

## Contexto
A usuária precisa de uma aplicação web para consultar, comparar e buscar atas e comunicados do COPOM (BCB). O objetivo é facilitar a análise de reuniões — ver diferenças entre documentos consecutivos (diff visual colorido), buscar palavras-chave com contexto histórico da Selic e exportar comparativos em PDF. A aplicação deve ser hospedada no GitHub Pages em https://github.com/nathaliadali/Historico-BCB.

---

## Abordagem: Single-file HTML (sem build system)
Mesmo padrão do app existente em `modelo-pequeno-porte` — tudo inline (CSS + JS + HTML), hospedagem estática via GitHub Pages. Vanilla JS, Chart.js via CDN.

---

## APIs utilizadas
| API | Endpoint |
|-----|----------|
| Ata por reunião | `https://www.bcb.gov.br/api/servico/sitebcb/copom/atas_detalhes?nro_reuniao={N}` |
| Comunicado por reunião | `https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao={N}` |
| Selic histórica | `https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados?formato=json` |

**Estrutura das respostas:**
- Ata: `conteudo[0].{ nroReuniao, dataReferencia, dataPublicacao, titulo, urlPdfAta, textoAta }`
- Comunicado: `conteudo[0].{ nro_reuniao, dataReferencia, titulo, textoComunicado }`
- Selic: `[{ data: "DD/MM/YYYY", valor: "13.75" }]`

---

## Paleta de cores (Icatu Vanguarda Brandbook)
```
--bcb:   #1B3157   (azul primário)
--bcb2:  #0D6696   (azul médio)
--teal:  #2E96BF
--cyan:  #00BADB   (destaque / borda)
--green: #5FBB47
--red:   #b91c1c
font: Palanquin (Google Fonts)
```
Diff: adições em `#5FBB47` (verde), remoções em `#b91c1c` (vermelho + strikethrough), sem fundo.

---

## Estrutura da aplicação (4 abas)

### Aba 1 — Comparativo de Atas
- Seletor de reunião atual (número) → anterior auto-preenche como N-1
- Botão "Comparar" → busca as duas atas via API, roda diff palavra-a-palavra
- Exibe: cabeçalho com nº e datas, legenda de cores, texto comparado
- Botão "Baixar PDF" → `window.print()` com CSS `@media print`

### Aba 2 — Comparativo de Comunicados
- Mesma lógica da Aba 1, mas usando a API de comunicados

### Aba 3 — Busca por Palavra
- Campo de texto + botão buscar
- Ao buscar: percorre todas as reuniões (255 → 1), carrega atas e comunicados, busca o termo
- Resultados agrupados em duas listas: **Atas** e **Comunicados**
  - Cada resultado: data formatada + trecho com palavra destacada + link "Ler documento completo"
  - Clicar abre modal com o texto completo e a palavra destacada
- Abaixo dos resultados: gráfico Chart.js da Selic com marcadores (bolinhas) nas datas onde a palavra foi encontrada
- Cache em `localStorage` para evitar re-fetch em buscas seguintes

### Aba 4 — Histórico Selic
- Chart.js com a série histórica completa da Selic (BGS 432)
- Interativo: hover mostra data e valor

---

## Algoritmo de Diff
Diff palavra-a-palavra simples (sem dependência externa):
1. Tokenizar ambos os textos por palavras (preservando espaços/pontuação como tokens)
2. Implementar LCS (Longest Common Subsequence) sobre os tokens
3. Renderizar: tokens apenas no novo → `<ins>`, tokens apenas no antigo → `<del>`, comuns → texto normal

Para textos HTML (como retorna a API), primeiro extrair texto puro via `DOMParser`, depois fazer diff por parágrafo/sentença para melhor legibilidade.

---

## Descoberta de reuniões
- Não existe endpoint de listagem
- Estratégia: começar em 255, decrementar até receber `conteudo: []` ou erro
- Limite prático: reuniões começam em torno de nro 1 (mas dados podem só existir a partir de ~100)
- Cache dos metadados (nro, data, tipo) no `localStorage` para agilizar buscas futuras

---

## Exportação PDF
- `window.print()` com `@media print` escondendo tudo exceto o painel de comparação
- CSS de impressão: fonte maior, cores preservadas (usar `-webkit-print-color-adjust: exact`)
- Cabeçalho impresso inclui: título, nº das reuniões, datas

---

## Arquivos a criar
| Arquivo | Descrição |
|---------|-----------|
| `index.html` | Aplicação completa (CSS + JS + HTML inline) |

---

## Deploy no GitHub Pages
1. Criar `index.html` no repositório local `c:\desenvolvimento\Atas e comunicados BCB`
2. Atualizar remote para `https://github.com/nathaliadali/Historico-BCB.git` (atualmente aponta para `nathaliadali/Atas-e-comunicados-BCB`)
3. Commit e push para branch `main`
4. Ativar GitHub Pages em Settings → Pages → Source: `main` / `/ (root)`

---

## Verificação
1. Abrir `https://nathaliadali.github.io/Historico-BCB/` no browser
2. Aba Comparativo Atas: selecionar reunião 255 → clicar Comparar → verificar diff colorido entre 255 e 254
3. Aba Comparativo Comunicados: idem para comunicados
4. Aba Busca: digitar "inflação" → verificar lista de resultados + gráfico Selic com marcadores
5. Botão Baixar PDF → verificar que abre diálogo de impressão com layout correto
6. Aba Selic: verificar gráfico com série histórica carregada
