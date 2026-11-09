# Estado da entrega e lista completa de pendências

Auditoria: 2026-11-08, America/Cuiaba. Branch: `homologacao`.

**Meta de desenvolvimento pausada pelo usuário.** Este registro salva o estado existente e classifica as issues; não autoriza retomada automática de implementação. O app ainda não está concluído para operação com dados reais.

## Resultado da classificação

29 issues com critérios do respectivo escopo atendidos; 20 abertas em andamento, incluindo a nova #49 de restauração. Dez das 29 concluídas são repetições cujo escopo foi comparado com a referência; não representam dez funcionalidades adicionais. Encerrar o motor de regras MVP (#7) não significa calendário completo; encerrar Docker de demonstração (#26) não significa publicação pública. A confirmação da sincronização remota será registrada no quadro após a API responder.

## Tudo que falta

| Prioridade / cartão | Pendência verificável | Issues |
| --- | --- | --- |
| Alta · K18.2 | Implementar impedimento descoberto depois de um voto: ocorrência por caderneta, suspensão da conferência, avaliação administrativa e nova equipe independente, preservando votos e histórico. Testar efeitos sobre decisões, agenda e concorrência. | #45 |
| Alta · K02.1 | Corrigir restauração em destino novo migrado. A migração 011 cria `review_gate`, mas o restaurador exige todas as tabelas vazias. Definir compatibilidade de versões e ensaiar PostgreSQL + arquivos + hashes, incluindo falhas e recuperação. | #49 |
| Alta · K19/K07 | Ampliar o reconhecimento e as regras além de BCG/Pentavalente/VIP, com exemplos variados autorizados, limites explícitos, revisão clínica e testes de exceções/intervalos. O catálogo público RNDS de vacinas não calcula datas individuais. | #5, #32, #33, #46 |
| Alta · K05/K20 | Definir e operar retenção, eliminação, atendimento de direitos, comprovação de representação familiar e resposta a incidentes; formalizar responsável e bases aplicáveis ao serviço. Termos e declaração de vínculo não resolvem esses procedimentos. | #22, #47 |
| Alta · K20 | Confirmar funcionamento do contato informado `example@unemat.bbr`. Não corrigir o endereço silenciosamente nem presumir que recebe solicitações. | #47 |
| Média · K09.1 | Separar pendências atuais do histórico resolvido e identificar motivos anteriores; distinguir cálculo automático de conferência profissional. Hoje uma resolvida ainda pode exibir o motivo antigo como se fosse atual. | #8, #10, #28, #48 |
| Média · K08 | Mostrar nome do profissional nas orientações da família, substituindo o trecho do identificador interno. Preservar conteúdo, vínculo e horário. | #15, #48 |
| Média · K06 | Exibir as pendências relacionadas no contexto da revisão UBS, junto de arquivo, sugestões e histórico. A fila já existe; falta esse contexto na conferência. | #13 |
| Média · K02 | Documentar diagrama de entidades/relacionamentos e decisões da modelagem existente. | #19 |
| Média · K06/K16 | Validar envio, câmera, prévia, instalação, navegação e offline em aparelhos Android e iPhone reais. Fotos e PDF foram autorizados pelo usuário, substituindo a restrição antiga a somente imagens. | #1, #40, #41, #43 |
| Média · K14/K16 | Preparar origem HTTPS para acesso pelo celular fora do computador, conforme ambiente de hospedagem a definir. O usuário escolheu Docker; demonstração local já existe. | #43, #44 |
| Média · K17 | Verificar entrega real dos avisos externos com autorização em cada plataforma suportada. A agenda já identifica familiar/data, proximidade em 30 dias e atraso; outras vacinas dependem de datas indicadas pela UBS até ampliar regras. | #44, #46 |
| Média · K21 | Concluir revisão de linguagem e hierarquia, navegação por teclado, leitor de tela e testes de tarefas com cidadãos, UBS e ACS. Validar aparelhos e acessibilidade além da inspeção visual automatizada. | #48 |
| Operação · K18 | Estabelecer e executar verificação documental dos profissionais e locais, com equipe elegível suficiente. O sorteio geográfico cruzado já existe, mas não comprova que pessoas não se conhecem. | #45, #47 |
| Gestão | Sincronizar colunas do GitHub Projects. O acesso disponível permite issues e push, mas falta escopo específico de projetos. Labels das issues e KANBAN.md não equivalem a mover colunas remotas. | Quadro Projects |

## Rascunho salvo, sem funcionalidade concluída

Antes da pausa, começou a estrutura de K18.2: campo `documents.review_hold`, tabelas `review_incidents` e `review_resolutions` e migração 012 com proteção de histórico. **Não há endpoint, comando administrativo nem aplicação dessa suspensão no fluxo de revisão.** O profissional que já votou ainda precisa procurar a administração; #45 continua aberta. K09.1 é planejamento, sem implementação da separação visual.

## Issues concluídas e evidência de escopo

- **#2:** Cadastro de família com campos obrigatórios, e-mail único, senha protegida por Argon2, aceites versionados e confirmação de cadastro. Equipe é cadastrada pela administração.
- **#3:** Entrada e saída com sessão protegida; credenciais inválidas e acesso sem autenticação são bloqueados no servidor.
- **#4:** Cadastro/edição de pessoa da família com nascimento válido, vínculo ao responsável e isolamento entre famílias. Comprovação documental adicional segue em #47.
- **#6:** Sugestões extraídas começam a conferir e não são doses confirmadas. Arquivo aprovado é distinto de dose validada; a confirmação exige o painel autorizado de três profissionais.
- **#7:** Motor versionado por idade, datas e intervalos, com fonte rastreável e resultados como possíveis pendências. Encerramento do motor no recorte MVP BCG/Pentavalente/VIP; expansão e revisão clínica seguem em #46.
- **#9:** Histórico por pessoa e responsável, com estados distintos e atualização após conferência autorizada. Fluxo exercitado com três contas sintéticas.
- **#11:** Avisos internos persistentes, acompanhamento de leitura e controle de duplicidade. Entrega externa de push real é requisito adicional aberto em #44.
- **#12:** A família acompanha espera, decisões, motivos de devolução, providências, profissionais e horários, preservando histórico e arquivo anterior no reenvio.
- **#14:** Decisões autorizadas e auditadas por arquivo e por registro, motivos/providências, recálculo e proteção contra votos duplicados/concorrentes. Impedimento posterior a voto segue em #45.
- **#16:** Fila ACS autorizada com identificação mínima para contato, motivos rastreáveis e retirada dos casos resolvidos.
- **#17:** Filtro de prioridade ACS com motivo explícito na interface (30 dias ou mais), dados mínimos e autorização por perfil; não é classificação automática de risco clínico.
- **#18:** Ações ACS vinculadas ao caso, autor, data, tipo e observação; histórico preservado e fila atualizada após resolução.
- **#20:** Controle de acesso por perfil e objeto no servidor: família própria, UBS atribuída e ACS com dados mínimos; cenários negativos automatizados.
- **#21:** Auditoria de decisões e ações, identidade/horário/alvo e proteção de histórico contra alteração/exclusão comum no banco.
- **#23:** Estrutura React/FastAPI, dependências documentadas, configuração por ambiente e execução de desenvolvimento/Docker; segredos fora do versionamento.
- **#24:** Principais fluxos e negativas cobertos por testes reproduzíveis, incluindo três votos e concorrência. CI d4e1757 aprovada nos três jobs com 49 testes Docker/PostgreSQL; não comprova funcionalidades ainda não implementadas.
- **#25:** README, roadmap, kanban, guia IA, AGENTS, operação e referências de UX versionados. Diagrama de banco específico continua aberto em #19.
- **#26:** Demonstração local preparada em Docker conforme escolha explícita do usuário, três perfis e documentação de execução. Encerramento limitado a esse ambiente escolhido; não significa publicação pública/produção. HTTPS e aparelhos seguem #43/#44; restauração tem issue própria.
- **#42:** Interface integrada às APIs, autenticação/autorização no servidor, arquivos privados e testes de envio, decisões e auditoria. Os requisitos adicionais #43–#48 permanecem independentes e abertos.

Duplicatas conferidas e encerradas pelo mesmo critério: #27 → #9, #29 → #7, #30 → #6, #31 → #6, #34 → #4, #35 → #4, #36 → #3, #37 → #3, #38 → #2, #39 → #2. As demais duplicatas acompanham a pendência da referência. Descrições anteriores são preservadas nas issues como histórico, sem tratá-las como estado atual.

## Issues abertas, uma a uma

- **[#1 — Implementar envio da foto da caderneta de vacinação](https://github.com/ImuniGov/ImuniGov/issues/1):** Validar câmera, escolha e prévia do arquivo em Android e iPhone reais. Fotos e PDF são permitidos por requisito posterior do usuário; a restrição antiga a somente imagens foi substituída. Ver #43.
- **[#5 — Implementar transcrição da caderneta por OCR](https://github.com/ImuniGov/ImuniGov/issues/5):** Ampliar o reconhecimento além de BCG/Pentavalente/VIP e homologar cadernetas variadas autorizadas, incluindo leitura ruim e transcrição manual. OCR continua produzindo somente sugestões a conferir.
- **[#8 — Identificar possíveis pendências vacinais](https://github.com/ImuniGov/ImuniGov/issues/8):** Concluir a apresentação de possíveis pendências, diferenciando cálculo automático de conferência profissional e separando motivos históricos resolvidos. Ampliar cobertura com revisão clínica (#10/#46).
- **[#10 — Implementar consulta de pendências vacinais](https://github.com/ImuniGov/ImuniGov/issues/10):** Separar pendências abertas do histórico resolvido; identificar como anterior o motivo de uma pendência resolvida e distinguir análise automática de validação profissional.
- **[#13 — Criar fila de validação para enfermagem](https://github.com/ImuniGov/ImuniGov/issues/13):** Mostrar no contexto da conferência da caderneta as pendências vinculadas àquela pessoa, junto do arquivo e dos registros sugeridos. A fila e os controles de acesso já existem.
- **[#15 — Implementar registro de conduta e orientação da UBS](https://github.com/ImuniGov/ImuniGov/issues/15):** Exibir o nome identificável do profissional nas orientações para a família. Hoje a tela mostra um trecho do identificador interno; vínculo, conteúdo e horário já são persistidos.
- **[#19 — Modelar banco de dados do ImuniGuia](https://github.com/ImuniGov/ImuniGov/issues/19):** Documentar o diagrama de entidades e relacionamentos e as decisões de modelagem. As tabelas, vínculos e migrações já existem; documentação de esquema ainda incompleta.
- **[#22 — Implementar requisitos de LGPD e privacidade](https://github.com/ImuniGov/ImuniGov/issues/22):** Definir e executar retenção/eliminação, comprovação de representação de menores, resposta a incidentes e atendimento operacional de direitos. Confirmar responsável e contato funcional; declaração no cadastro não equivale a prova documental. Ver #47.
- **[#28 — Identificar possíveis pendências vacinais](https://github.com/ImuniGov/ImuniGov/issues/28):** Concluir a apresentação de possíveis pendências, diferenciando cálculo automático de conferência profissional e separando motivos históricos resolvidos. Ampliar cobertura com revisão clínica (#10/#46). Referência: #8.
- **[#32 — Implementar transcrição da caderneta por OCR](https://github.com/ImuniGov/ImuniGov/issues/32):** Ampliar o reconhecimento além de BCG/Pentavalente/VIP e homologar cadernetas variadas autorizadas, incluindo leitura ruim e transcrição manual. OCR continua produzindo somente sugestões a conferir. Referência: #5.
- **[#33 — Implementar transcrição da caderneta por OCR](https://github.com/ImuniGov/ImuniGov/issues/33):** Ampliar o reconhecimento além de BCG/Pentavalente/VIP e homologar cadernetas variadas autorizadas, incluindo leitura ruim e transcrição manual. OCR continua produzindo somente sugestões a conferir. Referência: #5.
- **[#40 — Implementar envio da foto da caderneta de vacinação](https://github.com/ImuniGov/ImuniGov/issues/40):** Validar câmera, escolha e prévia do arquivo em Android e iPhone reais. Fotos e PDF são permitidos por requisito posterior do usuário; a restrição antiga a somente imagens foi substituída. Ver #43. Referência: #1.
- **[#41 — Implementar envio da foto da caderneta de vacinação](https://github.com/ImuniGov/ImuniGov/issues/41):** Validar câmera, escolha e prévia do arquivo em Android e iPhone reais. Fotos e PDF são permitidos por requisito posterior do usuário; a restrição antiga a somente imagens foi substituída. Ver #43. Referência: #1.
- **[#43 — Preparar aplicativo PWA e experiência mobile](https://github.com/ImuniGov/ImuniGov/issues/43):** Validar instalação, câmera, navegação e comportamento offline em Android/iPhone reais, usando HTTPS para acesso pelo celular fora do computador. Manifesto e testes automatizados não substituem aparelhos.
- **[#44 — Acompanhar próximas doses da família e avisos privados](https://github.com/ImuniGov/ImuniGov/issues/44):** Comprovar entrega real dos avisos externos nos aparelhos e navegadores suportados, com autorização do usuário. Agenda e janela de 30 dias existem; fora das três regras atuais, datas dependem do planejamento UBS.
- **[#45 — Exigir três revisores independentes com sorteio e restrições geográficas](https://github.com/ImuniGov/ImuniGov/issues/45):** Concluir tratamento administrativo de impedimento descoberto após voto: registrar ocorrência por caso, suspender a conferência, preservar histórico e permitir nova equipe independente. A migração 012 é apenas rascunho de estrutura; não há fluxo implementado. Verificação de documentos dos profissionais continua sendo procedimento humano.
- **[#46 — Integrar catálogo público RNDS e fontes oficiais do calendário](https://github.com/ImuniGov/ImuniGov/issues/46):** Ampliar e revisar clinicamente o calendário além de BCG/Pentavalente/VIP e definir manutenção das versões. RNDS público fornece terminologia, não datas individuais; não há API pública de recomendação individual integrada.
- **[#47 — Apresentar termos e consentimento específico para dados de saúde](https://github.com/ImuniGov/ImuniGov/issues/47):** Confirmar o contato informado example@unemat.bbr e formalizar responsável, bases aplicáveis, prazos de retenção, execução de eliminação, comprovação de representação e resposta a incidentes. Aceites versionados, reaceite e suspensão por revogação já existem; termos não encerram a adequação operacional.
- **[#48 — Revisar linguagem, hierarquia e acessibilidade da interface Família/UBS/ACS](https://github.com/ImuniGov/ImuniGov/issues/48):** Concluir revisão de textos e hierarquia (incluindo pendências resolvidas e nome do profissional), navegação por teclado/leitor de tela e testes de tarefas com cidadãos, UBS e ACS. Revisão visual e pesquisa de referências já feitas; não há certificação de acessibilidade nem validação com usuários reais.
- **[#49 — Corrigir restauração em banco migrado e validar backup PostgreSQL + arquivos](https://github.com/ImuniGov/ImuniGov/issues/49):** Corrigir restauração em banco realmente migrado e validar PostgreSQL + arquivos + hashes; tratar a linha inicial review_gate e compatibilidade de versões do backup.

## Validação e limites

- Base funcional d4e1757: [CI 42555673454](https://github.com/ImuniGov/ImuniGov/actions/runs/42555673454) aprovada em frontend, backend e Docker/PostgreSQL, com 49 testes Docker e 4 testes PWA. Três contas sintéticas conferiram arquivo e dose no navegador, preservando rodadas e histórico.
- Rascunho atual: 46 testes SQLite aprovados e 3 de OCR pulados por ausência dos motores locais; lint e formatação Python aprovados. Migração 012 aplicada a SQLite temporário e integridade referencial conferida pela migração. Isso não testa o fluxo de impedimento, que ainda não existe.
- Falha #49 reproduzida com banco SQLite temporário realmente migrado e sem dados de pacientes. O ensaio completo de restauração PostgreSQL + arquivos permanece pendente; os testes antigos de backup não cobriam o destino migrado.
- Docker local é demonstração. Nenhuma publicação HTTPS, entrega push real em aparelhos, validação clínica, validação jurídica ou certificação de acessibilidade está sendo declarada.
- Fluxo de três revisores, permissões, histórico e auditoria foi testado com dados fictícios. Não foram autenticados documentos de profissionais reais.

## Fontes e continuidade

[Referências e decisões de linguagem/UI/UX](DESIGN_UX.md), [operação](OPERACAO.md), [roadmap](../roadmap.md), [guia IA](../GUIA_IA.md) e [kanban](../KANBAN.md). Reabrir a implementação somente após retomada pelo usuário. Manter cartões, issues e evidências atualizados a cada passo, conforme AGENTS.md.
