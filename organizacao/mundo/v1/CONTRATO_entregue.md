# O contrato do mundo: a porta por onde a organização entrega o que acontece

O mundo é um processo no tempo. Quem o observa não é parte dele e não está neste pacote. A única ligação entre os dois é esta porta.

## A classe Mundo (organizacao/mundo/v1/mundo.py)
- `Mundo(semente: int, nulo: str | None = None)`: cria a empresa inteira com a semente (a mesma semente, a mesma empresa). `nulo`
  liga uma das versões nulas: "sem_defeito" (nenhuma liberação carrega defeito), "embaralhado" (o tempo dos processos sem ciclo),
  "sem_deriva" (a carteira não cresce).
- `mundo.processos() -> list[Processo]`: a lista fixa dos processos observáveis, cada um com `nome` (português, legível, único) e
  `campos` (lista de nomes de campos, português, legíveis). Entre cem e trezentos processos; cada um com um a oito campos
  numéricos. Nenhum campo pode ser a verdade disfarçada (um campo "houve liberação com defeito" conta a resposta).
- `mundo.passo() -> dict[str, list[float]]`: faz acontecer um minuto (as pessoas agem, os clientes batem no produto, o código roda,
  os bancos mudam) e devolve, para cada processo pelo nome, os valores dos campos naquele minuto, na ordem de `campos`. Um minuto
  por chamada, sempre o próximo. É o play: o observador chama `passo()` quando está pronto para o minuto seguinte; o mundo nunca
  anda sozinho.
- `mundo.t`: o minuto atual (inteiro, começa em 0). `mundo.dia()`, `mundo.minuto_do_dia()`, `mundo.dia_da_semana()` (0 = segunda).
- `mundo.salvar(pasta)` e `Mundo.carregar(pasta)`: pausa e retomada; o estado inteiro (os bancos, os agentes, o relógio) vai para a
  pasta e volta igual.
- `mundo.verdade() -> dict`: o que a empresa tem de verdade e quando aconteceu (ciclos, liberações e quais carregaram defeito, o
  incidente, a versão nova, a deriva, o sprint de pressa), com instantes. É só para a bancada; o observador nunca lê isto.
- `mundo.eventos_humanos() -> list[tuple[int, str]]`: uma linha por acontecimento visível a uma pessoa da empresa (liberação,
  incidente, correção no ar, contratação), com o instante; só para quem lê o diário conferir.

## O que não entra pela porta
Nenhum texto sobre o que importa. Nenhum rótulo de "normal" ou "anormal". Nenhum dado de pessoa: só agregados por equipe, projeto,
fila, rota, etapa, agenda, quadro, carteira.

## Custo
Trinta dias (43.200 chamadas de `passo()`) em menos de dez minutos de máquina, abaixo de 2 GB. Python 3.11; numpy e sqlite3
(biblioteca padrão). Nada de rede.

## Esclarecimentos da v1.0 (decididos antes da construção)
- **O relógio.** `t = 0` é a criação da empresa (segunda-feira, meia-noite). Cada `passo()` avança `t` e faz acontecer o minuto `t`;
  os valores devolvidos, `dia()`, `minuto_do_dia()`, `dia_da_semana()` e os instantes de `verdade()` se referem a esse mesmo `t`.
  Trinta dias vão de `t = 1` a `t = 43.200`.
- **`Processo`** tem `nome` e `campos` e nada mais. A lista não muda enquanto o mundo anda.
- **Nulo "embaralhado".** A empresa vive por um calendário interno sorteado em blocos de duração variável (de 25 a 240 minutos);
  cada bloco recebe uma hora, um dia da semana e um dia do mês sorteados, e dentro do bloco o calendário corre minuto a minuto.
  Pessoas, clientes, reuniões, liberações e tarefas agendadas do servidor seguem esse calendário; as durações e os atrasos de causa e
  efeito seguem o minuto real. Some todo ciclo de hora, dia da semana, sprint e mês; o mundo continua andando um minuto por chamada
  e nunca sozinho. `verdade()` registra o calendário sorteado: os blocos, com início, fim e a hora, o dia da semana e o dia do mês
  que cada um recebeu. O relógio da porta (`t`, `dia()`...) continua o real.
- **Nulo "sem_defeito".** Nenhuma liberação com defeito chega ao ar: as pessoas continuam escrevendo defeitos, mas a qualidade roda
  a bateria inteira de testes e barra todos. O incidente de infraestrutura fica (não é liberação); a verdade o marca como o único
  episódio de erros seguidos de chamados nesse nulo.
- **Nulo "sem_deriva".** Só a carteira deixa de crescer: cada cliente que entra leva à saída do cliente mais insatisfeito em até dois
  dias. A versão nova continua mudando a latência; em `verdade()` ela entra como "mudança de regime" (um degrau com instante),
  separada de "deriva" (o que cresce devagar).
- **Prioridade pode sair** pela porta (contagens de itens e chamados por prioridade), porque é o que as pessoas põem nos sistemas.
  Nenhum campo de alerta sai, nem qualquer campo calculado para dizer que algo está fora do normal.
- **O dono e o administrativo** formam a equipe "gestão" nos agregados; nenhum agregado sai de uma pessoa só.
- **As leis se repetem.** Incidente, versão que muda a latência e sprint de pressa acontecem por lei do mundo, não por calendário: o
  volume do banco enche com o uso e a operação dá folga de três a cinco semanas a cada vez; as funcionalidades dos épicos mudam o
  trabalho de uma rota em uma parte das liberações; o sprint de pressa nasce quando o planejado passa da capacidade. Nos primeiros
  30 dias cada um acontece ao menos uma vez (o estado inicial da empresa garante) e em 90 dias cada um se repete.

## v1.1: o mundo recebe atos
Quem observa a empresa também age nela. O ato vira coisa dentro do mundo, as pessoas tratam a coisa como tratam o resto, e a
resposta volta pela porta com atraso humano.
- `mundo.equipes() -> list[str]`: os nomes das equipes ("produto", "desenvolvimento", "qualidade", "atendimento", "vendas",
  "operação", "gestão").
- `mundo.receber(equipe: str, tipo: str, texto: str) -> int`: registra um ato para a equipe. `tipo` é "pergunta", "pedido" ou
  "convocacao". Devolve o número do ato (o protocolo que o item criado carrega no sistema da equipe). O ato acontece no próximo
  `passo()`: vira um item no fluxo de trabalho (produto, desenvolvimento, qualidade, operação), um chamado no atendimento, uma
  tarefa no CRM de vendas ou uma solicitação à gestão. Dentro do mundo a origem desses itens se chama "porta"; nos agregados eles são
  itens como os outros (fila, abertos, idade).
  - "pergunta": alguém da equipe trata o item na ordem da fila, dentro do horário e fora de reunião, entre uma tarefa e outra; a
    resposta é um texto curto montado com o que os sistemas da equipe mostram naquele momento, nunca a verdade.
  - "pedido": como a pergunta, mas a equipe age: a operação roda os testes da rota contra a versão no ar e, se falham, reverte (se a
    falha veio com a última liberação) ou abre a correção com prioridade crítica; a qualidade refaz os testes na versão no ar e
    reabre o item que causou a falha; o atendimento responde primeiro os chamados do componente nas quatro horas seguintes; o
    desenvolvimento passa o bug do componente para crítico ou procura a falha; o produto registra a história; vendas retoma as
    propostas paradas; a gestão marca um alinhamento das lideranças.
  - "convocacao": vira uma reunião na agenda da equipe no primeiro horário livre de todos; quem está nela não age nos sistemas
    enquanto dura; a resposta diz quando a reunião ficou marcada.
  Cada ato consome tempo de pessoa; muitos atos atrasam a equipe (a fila cresce, o prazo piora), sem penalidade escrita.
- `mundo.respostas() -> list[tuple[int, int, str, str]]`: as respostas que chegaram desde a última chamada, como
  `(t, número do ato, equipe, texto)`. Um ato não tratado até o fim do expediente do dia útil seguinte fica sem resposta.
- Nulo **"surdo"**: `receber()` aceita e devolve número, e nada acontece; `respostas()` fica vazio.
- `rodar.py <pasta> <dias> <semente> [nulo] [--atos arquivo.csv]`: o arquivo de atos tem cabeçalho `t,equipe,tipo,texto`; o ato da
  linha `t` é entregue logo antes do passo que faz o minuto `t`. As respostas são gravadas com instante em `respostas.csv`.

## Gravações
`rodar.py` grava `minutos.csv.gz`: uma linha por minuto (a linha `i` depois do cabeçalho é o minuto `t = i`), com os valores na
ordem de `processos()` e de `campos`; a primeira linha tem os nomes "processo.campo".

## Custo (v1.1)
Noventa dias (129.600 chamadas de `passo()`) em menos de trinta minutos de máquina, abaixo de 2 GB.
