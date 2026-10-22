# O contrato do mundo: a porta por onde a organização entrega o que acontece

O mundo é um processo no tempo. Quem o observa não é parte dele e não está neste pacote. A única ligação entre os dois é esta porta.

## A classe Mundo (organizacao/mundo/v1/mundo.py)
- `Mundo(semente: int, nulo: str | None = None)`: cria a empresa inteira com a semente (a mesma semente, a mesma empresa). `nulo`
  liga uma das versões nulas: "sem_defeito" (nenhuma liberação carrega defeito), "embaralhado" (o tempo dos processos sem ciclo),
  "sem_deriva" (a carteira não cresce).
- `mundo.processos() -> list[Processo]`: a lista fixa dos processos observáveis, cada um com `nome` (português, legível, único),
  `campos` (lista de nomes de campos, português, legíveis) `equipe` (o nome da equipe responsável por ele, para a porta de entrada) e `resolucao` (uma lista do tamanho de `campos`
  com a unidade mínima de cada medida: 1 chamado, 1 pessoa, 1 milissegundo, 0,5 ponto de processador; é a escala do instrumento, não dado). Entre cem e trezentos processos; cada um com um a oito campos
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

## v1.1: o mundo recebe atos
- `mundo.receber(equipe, tipo, texto) -> int`: um ato de quem observa, para uma equipe; `tipo` é "pergunta", "pedido" ou
  "convocacao"; vira item na fila da equipe (ou reunião na agenda), tratado pelas pessoas como qualquer outro, no horário, fora de
  reunião, com atraso humano; devolve o número do item; acontece no próximo `passo()`. O pedido muda o mundo (a equipe faz algo);
  a pergunta só consome tempo de pessoa; a convocação marca reunião. Muitos atos atrasam a equipe, e isso emerge.
- `mundo.respostas() -> list[tuple[int, int, str, str]]`: (t, número do item, equipe, texto) das respostas chegadas desde a última
  chamada; texto curto em português montado a partir do que os sistemas da equipe têm naquele momento, nunca a verdade.
- Nulo "surdo": `receber` aceita e nada acontece; `respostas` fica vazio.
- Dentro do mundo a origem desses itens se chama "porta"; nada os marca por fora.

## v1.2: a ordem de custo dos atos
- `atos.CUSTO = ("pergunta", "pedido", "convocacao")`: a ordem em que os atos custam à empresa, do mais barato ao mais caro. A
  pergunta só consome tempo de uma pessoa; o pedido faz a equipe agir; a convocação tira várias pessoas para uma reunião. É verdade
  do mundo declarada no contrato, para que quem observa não a escreva por conta própria. É ordem, não peso, e serve só para
  desempatar dois atos que renderam igual; não decide qual ato tentar primeiro. Olhar não passa pela porta e não custa nada.

## v1.3: os defeitos têm sequência própria, independente dos atos
- Erro de construção achado em 12/10 (pergunta do Fable sobre a linha B): cada pessoa tinha uma sequência de sorte só, e o tratamento
  de um ato de quem observa sorteava dela. Qualquer ato, mesmo só perguntas, deslocava toda a sorte do trabalho dessa pessoa e de quem
  dependia dela, e a mesma semente tinha outros defeitos: na semente 3, em 30 dias, 6 liberações com defeito sem atos e 2 com uma
  pergunta por dia útil a cada equipe.
- Correção: o tratamento de um ato sorteia de uma sequência própria da pessoa ("porta"). A escrita de um defeito, a revisão de código
  e o teste da qualidade sorteiam de uma sequência presa à história (projeto, título e quantas vezes esse título já foi feito, e a
  passagem pela etapa); a regressão, de uma sequência presa ao projeto e ao dia. Na mesma medida, as perguntas passam a mudar no máximo
  uma liberação com defeito (sementes 1 a 3: 4 e 4, 3 e 3, 4 e 3).
- O que continua mudando é caminho de verdade, como o contrato já diz: os atos tomam tempo das pessoas e mudam quando cada história
  fica pronta e em que liberação ela vai, e o pedido faz a equipe agir (cria tarefa, reverte, conserta).
- Toda medida feita no mundo grande antes da v1.3 é do mundo anterior e não se compara com as de depois.

## Decisões fixadas
- `t = 0` é a criação (segunda-feira, 0h); cada `passo()` avança `t` e faz acontecer o minuto `t`; 30 dias vão de 1 a 43.200.
- "embaralhado": calendário interno sorteado em blocos (hora, dia da semana e dia do mês de cada bloco); durações e atrasos
  causais no minuto real; `verdade()` registra o calendário sorteado.
- "sem_defeito": o incidente de infraestrutura fica; `verdade()` o marca.
- "sem_deriva": só a carteira; a versão que muda a latência entra em `verdade()` como "mudança de regime", não como deriva.
- Incidente, versão que muda a latência e sprint de pressa acontecem por lei e se repetem em corridas longas.
- Contagens por prioridade podem sair pela porta; nenhum campo calculado para dizer "anormal" sai.
- Gravações em csv.gz, primeira linha "processo.campo" na ordem de `processos()`.

## O formato de `verdade()` (para a bancada ler sem adivinhar)
Um dicionário com estas chaves, todas presentes (lista vazia ou `None` quando o nulo tira a coisa). Cada acontecimento diz onde ele
bate, em pares `[processo, campo]` com os nomes exatos de `processos()`, na ordem da causa, e o atraso típico em minutos entre eles.
- `liberacoes`: lista de `{"t": int, "defeito": bool, "onde": [[processo, campo], ...], "atrasos": [int, ...], "correcao_t": int | None}`.
  Para a liberação com defeito, `onde` começa pelo campo de erros da rota atingida e segue pelos chamados do componente (e o que
  mais a liberação atinge); `atrasos[i]` é o atraso típico, em minutos, entre `onde[i]` e `onde[i+1]`.
- `incidentes`: lista de `{"inicio": int, "fim": int, "onde": [[processo, campo], ...]}`.
- `mudancas_de_regime`: lista de `{"t": int, "onde": [[processo, campo]], "sentido": "subiu" | "desceu"}` (a versão nova que muda a latência de uma rota para sempre).
- `deriva`: `{"onde": [[processo, campo]], "taxa_por_semana": float, "sentido": "subiu" | "desceu"}` ou `None`.
- `sprints_de_pressa`: lista de `{"inicio": int, "fim": int, "projeto": str, "onde": [[processo, campo], ...]}`.
- `ciclos`: `{"dia": {"onde": [[processo, campo], ...]}, "semana": {"onde": [...]}, "mes": {"onde": [...]}}` ou, no nulo embaralhado, `None`
  com `calendario_embaralhado` preenchido (os blocos sorteados).
- `nulo`: o nome do nulo ou `None`; `semente`: a semente; `minutos_por_instante`: 1.

## Custo
Trinta dias (43.200 chamadas de `passo()`) em menos de dez minutos de máquina, abaixo de 2 GB. Python 3.11; numpy e sqlite3
(biblioteca padrão). Nada de rede.


## v1.4: a causa dos chamados na verdade
Só a verdade muda; o mundo, os minutos e as respostas ficam idênticos (conferido byte a byte nas gravações de `registros/semente1/`).
- `verdade()["chamados"]`: cada chamado com `origem` (a rota e o instante em que o cliente sentiu o erro, depois de tentar de novo, ou
  a lentidão, acima de 4 segundos) e `causa`: "defeito", "incidente", "queda do processo", "rota com erro", "rota lenta" ou "outros"
  (sem rota: dúvida, fatura, cobrança, nota). `chamados_por_causa` ganhou "rota com erro" e "rota lenta", e "queda do processo" passou
  a contar (antes ficava em "outros"). Cada incidente ganhou `chamados_por_rota_de_origem`.
- `verdade()["causas"]`: as leis que ligam o erro e a lentidão de cada rota aos chamados do componente da rota (novos, abertos,
  escalados, resolvidos) e às sessões abandonadas, com o mecanismo e o atraso; as janelas de rota em que a lei esteve ativa, com os
  chamados que gerou; os campos que se mexem juntos quando o produto para; e as categorias de um par de campos: causa declarada,
  causa comum (incidente ou queda do processo) e sem relação. `causas.classificar_par(verdade, de, para, inicio, fim)` classifica um
  par. O formato está descrito em `organizacao/mundo/v2/VERDADE.md` (seções `chamados` e `causas`), igual no v1.

## v1.5: o relógio como campo (opção, desligada por padrão)
- `Mundo(semente, nulo, relogio=True)` (ou `MUNDO_RELOGIO=1`): um processo `relógio`, o último, com `hora do dia` (0 a 23), `dia da
  semana` (0 = segunda) e `minuto do mundo`, no relógio da porta. Desligado, o mundo é o de antes, byte a byte.
