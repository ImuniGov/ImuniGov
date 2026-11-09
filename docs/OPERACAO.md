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

Cada profissional declara independência. Pode declarar impedimento antes de votar; após voto, exige análise administrativa preservando o histórico. Não há fluxo automático para alterar perfil já verificado. Votos são imutáveis. Uma recusa encerra a conferência com motivo e providência; três votos positivos confirmam o arquivo ou o registro específico. Arquivo conferido e dose confirmada são operações separadas.

**Migração 007:** decisões simples anteriores são reabertas para revisão tripla; os valores anteriores ficam na auditoria. Datas individuais concluídas são reavaliadas. Avaliar impacto e comunicar famílias antes de aplicar a uma instalação com dados reais. Nesta homologação os dados são sintéticos.

## Fontes do governo

`docker compose exec web python -m backend.manage sync-sources` consulta o JSON público RNDS. O worker repete a consulta diariamente. A última cópia válida é preservada em falha; resposta inválida não altera regras de vacinação. Os códigos e nomes são consultáveis em `/api/v1/vaccine-catalog` após login.

O calendário é uma regra local versionada, com fonte pública do Ministério da Saúde. O catálogo RNDS não contém recomendações individuais. O recorte automático atual é BCG/Pentavalente/VIP; datas de qualquer outra vacina podem ser definidas pela UBS. Para ampliar regras, preparar JSON compatível com `RuleSet`, conferir clinicamente fonte e intervalos, testar e executar `activate-rules ARQUIVO`. Esse comando publica versão nova e reavalia dependentes; não sobrescreve versão anterior.

## Privacidade

Texto vigente: `backend/legal/privacy-2026-11-08.json`. Responsável e contato foram informados pelo usuário: ImuniGuia, `example@unemat.bbr`. Confirmar a validade do contato antes de dados reais. Alterar o documento exige nova versão e preservação do anterior; o hash é calculado sobre os bytes versionados. Conta antiga não recebe aceite fabricado. O novo fluxo de aceite para contas antigas é pendência registrada em #47.

Solicitações da conta ficam em tabela própria e não apagam dados automaticamente. Operação administrativa:

```text
docker compose exec web python -m backend.manage privacy-requests
docker compose exec web python -m backend.manage answer-privacy --id ID --response "Resposta fundamentada ao titular"
```

O responsável deve monitorar a fila, verificar a identidade com minimização de dados e executar/validar a providência cabível. Registrar resposta não executa eliminação ou revogação por si só. Definir bases legais por operação, retenção, atendimento de direitos, comprovação de representação e resposta a incidentes antes de dados reais.

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
