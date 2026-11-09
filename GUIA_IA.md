# Guia de continuidade para IA

## Como retomar

1. Ler AGENTS.md → roadmap.md → KANBAN.md e a issue do cartão escolhido.
2. Conferir `git status --short`, `git branch --show-current` e `git remote -v`; preservar mudanças existentes. Atualizar referências remotas antes de comparar as branches.
3. Revalidar o diagnóstico no código atual. As revisões do levantamento são main 080b34ccd286b70ab761d4f8854cc09bf42fa9a4 e teste 025fbed4d44e6ab48b982b0a9973fe78e34acd09.
4. Escolher o primeiro cartão cujas dependências estão concluídas; no estado inicial, K01.
5. Mover o cartão para Em andamento antes da implementação e registrar cada avanço, bloqueio e resultado conforme AGENTS.md.
6. Validar critérios, atualizar documentação/quadro e preparar commit de escopo claro. Publicar conforme autorização vigente e confirmar o SHA remoto.

## Estado inicial: não confundir plano com implementação

A branch homologacao desta entrega nasce de main e adiciona documentação. O backend, SQLite, interface temporária e Docker estão em teste, sem merge nesta entrega. O arquivo de entrada React src/main.jsx e o favicon referidos pelo index.html da main não constam da árvore consultada.

A primeira ação é localizar/recuperar os fontes da interface e escolher a estrutura integrada. Inspecionar o histórico antes de pedir material à equipe. Não considerar o frontend recuperado somente por criar uma tela vazia.

Referências úteis, por branch:

| Origem | Arquivos | Papel |
| --- | --- | --- |
| main | package.json, package-lock.json, vite.config.js, index.html | Configuração React/Vite; entrada ausente. |
| teste | server.py | HTTP local, validação de upload, SQLite, arquivos e auditoria. |
| teste | patient.html, patient.js | Dependente e upload da família, sem login. |
| teste | index.html, app.js, styles.css, roles.css, home.html | Interface temporária, fila e decisão de documentos. |
| teste | docs/openapi.json, docs/swagger.html | Contrato documentado do protótipo; conferir contra os handlers. |
| teste | ARQUITETURA.md, docs/modelo-dados.svg | Desenho alvo; não prova implementação da stack final. |
| teste | Dockerfile, compose.yaml, INICIAR_IMUNIGUIA.bat | Operação local do protótipo. |

## Contrato que precisa ser preservado

- GET /api/health.
- GET/POST /api/dependents; DELETE /api/dependents/{id} somente sem documentos.
- GET/POST /api/documents; filtro status=pendente, aprovado ou rejeitado.
- GET /api/documents/{id} e /api/documents/{id}/file.
- POST /api/documents/{id}/decision.
- GET /api/audit?documentId={id}.

Upload multipart: dependentId, vaccine, doseDate, note, file. Decisão JSON: decision, reviewer, note. O servidor deverá obter autoria da sessão ao adicionar autenticação. Planejar compatibilidade/migração; não aceitar identidade enviada pelo cliente como prova.

O protótipo aceita JPG, PNG, WEBP e PDF até 10 MB. A issue #1 exige esclarecer a diferença entre requisito de imagem e PDF. Nome/tamanho do arquivo selecionado não é pré-visualização de conteúdo. Os estados do documento são pendente/aprovado/rejeitado; não reaproveitá-los como estado de dose.

## Execução e verificação

Estes comandos são referências lidas no código/documentação, não resultados de execução desta entrega.

### Frontend da main

```powershell
npm ci
npm run lint
npm run build
npm run dev
```

Vite está configurado para porta 3000. A ausência de src/main.jsx impede considerar o build funcional; recuperar os fontes primeiro. Não há script npm test no package.json consultado.

### Protótipo da teste (em checkout separado dessa branch)

```powershell
python server.py
```

Python 3.10+ e biblioteca padrão; endpoint de saúde em http://127.0.0.1:4173/api/health. Configurações: IMUNIGUI_HOST, IMUNIGUI_PORT e IMUNIGUI_DATA_DIR. Usar diretório temporário de dados sintéticos para ensaios, sem sobrescrever banco de usuário.

Alternativa documentada no protótipo:

```powershell
docker compose up --build -d
docker compose ps
```

Não executar estes comandos na homologacao inicial como se Docker/server.py já existissem nela. A configuração de proxy/base URL React → API ainda precisa ser definida em K01. O protótipo não tem autenticação; não é uma demonstração pública pronta.

### Validação por tipo de trabalho

| Mudança | Verificação esperada |
| --- | --- |
| Documentação | Links locais, IDs únicos, 42 issues cobertas, dependências sem ciclos e diagnóstico compatível com as revisões. |
| Integração frontend/API | Instalação pelo lockfile, lint/build e health; formulário → upload → fila → decisão → consulta, com arquivo sintético. |
| Auth/permissões | Anônimo, sessão encerrada, perfil indevido, acesso entre famílias e download indevido devem falhar; acesso autorizado deve passar. |
| Banco/storage | Migrações reproduzíveis, relações, hashes e restauração; preservar originais e registrar rollback. |
| OCR | Falha/baixa confiança, repetição idempotente e impossibilidade de confirmar dose automaticamente. |
| Calendário | Casos de idade, dose, intervalo e vigência; candidato excluído de confirmação; motivo/versão e recálculo rastreáveis. |
| ACS/notificações | Exposição mínima, autor/data, caso resolvido e ausência de duplicação de eventos. |

## Como registrar uma etapa

No cartão, descrever comportamento entregue, arquivos, comandos/resultados, checklist restante e próximo passo. Incluir commit/PR quando disponível sem fabricar identificadores ou exigir que um commit contenha seu próprio hash.

Usar referência de issue no commit quando pertinente; evitar “Closes #N” até a issue inteira estar satisfeita. Não fechar #1/#13/#14 somente porque o protótipo permite conferir arquivos. Não tratar as duplicatas como funcionalidades adicionais.

Se não houver ferramenta/acesso para GitHub Projects, manter KANBAN.md atualizado e registrar a sincronização remota pendente com alvo e motivo. A edição do Markdown não altera automaticamente a coluna do projeto no GitHub.
