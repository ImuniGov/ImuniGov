# Revisão de interface e linguagem

Data: 2026-11-08, America/Cuiaba. Escopo: Família, UBS, ACS, cadastro, agenda, avisos e privacidade. Cartão K21, issue #48. A revisão preserva estados e regras clínicas; mudanças de revisão tripla e LGPD são requisitos próprios (K18 e K20).

## Diagnóstico e direção

A interface anterior usava chamadas abstratas de cuidado, ilustração de caderneta sem interação, quatro estatísticas com ícones coloridos, textos pequenos e muitos blocos com a mesma ênfase. A visão vazia da UBS ainda oferecia cadastro de familiar, ação exclusiva da família. Essas escolhas dificultavam encontrar a próxima ação e distinguir conferência do arquivo de confirmação de uma dose.

A direção escolhida é um serviço de acompanhamento: navegação estável, superfícies neutras, verde reservado à ação e à seleção, títulos informativos, espaço entre grupos e listas de informação. Não se copia a identidade do NHS ou do governo brasileiro nem se sugere vínculo institucional.

## Pesquisa e aplicação

| Fonte consultada | Princípio identificado | Influência na implementação |
| --- | --- | --- |
| [Nielsen Norman Group — 10 heurísticas](https://www.nngroup.com/articles/ten-usability-heuristics/) | Linguagem familiar, estado visível, reconhecimento, prevenção de erro e minimalismo | Chamadas indicam a tarefa; status escrito acompanha a cor; os votos e a espera pela equipe são explícitos; original do arquivo permanece disponível. |
| [W3C — WCAG 2.2, tamanho de alvo](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html) | Alvos de toque e espaçamento adequados | Ações principais e controles com ícone têm pelo menos 44px; links de texto corrido seguem tratamento próprio. 44px é meta do produto, superior ao mínimo AA de 24px com exceções. |
| [W3C — contraste mínimo](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) | Texto legível, sem depender apenas de cor | Tons secundários mais escuros, avisos com texto, foco visível e tipografia de sistema. Não equivale a auditoria completa WCAG. |
| [CDC — linguagem simples em saúde](https://www.cdc.gov/health-literacy/php/develop-materials/plain-language.html) | Preferir palavras cotidianas e ações compreensíveis | “Vacinas registradas”, “O que fazer agora”, “Digitar uma dose do arquivo”; frases curtas com sujeito e ação. |
| [NHS — como escrever](https://service-manual.nhs.uk/content/how-we-write) | Conteúdo preciso, neutro e termos técnicos explicados | Retirada de metáforas e slogans; incerteza preservada; confirmar arquivo nunca significa confirmar dose. Informações clínicas ainda exigem revisão profissional. |
| [NHS — interface de detalhes](https://service-manual.nhs.uk/design-system/components/details) | Mostrar detalhes adicionais quando necessários | Explicação do cálculo da agenda, transcrição manual, auditoria e solicitações de dados usam detalhes expansíveis. Motivos de recusa e providências continuam expostos. |
| [GOV.UK — conferir respostas](https://design-system.service.gov.uk/patterns/check-answers/) | Permitir conferir antes de enviar | Prévia do arquivo preservada; motivo e providência separados na decisão; aceites distintos do envio. |
| [Ministério da Saúde — Calendário Nacional](https://www.gov.br/saude/pt-br/vacinacao/calendario) | Diferenciar esquema recomendado, idade e dose | Nomes das vacinas preservados; “próxima dose” não é “validade da vacina”; fonte e cobertura limitada da agenda ficam disponíveis. |

As referências de saúde são institucionais. NN/g orienta usabilidade; W3C orienta acessibilidade; CDC e NHS orientam comunicação; os design systems orientam padrões e organização. A aplicação ao contexto brasileiro é julgamento de projeto, não comprovação de eficácia por esses órgãos.

## Decisões por tarefa

- **Família:** próximas datas aparecem no início; recusas ganham “Retornos da UBS”, com motivo, providência, profissionais e data. O botão permite enviar outro arquivo da mesma pessoa, mantendo o original. A ação principal muda para acompanhar os envios quando já existem cadernetas.
- **UBS:** a fila é restrita às atribuições; a pessoa confirma independência antes do voto. O resultado coletivo depende de três aprovações; não se exibe voto alheio antes da conclusão. Impedimento é uma ação explícita. “Motivo da decisão” e “O que a família deve fazer” são campos diferentes.
- **ACS:** o menu “Contatos com famílias” descreve a tarefa. A busca ativa continua sendo o mesmo fluxo: prioridades, contatos e histórico preservados. Não recebe arquivos clínicos.
- **Cadastro:** texto completo dos termos em janela legível; caixas separadas e desmarcadas para termos, dados de saúde e declaração de maioridade/representação. A autorização de notificações permanece opcional e posterior.
- **Agenda:** pessoa, vacina, dose e data são informação principal. A explicação da fonte e do recorte é expansível; o alerta de regra vencida permanece visível.

## Vocabulário

| Antes | Texto adotado | Precisão preservada |
| --- | --- | --- |
| Histórico vacinal | Vacinas registradas | Não promete consulta ao registro oficial do SUS. |
| Evidência | Arquivo / foto / PDF, conforme contexto | Original continua associado ao registro. |
| Registro extraído / transcrito | Dose encontrada no arquivo | Informação permanece a conferir até decisão. |
| Possível pendência | Dose para conferir com a UBS | Ausência no histórico não comprova ausência de vacinação. |
| Busca ativa | Contatos com famílias, no menu | Prioridade e registro de ação continuam disponíveis ao ACS. |
| Recorte vigente | Vacinas avaliadas automaticamente | Não apresenta cobertura parcial como calendário completo. |
| OCR | Leitura automática, com explicação quando necessário | Falhas e necessidade de conferência humana ficam claras. |

Nomes de vacinas, siglas oficiais e números de doses não são substituídos por nomes vagos. Em partes profissionais, termos técnicos úteis são mantidos com contexto.

## Princípios de decisão

| Princípios | Aplicação e limite |
| --- | --- |
| Occam e KISS | Reutilizar componentes e padrões de formulário; não criar um novo menu para cada detalhe. |
| Hick e Pareto | Destacar a próxima ação e as datas; controles ocasionais ficam secundários. Nenhum dado clínico necessário é retirado para reduzir opções. |
| Fitts | Botões de toque de 44px e ações próximas ao contexto. Ações de recusa permanecem distintas da aprovação. |
| Jakob e affordance | Menus estáveis, links sublinhados, botões identificáveis, rótulos persistentes. |
| Gestalt | Proximidade, alinhamento e separação por linhas agrupam informações relacionadas. Cores não criam categorias fictícias. |
| Carga cognitiva e reconhecimento | Nome da pessoa e situação acompanham o registro; texto explica a providência sem exigir memorização. |
| Divulgação progressiva | Auditoria e explicações técnicas expansíveis; erros e retornos relevantes visíveis. |
| Forma a serviço da função | Removidas ilustrações sem ação, slogans e ícones repetidos nas estatísticas; tipografia local evita dependência de fonte externa. |

## Validação e limites

Lint, formatação, build e testes funcionais são registrados em KANBAN.md. A revisão visual inclui desktop e mobile; capturas desta sessão usam dados fictícios. Ainda são necessários testes moderados com cidadãos, UBS e ACS, aparelhos Android/iOS reais e avaliação completa por teclado/leitor de tela. Não há certificação de acessibilidade, pesquisa com usuários reais nem validação clínica integral nesta etapa.

## Navegação e telas móveis — 2026-11-11

- URLs autenticadas seguem `/tipo-de-perfil/nome-do-perfil/tela/acao`. Use segmentos adicionais para o identificador da caderneta, pessoa ou contato e para a etapa. Exemplo sintético: `/ubs/ana-souza/fila-de-conferencia/conferir-caderneta/<id>/doses`.
- O segmento `/busca` identifica a tela filtrada. O texto digitado fica no histórico da aba, vinculado à conta, fora da URL. Os filtros de situação e data ficam na URL e links antigos de avisos continuam funcionando. A API continua verificando o acesso aos dados.
- O calendário abre no mês atual, destaca os dias com doses e permite consultar toda a família, uma pessoa ou todas as datas. Datas que já passaram têm atalho e orientação para conferência.
- A UBS percorre Arquivo, Decisão, Doses e Histórico. Motivo e orientação aparecem conforme a decisão. A aprovação do arquivo e a confirmação de cada dose continuam sendo ações distintas.
- A tela do ACS explica a fila, a prioridade, as opções de contato e o registro de tentativas. A fila de cadernetas tem cartões em telas estreitas.

A segunda revisão (K21.2) deixou resumo e ajuda recolhíveis, encurtou os filtros do calendário e os rótulos da UBS, trouxe a busca e os contatos do ACS para a primeira tela e reservou a cor de alerta para prioridades altas. Validação no Chrome em 320 e 390 px com dados fictícios.

A revisão K21.3 separou as vacinas em Registradas, A conferir e Histórico. Registros cabem na largura do celular, e a grade de pendências mostra a menor dose aberta por vacina. A UBS abre a primeira caderneta disponível com Começar a conferir; decisões de outras cadernetas ficam bloqueadas até que a primeira deixe a fila do profissional. Resumo e instruções do início ficam no desktop.
