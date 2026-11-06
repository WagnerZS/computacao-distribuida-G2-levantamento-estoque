# Levantamento de Estoque — versão 2

Backend REST para levantamento de estoque usando Raspberry Pi, FastAPI e Redis. O sensor continua produzindo um evento de detecção; o Raspberry envia esse evento para a API via HTTP. O frontend será um cliente separado da API.

## Arquitetura

```text
Sensor KY-032 + Raspberry Pi
          │ HTTP POST
          ▼
FastAPI (API REST) ───────► Redis
          │                    ├─ produtos em cache
          │                    ├─ inventário atual
          │                    ├─ eventos
          │                    └─ relatórios temporários
          ▼
Frontend futuro (REST/JSON)
```

A versão 1 escolhia aleatoriamente um produto porque o sensor apenas detectava a passagem de um objeto. Esse comportamento é mantido quando a leitura não informa `product_id` nem `barcode`. Se a montagem futura tiver um leitor de código de barras, a mesma API aceita a identificação explícita do produto.

## Requisitos

- Python 3.12+
- UV ou pip
- Redis 7+
- Raspberry Pi com os sensores da versão 1

## Executar localmente

1. Instale as dependências:

```bash
uv sync
```

2. Inicie o Redis:

```bash
docker compose up -d redis
```

3. Copie as configurações:

```bash
cp .env.example .env
```

4. Inicie a API:

```bash
uv run task run
```

A documentação interativa fica em `http://localhost:8000/docs`.

## Endpoints

- `GET /api/v1/health` — saúde da API e conexão Redis.
- `GET /api/v1/products` — catálogo de produtos.
- `GET /api/v1/inventory` — levantamento atual.
- `POST /api/v1/inventory/readings` — registra uma detecção do sensor.
- `POST /api/v1/inventory/submit` — fecha o levantamento, armazena um relatório no Redis e limpa o inventário atual.
- `GET /api/v1/inventory/reports/{report_id}` — consulta um relatório fechado enquanto ele estiver no TTL configurado.

Exemplo de leitura do sensor sem identificação de produto:

```bash
curl -X POST http://localhost:8000/api/v1/inventory/readings \
  -H 'Content-Type: application/json' \
  -d '{"detected": true, "device_id": "raspberry-pi-01"}'
```

Exemplo com produto identificado:

```bash
curl -X POST http://localhost:8000/api/v1/inventory/readings \
  -H 'Content-Type: application/json' \
  -d '{"barcode": "7891000100011", "device_id": "raspberry-pi-01"}'
```

## Cliente serial de compatibilidade

O comando abaixo mantém a ponte serial usada na versão 1, mas troca o envio WebSocket por REST. No Raspberry, a futura leitura direta dos GPIOs pode chamar o mesmo endpoint.

```env
ESTOQUE_API_URL=http://IP_DO_SERVIDOR:8000
ESTOQUE_SERIAL_PORT=/dev/ttyUSB0
ESTOQUE_SERIAL_BAUDRATE=9600
```

```bash
uv run task cli
```

## Desenvolvimento

```bash
uv run task lint
uv run pytest
```

O estado operacional fica no Redis; o arquivo `estoque/dados/produtos.json` é a fonte inicial do catálogo e é carregado no cache na inicialização da API.
