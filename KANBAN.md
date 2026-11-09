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

Nenhum cartão ativo. Ao iniciar trabalho, mover o cartão correspondente para esta seção e registrar responsável/data.

## Em revisão

Nenhum cartão aguardando revisão.

## Bloqueado

Nenhum cartão formalmente bloqueado. K01 exige localizar os fontes ausentes; registrar aqui se a investigação confirmar que depende de material da equipe.

## A fazer

| ID | Marco / issues | Entrega | Depende de | Evidência exigida / próximo passo |
| --- | --- | --- | --- | --- |
| K01 | M1 · #23 | Recuperar frontend versionado e integrar a base de teste | K00 | Localizar src/main.jsx e assets; resolver conflitos de index.html/README; documentar diretórios, contrato API, porta/proxy; build e health verificados. |
| K02 | M1 · #19 | Banco, migrações e importação de dados/arquivos | K01 | Esquema, chaves e migrações reproduzíveis; relatório de contagens, relações e hashes antes/depois; restauração ensaiada. |
| K03 | M2 · #2, #3, #20, #42 | Cadastro, sessão e permissões no backend | K02 | E-mail único, hash de senha, logout; testes anônimo/perfil indevido/acesso entre famílias. |
| K04 | M2 · #4 | Dependentes completos e vinculados | K03 | Nascimento válido e isolamento por responsável comprovado; migrar nomes existentes sem atribuir dono arbitrário. |
| K05 | M2 · #21, #22 | Auditoria confiável e privacidade | K03, K04 | Autor autenticado, eventos protegidos; inventário de dados, regras de acesso, retenção e consentimento quando aplicável documentados. |
| K06 | M3 · #1, #42 | Upload e conferência na interface definitiva | K05 | Prévia/câmera, contrato de formatos e limite, arquivo privado, fila e decisão integrados; testes válidos/inválidos passam. |
| K07 | M4 · #5, #6 | OCR e candidatos a_conferir | K06 | Original vinculado, confiança/falha, tarefa idempotente; candidato nunca confirma dose. |
| K08 | M5 · #12, #13, #14, #15 | Revisão UBS, acompanhamento e orientação | K07 | Revisão de registro com identidade confiável, estado e orientação por família; recálculo de #14 permanece pendente até K09. |
| K09 | M6 · #7, #8, #9, #10, #14 | Regras, histórico e pendências | K08 | Regra/versão de origem, casos de borda e recálculo real após decisão; distinguir confirmado de candidato. |
| K10 | M7 · #11 | Notificações | K09 | Mesmo evento não duplica aviso; destinatário isolado e leitura persistida. |
| K11 | M7 · #16, #17, #18 | Busca ativa ACS | K09 | Motivo e prioridade, dados mínimos, autor e histórico de contatos; resolver caso remove da fila ativa. |
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
