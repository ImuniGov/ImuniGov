# Roadmap do ImuniGuia

> **Estado vigente da auditoria:** meta de implementação pausada pelo usuário. Não retomar desenvolvimento automaticamente. Lista completa em [docs/STATUS_ENTREGA.md](docs/STATUS_ENTREGA.md): 29 issues concluídas pelo respectivo escopo e 20 abertas, incluindo #49 (restauração falha em banco migrado). K18.2 tem somente rascunho de esquema/migração 012, sem fluxo implementado. As prioridades abaixo são para quando houver retomada. Docker local está entregue; HTTPS público, aparelhos reais, operação de privacidade, cobertura clínica ampliada e acessibilidade/usabilidade ainda precisam de validação. A confirmação remota desta auditoria será registrada em KANBAN.md.

Atualizado: 2026-11-08 (America/Cuiaba). Entrega em `homologacao`. O usuário escolheu execução Docker; hospedagem pública ainda não foi definida. O pedido atual inclui revisão completa de linguagem e experiência.

## Base e resultado atual

`main` em 080b34c possuía configuração React sem os fontes de `src`; `teste` em 025fbed forneceu o protótipo Python/SQLite. A integração reconstruiu a interface e preservou os contratos úteis, acrescentando autenticação e autorização. O levantamento inicial e o quadro anterior permanecem no histórico do Git. Não tratar aquele diagnóstico como descrição atual.

| Marco | Implementado | Aceite restante |
| --- | --- | --- |
| M0 — diagnóstico (#23, #25, #42) | Roadmap, kanban, guia e AGENTS.md | Manter documentação e issues sincronizadas. |
| M1 — base e dados (#19, #23) | React/FastAPI, PostgreSQL/Alembic, importação legada e hashes | Diagrama #19 e correção/ensaio de restauração #49 (PostgreSQL+arquivos). |
| M2 — acesso e família (#2–#4, #20–#22) | Conta de família, sessão, perfis, pessoas, exportação, privacidade | Reaceite implementado; faltam representação comprovada e operação de eliminação/retenção. |
| M3 — cadernetas (#1, #13, #14, #42) | Foto/PDF, prévia, OCR, arquivo privado, revisão e auditoria | Três contas e rodadas validadas; falta contexto de pendências na revisão e aparelhos reais. |
| M4 — regras e registros (#5–#10, #27–#35) | Leitura assistida, candidatos, histórico, motor versionado, pendências | Revisão clínica e ampliar cobertura além das três vacinas de rotina. |
| M5 — UBS (#12–#15) | Decisões separadas por arquivo/dose, motivos, providências, orientações e datas | Fluxo administrativo completo e aceite com equipe real. |
| M6 — ACS (#16–#18) | Busca ativa por pessoa, prioridade, ações e histórico | Teste de usabilidade com agentes e equipe responsável. |
| M7 — acompanhamento (#11, #43, #44) | Agenda familiar, avisos, push opt-in, mobile/PWA | Aparelhos reais, HTTPS e entrega push externa. |
| M8 — qualidade e operação (#24–#26) | Testes automatizados, Docker, CI e guias operacionais | CI d4e1757 aprovada; falta correção de restauração e validação operacional; hospedagem quando definida. |
| M9 — revisão independente e experiência (#45–#48) | Trio sorteado, geografia cruzada, RNDS público, termos, retorno à família e UI revisada | Pendências detalhadas abaixo e em KANBAN.md. |

## Prioridades antes de dados reais

1. Validar clinicamente as regras e suas exceções; ampliar por versões testadas. Catálogo de imunobiológicos não fornece datas individuais.
2. Validar controle de acesso, concorrência de votos, mudanças de perfil e fluxo administrativo de revisão independente. Sem equipe completa, aguardar.
3. Definir/controlar bases legais, retenção, atendimento de direitos, comprovação de representação, incidentes e contato de privacidade funcional. O contato informado foi `example@unemat.bbr`; não corrigir ou inventar outro endereço.
4. Testar backup/restauração PostgreSQL+volume, configurar HTTPS e verificar instalação/avisos em aparelhos reais quando houver hospedagem.
5. Validar linguagem, tarefas e acessibilidade com cidadãos, UBS e ACS; não substituir pesquisa com usuários por alterações visuais.

## Rastreabilidade das issues

Originais: #1 envio, #2 cadastro, #3 login, #4 dependentes, #5 OCR, #6 a conferir, #7 regras, #8 pendências, #9 histórico, #10 consulta de pendências, #11 avisos, #12 acompanhamento, #13 fila UBS, #14 decisões, #15 orientação, #16 fila ACS, #17 prioridade, #18 ações, #19 dados, #20 acesso, #21 auditoria, #22 LGPD, #23 estrutura, #24 testes, #25 documentação, #26 deploy.

Duplicatas que preservam o escopo das originais: #27→#9, #28→#8, #29→#7, #30–#31→#6, #32–#33→#5, #34–#35→#4, #36–#37→#3, #38–#39→#2, #40–#41→#1. #42 integra evolução do módulo de documentos. Não encerrar em massa.

Requisitos novos: #43 PWA/mobile, #44 agenda/avisos, #45 revisão tripla, #46 fontes oficiais, #47 termos/dados de saúde, #48 linguagem e design. Cada cartão mantém implementação, evidência e aceite restante.

A estética deve servir à compreensão: regras e referências em docs/DESIGN_UX.md. Kanban versionado é o quadro disponível; a sincronização das colunas do GitHub Projects está pendente por falta de permissão específica de projeto.
