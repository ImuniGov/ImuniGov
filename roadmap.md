# Roadmap do ImuniGuia

> **Estado vigente (2026-11-11):** desenvolvimento retomado por solicitação explícita do usuário na branch `homologacao`. Todas as pendências técnicas de código, testes e documentação listadas em [docs/STATUS_ENTREGA.md](docs/STATUS_ENTREGA.md) (`K02`, `K02.1`, `K06`, `K08`, `K09.1`, `K18.2`, `K19/K07`, `K05/K20`, `K21`) foram implementadas e verificadas localmente (51 testes Python/SQLite aprovados e 3 OCR pulados no Windows sem motores locais, 4 testes PWA aprovados, lint e build aprovados). Restam validações externas/humanas que dependem de ambiente e equipe real: ensaio em aparelhos físicos Android/iPhone com HTTPS público (`#1/#40/#41/#43/#44`), confirmação institucional da caixa postal `example@unemat.bbr` (`#47`), homologação clínica/humana com profissionais e cidadãos (`#45/#46/#48`) e escopo `project` no token do GitHub Projects.

Atualizado: 2026-11-11 (America/Cuiaba). Entrega em `homologacao`. O usuário escolheu execução Docker; hospedagem pública ainda não foi definida.

## Base e resultado atual

`main` em 080b34c possuía configuração React sem os fontes de `src`; `teste` em 025fbed forneceu o protótipo Python/SQLite. A integração reconstruiu a interface e preservou os contratos úteis, acrescentando autenticação e autorização. O levantamento inicial e o quadro anterior permanecem no histórico do Git. Não tratar aquele diagnóstico como descrição atual.

| Marco | Implementado | Aceite restante |
| --- | --- | --- |
| M0 — diagnóstico (#23, #25, #42) | Roadmap, kanban, guia e AGENTS.md | Manter documentação e issues sincronizadas. |
| M1 — base e dados (#19, #23, #49) | React/FastAPI, PostgreSQL/Alembic, DER em `docs/MODELAGEM_DADOS.md`, backup/restauração compatível com `review_gate` e esquema `012` | Ensaio operacional em banco PostgreSQL de produção quando houver hospedagem. |
| M2 — acesso e família (#2–#4, #20–#22, #47) | Conta de família, sessão, perfis, pessoas, exportação, reaceite, `verify-representation`, `execute-deletion` (art. 16 LGPD) e `security-incident` | Confirmar funcionamento real da caixa `example@unemat.bbr` e operação humana de atendimento. |
| M3 — cadernetas (#1, #13, #14, #42) | Foto/PDF, prévia, OCR, arquivo privado, revisão com contexto de pendências (#13) e auditoria | Validar envio/câmera em aparelhos Android e iPhone reais (#1/#40/#41/#43). |
| M4 — regras e registros (#5–#10, #27–#35, #46) | Leitura assistida ampliada (10 vacinas PNI e sinônimos), histórico, motor versionado `PNI-2026-INFANTIL-ROTINA-v2` (23 regras), separação de pendências abertas e histórico resolvido (#8/#10/#28) | Homologação clínica presencial e amostras reais autorizadas. |
| M5 — UBS (#12–#15, #45) | Decisões separadas por arquivo/dose, motivos, providências, orientações com nome do profissional (#15), datas e fluxo completo de impedimento pós-voto (`K18.2` / #45) | Verificação documental humana do quadro de profissionais. |
| M6 — ACS (#16–#18) | Busca ativa por pessoa, prioridade, ações e histórico | Teste de usabilidade com agentes e equipe responsável. |
| M7 — acompanhamento (#11, #43, #44) | Agenda familiar, avisos, push opt-in, mobile/PWA | Aparelhos reais, HTTPS externo e entrega push externa. |
| M8 — qualidade e operação (#24–#26, #49) | Testes automatizados (51 SQLite + 4 PWA locais; 3 OCR exigem Docker/CI), Docker, CI e guias operacionais | Hospedagem HTTPS pública quando definida. |
| M9 — revisão independente e experiência (#45–#48) | Trio sorteado, impedimento pós-voto (`K18.2`), RNDS público, termos/execução LGPD, retorno à família e UI revisada com semântica ARIA | Testes moderados com cidadãos/UBS/ACS em aparelhos reais. |
| M10 — navegação e telas móveis (K21.1, #43–#45, #48) | URLs por perfil, calendário mensal da família, conferência por etapas e guia de contatos do ACS | Validar com usuários e aparelhos físicos na homologação. |

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
