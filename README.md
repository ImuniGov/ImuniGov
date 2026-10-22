# ImuniGuia — envio e revisão de cadernetas

Aplicação local para receber cadernetas de vacinação e registrar a aprovação ou devolução de cada arquivo. O acesso é separado por atividade, sem login neste protótipo local. A forma recomendada de execução é com Docker.

## Dependências

### Execução recomendada: container

- [Docker Engine](https://docs.docker.com/engine/install/) 24 ou superior;
- Docker Compose v2 (`docker compose`).

Confira a instalação:

```bash
docker --version
docker compose version
```

Não é necessário instalar Python, bibliotecas ou banco de dados na máquina: a imagem usa Python 3.12 e SQLite já incluído na biblioteca padrão.

### Execução sem container

- Python 3.10 ou superior.

Não há dependências de pacotes externos; a aplicação usa apenas a biblioteca padrão do Python.

## Início rápido com Docker

Na raiz do projeto, execute:

```bash
docker compose up --build -d
```

Confira se está em execução:

```bash
docker compose ps
curl http://127.0.0.1:4173/api/health
```

Saída esperada da verificação: `{"ok": true, "service": "ImuniGuia upload-and-review"}`.

## Endereços locais

- <http://127.0.0.1:4173/> — escolha do tipo de acesso.
- <http://127.0.0.1:4173/paciente> — cadastro da pessoa e envio de foto/PDF da caderneta.
- <http://127.0.0.1:4173/agente-saude> — fila de análise, aprovação ou devolução com orientação.
- <http://127.0.0.1:4173/api/health> — verificação técnica do serviço.

## Executar sem Docker

Com Python 3.10 ou superior instalado, dê dois cliques em `INICIAR_IMUNIGUIA.bat`. Ou abra um terminal nesta pasta e execute:

```powershell
python server.py
```

Em Windows, dê dois cliques em `INICIAR_IMUNIGUIA.bat`; em qualquer sistema, também é possível abrir um terminal na pasta do projeto e executar:

```bash
python server.py
```

Encerre com `Ctrl+C` no terminal do servidor.

## Operação do container

Os documentos e o banco SQLite ficam no volume nomeado `imuniguia-data`, portanto continuam preservados ao recriar o container.

```bash
# Acompanhar mensagens do serviço
docker compose logs -f

# Parar e remover o container, preservando os dados
docker compose down

# Parar e remover também o banco e arquivos enviados (ação irreversível)
docker compose down --volumes

# Recriar depois de alterações no código
docker compose up --build -d
```

## Configuração

As variáveis abaixo já são definidas em `compose.yaml`; só precisam ser alteradas se houver necessidade específica:

| Variável | Padrão | Finalidade |
| --- | --- | --- |
| `IMUNIGUI_HOST` | `0.0.0.0` no container | Endereço em que o servidor escuta. |
| `IMUNIGUI_PORT` | `4173` | Porta local do serviço. |
| `IMUNIGUI_DATA_DIR` | `/data` no container | Local do banco SQLite e dos arquivos enviados. |

## Solução de problemas

| Situação | Como resolver |
| --- | --- |
| `ERR_CONNECTION_REFUSED` | Execute `docker compose ps`; se o serviço não estiver como `Up`, rode `docker compose up --build -d` e consulte `docker compose logs`. |
| A porta 4173 já está em uso | Pare o processo que usa a porta ou altere o lado esquerdo de `4173:4173` em `compose.yaml`, por exemplo para `4174:4173`. |
| Mudanças não aparecem | Reconstrua com `docker compose up --build -d` e atualize a página. |
| É preciso recomeçar sem dados de demonstração | Execute `docker compose down --volumes`; isso apaga o banco e todos os arquivos enviados. |

## Fluxo funcional

1. Na página de paciente, cadastre a pessoa, informe a vacina e envie um arquivo JPG, PNG, WEBP ou PDF de até 10 MB.
2. Na página de agente de saúde, abra o item pendente e confira o conteúdo do arquivo.
3. Aprove o envio ou devolva para ajuste com justificativa. Informe o nome do revisor.
4. Consulte o status, a justificativa e as decisões anteriores na fila.

A aprovação registra que o arquivo foi conferido. Ela não cria nem modifica um registro vacinal oficial.

## Arquitetura

A stack atual, o modelo de dados, as rotas da API e os componentes que serão reaproveitados na interface definitiva estão descritos em [ARQUITETURA.md](ARQUITETURA.md). A interface é temporária; o contrato da API e as regras do fluxo devem ser preservados durante a evolução.

## URLs da API

- `GET /api/health` — estado do serviço.
- `GET /api/dependents` e `POST /api/dependents` — listar e cadastrar dependentes.
- `DELETE /api/dependents/{id}` — remover dependente ainda sem documentos.
- `GET /api/documents` — listar documentos; aceita `?status=pendente`, `aprovado` ou `rejeitado`.
- `POST /api/documents` — enviar arquivo como `multipart/form-data` (`dependentId`, `vaccine`, `doseDate`, `note`, `file`).
- `GET /api/documents/{id}` — detalhes do documento.
- `GET /api/documents/{id}/file` — visualizar o arquivo.
- `POST /api/documents/{id}/decision` — registrar decisão em JSON. Exemplo: `{"decision":"rejeitado","reviewer":"Nome do revisor","note":"A data não está legível; envie uma foto mais nítida."}`.
- `GET /api/audit?documentId={id}` — histórico de envio e decisões.

## Persistência e limites atuais

SQLite e arquivos são guardados em `data/`; o diretório está no `.gitignore`. O servidor aceita apenas formatos permitidos após conferir a assinatura básica do arquivo, limita uploads a 10 MB, gera nomes aleatórios no armazenamento e registra hash SHA-256, data e histórico da decisão.

Como solicitado nesta etapa, não há autenticação. Qualquer pessoa que alcance o servidor local pode consultar, enviar e revisar arquivos, e o nome do revisor é autodeclarado. O serviço escuta somente em `127.0.0.1` por padrão. Para dados reais ou acesso por rede, é necessário implementar autenticação e autorização, proteção de transporte, política de retenção e controles de segurança adequados antes de publicar.
