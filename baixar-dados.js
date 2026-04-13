/**
 * baixar-dados.js
 * Baixa todas as atas, comunicados e série Selic do BCB
 * e salva em ./data/ para uso offline no index.html
 *
 * Uso: node baixar-dados.js
 * Requer Node.js 18+ (fetch nativo) ou 16+ com --experimental-fetch
 */

const fs   = require('fs');
const path = require('path');
const https = require('https');

const DATA_DIR = path.join(__dirname, 'data');
const DOCS_DIR = path.join(DATA_DIR, 'docs');

// Garante que os diretórios existem
fs.mkdirSync(DOCS_DIR, { recursive: true });

const API_ATA   = n => `https://www.bcb.gov.br/api/servico/sitebcb/copom/atas_detalhes?nro_reuniao=${n}`;
const API_COM   = n => `https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados_detalhes?nro_reuniao=${n}`;
const API_SELIC = 'https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados?formato=json';

const REUNIAO_INICIO = 300; // começa alto para pegar reuniões futuras também
const MAX_FALHAS     = 5;   // falhas consecutivas = chegou ao fim

// -----------------------------------------------------------------------
// HTTP helpers
// -----------------------------------------------------------------------
function fetchJson(url) {
  return new Promise((resolve, reject) => {
    https.get(url, { headers: { 'User-Agent': 'BCB-Historico/1.0' } }, res => {
      let body = '';
      res.on('data', d => body += d);
      res.on('end', () => {
        try { resolve(JSON.parse(body)); }
        catch { resolve(null); }
      });
    }).on('error', reject);
  });
}

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

// -----------------------------------------------------------------------
// Download de reuniões
// -----------------------------------------------------------------------
async function baixarReunioes() {
  const meta = [];
  let nro = REUNIAO_INICIO;
  let falhasConsec = 0;
  let total = 0;

  console.log(`\nBaixando reuniões a partir de ${REUNIAO_INICIO}...\n`);

  while (nro >= 1 && falhasConsec < MAX_FALHAS) {
    process.stdout.write(`  Reunião ${String(nro).padStart(3,' ')}... `);

    const ataFile = path.join(DOCS_DIR, `ata_${nro}.json`);
    const comFile = path.join(DOCS_DIR, `com_${nro}.json`);

    // Pula se já existe (modo incremental)
    const ataExiste = fs.existsSync(ataFile);
    const comExiste = fs.existsSync(comFile);

    let ataData = null;
    let comData = null;
    let achou = false;

    // Busca ata
    if (ataExiste) {
      ataData = JSON.parse(fs.readFileSync(ataFile, 'utf8'));
      achou = true;
    } else {
      const json = await fetchJson(API_ATA(nro)).catch(() => null);
      if (json && json.conteudo && json.conteudo.length > 0) {
        ataData = json.conteudo[0];
        fs.writeFileSync(ataFile, JSON.stringify(ataData), 'utf8');
        achou = true;
      }
    }

    // Busca comunicado
    if (comExiste) {
      comData = JSON.parse(fs.readFileSync(comFile, 'utf8'));
      achou = true;
    } else {
      const json = await fetchJson(API_COM(nro)).catch(() => null);
      if (json && json.conteudo && json.conteudo.length > 0) {
        comData = json.conteudo[0];
        fs.writeFileSync(comFile, JSON.stringify(comData), 'utf8');
        achou = true;
      }
    }

    if (achou) {
      meta.push({
        nro,
        dataAta: ataData ? (ataData.dataReferencia || ataData.dataPublicacao || null) : null,
        dataCom: comData ? (comData.dataReferencia || null) : null,
      });
      falhasConsec = 0;
      total++;
      console.log(`OK (ata: ${ataData ? 'sim' : 'não'}, com: ${comData ? 'sim' : 'não'})`);
    } else {
      falhasConsec++;
      console.log(`não encontrado (${falhasConsec}/${MAX_FALHAS})`);
    }

    nro--;

    // Pequena pausa para não sobrecarregar a API
    if (!ataExiste || !comExiste) await sleep(150);
  }

  // Salva meta.json ordenado por nro decrescente
  meta.sort((a, b) => b.nro - a.nro);
  fs.writeFileSync(path.join(DATA_DIR, 'meta.json'), JSON.stringify(meta, null, 2), 'utf8');
  console.log(`\n✓ ${total} reuniões salvas em ./data/docs/`);
  console.log(`✓ ./data/meta.json atualizado (${meta.length} entradas)`);
  return meta;
}

// -----------------------------------------------------------------------
// Download da Selic
// -----------------------------------------------------------------------
async function baixarSelic() {
  console.log('\nBaixando série histórica da Selic...');
  const json = await fetchJson(API_SELIC).catch(() => null);
  if (!json || !Array.isArray(json)) {
    console.log('✗ Erro ao baixar Selic');
    return;
  }

  const data = json.map(p => {
    const parts = p.data.split('/');
    return { x: `${parts[2]}-${parts[1]}-${parts[0]}`, y: parseFloat(p.valor) };
  });

  fs.writeFileSync(path.join(DATA_DIR, 'selic.json'), JSON.stringify(data), 'utf8');
  console.log(`✓ ${data.length} observações salvas em ./data/selic.json`);
}

// -----------------------------------------------------------------------
// Main
// -----------------------------------------------------------------------
(async () => {
  const inicio = Date.now();
  console.log('=== Baixar Dados BCB COPOM ===');

  await baixarSelic();
  await baixarReunioes();

  const seg = ((Date.now() - inicio) / 1000).toFixed(1);
  console.log(`\nConcluído em ${seg}s.`);
  console.log('Faça commit da pasta ./data/ e dê push para atualizar o GitHub Pages.\n');
})();
