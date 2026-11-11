# Guia de continuidade para IA

> **Estado vigente (2026-11-11):** desenvolvimento retomado por solicitação explícita do usuário na branch `homologacao`. Todas as entregas de código, testes e documentação listadas em [docs/STATUS_ENTREGA.md](docs/STATUS_ENTREGA.md) (`K02`, `K02.1`, `K06`, `K08`, `K09.1`, `K18.2`, `K19/K07`, `K05/K20`, `K21`) foram concluídas ou colocadas em revisão final com evidência local (51 testes Python/SQLite aprovados e 3 OCR pulados no Windows sem motores locais, 4 testes PWA aprovados, lint e build Vite aprovados). Registro completo em [KANBAN.md](KANBAN.md).

Atualizado em 2026-11-11 (America/Cuiaba). Ler AGENTS.md, roadmap.md e KANBAN.md antes de trabalhar. A branch de entrega é `homologacao`; `main` e `teste` são referências históricas. O diagnóstico inicial está nos commits anteriores, especialmente f6dd262.

## Estado técnico

- React 19/Vite, JSX, CSS responsivo, PWA com cache apenas público. Não inventar fontes TypeScript existentes.
- FastAPI/Pydantic, SQLAlchemy Core, Alembic (revisão `012`), PostgreSQL no Docker e SQLite em testes locais. Diagrama ER em `docs/MODELAGEM_DADOS.md`.
- Worker SQL persistente, OCR Tesseract por/eng e Poppler. Falha legível permite transcrição manual.
- Sessão opaca com cookie HttpOnly/SameSite, Argon2, CSRF, rate limit, autorização no servidor. Staff só por administração.
- Documento `pendente/aprovado/rejeitado`; dose `a_conferir/validado/recusado`. Não confluir estados.
- Três revisores sorteados com todas as comparações nascimento/trabalho de município/UF/RM/RIDE/AU, usando catálogo IBGE versionado. Perfis exigem verificação administrativa. Geografia não prova desconhecimento pessoal; declaração e impedimento complementam o fluxo.
- Impedimento descoberto após voto (`K18.2`): `POST /api/v1/documents/{id}/impediment` ou `backend.manage report-incident` abre ocorrência imutável em `review_incidents`, suspende a caderneta (`documents.review_hold = true`), reverte confirmações derivadas da evidência contaminada para `a_conferir`, recalcula pendências/agenda e aguarda `backend.manage resolve-incident`, que registra `review_resolutions` e abre nova rodada independente sem aprovar doses administrativamente.
- Votos, auditoria, aceites, mudanças de perfil, incidentes e resoluções de revisão são imutáveis (triggers append-only).
- RNDS público fornece terminologia de vacinas, não recomendação individual. Worker consulta diariamente; falha preserva última cópia. Regras clínicas não são ativadas por download automático.
- Rotina automática versionada em `backend/rules/routine-2026.json` (`PNI-2026-INFANTIL-ROTINA-v2`, 23 regras cobrindo BCG, Hepatite B, Pentavalente, Poliomielite VIP, Pneumocócica 10, Rotavírus humano com limite etário superior estrito, Meningocócica C, Febre amarela, Tríplice viral e Hepatite A). Datas individualizadas UBS (`DosePlan`) cobrem outras vacinas e esquemas especiais.
- Operação LGPD (`backend/manage.py`): `verify-representation`, `execute-deletion` (expurgo de textos OCR, candidatos não votados e arquivos sem vínculo; retenção sob bloqueio de registros clínicos auditados conforme art. 16 da LGPD) e `security-incident`.

## Próxima ordem de trabalho (validações externas/humanas)

1. Verificar execução da CI remota (GitHub Actions) com Docker/PostgreSQL e `REQUIRE_OCR=1` após push na branch `homologacao`.
2. Quando houver ambiente HTTPS público, validar instalação PWA, câmera, envio de foto/PDF, navegação offline e entrega real de Web Push em aparelhos físicos Android e iPhone (`#1/#40/#41/#43/#44`).
3. Confirmar institucionalmente a recepção de mensagens na caixa `example@unemat.bbr` informada pelo usuário (`#47`), sem alterar o endereço silenciosamente.
4. Executar verificação documental presencial de profissionais (`#45/#47`), revisão clínica formal das regras (`#46`) e testes moderados de usabilidade/acessibilidade com cidadãos, equipe UBS e ACS (`#48`).
5. Sincronizar colunas do GitHub Projects quando houver token com escopo `read:project`/`project`.

## Verificação

Comandos e fluxos administrativos em docs/OPERACAO.md. Testes SQLite usam diretórios temporários; PostgreSQL usa schemas temporários próprios, nunca tabelas do aplicativo. OCR real deve rodar no Docker com `REQUIRE_OCR=1`. Não versionar dados pessoais, credenciais, `.env`, volume ou arquivos sintéticos privados usados no navegador.

Atualizar KANBAN.md no mesmo commit. Issues novas #43–#48 representam requisitos posteriores ao diagnóstico. Duplicatas #27–#41 devem manter referência às originais; não encerrar automaticamente. GitHub Projects exige permissão de projeto ausente no acesso atual: não declarar colunas remotas atualizadas. REST de issues e push autenticado funcionam. Não imprimir tokens do gerenciador de credenciais.
