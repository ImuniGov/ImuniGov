# Operação e homologação

## Executar com Docker

1. Instale Docker Desktop e inicie o serviço.
2. No PowerShell, execute `./scripts/setup.ps1`. Ele cria `.env` apenas se ainda não existir, com senha aleatória do banco.
3. Abra http://localhost:4173. PostgreSQL não publica porta externa; arquivos ficam em volume privado.
4. Consulte `docker compose ps` e `docker compose logs --tail 80 web worker migrate` se precisar diagnosticar.

A hospedagem escolhida nesta etapa é preparação Docker local. Para instalar em celular fora do computador, configure uma origem HTTPS real, `PUBLIC_ORIGIN` e `COOKIE_SECURE=true`, além de proxy TLS. Não publicar a porta diretamente como substituto de TLS. Nunca versionar `.env`, bancos, backups, arquivos de pacientes ou chaves de push.

## Contas da equipe e revisão independente

Famílias se cadastram na interface. Profissionais são criados administrativamente:

```text
docker compose exec web python -m backend.manage create-user --email profissional@dominio.br --name "Profissional" --role ubs
```

A senha é solicitada no terminal, sem argumento na linha de comando. Para ACS, use `--role acs`. Não conceder perfil da equipe pelo cadastro público.

Após conferir identificação profissional, local de nascimento e local de trabalho, registre códigos de município IBGE e referência interna da verificação:

```text
docker compose exec web python -m backend.manage verify-reviewer --email profissional@dominio.br --professional-id REGISTRO-UNICO --birth-city CODIGO_IBGE --work-city CODIGO_IBGE --verification-ref PROTOCOLO_INTERNO
```

O comando não autentica certidões nem vínculos automaticamente: a conferência é responsabilidade administrativa. São necessários três profissionais com município, UF e grupos metropolitanos/RIDE/AU compatíveis em TODAS as comparações nascimento/trabalho entre pessoas. Se não houver trio completo, o arquivo aguarda. Não flexibilizar para destravar fila. Um profissional não pode cadastrar dois perfis com o mesmo registro profissional.

Cada profissional declara independência. Pode declarar impedimento antes de votar; após voto, exige análise administrativa preservando o histórico. O comando `update-reviewer` abaixo permite alteração administrativa auditada de perfil verificado. Votos são imutáveis. Uma recusa encerra a conferência com motivo e providência; três votos positivos confirmam o arquivo ou o registro específico. Arquivo conferido e dose confirmada são operações separadas.

**Migração 007:** decisões simples anteriores são reabertas para revisão tripla; os valores anteriores ficam na auditoria. Datas individuais concluídas são reavaliadas. Avaliar impacto e comunicar famílias antes de aplicar a uma instalação com dados reais. Nesta homologação os dados são sintéticos.

## Fontes do governo

`docker compose exec web python -m backend.manage sync-sources` consulta o JSON público RNDS. O worker repete a consulta diariamente. A última cópia válida é preservada em falha; resposta inválida não altera regras de vacinação. Os códigos e nomes são consultáveis em `/api/v1/vaccine-catalog` após login.

O calendário é uma regra local versionada, com fonte pública do Ministério da Saúde (`backend/rules/routine-2026.json`, versão `PNI-2026-INFANTIL-ROTINA-v2`). O catálogo RNDS não contém recomendações individuais. O recorte automático atual contempla 23 regras do calendário básico infantil PNI: BCG, Hepatite B (ao nascer com janela máxima de 30 dias), Pentavalente (D1–D3), Poliomielite VIP (D1–D3 e reforço aos 15 meses), Pneumocócica 10-valente (D1, D2 e reforço aos 12 meses), Rotavírus humano (D1 com limite estrito de 3 meses e 15 dias; D2 com limite estrito de 7 meses e 29 dias), Meningocócica C (D1, D2 e reforço aos 12 meses), Febre amarela (9 meses e reforço aos 4 anos), Tríplice viral (12 meses e 2ª dose aos 15 meses) e Hepatite A (15 meses). Esquemas especiais (CRIE), gestantes, campanhas sazonais e esquemas de atualização individual fora da faixa pediátrica devem ser planejados diretamente pela UBS (`DosePlan`). Para ampliar regras, preparar JSON compatível com `RuleSet`, conferir clinicamente fonte e intervalos, testar e executar `activate-rules ARQUIVO`. Esse comando publica versão nova e reavalia dependentes; não sobrescreve versão anterior.

## Privacidade, retenção, representação familiar e incidentes

Texto vigente: `backend/legal/privacy-2026-11-08-v3.json`. Responsável e contato foram informados pelo usuário: ImuniGuia, `example@unemat.bbr`. **Atenção:** o endereço `example@unemat.bbr` permanece preservado exatamente como informado no termo versionado (não corrigir silenciosamente nem presumir caixa postal ativa sem confirmação institucional). Alterar o documento exige nova versão e preservação do anterior; o hash é calculado sobre os bytes versionados. Conta antiga não recebe aceite fabricado. Contas antigas ou com versão/hash anterior recebem aviso de pausa e podem dar novo aceite explícito, mantendo consulta e exportação próprias. Não se inventa aceite anterior.

### Bases legais e retenção por operação (LGPD)

- **Acompanhamento digital familiar voluntário, OCR assistido e avisos:** consentimento específico e destacado para dados pessoais sensíveis de saúde (art. 11, I e art. 14, § 1º da LGPD).
- **Conferência tripla pela equipe UBS e busca ativa ACS:** tutela da saúde por profissionais de saúde e serviços de atenção primária (art. 11, II, *f* da LGPD), restrita a titulares com autorização vigente no acompanhamento digital.
- **Retenção e expurgo em pedidos de eliminação (art. 16, I e II da LGPD):**
  - **Eliminados imediatamente com `execute-deletion`:** textos brutos extraídos por OCR (`jobs.raw_text`), sugestões candidatas `a_conferir` que nunca receberam voto profissional, documentos `pendente` sem nenhum voto nem registro decidido (incluindo remoção física do arquivo em `uploads/`), sessões ativas, inscrições Web Push e avisos internos.
  - **Conservados sob bloqueio de uso clínico ativo:** documentos que já receberam voto ou decisão de conferência, registros vacinais validados ou recusados por painel profissional e trilhas de auditoria imutáveis (`audit_events`, `privacy_acceptances`, `review_votes`, `reviewer_changes`, `review_incidents`, `review_resolutions`).

Solicitações da conta ficam em tabela própria. Pedir revogação suspende imediatamente novas atividades do acompanhamento voluntário, acesso da equipe e avisos externos; não apaga dados já armazenados. Novos resultados de OCR iniciados sob autorização anterior são descartados; após retomar, a UBS pode repetir a leitura descartada. Operação administrativa:

```text
docker compose exec web python -m backend.manage privacy-requests
docker compose exec web python -m backend.manage answer-privacy --id ID --response "Resposta fundamentada ao titular"
docker compose exec web python -m backend.manage execute-deletion --request-id ID --administrative-ref PROTOCOLO_LGPD --note "Fundamentação do expurgo e retenção legal (art. 16 LGPD)"
docker compose exec web python -m backend.manage verify-representation --dependent ID_DEPENDENTE --verification-ref PROTOCOLO_DOC --note "Certidão ou termo de guarda conferido presencialmente"
docker compose exec web python -m backend.manage security-incident --severity media --administrative-ref INC-2026-01 --summary "Resumo técnico" --scope "Escopo afetado" --mitigation "Medidas adotadas"
```

O responsável deve monitorar a fila, verificar a identidade com minimização de dados e executar/validar a providência cabível. Registrar resposta (`answer-privacy`) não executa eliminação; para pedidos do tipo `eliminacao`, use `execute-deletion`, que expurga dados acessórios não votados, conserva registros auditados sob bloqueio (art. 16 da LGPD) e marca a solicitação como `executada`. A comprovação documental de representação familiar é registrada de forma auditável por `verify-representation`. Incidentes de segurança são registrados de forma imutável na trilha de auditoria por `security-incident`.

## Verificações

```text
npm ci
npm run lint
npm run format:check
npm run test:pwa
npm run build
python -m pytest -q
ruff check backend tests scripts/check_container.py
ruff format --check backend tests scripts/check_container.py
```

`REQUIRE_OCR=1` exige Tesseract com idioma português, Poppler e fontes para os testes reais. Windows sem esses motores pula três testes; o Docker contém os motores e deve executá-los.

O script `scripts/check_container.py` usa o banco Docker com schemas temporários `qa_*` isolados e remove apenas o schema criado pelo próprio teste. Não truncar tabelas do aplicativo. O workflow `.github/workflows/quality.yml` executa frontend, backend com OCR e Docker/PostgreSQL. Consulte o resultado real no GitHub; existência do arquivo não comprova CI aprovada.

## Backup e legado

Ferramentas: `python -m backend.backup --help` e `python -m backend.manage import-legacy DIRETORIO`.

- `backend.backup create` exporta todas as 22 tabelas de negócio na versão de esquema `013`, valida a revisão Alembic (`013`) quando `alembic_version` está presente e grava no `manifest.json` a contagem de linhas, o hash do snapshot JSON e os hashes SHA-256 individuais de cada arquivo em `uploads/`.
- `backend.backup restore` aceita destinos vazios ou recém-migrados (onde a migração `011` inseriu a linha inicial `review_gate(id='roster', revision=1)`), valida compatibilidade de `schema_version` (`001`, `012` ou `013`), revisão Alembic e colunas de cada tabela, restaura em transação única e remove quaisquer arquivos extraídos caso ocorra falha de integridade ou banco.
- Testes de importação legada verificam hashes e idempotência; dependentes importados ficam sem responsável até conferência administrativa e `bind-dependent`.
- Diagrama entidade-relacionamento e decisões de modelagem: [MODELAGEM_DADOS.md](MODELAGEM_DADOS.md).

## Impedimento descoberto após voto (K18.2)

Se um profissional perceber vínculo pessoal ou conflito de interesse **depois** de já ter registrado voto no arquivo ou em uma dose, ou se a administração identificar o conflito posteriormente:

1. **Declaração pelo próprio profissional autenticado:** ao acionar `POST /api/v1/documents/{id}/impediment` após já ter votado, o sistema registra impedimento pessoal, abre ocorrência em `review_incidents`, ativa `documents.review_hold = true`, suspende confirmações derivadas daquela evidência (`documents`, `vaccinations` voltam para `a_conferir` e planos de dose automáticos vinculados são desacoplados), recalcula pendências e agenda da pessoa e notifica a família.
2. **Abertura administrativa direta:** caso a ocorrência seja reportada externamente à administração:
   ```text
   docker compose exec web python -m backend.manage report-incident --document ID_DOCUMENTO --reviewer-email profissional@dominio.br --administrative-ref PROTOCOLO --reason "Conflito ou impedimento verificado após voto"
   ```
3. **Consulta de ocorrências abertas (ou histórico completo com `--all`):**
   ```text
   docker compose exec web python -m backend.manage review-incidents
   ```
4. **Resolução administrativa e sorteio de nova equipe independente:**
   ```text
   docker compose exec web python -m backend.manage resolve-incident --incident-id ID_OCORRENCIA --administrative-ref PROTOCOLO_DECISAO --note "Avaliação administrativa concluída; nova rodada independente"
   ```
   A resolução é gravada de forma imutável em `review_resolutions`, libera `review_hold`, avança `review_round`, preserva todos os votos anteriores na auditoria (ocultando-os de novos revisores UBS enquanto a nova rodada estiver pendente) e sorteia um novo trio geograficamente independente excluindo revisores impedidos. A administração nunca aprova arquivo ou dose diretamente.

### Contratos de autorização e representação

- `POST /api/v1/privacy/accept` exige `consent`, `healthConsent` e `adultDeclaration` verdadeiros, além de `termsVersion` e `privacyHash` da referência atual. Não reativa avisos externos automaticamente.
- `GET /api/v1/me` e respostas de autenticação incluem `user.privacy` para contas de família: `current`, `withdrawn` e versão vigente.
- Cadastro e edição de pessoa exigem `representationConfirmed: true`. É declaração auditada, não comprovação automática de parentesco.
- Sem autorização vigente, novas mutações do acompanhamento são negadas. Consulta e exportação próprias e solicitações de privacidade permanecem acessíveis. O catálogo público de vacinas não envia dados da família.
- A migração 010 acrescenta controle de revogação sem fabricar aceite. Dados históricos conservados não voltam a ser usados pela equipe sem novo aceite vigente. Qualquer outra base legal de uso deve ser desenhada e informada em operação separada; não existe exceção administrativa oculta.

## Alteração ou suspensão de profissional

Use primeiro uma prévia, sem `--apply`. Informe o protocolo que identifica a conferência administrativa e o motivo:

```text
docker compose exec web python -m backend.manage update-reviewer --email profissional@dominio.br --status suspenso --verification-ref PROTOCOLO --reason "Motivo verificado"
```

A saída informa quantas conferências em andamento serão reiniciadas e quantas decisões concluídas serão preservadas, além de `expectedVersion`. Para aplicar a mesma alteração, repita os argumentos acrescentando `--apply --expected-version HASH_DA_PREVIA`. Se outro administrador alterar o perfil, a versão antiga é recusada e uma nova prévia é necessária.

Para reverificar/reativar e atualizar localidades, use `--status ativo`, `--birth-city CODIGO_IBGE`, `--work-city CODIGO_IBGE`, uma nova referência e motivo. O registro profissional original permanece único e não é trocado silenciosamente. O sistema não autentica certidões, diplomas ou vínculos empregatícios por conta própria.

Ao aplicar:

- As sessões daquele profissional são encerradas. Suspenso não entra novamente nem acessa dados clínicos por uma sessão antiga.
- Mudanças de perfil ficam em histórico imutável com os dados anteriores e posteriores, motivo, protocolo e horário.
- Casos em andamento iniciam nova rodada. Votos anteriores permanecem registrados e não contam para a nova equipe. A conferência do arquivo reinicia; doses já concluídas conservam a decisão e os três profissionais da rodada original.
- Casos concluídos não são invalidados retroativamente apenas por mudança posterior de perfil; o profissional alterado perde aquela atribuição. Se surgirem novas doses a conferir nesse arquivo, uma nova rodada é aberta antes de continuar.
- O sorteio continua exigindo trio completo e todas as restrições geográficas. Impedimentos pessoais declarados não são esquecidos ao trocar de rodada. Sem equipe elegível, aguarda.
- A família recebe aviso e pode consultar votos de rodadas anteriores e exportá-los. Uma tela antiga não pode lançar voto em rodada nova: decisões exigem `reviewRound` correspondente à tela consultada.

As alterações de equipe, atribuições e votos usam uma trava curta no banco, antes das travas de responsável/documento, em ordem consistente. Essa serialização é adequada ao MVP e deve ser medida antes de operação de grande volume. O OCR continua fora dessa trava durante a leitura; o recálculo automático trabalha uma pessoa por transação.

A migração 011 preserva atribuições e votos como rodada 1. SQLite precisa reconstruir a restrição de unicidade das atribuições; apenas durante a migração Alembic a checagem de FKs é desativada, com `foreign_key_check` ao terminar e restauração da checagem antes de devolver a conexão. Fazer backup verificado e executar migrações sem versões antigas da aplicação atendendo requisições. No PostgreSQL a restrição é alterada transacionalmente.

Referência técnica: [Alembic — migrações batch e chaves estrangeiras](https://alembic.sqlalchemy.org/en/latest/batch.html#dealing-with-referencing-foreign-keys).

## Recuperação assistida de senha

Após confirmar a titularidade da conta pelo procedimento da instituição, a administração emite um código com:

```sh
docker compose exec web python -m backend.manage emit-reset-code --email conta@exemplo.test
```

Entregue o código à pessoa titular por canal privado. Ela usa **Esqueci a senha** no login e define uma nova senha. O código vale por 30 minutos, tem uso único e substitui qualquer código anterior. A alteração encerra as sessões da conta e desativa as inscrições de avisos. Códigos de recuperação ficam fora do backup. Não há envio automático de e-mail.

No login, **Lembrar de mim** mantém a sessão neste navegador por até sete dias. A sessão padrão expira em até oito horas e usa um cookie de sessão.
