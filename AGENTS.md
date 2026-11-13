# Instruções para agentes e colaboradores

## Escopo e leitura inicial

Estas instruções valem para todo o repositório. Antes de alterar qualquer arquivo, ler [roadmap.md](roadmap.md), [KANBAN.md](KANBAN.md) e [GUIA_IA.md](GUIA_IA.md), além da issue relacionada. Conferir instruções mais específicas em subdiretórios.

Meta do projeto: integrar na branch `homologacao` o frontend de `main` e a base funcional de `teste`, evoluindo o MVP de Família, UBS e ACS sem perder contratos nem rastreabilidade.

## Obrigação: manter o kanban atualizado a cada passo

1. Antes de implementar, localizar/criar cartão com ID estável, issue, objetivo, dependências, responsável e critérios verificáveis; mover para **Em andamento**.
2. Ao terminar cada passo significativo, atualizar checklist, estado, evidência, data e próximo passo em `KANBAN.md`. Não deixar essa atualização apenas para o fim da conversa.
3. Se surgir impedimento, mover para **Bloqueado** e informar causa, trabalho já feito, dependência e ação concreta para destravar.
4. Quando pronto para revisão, mover para **Em revisão** com comandos/resultados e limitações reais.
5. Só mover para **Concluído** depois de satisfazer os critérios de aceitação e validar a entrega na branch correta. Código existente somente em outra branch ou checkbox antigo não basta.
6. Incluir a atualização de kanban no mesmo commit da etapa correspondente. Registrar resumo da transição no histórico do quadro.
7. Atualizar `roadmap.md` quando houver mudança de escopo, diagnóstico, dependência, marco ou conclusão de marco; manter `GUIA_IA.md` e README coerentes quando a execução mudar.
8. Quando houver issue/GitHub Projects associados e acesso disponível, sincronizar checklist, estado e coluna correspondentes. Preservar critérios e histórico; verificar a atualização. Se a ferramenta não suportar Projects ou faltar acesso, registrar no cartão a sincronização remota pendente. Não afirmar sincronização automática.
9. Não encerrar uma issue por entrega parcial. Antes de consolidar duplicatas #27–#41, conferir escopo e vínculos, registrar qual issue é referência e preservar rastreabilidade.
10. Não inventar evidência, execução de testes, percentual concluído ou status remoto. Registrar “não executado” e o motivo quando aplicável.

## Branches e preservação

- Trabalhar em `homologacao` para esta integração; conferir branch, status e origem antes de editar ou publicar.
- `main` e `teste` são fontes de referência desta entrega. Não sobrescrever uma com a outra.
- Não fazer merge cego: há colisões de index.html, README e configuração. Preservar frontend e contratos do protótipo e documentar a estrutura escolhida.
- Não apagar alterações alheias, banco, uploads ou histórico para resolver conflitos. Não usar push forçado.
- Commitar alterações de escopo claro; push/PR conforme a autorização da tarefa vigente.

## Regras de domínio e segurança

- Documento `aprovado` significa arquivo conferido; não significa dose confirmada.
- OCR gera candidato `a_conferir`; só profissional autorizado valida/recusa registro vacinal.
- Autorização deve ser aplicada no servidor por perfil e objeto. Família acessa seus vínculos; UBS revisa conforme atribuição; ACS recebe dados mínimos de busca ativa.
- Preservar contratos existentes ou oferecer migração/alias documentados. Identidade autenticada deve substituir o campo reviewer autodeclarado sem confiar no cliente.
- Preservar integridade e hashes ao migrar SQLite e arquivos. Armazenamento privado continua exigindo autorização de download.
- Não versionar dados pessoais, documentos reais, banco, uploads, segredos ou credenciais. Usar dados sintéticos nas verificações.
- Regras vacinais devem ter fonte e versão verificadas quando implementadas; cálculo indica possíveis pendências, sujeito à conferência profissional.

## Qualidade e entrega

Executar verificações proporcionais à mudança e registrar resultado no cartão. Alterações funcionais exigem testes dos critérios afetados, incluindo negativas de acesso quando pertinente. Documentação exige conferir links, IDs, cobertura de issues e consistência entre os arquivos.

Não anunciar build ou testes como aprovados se não foram executados. Relatar branch, arquivos/funcionalidade entregues, validação, limitações e próximo cartão. O guia explica os comandos atuais e as lacunas conhecidas.

## Requisitos confirmados nesta evolução

- Revisão exige três profissionais distintos sorteados. Cruzar nascimento e trabalho de cada pessoa com ambos os locais das outras: município, UF e RM/RIDE/AU. Sem trio elegível, aguardar sem relaxar a regra. Não alegar que geografia comprova ausência de vínculo pessoal.
- Uma recusa deve mostrar à família motivo, providência, profissional e data. Não apagar o arquivo anterior para reenviar.
- Catálogos públicos do governo e regras clínicas são fontes diferentes. Preservar URL, versão, hash e cópia válida; nunca ativar regra clínica pelo simples download de terminologia.
- Manter termos e autorização de dados de saúde separados, desmarcados e versionados. Não fabricar aceite de contas antigas nem afirmar execução de revogação apenas porque um pedido foi recebido.
- Interface deve usar linguagem familiar com precisão clínica, hierarquia orientada à tarefa e decoração com finalidade. Consultar docs/DESIGN_UX.md antes de acrescentar componentes, textos ou novos padrões visuais.
