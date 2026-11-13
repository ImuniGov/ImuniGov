# ImuniGuia

Aplicativo de acompanhamento de vacinação para famílias, UBS e agentes comunitários. Integração na branch **homologacao**, com interface mobile e PWA, API privada, PostgreSQL e execução local com Docker.

## Executar

Com Docker Desktop iniciado, no PowerShell:

```powershell
./scripts/setup.ps1
```

Abra http://localhost:4173. O script gera configuração local com senha aleatória do banco. Não envie `.env`, documentos ou bancos ao GitHub. Para funcionamento instalável em celular fora do computador, a implantação precisa de origem HTTPS real.

## Fluxos disponíveis

- **Família:** conta própria, pessoas da família, prévia e envio de foto/PDF, andamento da conferência, retorno da UBS com motivo e providência, registros, orientações, próximas doses e avisos privados.
- **UBS:** conta administrativa e perfil profissional verificado; sorteio de três profissionais com separação geográfica cruzada; conferência do arquivo e de cada dose com contexto de pendências vinculadas; recusa justificada, impedimentos antes ou após voto (com suspensão automática e abertura administrativa de nova rodada independente), transcrição manual, orientações identificadas com nome do profissional e datas individuais.
- **ACS:** lista de famílias para contato, prioridade, registro de ações e histórico preservado, sem acesso ao arquivo clínico.
- **Privacidade:** termos e autorização específica no cadastro, versão/hash e horário registrados, exportação própria, canal e solicitações de direitos na conta, além de comandos administrativos de comprovação documental de representação familiar, execução auditada de eliminação/retenção (art. 16 da LGPD) e registro imutável de incidentes de segurança.

OCR é leitura automática assistida: gera informação **a conferir** e nunca confirma doses. Três aprovações independentes são exigidas; uma recusa devolve o motivo e a próxima providência. Sem trio elegível, aguarda sem relaxar restrições. Distância geográfica não prova ausência de relacionamento pessoal.

## Fontes e limites

Catálogo de vacinas consultado no [FHIR público da RNDS](https://fhir.saude.gov.br/ria/pt-BR/CodeSystem-BRImunobiologico.json), com versão, hash, atualização diária e última cópia válida. As datas de rotina usam regras locais versionadas vinculadas à instrução oficial do Ministério da Saúde (`PNI-2026-INFANTIL-ROTINA-v2`). O recorte automático atual cobre o calendário básico infantil PNI (**BCG, Hepatite B ao nascer, Pentavalente, Poliomielite VIP, Pneumocócica 10-valente, Rotavírus humano com limite etário estrito, Meningocócica C, Febre amarela, Tríplice viral e Hepatite A**); esquemas especiais (CRIE), gestantes e outras vacinas podem ser planejados individualmente pela UBS. Ausência de aviso não comprova vacinação completa. Não há consulta ao histórico pessoal da RNDS.

Esta é uma versão de homologação com dados fictícios. Antes de dados reais: concluir revisão clínica e jurídico-operacional, validar representação de familiares, retenção, canal informado de privacidade e plano de backup/incident response. Avisos externos são opcionais e dependem do aparelho, conexão e permissão.

## Documentação

- [Kanban e pendências verificáveis](KANBAN.md)
- [Lista completa de pendências e estado das issues](docs/STATUS_ENTREGA.md)
- [Roadmap e marcos](roadmap.md)
- [Guia de continuidade para IA](GUIA_IA.md)
- [Operação, equipe, migrações e testes](docs/OPERACAO.md)
- [Modelagem de dados e diagrama ER](docs/MODELAGEM_DADOS.md)
- [Decisões de UI/UX e referências](docs/DESIGN_UX.md)
- [Instruções obrigatórias de colaboração](AGENTS.md)

Interface e documentação da API: http://localhost:4173/api/docs (aplicativo local iniciado).
