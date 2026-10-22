# ImuniGuia — envio e revisão de cadernetas

Aplicação local para receber cadernetas de vacinação e registrar a aprovação ou devolução de cada arquivo. O acesso é separado por atividade, sem login neste protótipo local.

## Executar no Windows

Com Python 3.10 ou superior instalado, dê dois cliques em `INICIAR_IMUNIGUIA.bat`. Ou abra um terminal nesta pasta e execute:

```powershell
python server.py
```

Acesse uma das páginas abaixo. Encerre com `Ctrl+C` no terminal do servidor. O aplicativo usa somente bibliotecas incluídas no Python, sem instalação de pacotes.

- <http://127.0.0.1:4173/paciente> — cadastro da pessoa e envio de foto/PDF da caderneta.
- <http://127.0.0.1:4173/agente-saude> — fila de análise, aprovação ou devolução com orientação.
- <http://127.0.0.1:4173/> — página para escolher o tipo de acesso.

## Executar com container

Com Docker e Docker Compose instalados, execute:

```bash
docker compose up --build -d
```

O serviço ficará disponível nas mesmas URLs locais. Os documentos e o banco SQLite ficam no volume nomeado `imuniguia-data`, portanto continuam preservados ao recriar o container. Para encerrar, use `docker compose down`; para remover também os dados locais, use `docker compose down --volumes`.

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
