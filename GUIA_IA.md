# Guia de continuidade para IA

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

1. CI do código 57f4e3c já passou em frontend, backend e Docker/PostgreSQL (execução 42551947165). Não repetir testes aprovados sem mudança ou falha; verificar os checks dos próximos commits funcionais.
2. Fechar lacunas de K18/#45: mudança/reatribuição de perfil profissional, confirmação administrativa de documentos e revisão de concorrência/homologação por três contas.
3. Fechar K20/#47: aceite de nova versão e suspensão por revogação implementados; execução monitorada de pedidos de eliminação, comprovação de representação, canal e retenção reais. A revogação suspende o processamento voluntário, novos acessos da equipe e avisos externos; resultados OCR anteriores à interrupção são descartados mesmo se houver novo aceite durante a leitura. Consulta/exportação própria continua disponível. Eliminação e retenção ainda exigem procedimento administrativo.
4. Revisão clínica das regras, ampliação explícita da cobertura e testes de vacinas/condições especiais. Não usar dados agregados de doses aplicadas como calendário.
5. Continuar revisão acessível com usuários e aparelhos reais. Ler docs/DESIGN_UX.md; preservar linguagem simples, precisão clínica, padrões e hierarquia funcional.
6. Operação: backup/restauração PostgreSQL+arquivos, implantação HTTPS quando houver hospedagem, teste de push real opt-in. Não publicar ou contratar serviço não solicitado.

## Verificação

Comandos e fluxos administrativos em docs/OPERACAO.md. Testes SQLite usam diretórios temporários; PostgreSQL usa schemas temporários próprios, nunca tabelas do aplicativo. OCR real deve rodar no Docker com `REQUIRE_OCR=1`. Não versionar dados pessoais, credenciais, `.env`, volume ou arquivos sintéticos privados usados no navegador.

Atualizar KANBAN.md no mesmo commit. Issues novas #43–#48 representam requisitos posteriores ao diagnóstico. Duplicatas #27–#41 devem manter referência às originais; não encerrar automaticamente. GitHub Projects exige permissão de projeto ausente no acesso atual: não declarar colunas remotas atualizadas. REST de issues e push autenticado funcionam. Não imprimir tokens do gerenciador de credenciais.
