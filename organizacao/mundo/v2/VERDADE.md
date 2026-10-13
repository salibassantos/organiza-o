# A verdade do mundo v2, campo a campo

A verdade é o que a empresa teve de fato e quando. Ela existe só para a bancada: nada nela é lido pelas pessoas nem pelos sistemas, e
nada dela sai pela porta. Um juiz de fora confere com ela o que o observador percebeu: **o que aconteceu, onde (processo e campo),
quando, por quanto tempo e por causa de quê**.

## Onde ela mora e como se lê

- `mundo.verdade() -> dict`: todos os registros, do minuto 1 ao minuto atual (os gravados em disco e os ainda em memória), cada
  lista em ordem de tempo.
- `mundo.verdade_por_minuto(inicio=0, fim=None) -> (t, valores, colunas)`: a verdade minuto a minuto entre dois instantes
  (inclusive). `t` é um vetor de instantes, `valores` uma matriz `len(t) x len(colunas)` (float32; `NaN` só no minuto 0, que não
  acontece), `colunas` os nomes da tabela "verdade por minuto" abaixo.
- `mundo.eventos_humanos() -> list[(t, texto)]`: o que uma pessoa da empresa veria acontecer.
- A pasta de história (`mundo.pasta_da_historia()`; em `rodar.py`, `<pasta>/historia`) guarda o passado, um par de arquivos por dia
  real `d` (minutos `d x 1440` a `d x 1440 + 1439`):
  - `dia_NNNNN.npz`: `t` (1440 instantes), `valores` (1440 x 82, float32) e `colunas` (os nomes);
  - `dia_NNNNN.json`: `{"dia", "registros": {lista: [registros]}, "eventos_humanos": [[t, texto]]}`. Um registro vai para o disco no
    fim do dia em que ficou definitivo há sete dias (sete dias depois de fechado, quando nenhum chamado ou escalação tardia ainda
    pode mudá-lo). Os registros abertos e os recentes ficam em memória e aparecem em `verdade()` do mesmo jeito.
  - Os arquivos de um dia fechado nunca mais mudam. Ao salvar, a história vai junto (`<pasta>/historia`); cada carga ganha uma pasta
    nova com o passado copiado, para que dois ramos do mesmo estado não escrevam no mesmo lugar.

## Convenções

- **Instantes** são minutos `t` da porta (`t = 0` é a criação, segunda-feira 1º de junho de 2026, 0h; cada `passo()` faz acontecer o
  minuto `t`). **Durações** são em minutos (`_min`).
- **`onde`** é sempre uma lista de pares `[processo, campo]` com os nomes exatos de `processos()`: os campos em que o acontecimento
  aparece. **`causa`** é um texto curto com o mecanismo.
- `null` quer dizer "ainda não aconteceu" (um episódio ainda no ar tem `saiu_do_ar: null`).

## O topo

| campo | o que é |
|---|---|
| `versao_do_mundo` | 2 |
| `semente`, `nulo` | a semente e o nulo do mundo (`null` na empresa normal) |
| `minutos` | o minuto atual |
| `convencao_do_tempo` | a convenção acima, por extenso |
| `ciclos` | as leis do calendário (abaixo) |
| `liberacoes`, `liberacoes_com_defeito` | toda implantação; as que levaram defeito ao ar |
| `episodios_de_defeito_no_ar` | cada defeito que chegou ao ar, do primeiro erro à saída |
| `incidentes` | o produto parado por volume do banco cheio |
| `cadastros_adiados_por_volume_cheio` | contas de clientes novos que não gravaram com o volume cheio |
| `mudancas_de_regime` | as liberações que mudaram para sempre o trabalho de uma rota |
| `deriva` | a carteira, o teto do mercado, os platôs e as expansões |
| `campanhas` | os dias de campanha injetados |
| `sprints`, `sprints_de_pressa` | os sprints de Produto e Plataforma; os planejados acima da capacidade |
| `defeitos_escritos`, `defeitos_barrados_antes_do_ar` | defeitos que as pessoas escreveram; os que a revisão, a qualidade ou a regressão barraram |
| `quedas_do_processo_por_memoria` | as quedas curtas do processo quando o defeito de memória está no ar |
| `pessoal` | contratações e saídas |
| `chamados_por_causa` | contagem total de chamados por causa: defeito, incidente, queda do processo, outros |
| `atos` | cada ato recebido pela porta, com tudo o que a equipe fez e o que custou |
| `latencia_por_dia` | a latência média de cada rota no horário comercial, dia a dia |
| `volume_inicial_folga_dias` | quantos dias de folga o volume do banco tinha na criação |
| `verdade_por_minuto` | a pasta, o número de dias gravados e a descrição de cada coluna |
| `observacao_do_nulo` | nos nulos, o que muda na verdade |

### `ciclos`

Na empresa normal: `dia_util`, `semana`, `sprint`, `mes` (as leis por extenso), `fins_de_sprint` (lista de `{t, projeto, numero}`) e
`fins_de_mes` (lista de instantes da virada para o último dia do mês). No nulo embaralhado: `ausentes` (texto) e
`blocos_do_calendario`: lista de `{inicio, fim, hora, dia_da_semana, dia_do_mes}` com o calendário que cada bloco de 25 a 240 minutos
recebeu.

### `liberacoes` (uma por implantação)

| campo | o que é |
|---|---|
| `t` | o instante da implantação |
| `versao` | o nome da versão que foi ao ar |
| `tipo` | "regular" (terças e quintas, ou sexta de fim de sprint), "correção" (correção no ar) ou "reversão" (volta à versão anterior) |
| `defeitos_que_entraram`, `defeitos_que_sairam` | pares `[função, implementação]` com defeito que a implantação pôs ou tirou do ar |
| `funcoes_que_mudaram_de_comportamento` | funções cuja implementação nova muda o trabalho (mudança de regime) |
| `funcionalidades` | as funcionalidades que vieram nos itens liberados |
| `pedida_pelo_ato` | o número do ato que pediu a reversão, quando foi um pedido da porta à operação; senão `null` |

### `episodios_de_defeito_no_ar` (um por defeito que chegou ao ar)

| campo | o que é |
|---|---|
| `funcao`, `implementacao`, `componente` | onde está o código errado |
| `como_aparece`, `descricao` | o tipo do defeito ("exceção", "lento", "gravação dupla", "fila", "memória") e o que ele faz |
| `onde` | as rotas que chamam a função (campo "respostas com erro no minuto") e os chamados do componente ("abertos") |
| `liberado_em`, `versao` | quando e em que versão entrou no ar |
| `primeiro_erro`, `erros` | o primeiro erro que o defeito causou e o total |
| `primeiro_chamado`, `chamados` | o primeiro chamado ligado a ele e o total |
| `primeira_escalacao`, `escalacoes` | a primeira escalação ao desenvolvimento e o total |
| `saiu_do_ar`, `duracao_no_ar_min` | quando saiu e quanto tempo ficou |
| `saiu_por` | "regular", "correção" ou "reversão" (a implantação que o tirou) |
| `saiu_pelo_ato` | o ato que pediu a reversão que o tirou, se houve |
| `atos_que_o_tocaram` | atos tratados sobre o componente do defeito enquanto ele estava no ar |

A causa de um erro ou chamado é o defeito quando a exceção nasce na função defeituosa (o chamado guarda o instante e a função do
erro que o motivou).

### `incidentes` (o produto parado por volume do banco cheio)

| campo | o que é |
|---|---|
| `inicio`, `fim`, `duracao_min` | da primeira à última falha seguida da sonda |
| `causa` | "volume do banco cheio" |
| `onde` | a sonda, o espaço livre do banco e os erros de todas as rotas |
| `primeiro_chamado`, `chamados`, `primeira_escalacao`, `escalacoes` | os chamados e escalações que ele causou |
| `causa_diagnosticada`, `tratado_em` | o que a operação achou e quando terminou o tratamento |
| `folga_dada_em_dias`, `registros_apagados` | o volume novo (em dias de crescimento estimado) e a auditoria apagada |
| `volume_paginas_no_inicio`, `paginas_livres_no_inicio` | o volume quando o produto parou |

O volume continua enchendo com o uso, por lei; cada vez é um incidente tratado e recuperável. Nenhuma escrita com o volume cheio
derruba o mundo: a requisição falha com o erro do próprio banco, a conta de um cliente novo espera (abaixo) e as escritas dos
clientes são refeitas de hora em hora.

### `cadastros_adiados_por_volume_cheio`

`{t, cliente, motivo, gravado_em}`: o administrativo não conseguiu gravar a conta de um cliente novo; `gravado_em` é quando gravou,
na primeira tentativa (de hora em hora) depois que a operação aumentou o volume. Até lá o cliente não usa o produto e não conta
na carteira.

### `quedas_do_processo_por_memoria`

`erros_no_registro` (instantes dos erros "MemoryError" do processo) e `sonda_parada`: registros como os de `incidentes`, com causa
"processo parado" e `onde` = a sonda e os reinícios do servidor.

### `mudancas_de_regime`

| campo | o que é |
|---|---|
| `t`, `versao` | a liberação |
| `funcao`, `de`, `para` | a função e as implementações (antes e depois) |
| `rotas`, `onde` | as rotas que chamam a função; o campo "latência média em ms" de cada uma |
| `tipo` | "mudança de regime" |
| `latencia_media_7_dias_antes`, `latencia_media_7_dias_depois` | por rota, a média da latência no horário comercial nos sete dias antes e depois (preenchida oito dias depois) |

### `deriva`

| campo | o que é |
|---|---|
| `carteira_por_dia` | `[t, clientes ativos]` a cada dia vivido |
| `crescimento_por_semana_em_porcento` | a variação da carteira de sete em sete dias vividos |
| `entradas_e_saidas` | `[t, "entrada" ou "saída", plano]` |
| `teto_inicial` | o teto do mercado na criação (`null` no nulo sem_deriva) |
| `platos` | `{inicio, fim, duracao_min, teto, carteira_no_inicio, carteira_no_fim, causa, onde, terminou_por}` |
| `expansoes` | `{decidida_em, vale_a_partir_de, teto_antes, teto_depois, carteira_na_decisao, causa}` |

A lei: a chegada de leads (site e indicação) é multiplicada pela saturação `max(0,05, min(1, (teto - carteira) / (0,1 x teto)))`.
O platô começa quando a carteira passa de 96,5% do teto. Depois de 25 a 70 dias parada, o dono decide (em 70% das vezes) abrir
mercado novo: o teto sobe 15% a 35%, valendo de duas a quatro semanas depois; o platô termina nesse instante (`terminou_por`) e a
carteira volta a crescer. O teto nunca passa de 2,6 vezes o inicial: depois disso o platô é para sempre. A coluna `fase_da_deriva`
da verdade por minuto mostra as fases.

### `campanhas`

`{inicio, fim, duracao_min, forca, onde, causa}`. Enquanto a campanha corre: as sessões dos clientes crescem (1 + 0,8 x força), cada
sessão folheia mais páginas do catálogo, as dúvidas que viram chamado crescem (1 + 1,5 x força) e os leads do site crescem
(1 + 3 x força). `onde` lista os campos que ela move.

### `sprints`

`{projeto, numero, inicio, meta_pontos, capacidade_pontos, meta_sobre_capacidade, pressa, fim, pontos_feitos}`; `pressa` é
verdadeiro quando a meta passa de 1,15 vez a capacidade. `fins_de_sprint` está em `ciclos`.

### `defeitos_escritos`, `defeitos_barrados_antes_do_ar`, `pessoal`

`{t, item, projeto, funcao, implementacao, pressa_do_squad}`; `{t, item, funcao, por}` (por "revisão de código", "qualidade" ou
"regressão"); `{t, tipo, equipe}` (tipo "contratação" ou "saída").

### `atos` (um por ato que chegou ao mundo)

| campo | o que é |
|---|---|
| `numero`, `equipe`, `tipo`, `texto` | o ato como foi recebido ("pergunta", "pedido" ou "convocacao") |
| `recebido` | o minuto em que virou coisa dentro do mundo (o passo seguinte ao `receber()`) |
| `rota`, `componente` | a rota e o componente que o texto cita (ou `null`) |
| `virou` | `{sistema, item}`: o item criado no fluxo, no CRM ou no quadro |
| `demora_ate_ficar_disponivel_min`, `disponivel_em` | a demora da equipe naquele momento e o instante em que o ato pôde ser pego |
| `equipe_ao_receber`, `equipe_ao_tratar` | o estado da equipe (abaixo) nos dois momentos |
| `pego_em`, `tratado_em`, `minutos_de_trabalho` | quando alguém pegou, quando respondeu, quanto trabalho custou |
| `trabalho_adiado` | `{tarefa, item, minutos_que_faltavam, pessoa}`: o que a pessoa largou para tratar o pedido (atrasou o tempo do pedido); `null` se ela estava livre |
| `efeito` | `{util, acoes, encurta, nao_encurta, colateral}` (abaixo) |
| `confianca_antes`, `confianca_depois` | a confiança da equipe em quem pede, antes e depois deste ato |
| `resposta` | o texto devolvido pela porta (o pedido começa com "Pedido tratado.") |
| `desfecho` | "respondido" ou "sem resposta" (com `expirou_em`: o fim do expediente do dia útil seguinte) |
| `horas_extras_atribuidas` | `{t, pessoa, equipe, minutos, onde}`: hora extra que alguém fez porque o dia foi tomado por pedidos |

O **`efeito`**: `util` diz se o pedido resolveu algo (`true`/`false`; `null` em pergunta e convocação); `acoes` é o que a equipe fez
nos sistemas (testes rodados e com que cobertura, bug aberto, reversão, prioridade mudada, foco, reunião marcada); `encurta` são os
campos em que o tratamento encurta o problema; `nao_encurta`, os campos ligados ao problema que o tratamento não encurta;
`colateral`, os campos de outros processos que pioram por causa do tratamento (fila de outra equipe, sprint, horas extras, prazos
do atendimento). A medida do efeito é a comparação de ramos: o mesmo estado salvo com o ato e sem ele.

O **estado da equipe**: `demora_resposta` e `demora_tratamento` (minutos típicos, estáveis, sorteados da semente), `cansaco`,
`atencao`, `confianca` e `ocupacao`. A demora de um ato é
`base x (1 + 1,5 x ocupação) x (1 + 0,8 x cansaço) x (1 + 0,6 x atenção) / confiança`; a duração do trabalho é multiplicada por
`1 + 0,5 x cansaço`; com pouca confiança a equipe verifica por cima (cobertura `min(1, 0,5 + 0,5 x confiança)`). Pedido útil soma 0,15
à confiança (até 1,6); pedido inútil tira 0,2 (até 0,4); a cada dia vivido a confiança volta 5% para 1. A pergunta gasta 0,25 de
atenção, o pedido 0,5, a convocação 0,35; a atenção volta em umas duas horas. O cansaço sobe com as horas extras da equipe e desce
com o descanso.

### `latencia_por_dia`

`{dia, t, media_no_horario_comercial_ms: {rota: média}}`.

## A verdade por minuto (colunas de `dia_NNNNN.npz` e de `verdade_por_minuto()`)

| coluna | o que mede |
|---|---|
| `t` | o minuto da porta |
| `data_do_calendario` | a data em que as pessoas e os processos vivem (dias desde a criação; no nulo embaralhado, a data sorteada) |
| `minuto_do_calendario` | o minuto do dia em que as pessoas e os processos vivem (0 a 1439) |
| `dia_util` | 1 se a data do calendário é dia útil |
| `defeitos_no_ar` | quantos defeitos estão no código em produção neste minuto |
| `defeitos_no_ar.<componente>` | o mesmo, por componente: login, catalogo, pedido, frete, pagamento, fiscal, relatorio, notificacao |
| `erros_de_defeito` | respostas com erro neste minuto cuja exceção nasceu numa função com defeito no ar |
| `erros_de_outra_causa` | respostas com erro neste minuto sem defeito no ar por trás (entrada inválida, produto parado) |
| `produto_parado` | 1 enquanto a sonda falha seguidamente (incidente ou queda do processo aberto) |
| `incidente_de_volume` | 1 enquanto o incidente aberto é o volume do banco cheio |
| `volume_paginas` | o tamanho do volume do banco do produto, em páginas de 4096 bytes |
| `volume_paginas_livres` | as páginas livres no volume |
| `chamados_por_defeito` | chamados abertos neste minuto que nasceram de um defeito no ar |
| `chamados_por_incidente` | chamados abertos neste minuto que nasceram do produto parado |
| `chamados_de_outra_causa` | chamados abertos neste minuto sem defeito nem incidente por trás |
| `carteira` | clientes ativos |
| `teto_do_mercado` | o teto da carteira que o mercado comporta agora (0 no nulo sem_deriva) |
| `fase_da_deriva` | 0 crescendo, 1 platô (carteira no teto), 2 expansão decidida e ainda não valendo |
| `saturacao` | o fator que multiplica a chegada de leads (1 longe do teto, perto de 0 no teto) |
| `campanha` | a força da campanha em curso (0 sem campanha) |
| `pressa.PROD`, `pressa.PLAT` | a pressa de cada squad: pontos que faltam no sprint sobre o que ainda dá para fazer (0,5 a 2,5) |
| `pessoas_presentes` | pessoas trabalhando neste minuto |
| `implantacao` | 1 se houve implantação neste minuto |
| `atos_recebidos` | atos que viraram coisa dentro do mundo neste minuto |
| `atos_tratados` | atos tratados (respondidos) neste minuto |
| `<equipe>.atos_na_fila` | atos esperando a equipe |
| `<equipe>.atos_em_tratamento` | pessoas da equipe tratando um ato agora |
| `<equipe>.cansaco` | cansaço da equipe (0 descansada; sobe com hora extra e com pedidos) |
| `<equipe>.atencao` | atenção já gasta pela porta na equipe |
| `<equipe>.confianca` | confiança da equipe em quem pede (0,4 a 1,6; 1 neutra) |
| `<equipe>.ocupacao` | ocupação da equipe (gente presa em reunião ou urgência, e a fila regular) |
| `<equipe>.demora_de_pedido` | minutos que um pedido levaria agora até alguém da equipe pegá-lo |

`<equipe>` é uma das sete: produto, desenvolvimento, qualidade, atendimento, vendas, operação, gestão. São 82 colunas. A descrição
de cada uma também vem em `verdade()["verdade_por_minuto"]["colunas"]`.

## Os nulos na verdade

- **sem_defeito**: nenhuma liberação leva defeito; os episódios de erro seguidos de chamados são só os incidentes.
- **embaralhado**: `ciclos` traz os blocos do calendário sorteado; `data_do_calendario` e `minuto_do_calendario` mostram o calendário
  vivido minuto a minuto.
- **sem_deriva**: sem teto, platô nem expansão (`teto_inicial` nulo, `teto_do_mercado` 0); cada entrada leva a uma saída.
- **surdo**: nenhum ato chega ao mundo; `atos` fica vazio e as colunas das equipes mostram só o trabalho regular.
