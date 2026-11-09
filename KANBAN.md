# Kanban do ImuniGuia

Atualizado em: 2026-11-08 (America/Cuiaba).
Meta: integrar frontend e funcionalidades em homologacao e evoluir o MVP conforme [roadmap.md](roadmap.md).
Este é o quadro operacional versionado. Issues guardam o escopo e os critérios de aceitação; GitHub Projects, se utilizado pela equipe, deve refletir os mesmos cartões, sem inventar sincronização.

## Regras do quadro

- Colunas: A fazer → Em andamento → Em revisão → Concluído; Bloqueado registra impedimento e ação para destravar.
- Começar no máximo um cartão por responsável. Dividir cartões grandes antes de codificar; manter vínculo ao cartão pai, marco e issue.
- Toda mudança de etapa exige atualização neste arquivo, evidência, data e próximo passo no mesmo conjunto de alterações.
- Concluído exige implementação na branch de entrega, critérios da issue satisfeitos, validação registrada e documentação correspondente. Entrega parcial fica aberta com checklist explícito.
- “Protótipo em teste” não equivale a “concluído em homologacao”.
- O trabalho de documentação desta entrega não conclui a issue #25 inteira.

## Em andamento

### K06 — Interface completa e integração (M3, #1 e #42)

- Responsável: IA; 2026-11-08. Backend dos cartões predecessores pronto para revisão; concluir validação integrada antes de marcar os marcos.
- [x] Fluxos privados de dependentes, upload, arquivo, revisão e auditoria implementados no servidor.
- [x] Interface Família/UBS/ACS implementada; build e lint sem avisos.
- [x] Navegador: cadastro família/dependente, prévia e envio de imagem, OCR real 94%, conferência de arquivo e confirmação separada de registro pela UBS.
- [ ] Verificação visual e ponta a ponta pelo navegador.
- Próximo passo: concluir navegador ACS/mobile e requisitos novos K16/K17.

## Em revisão

| Cartão | Implementação / evidência já obtida | Falta para concluir |
| --- | --- | --- |
| K01 | React/Vite reconstruído com favicon/proxy; npm ci, build e health passam. Contratos de teste implementados na API FastAPI. | Confirmar integração visual e documentar reconstrução e mudanças de segurança. |
| K02 | SQLAlchemy/Alembic, migração inicial imutável, importação legada idempotente com hashes; backup/restauração com recusa de sobrescrita testados. | Executar também com PostgreSQL em Docker. |
| K03 | Sessão opaca em cookie HttpOnly, Argon2, CSRF, perfis concedidos só por administração; testes de acesso cruzado passam. | Conferir fluxo no navegador e revisar configuração Docker. |
| K04 | Nascimento, dono, atualização e isolamento; importação não inventa responsável. | Exercitar formulário e negativas de nascimento no teste integrado. |
| K05 | Auditoria de ator autenticado, ciência de privacidade, exportação própria; ACS recebe dados mínimos. | Travas de auditoria no banco e política operacional documentada. |
| K07 | Worker SQL durável, OCR Tesseract/PDF e candidatos a_conferir; testes de falha/idempotência passam. | Exercitar motor real no container, incluindo PDF. |
| K08 | Decisões de documento e registro separadas; orientação liberada só para responsável; testes do fluxo passam. | Interface e validação visual. |
| K09 | Regras versionadas para recorte BCG/Pentavalente/VIP, idade e intervalos; recálculo real após decisão. Fonte PNI 2026 consultada. | Revisar limites/cobertura, fonte e comunicar recorte na interface; fora do recorte não equivale a situação regular. |
| K10 | Notificações idempotentes privadas e leitura persistida; testes passam. | Interface e teste no navegador. |
| K11 | Fila ACS com motivo, prioridade e contato; ações preservadas após resolução; testes passam. | Interface, filtros e verificação visual. |

## Bloqueado

Nenhum cartão formalmente bloqueado. Docker Desktop iniciado e engine respondeu 29.4.3. Hospedagem pública não faz parte desta entrega: usuário escolheu preparar com Docker.

### K16 / K17 — Novo escopo solicitado: mobile/PWA e próximas doses

- Responsável: IA; 2026-11-08; em preparação dentro da integração K06.
- [x] K16: manifest e ícones 192/512/maskable, service worker só para assets públicos, tela offline e navegação inferior mobile. Build/lint passam e 4 testes Node verificam a instalação/cache.
- [ ] K16: revisão no navegador mobile e confirmação de instalação/preparação do service worker.
- [x] K17: agenda por pessoa da família, datas próximas/atrasadas e avisos persistidos. Web Push opcional com payload genérico, proteção CSRF e revogação ao sair.
- [x] 18 testes Python passaram: janelas de 30/31/0/-1 dias, família isolada, candidato não confirma dose, aviso idempotente, push sem conteúdo clínico/repetição e retry.
- [ ] Revisão visual da agenda e complemento de datas individualizadas pela UBS para vacinas fora do recorte. Alertas referem-se à data recomendada da dose, não à validade de lote.
- Critério: testes de datas e isolamento, instalação/configuração PWA verificadas e interface revisada em 390px.

## A fazer

| ID | Marco / issues | Entrega | Depende de | Evidência exigida / próximo passo |
| --- | --- | --- | --- | --- |
| K12 | M8 · #24 | Consolidar testes e CI | K10, K11 | Testes acrescentados desde K01; CI executa instalação, lint, build, migrações e fluxos relevantes; registrar comandos/resultados. |
| K13 | M8 · #25 | Completar documentação operacional | K12 | Pessoa nova reproduz execução e fluxo; README, arquitetura, configuração e contribuição sincronizados com código real. |
| K14 | M8 · #26 | Publicar demonstração validada | K13 | Hospedagem definida, HTTPS/segredos, backup/restauração e fluxo completo verificados; registrar URL e limitações. |
| K15 | M0 · #1–#9, #27–#41 | Conferir duplicatas e vínculos do quadro remoto | K00 | Comparar escopo e itens de projeto antes de escolher referência; registrar equivalências e preservar histórico. Não encerra automaticamente issues repetidas. |

## Concluído

### K00 — Diagnóstico e planejamento inicial

- Marco: M0. Relacionado a #23, #25 e #42, sem encerrar essas issues.
- Data: 2026-11-08.
- Responsável: IA nesta entrega.
- [x] Consultar main 080b34c, teste 025fbed e as 42 issues.
- [x] Registrar a ausência dos fontes React na main e os limites do protótipo.
- [x] Criar roadmap.md, KANBAN.md, GUIA_IA.md e AGENTS.md; atualizar README.md.
- [x] Conferir cobertura das 42 issues, vínculos internos e dependências dos cartões.
- Evidência: arquivos desta entrega e revisões imutáveis citadas no roadmap. Inspeção estática; não houve validação funcional do aplicativo.
- Próximo passo: K01.

## Histórico de mudanças

| Data | Cartão | Transição | Evidência / próximo passo |
| --- | --- | --- | --- |
| 2026-11-08 | K00 | Em andamento → Concluído | Diagnóstico, quatro documentos de planejamento e README; continuar por K01. |
| 2026-11-08 | K01–K15 | Criados em A fazer | Ordem, dependências e critérios acima; issues continuam abertas. |

## Modelo para atualizar um cartão

Ao detalhar um cartão, mover sua linha para a coluna correta ou substituí-la por uma ficha (sem duplicar o ID):

- ID e título:
- Marco / issue / cartão pai:
- Estado, responsável e data:
- Objetivo e critérios de aceitação:
- Checklist feito / restante:
- Dependências:
- Evidência: arquivos, comandos e resultados; commit/PR quando disponível:
- Bloqueio e ação para destravar:
- Próximo passo:

Atualizar também o histórico. Se GitHub Projects ou issues não puderem ser sincronizados, registrar o alvo, a transição pendente e o motivo; manter a entrega de código e o quadro versionado coerentes. Não declarar o quadro remoto atualizado sem leitura de confirmação.

| 2026-11-08 | K01 | A fazer → Em andamento | Histórico sem fontes React; reconstrução autorizada pelo novo escopo. Docker escolhido pelo usuário. |

| 2026-11-08 | K01–K11 | Implementação de base → Em revisão; K06 em andamento | 9 testes passam, build passa, migração/importação/backup/restauração sintéticos verificados em SQLite. Revisão Docker e interface pendentes. |

Sincronização remota pendente: GitHub Projects não tem ferramenta de edição de colunas nesta sessão. Escrita do conector GitHub retornou 403 na entrega anterior; commits/push são feitos pelo Git autenticado. Não declarar issues encerradas.

| 2026-11-08 | K06/K16/K17 | Implementação → Em revisão parcial | React completo, mobile/PWA e agenda; 18 testes Python e 4 testes PWA passaram. Docker em reconstrução; PostgreSQL completo, mobile e docs ainda em validação. |
