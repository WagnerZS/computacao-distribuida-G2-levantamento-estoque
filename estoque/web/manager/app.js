const refreshButton = document.querySelector('#refresh');
const source = document.querySelector('#source');
const version = document.querySelector('#version');
const chart = document.querySelector('#chart');
const empty = document.querySelector('#empty');
const message = document.querySelector('#message');

function render(data) {
  const items = data.items || [];
  chart.innerHTML = '';
  empty.hidden = items.length > 0;
  source.textContent = data.source === 'cache' ? 'Fonte: Redis cache' : 'Fonte: SQLite → Redis';
  version.textContent = data.cache_version ? `versão ${data.cache_version}` : '';
  if (!items.length) return;
  const max = Math.max(...items.map(item => item.quantidade), 1);
  for (const item of items) {
    const wrap = document.createElement('div');
    wrap.className = 'bar-wrap';
    const value = document.createElement('span');
    value.className = 'bar-value';
    value.textContent = item.quantidade;
    const bar = document.createElement('div');
    bar.className = 'bar';
    bar.style.height = `${Math.max(8, (item.quantidade / max) * 220)}px`;
    bar.title = `${item.produto.nome}: ${item.quantidade}`;
    const label = document.createElement('span');
    label.className = 'bar-label';
    label.textContent = item.produto.nome;
    wrap.append(value, bar, label);
    chart.append(wrap);
  }
}

async function refresh() {
  refreshButton.disabled = true;
  message.textContent = 'Consultando cache…';
  try {
    const response = await fetch('/api/estoque/inventario', { cache: 'no-store' });
    if (!response.ok) throw new Error('Não foi possível consultar o inventário');
    const data = await response.json();
    render(data);
    message.textContent = data.source === 'cache' ? 'Dados retornados do Redis' : 'Cache reconstruído a partir do SQLite';
  } catch (error) {
    message.textContent = error.message;
  } finally {
    refreshButton.disabled = false;
  }
}

refreshButton.addEventListener('click', refresh);
refresh();

document.addEventListener("DOMContentLoaded", () => {
    const leitorLink = document.getElementById("leitor-link");

    if (leitorLink) {
        leitorLink.href = `${window.location.protocol}//${window.location.hostname}:5050/`;
    }
});