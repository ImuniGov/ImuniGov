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

O calendário é uma regra local versionada, com fonte pública do Ministério da Saúde. O catálogo RNDS não contém recomendações individuais. O recorte automático atual é BCG/Pentavalente/VIP; datas de qualquer outra vacina podem ser definidas pela UBS. Para ampliar regras, preparar JSON compatível com `RuleSet`, conferir clinicamente fonte e intervalos, testar e executar `activate-rules ARQUIVO`. Esse comando publica versão nova e reavalia dependentes; não sobrescreve versão anterior.

## Privacidade

Texto vigente: `backend/legal/privacy-2026-11-08-v3.json`. Responsável e contato foram informados pelo usuário: ImuniGuia, `example@unemat.bbr`. Confirmar a validade do contato antes de dados reais. Alterar o documento exige nova versão e preservação do anterior; o hash é calculado sobre os bytes versionados. Conta antiga não recebe aceite fabricado. Contas antigas ou com versão/hash anterior recebem aviso de pausa e podem dar novo aceite explícito, mantendo consulta e exportação próprias. Não se inventa aceite anterior.

Solicitações da conta ficam em tabela própria. Pedir revogação suspende imediatamente novas atividades do acompanhamento voluntário, acesso da equipe e avisos externos; não apaga dados já armazenados. Novos resultados de OCR iniciados sob autorização anterior são descartados; após retomar, a UBS pode repetir a leitura descartada. Um aviso genérico já em trânsito pode não ser cancelável. Operação administrativa:

```text
docker compose exec web python -m backend.manage privacy-requests
docker compose exec web python -m backend.manage answer-privacy --id ID --response "Resposta fundamentada ao titular"
```

O responsável deve monitorar a fila, verificar a identidade com minimização de dados e executar/validar a providência cabível. Registrar resposta não executa eliminação. A revogação já foi aplicada pelo pedido, e só novo aceite da própria família retoma o acompanhamento. Definir bases legais por operação, retenção, atendimento de direitos, comprovação de representação e resposta a incidentes antes de dados reais.

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

Ferramentas: `python -m backend.backup --help` e `python -m backend.manage import-legacy DIRETORIO`. Testes de importação verificam hashes e idempotência; dependentes importados ficam sem responsável até conferência administrativa e `bind-dependent`. Não assumir que teste sintético de SQLite cobre restauração operacional completa do PostgreSQL. Definir e testar backup de banco e volume de arquivos antes de operação real.

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
