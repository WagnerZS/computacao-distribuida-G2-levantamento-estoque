# Gerenciamento de Estoque — G2

Backend REST e sensor de proximidade (KY-032) para simular leitor de código de barras para Raspberry Pi. A detecção do sensor não depende da API estar ligada: cada detecção real sorteia um produto localmente e é persistida em uma fila SQLite no Raspberry. O lote só é enviado quando o operador clica em **Enviar** na tela do leitor.

## Arquitetura

```
KY-032 (GPIO17) ─┐
LED (GPIO27)     ├─ Raspberry: leitor na GPIO + fila SQLite + tela local :5050
Buzzer (GPIO22) ─┘                         │ botão Enviar
                                           │ POST /api/estoque/inventario/leituras/lote
                                           ▼
                                FastAPI REST :5000
                                           │
                                SQLite base de dados
                                           │ cache 30s / versão
                                           ▼
                                         Redis
```

O GPIO usa numeração BCM: sensor em `17` (pino físico 11), LED em `27` (pino físico 13) e buzzer em `22` (pino físico 15).   
Os 3 componentes trabalham juntos para simular um leitor de código de barras.

## Comportamento do leitor

- O sensor está limitado a uma detecção por segundo no máximo para evitar spam ou leituras aceidentais, mas ainda preservar agilidade.

- Cada detecção sorteia um produto do catálogo local e grava uma linha em `ESTOQUE_READER_QUEUE_DATABASE_PATH`.

- Falha de GPIO, API desligada ou erro HTTP não apaga a fila nem interrompe o monitoramento.

- A tela local em `http://IP_DA_RASPBERRY:5050` mostra somente a lista de produtos do lote atual e possui o botão **Enviar**; ela não consulta o cache gerencial.

- Ao clicar em **Enviar**, todo o lote pendente é enviado para `POST /api/estoque/inventario/leituras/lote`. Se o envio falhar, as leituras permanecem na fila.

- O leitor não faz tentativas automáticas de envio: nenhuma leitura é encaminhada enquanto o operador não clicar em **Enviar**.

## Painel gerencial

O painel gerencial fica em `http://IP_DO_SERVIDOR:5000/manager`. Ao abrir a tela e ao clicar em **Atualizar**, ela chama `GET /api/estoque/inventario`. Esse endpoint tenta primeiro o Redis; se a entrada passou dos 30 segundos de TTL, não existe ou tem uma versão diferente da versão do SQLite, lê o SQLite e reconstrói o cache.

Depois que um lote é enviado pelo leitor, o backend grava os produtos no SQLite, incrementa a versão do inventário, invalida a entrada antiga e reconstrói o cache. Assim, a próxima abertura ou atualização do painel gerencial já encontra os dados do lote mais recente.

## Backend: SQLite e Redis

O SQLite (`ESTOQUE_DATABASE_PATH`) é a base de dados. Ele contém catálogo, inventário atual, versões e relatórios. O Redis não é banco principal: cada valor em cache guarda a versão do SQLite e possui TTL de 30 segundos. Se a versão do SQLite mudar, o cache é considerado divergente e é reconstruído imediatamente, mesmo antes do TTL.

O Redis está hospedado no Redis Cloud. Defina a URL no arquivo `.env`:

```
ESTOQUE_REDIS_URL=redis://default:SENHA@HOST:12493
```

## Executar a API

```bash
uv sync

cp .env.example .env
# edite ESTOQUE_REDIS_URL, se necessário
uv run task run
```

A API fica em `http://localhost:5000` e a documentação em `/docs`.

### Endpoints

- `GET /api/estoque/health` — saúde do banco e do Redis.

- `GET /api/estoque/produtos` — catálogo com cache Redis validado pela versão SQLite.

- `GET /api/estoque/inventario` — inventário atual; a resposta informa `source: database` ou `source: cache`.

- `POST /api/estoque/inventario/leituras/lote` — lote enviado pelo leitor GPIO.

## Executar no Raspberry Pi

Instale o backend GPIO do sistema e permita que o ambiente veja os pacotes do Raspberry Pi OS:

```bash
sudo apt update
sudo apt install -y python3-lgpio

uv venv --system-site-packages
uv sync
```

Configure a API acessível pela Raspberry:

```
ESTOQUE_API_URL=http://IP_DO_SERVIDOR:5000
ESTOQUE_READER_PORT=5050
ESTOQUE_READER_QUEUE_DATABASE_PATH=estoque/dados/leitor-pendente.sqlite3
```

Inicie o leitor:

```bash
uv run task cli
```

Abra `http://IP_DA_RASPBERRY:5050`.

## Testes

```bash
uv run task test
```