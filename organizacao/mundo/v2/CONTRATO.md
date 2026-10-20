# O contrato do mundo v2: a porta por onde a organização entrega o que acontece

O mundo é um processo no tempo. Quem o observa não é parte dele e não está neste pacote. A única ligação entre os dois é esta porta.
O v2 é lido do mesmo jeito que o v1: quem lê o v1 lê o v2 sem mudar nada além do caminho do pacote.

## O que fica igual ao v1

- `Mundo(semente: int, nulo: str | None = None)`: a mesma semente, a mesma empresa. Os nulos: "sem_defeito" (nenhuma liberação
  carrega defeito), "embaralhado" (o tempo dos processos sem ciclo), "sem_deriva" (a carteira não cresce) e "surdo" (nenhum ato
  chega ao mundo). (v2.2) "paciente": as equipes sem atenção, cansaço nem confiança (ver abaixo).
- `mundo.processos() -> list[Processo]`: a lista fixa dos 131 processos. Cada `Processo` tem `nome`, `campos`, **`equipe`** (a equipe
  responsável, uma das sete) e **`resolucao`** (uma lista, um número por campo: o menor passo que o campo dá ao sair pela porta;
  1 para contagens, 0,1 para milissegundos, porcentagens, horas e milhares, 0,01 para megabytes, reais e horas extras). A lista não
  muda enquanto o mundo anda. Nenhum campo é a verdade disfarçada; nenhum campo de alerta ou de "anormal" sai. Contagens por
  prioridade saem.
- `mundo.passo() -> dict[str, list[float]]`: faz acontecer o próximo minuto e devolve os valores de cada processo naquele minuto,
  na ordem de `campos`. Um item por processo por minuto.
- `mundo.t`, `mundo.dia()`, `mundo.minuto_do_dia()`, `mundo.dia_da_semana()` (0 = segunda). `t = 0` é a criação (segunda-feira,
  1º de junho de 2026, 0h); cada `passo()` avança `t` e faz acontecer o minuto `t`.
- `mundo.equipes() -> list[str]`: "produto", "desenvolvimento", "qualidade", "atendimento", "vendas", "operação", "gestão".
- `mundo.receber(equipe, tipo, texto) -> int`: um ato ("pergunta", "pedido" ou "convocacao") para uma equipe; devolve o número do
  ato. O ato vira coisa dentro do mundo no passo seguinte.
- `mundo.respostas() -> list[(t, numero, equipe, texto)]`: as respostas que chegaram desde a última chamada. A pergunta volta com
  uma resposta; o pedido volta com um aviso de tratado (o texto começa com "Pedido tratado."; (v2.2) ou com "Pedido não entendido:"
  quando a equipe não reconhece nada nele); a convocação volta com a reunião
  marcada. O que não for tratado até o fim do expediente do dia útil seguinte fica sem resposta.
- `mundo.salvar(pasta)` e `Mundo.carregar(pasta)`: pausa e retomada; continuar depois de carregar dá exatamente a mesma vida que
  continuar sem parar.
- `mundo.verdade() -> dict` e `mundo.eventos_humanos() -> list[(t, texto)]`: só para a bancada.

## O que o v2 acrescenta

- `Mundo(semente, nulo=None, tempo_real=False, historia=None)`: `historia` é a pasta onde a verdade por minuto e os registros
  fechados vão ficando, um arquivo por dia (sem ela, uma pasta temporária nova).
- `Mundo.carregar(pasta, historia=None)`: cada carga ganha a sua própria pasta de história, com o passado copiado do estado salvo.
  Duas cargas do mesmo estado são dois ramos independentes.
- `mundo.injetar_campanha(inicio, duracao=1440, forca=1.0)`: um dia de campanha que move vários processos ao mesmo tempo (sessões,
  rota do catálogo, chamados, funil), do minuto `inicio` a `inicio + duracao`. É uma entrada do mundo como os atos (entra na sequência
  de entradas e no caminho), vale em todos os nulos e fica na verdade com início, fim, força e onde.
- `mundo.verdade_por_minuto(inicio=0, fim=None) -> (t, valores, colunas)` e `mundo.pasta_da_historia()`: a verdade minuto a minuto.
- O formato da verdade está em `VERDADE.md`, campo a campo: o que aconteceu, onde (processo e campo), quando, por quanto tempo e por
  causa de quê.

## v2.1: a causa dos chamados e o calendário na verdade

Só a verdade muda; o mundo e os minutos ficam iguais. `verdade()` ganha `chamados` (a rota e o instante que motivaram cada chamado e
a sua causa), `causas` (as leis que ligam rota a chamados, as janelas em que agiram e as três categorias de um par: causa declarada,
causa comum, sem relação) e `calendario` (os motores do calendário por campo, com o caminho e a força medida). A verdade por minuto
ganha 27 colunas no fim. Ver `VERDADE.md`.

## v2.2: a reversão própria, o nulo paciente e o ouvinte

Versão v2.2: o código do mundo é o do commit `079d3a8` (ramo mundo-servico). Ele vem em três passos: `b6f7433` (a reversão própria e o
nulo paciente: só campos novos na verdade, o resto byte a byte igual, com e sem atos), `6128b33` (o ouvinte: sem atos, byte a byte
igual; com atos, a rota de cada texto é a mesma, e muda o que a equipe faz quando o pedido é de olhar e dizer ou não nomeia nada que
ela reconheça) e `079d3a8` (a lei medida e as vidas de 90 dias, sem mudar o mundo).

Os minutos, as respostas e a verdade de antes ficam iguais, byte a byte; só entram campos novos.

- Cada episódio de defeito ganha `reverteria_sozinha_em`, `sairia_sozinha_por`, `persistente`, `antecipou_min`, `ramo_sem_ato`,
  `atos_recebidos_no_ar` e `atos_tratados_no_ar`, e o `efeito` de cada pedido tratado ganha `antecipou_min`. O instante em que a
  empresa tiraria o defeito sem nenhum ato sai de um ramo sem ato que o mundo anda por conta própria, fora do caminho vivido (ver
  `VERDADE.md`). A lei da reversão própria, por classe de defeito, escrita e medida, está em `VERDADE.md`.
- `noventa.py` e `RESULTADO_90_dias.md`: por rota e por semente (1 a 8), os episódios de defeito, as reversões e as correções
  em 90 dias do mundo sozinho, e o custo por dia simulado (perto de 6 s de processador, de 4 no começo a 7,5 no fim).
- `Mundo(semente, nulo="paciente")`: as equipes sem atenção, cansaço nem confiança; a demora de um ato só pela base e pela ocupação;
  a confiança fixa em 1; os pedidos não lançam hora extra. Tudo o mais igual ao normal: sem atos, os minutos são os da vida normal da
  mesma semente.
- O ouvinte (`ouvinte.py`): a porta lê o texto inteiro. A rota continua sendo achada como antes (os textos que já caíam numa rota
  caem na mesma); além dela, a equipe entende o processo e o campo pelo nome dos painéis (qualquer processo), o tempo ("desde o dia
  12, 10h", "há duas horas") e o tipo do pedido ("olhar e dizer", "corrigir ou reverter", "pôr à frente da fila"). A verdade de cada
  ato guarda `entendido` e `pediu_esclarecimento`. Muda o que a equipe faz em dois casos: o pedido de olhar e dizer é respondido
  com a leitura do painel, sem ação (`util` nulo), e o pedido em que a equipe não reconhece nada volta com uma pergunta, começando
  por "Pedido não entendido:" (`util` nulo). Toda pergunta, e todo pedido de olhar e dizer, que nomeia um processo leva junto o que
  o painel dele mostrou desde o instante entendido (ou na última hora): média, máximo e o valor de agora. Sem atos, nada disso
  muda os minutos.

## O mundo com consequência

- Cada equipe é um agente com fila, capacidade (as pessoas presentes e livres), cansaço, atenção e memória de quem lhe pede
  (confiança). Cada equipe tem a sua demora própria e estável para responder e para tratar, sorteada da semente.
- A pergunta gasta atenção. O pedido entra na frente da fila: quem o pega larga o que fazia, e o que fazia atrasa. A equipe ocupada
  responde mais devagar. Pedido que não resolveu nada piora a próxima resposta (a equipe confia menos e verifica por cima); pedido
  certo melhora.
- Tratar um problema o encurta de forma mensurável em uns campos e não em outros; tratar tem custo colateral em outros processos
  (fila de outra equipe, sprint, horas extras, prazos do atendimento). A verdade de cada ato diz quais.
- O tempo do mundo corre com ou sem quem lê: ler `respostas()` ou os valores não muda nada.

## Ramos

O mundo é uma função determinística da semente e da sequência de entradas recebidas (atos e campanhas, cada um com o seu instante).
De qualquer estado salvo, alimentado com outra sequência, ele anda por outro caminho, sempre o mesmo para a mesma sequência. Um juiz
mede o efeito de um ato comparando o mundo com o ato e o mesmo mundo sem ele a partir do mesmo instante: até o minuto em que o ato
vira coisa dentro do mundo os dois são idênticos. Quem lê o mundo só tem acesso ao caminho vivido. O nulo surdo é o caminho em que
nenhum ato chega ao mundo (as campanhas, que não são atos de quem lê, continuam valendo).

## Leis novas

- **A deriva assenta.** A carteira cresce, assenta num platô perto do teto do mercado por um tempo e pode voltar a crescer quando o
  dono abre mercado novo. A verdade registra o início e o fim de cada platô e cada expansão. No nulo sem_deriva, nada disso.
- **O disco não mata o mundo.** O volume do banco do produto continua enchendo com o uso; cada vez é um incidente tratado e
  recuperável. Nenhuma escrita com o volume cheio levanta exceção para fora do mundo.
- **Vida longa.** Os sistemas guardam o que é recente e apagam o que passou da janela de retenção; a empresa esquece o que já não
  serve; a verdade vai para o disco. Memória e custo por minuto não crescem com a idade do mundo;
  acompanham a carteira, que tem teto.

## Custo

Python 3.11, numpy e sqlite3. Nada de rede. O custo acompanha a carteira, não a idade do mundo: perto de 4 segundos de máquina por
dia simulado com 460 clientes e perto de 10 com 670; um ano em perto de 47 minutos, com memória máxima de 227 MB (medidas em
`RELATORIO.md`). A pasta de história cresce perto de 0,12 MB por dia simulado.
