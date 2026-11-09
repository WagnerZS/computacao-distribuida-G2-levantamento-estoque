const pending = document.querySelector('#pending');
const productList = document.querySelector('#product-list');
const empty = document.querySelector('#empty');
const message = document.querySelector('#message');
const sendButton = document.querySelector('#send');

function render(data) {
  const items = data.items || [];
  pending.textContent = `${data.pending ?? 0} produtos pendentes`;
  productList.innerHTML = '';
  empty.hidden = items.length > 0;
  if (!items.length) return;
  for (const item of items) {
    const row = document.createElement('li');
    row.innerHTML = `<span>${item.product.nome}</span><strong>${item.quantidade}</strong>`;
    productList.append(row);
  }
}

async function refresh() {
  try {
    const response = await fetch('/api/leitor/status');
    if (!response.ok) throw new Error('status');
    const data = await response.json();
    render(data);
    message.textContent = 'Monitorando GPIO17';
  } catch (_) {
    message.textContent = 'Não foi possível consultar a fila local';
  }
}

sendButton.addEventListener('click', async () => {
  sendButton.disabled = true;
  message.textContent = 'Enviando lote para a API…';
  try {
    const response = await fetch('/api/leitor/enviar', { method: 'POST' });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Falha no envio');
    render(data.status);
    message.textContent = `${data.sent} produto(s) enviado(s) para a API`;
  } catch (error) {
    message.textContent = error.message + ' — leituras preservadas';
  } finally {
    sendButton.disabled = false;
  }
});

refresh();
setInterval(refresh, 1000);

document.addEventListener("DOMContentLoaded", () => {
    const gestorLink = document.getElementById("gestor-link");

    if (gestorLink ) {
        gestorLink .href = `${window.location.protocol}//${window.location.hostname}:5000/manager`;
    }
});