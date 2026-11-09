# Roadmap do ImuniGuia

Atualizado em: 2026-11-08 (America/Cuiaba).
Meta: integrar a base funcional de `teste` ao frontend de `main` na branch `homologacao`, até um MVP verificável para Família, UBS e ACS.

## Base desta análise

- [main em 080b34c](https://github.com/ImuniGov/ImuniGov/tree/080b34ccd286b70ab761d4f8854cc09bf42fa9a4): 7 arquivos versionados; configuração React/Vite, scripts dev/build/lint/preview e HTML apontando para `/src/main.jsx`. Não existem `src/` nem `favicon.svg` nessa revisão. A interface completa não pode ser considerada disponível ou executável.
- [teste em 025fbed](https://github.com/ImuniGov/ImuniGov/tree/025fbed4d44e6ab48b982b0a9973fe78e34acd09): protótipo Python da biblioteca padrão + SQLite, HTML/CSS/JS, Docker/Compose, OpenAPI e arquitetura alvo.
- [Issues do repositório](https://github.com/ImuniGov/ImuniGov/issues): 42 issues consultadas, todas abertas na coleta. #1, #13 e #14 têm entregas parciais descritas. Checkbox marcado na issue não comprova sozinho implementação do requisito completo.
- [Arquitetura alvo em teste](https://github.com/ImuniGov/ImuniGov/blob/025fbed4d44e6ab48b982b0a9973fe78e34acd09/ARQUITETURA.md): React/TypeScript, FastAPI/Pydantic/SQLAlchemy, Alembic/PostgreSQL, armazenamento privado S3/MinIO, Redis/Celery e CI são destino planejado; não são a stack já implementada.

Atualização de execução: o usuário solicitou concluir o app e escolheu Docker. Como não há fontes React no histórico, a interface está sendo reconstruída. Backend FastAPI/SQLAlchemy, contratos legados, migrações, importação e testes já implementados; consultar KANBAN.md para estado e verificações atuais. O diagnóstico abaixo é o levantamento inicial, preservado como referência histórica. Não há previsão de prazo inventada.

## O que existe e o que falta

| Área | Evidência existente | Limite atual |
| --- | --- | --- |
| Frontend main | package.json, vite.config.js e index.html | Entrada React e assets ausentes; recuperar antes de integrar. |
| Dependentes | teste/server.py e formulários: nome, ID e listagem; remoção sem documentos | Sem nascimento, conta responsável ou isolamento entre famílias. |
| Upload | teste/patient.js, app.js e server.py: multipart, tipos, assinatura básica, 10 MB, SHA-256 e arquivo privado fora da pasta pública | Sem autenticação; seleção mostra nome/tamanho, não prévia da imagem; câmera não implementada; PDF aceito além de imagens. |
| Conferência de documento | Fila, filtro, abertura, aprovação/devolução, justificativa, data e auditoria no protótipo | Revisor autodeclarado; documento aprovado não é registro vacinal validado. |
| Auditoria | Tabela audit_events e GET /api/audit | Escopo de documento, sem identidade autenticada nem auditoria completa UBS/ACS. |
| Operação | Python, Docker/Compose e volume SQLite no protótipo | Sem integração React/API, migração PostgreSQL, suíte automatizada ou workflow CI versionados nas árvores consultadas. |
| OCR, calendário, histórico vacinal, pendências, orientação, ACS, notificações | Requisitos nas issues e arquitetura | Não há implementação desses módulos nas revisões consultadas. |

Verificação desta análise: inspeção estática de árvores, código, documentação e issues. Não foram executados build, backend ou testes funcionais. Não há homologação funcional comprovada.

## Etapas e critérios de saída

| Marco | Entrega e ordem | Dependências | Critério de saída |
| --- | --- | --- | --- |
| M0 | Diagnóstico, roadmap, kanban e instruções IA | Nenhuma | Documentos versionados e referências verificadas. |
| M1 | Base integrada: recuperar frontend; definir diretórios; trazer contratos/lógica de teste com conflitos resolvidos; configurar API, banco e migrações | M0 | Entrada React presente, build passa, health responde e importação de dados/arquivos tem integridade verificada. Issues #23 e #19. |
| M2 | Cadastro, sessão, perfis, vínculo de dependentes, auditoria e privacidade | M1 | Família não acessa dados alheios; anônimo não acessa arquivos; UBS/ACS respeitam permissões no servidor; testes de negativas passam. Issues #2–#4, #20–#22. |
| M3 | Primeira fatia ponta a ponta na interface definitiva: dependente → upload → fila → decisão → consulta | M2 | Executar fluxo com dados sintéticos, prévia real e câmera onde compatível; validar PDF no contrato; API/OpenAPI alinhados; revisão mantém autoria e auditoria. Issues #1 e #42; partes de #12–#14. |
| M4 | OCR assíncrono e registros candidatos | M3 | Extração ligada ao original, falhas e baixa confiança visíveis; repetição não duplica registros; nenhum candidato confirma dose. Issues #5 e #6. |
| M5 | Revisão UBS de registros, situação e orientação para família | M4 | Profissional autorizado confirma/recusa candidato; histórico de decisão e orientação liberada visíveis só ao responsável correto. Issues #12–#15. |
| M6 | Catálogo/regras versionadas, histórico e possíveis pendências | M5 | Cálculos rastreáveis por regra/versão; limites de idade/intervalo testados; decisão dispara recálculo sem usar candidato como dose confirmada. Issues #7–#10. |
| M7 | Alertas e busca ativa ACS | M6 | Evento não duplica aviso; ACS vê motivo e dados mínimos, registra contato e caso resolvido sai da fila preservando histórico. Issues #11, #16–#18. |
| M8 | Demonstração verificável | M7 | CI passa, documentação de execução reproduzida, revisão de acesso e privacidade, backup/restauração e fluxo completo na hospedagem documentados. Issues #24–#26. |

Testes, documentação, privacidade e auditoria acompanham cada marco; M8 consolida a evidência final. Em M5, preparar eventos/contratos de recálculo; só considerar #14 completa após M6 implementar e validar o recálculo real.

## Inventário rastreável do backlog

“Parcial em teste” indica código de protótipo ou documentação existente, não conclusão na homologacao. “A fazer” indica ausência de implementação encontrada. Todas as issues abaixo permaneciam abertas na coleta.

| Issue | Marco | Diagnóstico | Próximo trabalho verificável |
| --- | --- | --- | --- |
| [#1](https://github.com/ImuniGov/ImuniGov/issues/1) — Implementar envio da foto da caderneta de vacinação | M3 | Parcial em teste | Autenticação e vínculo; câmera, pré-visualização real e decisão documentada sobre PDF. |
| [#2](https://github.com/ImuniGov/ImuniGov/issues/2) — Implementar cadastro de usuário | M2 | A fazer | Cadastro persistido, e-mail único e hash de senha; formulário integrado. |
| [#3](https://github.com/ImuniGov/ImuniGov/issues/3) — Implementar autenticação de usuário | M2 | A fazer | Login/logout, sessão válida e bloqueio de rotas anônimas. |
| [#4](https://github.com/ImuniGov/ImuniGov/issues/4) — Implementar cadastro de dependente | M2 | Parcial em teste | Nascimento válido, vínculo com responsável e isolamento entre famílias. |
| [#5](https://github.com/ImuniGov/ImuniGov/issues/5) — Implementar transcrição da caderneta por OCR | M4 | A fazer | OCR, processamento assíncrono, confiança/erros e vínculo com original. |
| [#6](https://github.com/ImuniGov/ImuniGov/issues/6) — Classificar registros extraídos como 'a conferir' | M4 | A fazer | Entidade de registro candidato a_conferir, distinta do status do documento. |
| [#7](https://github.com/ImuniGov/ImuniGov/issues/7) — Implementar motor de regras do calendário vacinal | M6 | A fazer | Regras versionadas por vigência, idade, dose e intervalo, com origem rastreável. |
| [#8](https://github.com/ImuniGov/ImuniGov/issues/8) — Identificar possíveis pendências vacinais | M6 | A fazer | Cálculo e recálculo de possíveis pendências após mudança de histórico. |
| [#9](https://github.com/ImuniGov/ImuniGov/issues/9) — Implementar consulta do histórico vacinal | M6 | A fazer | Histórico por dependente com origem e distinção candidato/confirmado. |
| [#10](https://github.com/ImuniGov/ImuniGov/issues/10) — Implementar consulta de pendências vacinais | M6 | A fazer | Consulta privada de pendências, situação e próximo passo orientado. |
| [#11](https://github.com/ImuniGov/ImuniGov/issues/11) — Implementar alertas e notificações de pendências | M7 | A fazer | Notificações por evento, idempotência e marcação de leitura. |
| [#12](https://github.com/ImuniGov/ImuniGov/issues/12) — Implementar acompanhamento da situação de validação | M5 | A fazer | Acompanhamento da família com estado, atualização e motivo de recusa. |
| [#13](https://github.com/ImuniGov/ImuniGov/issues/13) — Criar fila de validação para enfermagem | M5 | Parcial em teste | Acesso UBS autenticado, extrações OCR e pendência na fila. |
| [#14](https://github.com/ImuniGov/ImuniGov/issues/14) — Implementar validação ou recusa de registro vacinal | M5 | Parcial em teste | Decisão de registro vacinal por profissional autenticado e recálculo; aprovação de arquivo não confirma dose. |
| [#15](https://github.com/ImuniGov/ImuniGov/issues/15) — Implementar registro de conduta e orientação da UBS | M5 | A fazer | Orientação vinculada ao caso, autoria, histórico e liberação à família. |
| [#16](https://github.com/ImuniGov/ImuniGov/issues/16) — Criar fila de busca ativa para ACS | M7 | A fazer | Fila ACS com critério rastreável, filtros e saída de casos resolvidos. |
| [#17](https://github.com/ImuniGov/ImuniGov/issues/17) — Implementar visualização de famílias prioritárias | M7 | A fazer | Prioridades e motivos, com acesso restrito e dados mínimos. |
| [#18](https://github.com/ImuniGov/ImuniGov/issues/18) — Implementar registro de ação de busca ativa | M7 | A fazer | Contato, data, autor e histórico de ações sem apagar eventos anteriores. |
| [#19](https://github.com/ImuniGov/ImuniGov/issues/19) — Modelar banco de dados do ImuniGuia | M1 | Parcial em teste | Modelo executável completo, migrações e importação íntegra de SQLite/arquivos. |
| [#20](https://github.com/ImuniGov/ImuniGov/issues/20) — Implementar controle de acesso por perfil | M2 | A fazer | Permissões no backend por perfil e objeto; testes de acesso cruzado. |
| [#21](https://github.com/ImuniGov/ImuniGov/issues/21) — Implementar auditoria das ações do sistema | M2 | Parcial em teste | Ator autenticado, abrangência UBS/ACS e consulta restrita de eventos protegidos. |
| [#22](https://github.com/ImuniGov/ImuniGov/issues/22) — Implementar requisitos de LGPD e privacidade | M2 | A fazer | Inventário de dados, finalidade, acesso, retenção/descarte e consentimento quando aplicável. |
| [#23](https://github.com/ImuniGov/ImuniGov/issues/23) — Configurar estrutura inicial do projeto | M1 | Parcial em teste e main | Restaurar src/main.jsx e assets faltantes; integrar estrutura, configuração e execução reproduzível. |
| [#24](https://github.com/ImuniGov/ImuniGov/issues/24) — Implementar testes das principais funcionalidades | M8 | A fazer | Suíte reproduzível de domínio, API, acesso e fluxos principais; CI com lint/build/testes. |
| [#25](https://github.com/ImuniGov/ImuniGov/issues/25) — Criar documentação do projeto | M8 | Parcial em teste | Manter instruções de execução validadas após integrar frontend e backend; arquitetura local sincronizada. |
| [#26](https://github.com/ImuniGov/ImuniGov/issues/26) — Configurar deploy do MVP | M8 | A fazer | Plataforma, segredos, HTTPS, backup/restauração e fluxos validados em demonstração. |
| [#42](https://github.com/ImuniGov/ImuniGov/issues/42) — Evoluir módulo de documentos: interface definitiva, autenticação e segurança | M3 | Parcial em teste | Entregar frontend definitivo conectado, identidade confiável, segurança e testes do módulo. |

## Duplicatas a conferir

Há títulos repetidos; preservar histórico e vínculos antes de consolidar. Não fechar automaticamente apenas pela igualdade de título.

| Issue de referência | Possíveis duplicatas |
| --- | --- |
| [#1](https://github.com/ImuniGov/ImuniGov/issues/1) | [#40](https://github.com/ImuniGov/ImuniGov/issues/40), [#41](https://github.com/ImuniGov/ImuniGov/issues/41) |
| [#2](https://github.com/ImuniGov/ImuniGov/issues/2) | [#38](https://github.com/ImuniGov/ImuniGov/issues/38), [#39](https://github.com/ImuniGov/ImuniGov/issues/39) |
| [#3](https://github.com/ImuniGov/ImuniGov/issues/3) | [#36](https://github.com/ImuniGov/ImuniGov/issues/36), [#37](https://github.com/ImuniGov/ImuniGov/issues/37) |
| [#4](https://github.com/ImuniGov/ImuniGov/issues/4) | [#34](https://github.com/ImuniGov/ImuniGov/issues/34), [#35](https://github.com/ImuniGov/ImuniGov/issues/35) |
| [#5](https://github.com/ImuniGov/ImuniGov/issues/5) | [#32](https://github.com/ImuniGov/ImuniGov/issues/32), [#33](https://github.com/ImuniGov/ImuniGov/issues/33) |
| [#6](https://github.com/ImuniGov/ImuniGov/issues/6) | [#30](https://github.com/ImuniGov/ImuniGov/issues/30), [#31](https://github.com/ImuniGov/ImuniGov/issues/31) |
| [#7](https://github.com/ImuniGov/ImuniGov/issues/7) | [#29](https://github.com/ImuniGov/ImuniGov/issues/29) |
| [#8](https://github.com/ImuniGov/ImuniGov/issues/8) | [#28](https://github.com/ImuniGov/ImuniGov/issues/28) |
| [#9](https://github.com/ImuniGov/ImuniGov/issues/9) | [#27](https://github.com/ImuniGov/ImuniGov/issues/27) |

## Próxima ação

Começar pelo cartão K01 em [KANBAN.md](KANBAN.md). Recuperar os fontes ausentes da interface junto à equipe/histórico e preparar a integração preservando os contratos de teste. Não substituir o frontend por uma tela inventada e considerar a recuperação concluída.

A cada início, avanço, bloqueio e conclusão, atualizar o kanban conforme [AGENTS.md](AGENTS.md). O [GUIA_IA.md](GUIA_IA.md) explica como retomar o trabalho e validar a entrega.
