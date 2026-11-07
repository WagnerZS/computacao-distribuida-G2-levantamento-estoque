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

## Leitor GPIO na Raspberry Pi

O leitor GPIO implementa o comportamento do sketch `leitor-codigo-barras.ino`. Os números abaixo usam a numeração BCM da Raspberry Pi (não os números dos pinos do Arduino):

| Sinal | Pino no sketch Arduino | GPIO Raspberry (BCM) | Pino físico |
|---|---:|---:|---:|
| Saída do sensor | 2 | 17 | 11 |
| LED | 8 | 27 | 13 |
| Buzzer | 9 | 22 | 15 |

O leitor usa `DigitalInputDevice(17, pull_up=True)` e consulta `sensor.value` a cada 0,2 s. Quando o valor e `0`, registra "OBSTACULO DETECTADO!" e envia uma leitura a API; se a API estiver indisponivel ou recusar a leitura, tenta novamente a cada 2 segundos ate obter sucesso. O envio HTTP e o efeito do LED/buzzer rodam em tarefas isoladas, entao uma falha inesperada nelas e registrada sem encerrar a leitura do sensor. Enquanto o sensor continuar detectando o mesmo obstaculo, nao inicia um novo envio independente. Quando volta a `1`, registra "CAMINHO LIVRE". O LED e o buzzer PWM reproduzem o efeito do sketch.

Use um resistor adequado em série com o LED. Os pinos GPIO da Raspberry Pi são de 3,3 V: não aplique 5 V ao sensor ou às entradas GPIO; verifique o nível lógico da saída do sensor e use adaptação de nível quando necessário. Não conecte um buzzer que exceda a corrente permitida por um GPIO diretamente.

Execute na Raspberry Pi:

```bash
sudo apt install python3-lgpio
uv venv --system-site-packages
uv sync
uv run task cli-gpio
```

O leitor seleciona explicitamente o backend `lgpio`, evitando o backend `native` baseado em `/sys/class/gpio`. Se ja existir um ambiente `.venv` sem acesso aos pacotes do sistema, recrie-o com `uv venv --clear --system-site-packages` antes de executar `uv sync`. Verifique tambem se o usuario tem permissao de leitura e escrita em `/dev/gpiochip*`.

Configure `ESTOQUE_API_URL` no `.env` com o endereco acessivel da API. `localhost` so funciona quando a API roda na propria Raspberry Pi; se ela estiver em outro computador, use o IP desse computador, por exemplo `http://192.168.1.10:8000`. A dependencia `gpiozero` e instalada junto com as demais. O log do leitor mostra o estado do sensor e confirma cada deteccao e envio.

## Cliente serial de compatibilidade

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
