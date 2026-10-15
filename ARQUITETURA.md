# Arquitetura do módulo de documentos

## Objetivo e escopo

Este documento registra a arquitetura da implementação inicial do fluxo de envio, consulta e revisão de arquivos de cadernetas do ImuniGuia. A versão atual foi construída para a entrega da atividade acadêmica. A interface é temporária e será substituída. As APIs e as regras de negócio do fluxo são a base que será reaproveitada.

A implementação atual não tem autenticação nem autorização por perfil. Portanto, serve para desenvolvimento local e demonstração do fluxo, não para armazenar documentos reais nem para publicação em rede.

## Stack atual

| Camada | Tecnologia atual | Responsabilidade |
| --- | --- | --- |
| Interface | HTML, CSS e JavaScript sem framework | Cadastro simples de dependentes, envio de arquivo, fila e ações de revisão em uma página. |
| API e aplicação | Python 3, biblioteca padrão (`http.server`) | Endpoints HTTP, validação de entrada e arquivo, regras de estado e coordenação da persistência. |
| Banco relacional | SQLite | Dependentes, metadados de documentos, estado da revisão e eventos de auditoria. |
| Arquivos | Sistema de arquivos local em `data/uploads` | Conteúdo enviado, com nome interno aleatório; os arquivos ficam fora da pasta pública. |
| Execução local | Python instalado e `INICIAR_IMUNIGUIA.bat` no Windows | Inicialização do servidor em `127.0.0.1:4173`. |

Não há dependências Python externas nesta versão. Docker não é necessário para executar o módulo localmente. Um `Dockerfile` ou `docker-compose` só deve ser introduzido quando facilitar um ambiente compartilhado, integração contínua ou implantação reproduzível.

## Organização lógica

```text
Navegador
  ├─ Interface temporária (HTML/CSS/JavaScript)
  └─ HTTP/REST
       └─ API Python
            ├─ validação e regras do fluxo
            ├─ SQLite
            └─ armazenamento privado de arquivos
```

A interface consome URLs próprias da API. Isso permite trocá-la por outra interface sem reimplementar o fluxo de upload, consulta, decisão e auditoria. Na evolução, convém separar os handlers HTTP, os serviços/regras de negócio, os repositórios de dados e o armazenamento de arquivos em módulos próprios, preservando os contratos descritos abaixo.

## API atual e contratos a preservar

| Método e rota | Uso |
| --- | --- |
| `GET /api/health` | Verificar disponibilidade do serviço. |
| `GET /api/dependents` | Listar dependentes. |
| `POST /api/dependents` | Cadastrar dependente com `name`. |
| `DELETE /api/dependents/{id}` | Remover dependente sem documentos associados. |
| `GET /api/documents?status={status}` | Listar documentos, opcionalmente filtrados por `pendente`, `aprovado` ou `rejeitado`. |
| `POST /api/documents` | Receber `multipart/form-data` com `dependentId`, `vaccine`, `doseDate`, `note` e `file`. |
| `GET /api/documents/{id}` | Consultar metadados e estado do documento. |
| `GET /api/documents/{id}/file` | Obter o arquivo associado. |
| `POST /api/documents/{id}/decision` | Registrar `decision`, `reviewer` e `note`; decisão é `aprovado` ou `rejeitado`. |
| `GET /api/audit?documentId={id}` | Consultar eventos do documento. |

As respostas usam JSON, com objetos `item` para registros individuais e `items` para coleções. Mudanças incompatíveis nesses caminhos, nomes de campos ou estados devem ser feitas com migração planejada ou versionamento da API, para que a interface futura continue consumindo o módulo.

## Modelo de dados atual

- **`dependents`**: `id`, `name`, `created_at`.
- **`documents`**: dependente associado, nomes original e interno do arquivo, tipo, tamanho, SHA-256, vacina/registro, data informada, observação, estado, orientação da revisão, revisor informado e datas de envio e decisão.
- **`audit_events`**: documento associado, evento, detalhes e data/hora.

Relações principais: um dependente pode ter vários documentos; cada documento pertence a um dependente e pode ter vários eventos de auditoria. Os estados usados pela API são `pendente`, `aprovado` e `rejeitado`. A decisão só registra a conferência do arquivo; não cria nem altera o histórico vacinal oficial.

## O que será reaproveitado

1. **Contrato REST**: rotas, campos, formatos de resposta e estados do fluxo serão mantidos para a nova interface. Alterações incompatíveis exigem versionamento/migração.
2. **Regras do fluxo**: associação ao dependente, upload pendente, decisão de aprovação/devolução com justificativa, atualização do estado e trilha de auditoria continuam como comportamento de negócio.
3. **Validações de arquivo**: limite atual de 10 MB, verificação básica da assinatura do conteúdo, nome interno aleatório e hash SHA-256 são a base para controles mais fortes.
4. **Modelo conceitual**: dependentes, documentos e eventos de auditoria permanecem como entidades. A estrutura física poderá ser migrada do SQLite para PostgreSQL sem descartar os dados ou relações.
5. **Separação entre metadados e conteúdo**: a API continuará servindo os arquivos por identificador, sem expor o caminho interno. O armazenamento local poderá ser substituído por armazenamento privado de objetos, mantendo a API.

O reaproveitamento é funcional e contratual: as regras e o contrato da API devem continuar atendendo ao fluxo. O código atual está concentrado em `server.py`; ele pode ser reorganizado e reforçado, mas não se deve recomeçar o módulo ignorando esses contratos e regras.

## Itens ainda no backlog

- Autenticação e autorização por perfil, com identidade confiável do revisor e controle de acesso aos dependentes e documentos.
- Reforço de segurança das APIs e do armazenamento, incluindo proteção contra abuso, política de retenção e controles apropriados para publicação.
- Interface definitiva, substituindo a página atual e consumindo as APIs existentes.
- OCR, dados extraídos e cálculo de possíveis pendências, que não fazem parte da implementação atual.
- Testes automatizados e documentação formal do contrato da API.
- Avaliação de FastAPI (ou framework equivalente), PostgreSQL e Docker quando o ambiente de implantação justificar essa evolução; a migração deve preservar as regras e o contrato do módulo.

O acompanhamento desses próximos passos está na [issue #42](https://github.com/EduFlauzino/ImuniGov/issues/42).
