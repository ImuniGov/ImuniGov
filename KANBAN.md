# Kanban do ImuniGuia

Atualizado: 2026-11-11 (America/Cuiaba). Branch: **homologacao**. **Desenvolvimento retomado por solicitação explícita do usuário.**

## Execução ativa — 2026-11-11

- **K02 · #19 (Concluído em 2026-11-11):** Diagrama Entidade-Relacionamento (DER), dicionário de tabelas, restrições de imutabilidade e decisões de modelagem documentados em [`docs/MODELAGEM_DADOS.md`](docs/MODELAGEM_DADOS.md) e referenciados no `README.md` e `docs/OPERACAO.md`.
- **K02.1 · #49 (Em revisão em 2026-11-11):** Restaurador (`backend/backup.py`) corrigido para aceitar e substituir a linha semente `review_gate (roster=1)` criada pela migração 011 em bancos recém-migrados, validar versão de migração Alembic (`012`) e colunas do manifesto, e reverter arquivos/transação em falha permitindo recuperação. Validado em `tests/test_migration.py` (4 testes passando); ensaio Docker/PostgreSQL será validado na CI.
- **K08 · #15 (Concluído em 2026-11-11):** Nome identificável do profissional (`author_name`) exibido nas orientações liberadas à família em `src/Workspaces.jsx` e retornado em `POST /api/v1/pendings/{id}/guidance` e `GET /api/v1/dependents/{id}/guidance`, preservando conteúdo, vacina/dose, vínculo e horário. Validado em `tests/test_app.py`.
- **K06 · #13 (Concluído em 2026-11-11):** Contexto das possíveis pendências vacinais (abertas e histórico resolvido) exibido diretamente no modal de conferência da caderneta da UBS (`DocumentReview` em `src/Workspaces.jsx`). Validado em `tests/test_app.py` e build Vite.
- **K09.1 · #8, #10, #28, #48 (Concluído em 2026-11-11):** Pendências abertas separadas do histórico expansível de pendências resolvidas na API (`open`, `resolved`, `historical_reason`, `evaluation_type`) e na interface (`FamilyHistory` e `DocumentReview`), identificando explicitamente motivos anteriores e distinguindo cálculo automático de conferência profissional. Validado em `tests/test_app.py`.
- **K18.2 · #45 (Em revisão em 2026-11-11):** Fluxo completo de impedimento descoberto após voto implementado em `backend/reviews.py`, `backend/clinical.py`, `backend/routes.py`, `backend/manage.py` e `src/Workspaces.jsx`: registro de ocorrência imutável por caderneta (`review_incidents`), suspensão da conferência (`documents.review_hold`), retirada das confirmações daquela evidência da avaliação (reabrindo doses `a_conferir`, lembretes `dose_plans` e pendências), bloqueio de acesso do profissional impedido e de novos votos durante a suspensão, comandos administrativos (`review-incidents`, `report-incident`, `resolve-incident`) que registram resolução (`review_resolutions`) e abrem nova rodada com equipe independente sem aprovar doses por conta própria, além de proteção de privacidade das notas de rodadas anteriores na auditoria. Validado em `tests/test_independent_review.py` e `tests/test_review_lifecycle.py` (16 testes passando, incluindo concorrência e imutabilidade).
- **K19/K07 · #5, #32, #33, #46 (Em revisão em 2026-11-11):** Reconhecimento OCR (`backend/worker.py`, `backend/sources.py`, `src/format.js`, `src/Workspaces.jsx`) e regras vacinais (`backend/rules/routine-2026.json`, versão `PNI-2026-INFANTIL-ROTINA-v2`) ampliados para 23 regras em 10 vacinas do calendário básico infantil PNI (`BCG`, `Hepatite B`, `Pentavalente`, `Poliomielite VIP`, `Pneumocócica 10`, `Rotavírus humano` com janela etária superior estrita, `Meningocócica C`, `Febre amarela`, `Tríplice viral`, `Hepatite A`). Validado em `tests/test_app.py` e `tests/test_sources.py` (11 testes passando); falta homologação clínica presencial.
- **K05/K20 · #22, #47 e K21 · #48 (Em revisão em 2026-11-11):** Procedimentos administrativos de retenção/eliminação (`execute-deletion`, com expurgo de texto OCR, candidatos não votados e arquivos sem vínculo e retenção sob bloqueio de registros clínicos auditados conforme art. 16 da LGPD), comprovação documental de representação familiar (`verify-representation` e indicador `representationVerified` em `/api/dependents`) e resposta a incidentes (`security-incident`) implementados em `backend/privacy.py`, `backend/manage.py`, `backend/routes.py` e `docs/OPERACAO.md`, além de melhorias de acessibilidade/ARIA (`scope="col"`, `aria-expanded`, `aria-live`, estado `"Executado"`) em `src/App.jsx`, `src/Workspaces.jsx` e `src/PrivacyRights.jsx`. Validado em `tests/test_privacy.py` (2 testes passando); pendente confirmação institucional da caixa `example@unemat.bbr` e testes presenciais com usuários reais.

## Auditoria anterior (base de retomada)

Lista completa e critérios por issue: [docs/STATUS_ENTREGA.md](docs/STATUS_ENTREGA.md). Esta classificação substitui os estados do quadro anterior preservado no histórico abaixo.

**29 concluídas e 20 em andamento.** Dez concluídas são repetições conferidas; a nova #49 registra falha de restauração. Conclusão é do escopo da issue, não certificação clínica/jurídica nem produto pronto para dados reais.

## Concluído

| Cartão / recorte concluído | Issues | Evidência |
| --- | --- | --- |
| K00/K01 · diagnóstico, estrutura e módulo integrado | #23, #42 | React/API, autorização e CI d4e1757 aprovada. |
| K03/K04 · conta, sessão e pessoas vinculadas | #2, #3, #4, #20 | Cadastro, isolamento, autenticação e negativas automatizadas; prova documental adicional segue K20. |
| K05 · auditoria | #21 | Autor/data/alvo, histórico e proteção contra alteração comum; operação de privacidade segue aberta. |
| K06 · histórico e retorno da UBS | #9, #12 | Estados distintos, motivos e providências; três contas fictícias no navegador. |
| K07 · sugestões sempre a conferir | #6 | OCR não confirma doses; conferência por profissionais. Parser amplo segue aberto. |
| K08 · decisões por arquivo e dose | #14 | Autorização, recálculo, motivos, auditoria e concorrência testados. Orientações identificáveis seguem #15. |
| K09 · motor versionado no recorte de três vacinas | #7 | Idade/intervalos/fonte; não equivale a calendário integral. |
| K10 · avisos internos | #11 | Persistência, leitura e controle de duplicação; entrega push externa segue #44. |
| K11 · busca ativa ACS | #16, #17, #18 | Fila mínima, motivo de prioridade e ações vinculadas com histórico. |
| K12/K13 · testes e documentação base | #24, #25 | CI reproduzível, operação e guias; diagrama específico segue #19. |
| K14 · demonstração Docker escolhida pelo usuário | #26 | Execução local dos três perfis documentada; não há hospedagem pública. |
| K15 · duplicatas equivalentes conferidas | #27, #29, #30, #31, #34, #35, #36, #37, #38, #39 | Critérios comparados com #9/#7/#6/#4/#3/#2; escopo e histórico preservados. |

## Em andamento — implementação pausada

Responsável por continuidade: mantenedor/IA após retomada; validações clínicas/operacionais dependem das equipes responsáveis. Critérios completos e dependências em STATUS_ENTREGA e nas issues.

| Cartão | Issues | Próximo passo / critério restante |
| --- | --- | --- |
| K02 | #19 | Diagrama e decisões da modelagem. |
| K02.1 | #49 | Corrigir restauração em banco migrado; validar PostgreSQL + arquivos + hashes sem sobrescrever dados. |
| K05/K20 | #22, #47 | Canal funcional, retenção/eliminação, representação, direitos e incidentes; aceitar termos não substitui operação. |
| K06/K16 | #1, #40, #41, #43 | Testar envio/câmera/PWA em Android/iPhone reais; acesso HTTPS fora do computador. |
| K06 | #13 | Contexto das pendências na revisão UBS. |
| K07/K19 | #5, #32, #33, #46 | Ampliar parser/regras além de BCG/Penta/VIP e revisar clinicamente. |
| K08 | #15 | Nome identificável de quem libera orientações à família. |
| K09/K09.1 | #8, #10, #28 | Separar pendências atuais de histórico e motivos resolvidos. K09.1 ainda só planejado. |
| K17 | #44 | Entrega real de push autorizado e validação nos aparelhos. |
| K18/K18.2 | #45 | Impedimento após voto: rascunho só de esquema 012, sem endpoints/comando/efeitos. Preservar rodadas e testes existentes. |
| K21 | #48 | Textos/contexto, teclado/leitor de tela e testes com cidadãos/UBS/ACS. |

## Evidências atuais

Base d4e1757: [CI aprovada](https://github.com/ImuniGov/ImuniGov/actions/runs/42555673454), três jobs, 49 testes Docker/PostgreSQL e 4 PWA. Auditoria do rascunho: 46 testes SQLite aprovados, 3 OCR pulados por dependências locais; lint/formatação aprovados. Migração 012 aplicada em SQLite temporário. Falha de restauração #49 reproduzida no destino migrado sem pacientes. Não afirmar testes de fluxo pós-voto inexistente nem homologação em aparelhos reais.

## Sincronização remota

Atualização executada e conferida por nova leitura da API: **29 issues fechadas como concluídas e 20 abertas com label em andamento**, total de 49; dez fechadas são duplicatas de critérios equivalentes. Histórico original preservado. Nova falha registrada na #49. Acesso de issues/push funciona. **GitHub Projects: colunas não sincronizadas**, por falta de `read:project`/`project`; labels de issues e este arquivo são superfícies distintas. Nenhuma alteração de permissões foi feita.

CI do estado salvo em **92f75f9**: [execução 42558280959](https://github.com/ImuniGov/ImuniGov/actions/runs/42558280959) **aprovada** em frontend, backend e docker-postgres. O commit posterior registra apenas documentação.

## Histórico desta auditoria

| Data | Passo | Evidência / restante |
| --- | --- | --- |
| 2026-11-08 | Meta pausada; somente auditoria e salvamento | Rascunho K18.2 mantido como incompleto. |
| 2026-11-08 | 48 issues revisadas, duplicatas comparadas e #49 criada | 29 concluídas pelo escopo, 20 abertas; histórico preservado. |
| 2026-11-08 | Sincronização verificada e CI aprovada | 29 fechadas, 20 abertas; estados/labels conferidos em nova leitura. CI 42558280959 nos três jobs. Projects permanece pendente. |
| 2026-11-08 | Falha de restauração documentada | Linha inicial review_gate incompatível com exigência de banco totalmente vazio; não corrigida nesta etapa. |
| 2026-11-11 | Retomada explícita e conclusão de K02 (#19), K08 (#15), K06 (#13) e K09.1 (#8/#10/#28/#48) | DER em `docs/MODELAGEM_DADOS.md`; `author_name` nas orientações; contexto de pendências na revisão UBS; separação visual e na API entre pendências abertas e histórico resolvido. |
| 2026-11-11 | K02.1 (#49), K18.2 (#45), K19/K07 (#5/#32/#33/#46), K05/K20 (#22/#47) e K21 (#48) implementados e em revisão | Restauração compatível com `review_gate` e esquema `012`; fluxo pós-voto completo com suspensão e nova rodada independente; 23 regras PNI + parser ampliado; comandos LGPD (`verify-representation`, `execute-deletion`, `security-incident`) e melhorias ARIA. 51 testes SQLite aprovados (3 OCR pulados sem motores locais) + 4 PWA aprovados. |

<details>
<summary>Histórico do quadro anterior — estados abaixo substituídos pela auditoria acima</summary>

# Kanban do ImuniGuia

Atualizado: 2026-11-08 (America/Cuiaba). Branch de entrega: **homologacao**. O quadro registra implementação e aceite restante; código publicado não implica aprovação clínica, jurídica ou operação com dados reais.

## Regras

- A fazer → Em andamento → Em revisão → Concluído. Bloqueado exige causa e ação concreta.
- Atualizar este arquivo a cada passo significativo e no mesmo commit do código.
- Concluído exige todos os critérios e evidências atuais; não usar testes antigos como prova de código posterior.
- Preservar escopo e histórico das issues. Duplicatas não são encerradas automaticamente.
- GitHub Projects e este arquivo são superfícies distintas. Não declarar sincronização de colunas sem leitura de confirmação.

## Em andamento

**K18.2 · #45 — impedimento após voto.** Registrar ocorrência por caderneta, preservar votos, suspender conferência e retirar confirmações daquela evidência da avaliação até nova revisão. Administração registra análise e libera apenas nova equipe independente, sem aprovar doses por conta própria. Testar privacidade, duplicidade, rodadas, lembretes e concorrência.

**K09.1 · #10/#48 — pendências resolvidas.** Separar abertas de histórico expansível, preservando motivo anterior, fonte, data e orientações.

## Último avanço de revisão independente

**K18.1 · #45 — alteração e suspensão de revisores — Em revisão.** Alteração cadastral auditada, retirada de sessões/acesso, nova rodada para conferências em andamento e preservação de votos e decisões anteriores implementados. Comando administrativo tem prévia e versão esperada para impedir alterações baseadas em perfil desatualizado. Mudanças/votos/atribuições são serializados no banco, sem relaxar geografia.

Evidências: **49 testes Docker/PostgreSQL com OCR real passaram**; migração SQLite com atribuições/votos já existentes preservou dados e FKs; testes concorrentes de três votos, envio duplicado, sorteio e alteração de perfil contra voto passaram em SQLite e PostgreSQL. No navegador, três contas fictícias distintas aprovaram o arquivo e depois a dose; após um e dois votos o caso permaneceu a conferir, após o terceiro confirmou. Família viu os três profissionais e retornos. O teste não autentica documentação profissional real.

Restante: encaminhamento administrativo de impedimento descoberto depois de voto (K18.2), revisão jurídico-operacional e teste com equipe real. [CI do código d4e1757 aprovada](https://github.com/ImuniGov/ImuniGov/actions/runs/42555673454) nos três jobs. No teste local do comando com prévia/aplicação, um caso em andamento foi reiniciado e dois concluídos foram preservados; a família abriu o voto da rodada 1 durante a rodada 2.

## Último avanço em revisão

**K20.1 · #47 — continuidade e revogação da autorização — Em revisão.** Novo aceite explícito para contas antigas/termos alterados; revogação suspende processamento, acesso da equipe e avisos externos, preservando consulta/exportação própria. Resultado OCR em andamento é descartado mesmo se houver reaceite durante a leitura. Declaração `representationConfirmed` exigida no servidor e registrada na auditoria; não substitui prova do vínculo.

Evidência: **39 testes passaram no Docker/PostgreSQL com OCR real**, incluindo quatro cenários de ciclo de autorização; lint, formatação e build passaram. No navegador, conta anterior exibiu pausa, texto vigente e caixas desmarcadas; nenhum aceite foi feito em nome do usuário. Nova versão `2026-11-08.3`; anterior preservada. Migração 010 não cria autorizações antigas. [CI deste avanço aprovada](https://github.com/ImuniGov/ImuniGov/actions/runs/42552984180) no código `ed96a06`, nos três jobs. Eliminação, retenção e comprovação documental continuam pendentes na #47.

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
| K18 · #45 | Trio sorteado completo; geografia nascimento/trabalho cruzada; independência, impedimento, votos imutáveis, recusa com motivo/providência | Aprovação positiva por três contas, concorrência e mudanças de perfil/rodadas validadas. Falta encaminhamento por caso para impedimento posterior ao voto (K18.2). Verificação documental é administrativa; geografia não prova ausência de vínculo pessoal. |
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

| 2026-11-08 | K20.1 em revisão | Suspensão efetiva, reaceite explícito e representação no servidor; 39 testes Docker passaram. CI ed96a06 aprovada nos três jobs, execução 42552984180. |

## Pendências identificadas durante a homologação

- **K18.2 · #45:** o profissional que já votou ainda recebe orientação de procurar a administração ao declarar impedimento. Implementar encaminhamento por caso sem alterar artificialmente seu perfil, com preservação do histórico e tratamento explícito de decisões já concluídas.
- **K09.1 · #10/#48:** pendências resolvidas mantêm o motivo histórico antigo na lista. Mostrar explicitamente que o motivo é anterior e organizar resolvidas como histórico, para não sugerir ausência atual de uma dose confirmada.

| 2026-11-08 | K18.1 em revisão | Rodadas, suspensão e alteração auditada; homologação com três contas no navegador e testes de concorrência. CI d4e1757 aprovada na execução 42555673454. |

| 2026-11-08 | K18.1 validado tecnicamente | CI 42555673454 aprovada; três contas conferidas pelo navegador; CLI com prévia/versão e histórico anterior exercitada com dados fictícios. K18.2 permanece aberto. |


</details>
