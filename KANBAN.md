# Kanban do ImuniGuia

Atualizado: 2026-11-08 (America/Cuiaba). Branch de entrega: **homologacao**. O quadro registra implementação e aceite restante; código publicado não implica aprovação clínica, jurídica ou operação com dados reais.

## Regras

- A fazer → Em andamento → Em revisão → Concluído. Bloqueado exige causa e ação concreta.
- Atualizar este arquivo a cada passo significativo e no mesmo commit do código.
- Concluído exige todos os critérios e evidências atuais; não usar testes antigos como prova de código posterior.
- Preservar escopo e histórico das issues. Duplicatas não são encerradas automaticamente.
- GitHub Projects e este arquivo são superfícies distintas. Não declarar sincronização de colunas sem leitura de confirmação.

## Em andamento

**K20.1 · #47 — continuidade e revogação da autorização — Em revisão.** Novo aceite explícito para contas antigas/termos alterados; revogação suspende processamento, acesso da equipe e avisos externos, preservando consulta/exportação própria. Resultado OCR em andamento é descartado mesmo se houver reaceite durante a leitura. Declaração `representationConfirmed` exigida no servidor e registrada na auditoria; não substitui prova do vínculo.

Evidência: **39 testes passaram no Docker/PostgreSQL com OCR real**, incluindo quatro cenários de ciclo de autorização; lint, formatação e build passaram. No navegador, conta anterior exibiu pausa, texto vigente e caixas desmarcadas; nenhum aceite foi feito em nome do usuário. Nova versão `2026-11-08.3`; anterior preservada. Migração 010 não cria autorizações antigas. CI deste avanço será conferida após push. Eliminação, retenção e comprovação documental continuam pendentes na #47.

## Em revisão

| Cartão / issues | Implementado | Aceite restante |
| --- | --- | --- |
| K01 · #23/#42 | React/FastAPI integrados; interface dos três perfis; build e lint | Aceite final do produto e CI remota. |
| K02 · #19 | PostgreSQL/Alembic, SQLite local, legado idempotente com hashes, testes de migração | Backup/restauração operacional PostgreSQL+arquivos. |
| K03 · #2/#3/#20 | Sessão opaca, Argon2, CSRF, autorização por objeto/perfil, equipe administrativa | Revisão de implantação HTTPS e escopos reais. |
| K04 · #4 | Nascimento, responsável, edição e isolamento | Comprovação administrativa de representação e menores (#47). |
| K05 · #21/#22 | Auditoria imutável, exportação, aceites e solicitações de direitos | Retenção, eliminação e comprovação documental; reaceite e suspensão implementados em K20.1. |
| K06 · #1/#9/#12/#13/#42 | Interface mobile/desktop, envio com prévia, original, estados e retorno UBS | Testes com usuários e revisão acessível completa. |
| K07 · #5/#6 | Tesseract por/eng e Poppler, imagens/PDF, candidatos, falha/retry e transcrição manual | Homologação com amostras reais autorizadas e ampliação do parser além das três vacinas. |
| K08 · #14/#15 | Arquivo e cada dose separados; orientação, motivo, providência, autor/data | Aceite operacional de UBS e administração de perfis. |
| K09 · #7/#8/#10 | Regras versionadas BCG/Pentavalente/VIP, idade/intervalos e recálculo | Revisão clínica e expansão da cobertura. |
| K10 · #11 | Avisos persistentes idempotentes e leitura | Entrega de push em aparelhos autorizados reais. |
| K11 · #16/#17/#18 | ACS por pessoa, contatos mínimos, prioridade e histórico após resolução | Homologação com equipe ACS e definição de escopo territorial se necessário. |
| K12 · #24 | Testes funcionais e workflow frontend/backend/Docker | CI do código 57f4e3c aprovada nos três jobs; falta homologação final dos três perfis. |
| K13 · #25 | README, roadmap, guia IA, instruções, operação e referências UI/UX | Reprodução da execução por pessoa nova. |
| K16 · #43 | PWA, ícones, offline público, cache sem dados clínicos, navegação mobile | Instalação Android/iOS real com HTTPS externo. |
| K17 · #44 | Agenda familiar, janela de 30 dias, atraso, data individual de qualquer vacina e push opt-in | Validar entrega externa de push e expandir regras clínicas. |
| K18 · #45 | Trio sorteado completo; geografia nascimento/trabalho cruzada; independência, impedimento, votos imutáveis, recusa com motivo/providência | Homologar aprovação positiva nas três contas pelo navegador, concorrência e mudanças de perfil/reatribuição. Verificação documental é administrativa; geografia não prova ausência de vínculo pessoal. |
| K19 · #46 | Catálogo público RNDS com código/fonte/versão/hash, atualização diária e cópia preservada; fonte do MS na agenda | Ampliar regras clinicamente. Não há API pública de recomendação individual integrada nem prontuário pessoal RNDS. |
| K20 · #47 | Texto legível no cadastro/conta, aceites separados desmarcados, versão/hash, autoria/horário, solicitações e resposta administrativa | Confirmar canal `example@unemat.bbr`; controlador, retenção, representação; execução das providências de eliminação e comprovação documental; reaceite e revogação implementados em K20.1. |
| K21 · #48 | Pesquisa e decisões documentadas; linguagem direta, ações por tarefa, menos decoração, leitura maior, foco e toque; Retornos da UBS | Testes moderados com cidadãos/UBS/ACS e revisão completa de acessibilidade. Sem certificação WCAG ou validação clínica integral. |

## A fazer

| Cartão | Objetivo | Dependência |
| --- | --- | --- |
| K14 · #26 | Implantação HTTPS quando houver hospedagem; backup/restauração operacional e teste de aparelhos reais | Usuário escolheu preparar Docker; nenhum provedor público definido. Não tratar ausência de hospedagem como falha da execução local. |
| K15 · #27–#41 | Avaliar consolidação de duplicatas com a equipe, preservando critérios e vínculos | Referências registradas no roadmap e nas issues. Não fechar em massa. |

## Bloqueado

**Sincronização de colunas do GitHub Projects:** acesso Git autenticado permite issues e push; GraphQL retornou `INSUFFICIENT_SCOPES`, exigindo `read:project` (e `project` para escrita). O conector também recusou escrita com 403. A ação para destravar é disponibilizar autenticação com permissão específica de projetos. Não modificar permissões por conta própria. O quadro versionado permanece disponível e as issues foram atualizadas pela API REST autorizada.

## Concluído

**K00 — diagnóstico e planejamento inicial:** main 080b34c, teste 025fbed e 42 issues consultados; roadmap, guia, AGENTS e kanban criados e publicados no commit f6dd262. Não equivale à conclusão das issues funcionais.

## Evidências desta etapa

Código publicado: [57f4e3c](https://github.com/ImuniGov/ImuniGov/commit/57f4e3c37d561aa32ae4519f9a0f5c86a0bb19af).

- API/SQLite: testes de fluxo, acesso cruzado, calendário, avisos, trio, comparações geográficas cruzadas/RIDE, recusa para família, independência, privacidade, indisponibilidade RNDS e imutabilidade. **32 passaram, 3 pulados** no Windows por ausência dos motores OCR locais; OCR é exigido no Docker.
- Docker/PostgreSQL: execução dos mesmos fluxos em schemas temporários próprios; OCR real de imagem, PDF escaneado e PDF com texto. **35 passaram** na execução final com `REQUIRE_OCR=1`, incluindo OCR real e testes negativos de imutabilidade.
- Frontend: lint sem avisos, formatação e build passaram; **4 testes PWA passaram** (ícones, cache público e exclusão de API privada).
- Consulta real de RNDS: `backend.manage sync-sources` retornou `ok: true`; snapshot oficial contém **80 conceitos de vacinas ativas** de 118 imunobiológicos, versão publicada pela fonte `1.0.0-release`. A data de consulta não é a data de publicação do catálogo.
- Navegador: termos abrem com leitura completa e caixas desmarcadas; família e UBS; devolução de arquivo sintético com motivo e providência; retorno visível à família; mobile 390px e 320px sem transbordamento horizontal do documento, desktop 1366px e navegação. Reenvio abre com a pessoa correta selecionada. Não houve aceite de termos reais em nome do usuário nem envio de dados de pacientes.
- **CI remota aprovada** no código publicado `57f4e3c`: [execução 42551947165](https://github.com/ImuniGov/ImuniGov/actions/runs/42551947165), jobs frontend, backend e docker-postgres com `success`. O commit seguinte apenas registra esta evidência em documentação e não altera código executável. Hospedagem pública, push externo real, aparelhos e usuários reais não foram declarados verificados.

## Sincronização remota

- Issues novas: #43 PWA, #44 agenda, #45 revisão tripla, #46 governo, #47 termos e dados de saúde, #48 design/linguagem.
- **42 issues atualizadas e conferidas na resposta da API REST**, #1–#42. A atualização preserva descrição original, informa implementação atual, limitações e referência das duplicatas. Todas permanecem abertas para aceite.
- GitHub Projects: colunas não atualizadas por ausência de permissão; não confundir atualização de issues com movimentação do quadro.

## Histórico

| Data | Passo | Evidência e próximo passo |
| --- | --- | --- |
| 2026-11-08 | K00 concluído | Diagnóstico e planejamento publicados. |
| 2026-11-08 | Base K01–K11 implementada; em revisão | API segura, persistência, OCR e fluxos; commits 8299924 e c74a76f publicados. |
| 2026-11-08 | K16/K17 implementados; em revisão | Mobile/PWA, agenda, avisos e datas UBS; testes e revisão visual. |
| 2026-11-08 | K18/K20 implementados; em revisão parcial | Trio independente, votos e termos específicos. Pendências operacionais acima. |
| 2026-11-08 | K19/K21 implementados; em revisão | RNDS público e revisão de UX fundamentada. Fontes em docs/DESIGN_UX.md; próximos passos clínicos/acessíveis explícitos. |
| 2026-11-08 | Issues e documentação atualizadas | Novos requisitos #43–#48 e progresso #1–#42. Código 57f4e3c publicado; CI aprovada nos três jobs. |

| 2026-11-08 | Validação remota confirmada | Interface, backend e Docker/PostgreSQL passaram na execução 42551947165. Registro documental publicado sem alteração funcional. |

| 2026-11-08 | K20.1 em revisão | Suspensão efetiva, reaceite explícito e representação no servidor; 39 testes Docker passaram. CI do novo commit pendente. |
