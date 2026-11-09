# Guia de continuidade para IA

> **Estado vigente da auditoria:** meta de implementação pausada pelo usuário. Não retomar desenvolvimento automaticamente. Lista completa em [docs/STATUS_ENTREGA.md](docs/STATUS_ENTREGA.md): 29 issues concluídas pelo respectivo escopo e 20 abertas, incluindo #49 (restauração falha em banco migrado). K18.2 tem somente rascunho de esquema/migração 012, sem fluxo implementado. As prioridades abaixo são para quando houver retomada. Docker local está entregue; HTTPS público, aparelhos reais, operação de privacidade, cobertura clínica ampliada e acessibilidade/usabilidade ainda precisam de validação. Estados e labels das 49 issues conferidos por nova leitura; CI 92f75f9 aprovada nos três jobs (execução 42558280959). Registro em KANBAN.md.

Atualizado em 2026-11-08 (America/Cuiaba). Ler AGENTS.md, roadmap.md e KANBAN.md antes de trabalhar. A branch de entrega é `homologacao`; `main` e `teste` são referências históricas. O diagnóstico inicial está nos commits anteriores, especialmente f6dd262.

## Estado técnico

- React 19/Vite, JSX, CSS responsivo, PWA com cache apenas público. Não inventar fontes TypeScript existentes.
- FastAPI/Pydantic, SQLAlchemy Core, Alembic, PostgreSQL no Docker e SQLite em testes locais.
- Worker SQL persistente, OCR Tesseract por/eng e Poppler. Falha legível permite transcrição manual.
- Sessão opaca com cookie HttpOnly/SameSite, Argon2, CSRF, rate limit, autorização no servidor. Staff só por administração.
- Documento `pendente/aprovado/rejeitado`; dose `a_conferir/validado/recusado`. Não confluir estados.
- Três revisores sorteados com todas as comparações nascimento/trabalho de município/UF/RM/RIDE/AU, usando catálogo IBGE versionado. Perfis exigem verificação administrativa. Geografia não prova desconhecimento pessoal; declaração e impedimento complementam o fluxo.
- Votos, auditoria e aceites são rastreáveis; votos e aceites não podem ser fabricados. Legado de revisão simples é reaberto na migração 007, preservando decisões na auditoria.
- RNDS público fornece terminologia de vacinas, não recomendação individual. Worker consulta diariamente; falha preserva última cópia. Regras clínicas não são ativadas por download automático.
- Rotina automática limitada a BCG/Pentavalente/VIP. Datas individualizadas UBS cobrem outras vacinas. Não afirmar cobertura integral do PNI ou prontuário oficial RNDS.

## Próxima ordem de trabalho

1. CI mais recente do código d4e1757 passou em frontend, backend e Docker/PostgreSQL (execução 42555673454), com 49 testes Docker. Não repetir testes aprovados sem mudança ou falha; verificar os checks dos próximos commits funcionais.
2. Fechar lacunas de K18/#45: alteração/suspensão e reatribuição por rodadas implementadas, com prévia/versionamento, votos preservados e concorrência testada. Três contas fictícias homologadas no navegador (arquivo e dose), inclusive preservação de voto anterior após nova rodada. Continuar K18.2: impedimento posterior ao voto por caso, sem alterar artificialmente perfil; manter procedimento humano de verificação documental.
3. Fechar K20/#47: aceite de nova versão e suspensão por revogação implementados; execução monitorada de pedidos de eliminação, comprovação de representação, canal e retenção reais. A revogação suspende o processamento voluntário, novos acessos da equipe e avisos externos; resultados OCR anteriores à interrupção são descartados mesmo se houver novo aceite durante a leitura. Consulta/exportação própria continua disponível. Eliminação e retenção ainda exigem procedimento administrativo.
4. Revisão clínica das regras, ampliação explícita da cobertura e testes de vacinas/condições especiais. Não usar dados agregados de doses aplicadas como calendário.
5. Continuar revisão acessível com usuários e aparelhos reais. Ler docs/DESIGN_UX.md; preservar linguagem simples, precisão clínica, padrões e hierarquia funcional.
6. Operação: backup/restauração PostgreSQL+arquivos, implantação HTTPS quando houver hospedagem, teste de push real opt-in. Não publicar ou contratar serviço não solicitado.

## Verificação

Comandos e fluxos administrativos em docs/OPERACAO.md. Testes SQLite usam diretórios temporários; PostgreSQL usa schemas temporários próprios, nunca tabelas do aplicativo. OCR real deve rodar no Docker com `REQUIRE_OCR=1`. Não versionar dados pessoais, credenciais, `.env`, volume ou arquivos sintéticos privados usados no navegador.

Atualizar KANBAN.md no mesmo commit. Issues novas #43–#48 representam requisitos posteriores ao diagnóstico. Duplicatas #27–#41 devem manter referência às originais; não encerrar automaticamente. GitHub Projects exige permissão de projeto ausente no acesso atual: não declarar colunas remotas atualizadas. REST de issues e push autenticado funcionam. Não imprimir tokens do gerenciador de credenciais.
