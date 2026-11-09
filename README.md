# ImuniGuia

Projeto de apoio ao acompanhamento vacinal: a família envia a caderneta, a UBS confere evidências e registros e o ACS acompanha os casos de busca ativa. OCR e regras automáticas devem produzir informações a conferir e possíveis pendências; a confirmação depende de profissional autorizado.

## Planejamento e continuidade

- [Roadmap e diagnóstico das branches](roadmap.md): o que existe, o que falta, marcos e rastreabilidade das 42 issues.
- [Kanban versionado](KANBAN.md): trabalho atual, dependências, evidências e próximos passos.
- [Guia para IA](GUIA_IA.md): como retomar, preservar contratos e verificar cada entrega.
- [Instruções do projeto](AGENTS.md): obrigação de atualizar o kanban em cada etapa.

## Estado da homologacao

Esta branch nasce da main 080b34c e adiciona planejamento. A configuração do frontend usa React e Vite, mas os fontes de src/main.jsx e o favicon referidos no HTML estão ausentes na revisão analisada. O primeiro cartão, K01, trata da recuperação e integração.

A branch [teste](https://github.com/ImuniGov/ImuniGov/tree/025fbed4d44e6ab48b982b0a9973fe78e34acd09) contém o protótipo local funcional de dependentes, upload, fila, decisão e auditoria, em Python/SQLite, com interface temporária e Docker. Esse código ainda precisa ser integrado. O protótipo não tem autenticação; arquivo aprovado não equivale a dose confirmada.

Stack alvo documentada em teste: React/TypeScript, FastAPI, PostgreSQL, armazenamento privado e processamento assíncrono. Isso descreve o destino planejado, não a implementação disponível nesta branch.

## Desenvolvimento

Depois de recuperar os fontes ausentes:

```powershell
npm ci
npm run lint
npm run build
npm run dev
```

O Vite está configurado para porta 3000. Não há script de testes no package.json consultado. O build não foi executado nesta entrega de documentação. Para executar o protótipo em um checkout de teste, consultar as instruções de Python/Docker no [GUIA_IA.md](GUIA_IA.md) e no README daquela branch.

## Contribuição

Ler AGENTS.md, escolher o próximo cartão disponível, conferir sua issue e atualizar KANBAN.md antes de implementar e a cada avanço. Registrar validação e trabalho restante no mesmo commit da etapa. Não concluir issues parciais nem consolidar duplicatas sem conferir escopo e vínculos.
