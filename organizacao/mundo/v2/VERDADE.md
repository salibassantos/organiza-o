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
  - `dia_NNNNN.npz`: `t` (1440 instantes), `valores` (1440 x 109, float32) e `colunas` (os nomes);
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
| `chamados_por_causa` | contagem total de chamados por causa: defeito, incidente, queda do processo, rota com erro, rota lenta, outros (sem rota) |
| `chamados` | (v2.1) cada chamado, com a rota e o instante que o motivaram e a sua causa |
| `causas` | (v2.1) as leis que ligam rota a chamados, as janelas de rota, as três categorias de um par e os campos que se mexem juntos quando o produto para |
| `calendario` | (v2.1) o que o calendário move em cada campo: motores declarados, caminho e força medida |
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
| `atos_recebidos_no_ar`, `atos_tratados_no_ar` | (v2.2) quantos atos chegaram ao mundo e quantos foram tratados enquanto ele estava no ar (de qualquer equipe) |
| `ramo_sem_ato` | (v2.2) `{desde, ate}`: o ramo sem ato que mediu a saída sozinha (ver abaixo); `null` quando nenhum ato chegou nem estava aberto enquanto ele esteve no ar (aí o caminho vivido é o ramo sem ato) |
| `reverteria_sozinha_em` | (v2.2) o instante em que a empresa o tiraria do ar sem nenhum ato; `null` se no ramo ele ainda estava no ar no fim (`ramo_sem_ato.ate`) |
| `sairia_sozinha_por` | (v2.2) "regular", "correção" ou "reversão": a implantação que o tiraria sem nenhum ato |
| `persistente` | (v2.2) `true` quando, sem ato, ele dura até uma liberação regular (ou até o fim do ramo); `false` quando a operação o reverte ou o corrige no ar sozinha |
| `antecipou_min` | (v2.2) `reverteria_sozinha_em` menos `saiu_do_ar`: o quanto os atos, juntos, anteciparam a saída (negativo quando a atrasaram; 0 quando ela teria vindo no mesmo minuto); sem saída no ramo, conta até o fim dele e é um mínimo; 0 sem ramo |

**(v2.2) O ramo sem ato.** O mundo é determinístico pela semente e pelas entradas. Quando um ato chega ao mundo, ou ainda está aberto
(recebido e não respondido), com um defeito no ar que ainda não tem ramo, o estado do fim do minuto anterior é guardado. Quando o
defeito sai do ar, esse estado anda de novo, sem nenhum ato daí em diante (os atos abertos são descartados sem tratamento; as
campanhas injetadas até a saída real continuam valendo), até o defeito sair no ramo ou até 28 dias depois de ter entrado no ar. O
instante e a implantação dessa saída são `reverteria_sozinha_em` e `sairia_sozinha_por`. Os ramos andam fora do mundo vivido: os
minutos, as respostas e o resto da verdade são os mesmos de antes da v2.2. Um defeito em que nenhum ato chegou nem estava aberto
não precisa de ramo: o caminho vivido já é o sem ato, e `reverteria_sozinha_em` é `saiu_do_ar`.

**(v2.2) A lei da reversão própria: o que a empresa tira do ar sozinha, por quê e em quanto tempo.** Os defeitos entram no ar com
as liberações regulares (terças e quintas a partir das 15h, e a sexta de fim de sprint às 11h), sempre no expediente. Daí em diante
três caminhos os tiram sem nenhum ato:

- *o alerta e a reversão*: a cada 5 minutos a operação olha cada rota; com 20 erros ou mais e 10% ou mais das requisições com erro
  em 10 minutos, abre um alerta. Quem da operação estiver presente e livre (sem reunião nem urgência, só em trabalho interno) o pega,
  com chance de 7% a cada minuto, e investiga de 12 a 35 minutos. Se a última implantação foi uma liberação regular há menos de 36
  horas, os erros não existiam nas 10 horas antes dela e 25% ou mais das requisições da última meia hora falham, a operação reverte
  para a versão anterior (de 8 a 18 minutos). Fora do expediente ninguém pega alerta: só o produto parado chama o plantão. A
  reversão tira junto todos os defeitos daquela liberação (a reversão "de carona");
- *o bug e a correção no ar*: o alerta que não reverte vira bug crítico (erros, memória) ou alto (lentidão, fila); o chamado de
  cliente que o atendimento não resolve vira bug (alto com 3 chamados ligados, crítico com 6). O bug crítico sem dono é pego na hora
  pelo plantão do squad; o bug crítico ou alto aprovado pela qualidade vai para a correção no ar, feita no expediente ou, se é
  crítico, pelo plantonista da operação a qualquer hora;
- *a liberação regular*: a correção de um bug de prioridade média, ou a troca do código por uma história, entra na próxima liberação
  regular. Esse é o defeito *persistente*.

Medido em oito vidas de 90 dias sem atos (sementes 1 a 8, `RESULTADO_90_dias.md`): 229 episódios; 75 saem por reversão própria, 35
por reversão de carona, 110 por correção no ar e 9 por liberação regular (4%: são os persistentes). Por classe:

- **exceção** (o código quebra numa entrada: login com acento, conta sem telefone, última página do catálogo, termo acentuado,
  quantidade de dois algarismos, CEP com zero; 95 episódios). A rota dá erro em massa, o alerta vem em minutos e a operação reverte
  sozinha: 71 por reversão própria, em 0,8 h de mediana e 1,3 h em 90%. Não revertem quando a taxa de erro da rota fica abaixo de 25%
  (a entrada que quebra é rara) ou a liberação já tem mais de 36 horas: aí o bug crítico vira correção no ar (22, mediana de 17 h, 90%
  em 3 dias). Uma persistiu até a liberação regular. Um pedido pode antecipar pouco aqui: a operação já reverte em menos de uma hora
  e meia.
- **lento** (o relatório lê todos os pedidos; a exportação faz uma consulta por pedido; 21 episódios). Não dá erro até a tabela
  crescer: o alerta de lentidão (latência acima de 2,5 vezes a habitual e de 400 ms em 15 minutos) vira bug alto, sem reversão. Sai
  por correção no ar (9, mediana de 2,9 dias, 90% em 21 dias), de carona numa reversão (7), por reversão própria quando o relatório
  estoura em erro (4), ou na liberação regular (1). É a classe que fica mais tempo no ar sozinha.
- **fila** (a nota fiscal falha fora do Sul e do Sudeste; o e-mail falha sem nome fantasia; 78 episódios). Falha na fila de trabalhos,
  nenhuma rota dá erro: nunca há reversão própria. O alerta de fila (mais de 150 trabalhos pendentes) vira bug alto e correção no ar
  (57, mediana de 23 h, 90% em 3 dias); 20 saem de carona e 1 na liberação regular.
- **gravação dupla** (o clique duplo cobra duas vezes; 20 episódios, todos na rota pagamento). Silenciosa: nenhum erro, nenhum
  alerta. Só os chamados de cobrança em dobro, escalados pelo atendimento, viram bug, que sobe para alto e crítico com os chamados
  ligados: 16 saem por correção no ar (mediana de 21 h, 90% em 3 dias) e 4 de carona.
- **memória** (as sessões nunca saem do cache; 15 episódios). A memória cresce em dias até o processo cair; com duas quedas em 24
  horas, alerta de memória e bug crítico. Sai por correção no ar (6, mediana de 4,4 dias, 90% em 9 dias), pela liberação regular (6,
  mediana de 6 dias, 90% em 12 dias: a classe mais persistente) ou de carona (3).

A causa de um erro ou chamado é o defeito quando a exceção nasce na função defeituosa (o chamado guarda o instante e a função do
erro que o motivou).

### `incidentes` (o produto parado por volume do banco cheio)

| campo | o que é |
|---|---|
| `inicio`, `fim`, `duracao_min` | da primeira à última falha seguida da sonda |
| `causa` | "volume do banco cheio" |
| `onde` | a sonda, o espaço livre do banco e os erros de todas as rotas |
| `primeiro_chamado`, `chamados`, `primeira_escalacao`, `escalacoes` | os chamados e escalações que ele causou |
| `chamados_por_rota_de_origem` | (v2.1) quantos desses chamados vieram de cada rota (a rota em que o cliente sentiu o erro) |
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
"processo parado" e `onde` = a sonda e os reinícios do servidor. Os chamados que nasceram dela contam em `chamados_por_causa`
como "queda do processo" (antes da v2.1 caíam em "outros").

### `chamados` (v2.1, um por chamado)

| campo | o que é |
|---|---|
| `t`, `item`, `componente`, `motivo` | quando o chamado chegou, o item no fluxo, o componente e o motivo ("erro", "lentidão", "dúvida", "fatura", "cobrança em dobro", "nota não emitida", "cancelamento") |
| `origem` | para erro e lentidão: `{rota, processo, instante, evento}`, a rota e o minuto em que o cliente sentiu o erro (desistiu depois de tentar de novo) ou a lentidão (mais de 4 segundos); `null` nos outros motivos |
| `causa` | "defeito", "incidente", "queda do processo", "rota com erro" (sem defeito, incidente nem queda), "rota lenta" (sem defeito lento nem incidente) ou "outros" (sem rota por trás) |
| `registro_da_causa` | o episódio de defeito (`funcao`, `liberado_em`), o incidente ou a queda (pelo `inicio`) |
| `janela_de_rota` | o `inicio` da janela de rota de onde veio |
| `escalado_em` | quando o atendimento o escalou (no incidente, ao item do incidente; com defeito, ao bug) |

O chamado de lentidão numa rota que chama uma função com defeito lento no ar é do defeito. O cliente sente o produto parado alguns
minutos antes de a sonda declarar o incidente; o chamado cujo erro aconteceu até 10 minutos antes do início do incidente é dele.

### `causas` (v2.1): causa declarada, causa comum, sem relação

- `leis`: uma lei por rota e por evento. `de`: os campos da rota (erro: "respostas com erro no minuto"; lentidão: "latência média em
  ms" e "latência do percentil 95 em ms"). `para`: os campos dos chamados do componente da rota ("novos no minuto", "abertos",
  "escalados", "resolvidos no minuto") e, no erro, "sessões abandonadas depois de erro no minuto". `mecanismo` e `atraso` por campo:
  o chamado chega com atraso lognormal de mediana 12 minutos (90% em até 32, 99% em até 70); a escalação vem quando o atendimento o
  pega (minutos a horas); a resolução, horas depois. Rota e componente: login e conta → login e conta; catálogo, busca e produto →
  catálogo e busca; carrinho e pedido → pedido e carrinho; frete → frete; pagamento → pagamento; notas fiscais → fiscal; relatório e
  exportação → relatórios.
- `janelas_de_rota`: os trechos em que clientes sentiram erro ou lentidão numa rota (eventos a menos de uma hora um do outro):
  `rota`, `tipo` ("erro" ou "lentidão"), `inicio`, `fim`, `duracao_min`, `sessoes_afetadas`, `contextos` ("incidente", "queda do
  processo", "defeito", "erro sem defeito", "rota lenta"), `de` e `para` (os pares da lei, categoria "causa declarada"),
  `chamados_gerados`, `chamados_escalados` e `chamados` (os itens). Uma janela sem chamado mostra a lei ativa e não realizada (os
  chamados são sorteados por cliente).
- `campos_quando_o_produto_para`: os campos que se mexem juntos num incidente ou numa queda do processo (as rotas, a sonda, o servidor,
  o banco, a fila, as integrações, pedidos e pagamentos, as sessões, regiões e planos, os canais, os chamados de todos os componentes,
  o Suporte, o fluxo do atendimento e da operação).
- `categorias` e `ordem`: um par `[processo, campo] → [processo, campo]` é, na ordem:
  1. **causa declarada**, quando uma lei o liga e agiu no intervalo olhado (há janela de rota nele; sem intervalo, em algum momento
     da vida), ou quando o `onde` de um episódio de defeito no ar no intervalo o liga; a lei que não agiu aparece nas provas, sem
     contar como causa;
  2. **causa comum (incidente)** ou **causa comum (queda do processo)**, quando os dois campos estão em `campos_quando_o_produto_para`
     e o intervalo olhado encosta num incidente ou numa queda (até seis horas depois do fim, enquanto os chamados chegam e são
     escalados);
  3. **causa comum (calendário)**, quando os dois campos são movidos pelo calendário (abaixo): o mesmo relógio mexe nos dois, pelo
     mesmo motor ou por motores diferentes; as provas dizem os motores em comum e a correlação dos perfis por hora da semana;
  4. **sem relação**, nenhuma das anteriores.
  `causas.classificar_par(verdade, de, para, inicio, fim)` devolve a primeira categoria que vale, todas as que valem e as provas
  (as janelas da lei no intervalo, o incidente, os motores em comum e a correlação dos perfis). Exemplo, num incidente: "rota login, respostas com erro" →
  "chamados de login e conta, escalados" é causa declarada; "rota catálogo, respostas com erro" → "chamados de login e conta,
  escalados" é causa comum (incidente).

### `calendario` (v2.1): o que o calendário move em cada campo

- `motores`: as regras do mundo que dependem do relógio, com os números do código: horário das lojas, semana das lojas, fim do mês das
  lojas, pagamento das faturas, expediente das pessoas, agenda fixa, sprint, liberações, tarefas do servidor, mês da empresa,
  horário do mercado.
- `campos`: para cada `processo.campo`, `motores` e `caminhos` (cada motor com o caminho pelo qual chega ao campo) e a força medida:
  `fracao_da_variancia` (a parte da variância do campo, minuto a minuto, que a hora da semana explica, na empresa normal),
  `controle_embaralhado_pelo_relogio_da_porta` (a mesma conta no nulo embaralhado, onde o calendário não corresponde ao relógio: o
  piso do acaso), `embaralhado_pelo_calendario_interno` (no mesmo nulo, contada pelo calendário em que as pessoas vivem: mostra que é o
  calendário que move) e `movido_pelo_calendario`.
- `regra`: o campo é movido pelo calendário quando tem motor declarado e a fração passa de 0,05, é ao menos o dobro da do controle e
  fica ao menos 0,05 acima dela (nos campos que se acumulam devagar, como chamados abertos e horas extras do dia, o acaso sozinho
  já explica uma fração maior, e o controle mostra quanto).
  Dois campos movidos são **causa comum (calendário)**; `calendario.correlacao_dos_perfis(a, b)` dá a correlação dos seus perfis
  (perto de 1, sobem e descem juntos; perto de -1, um sobe quando o outro desce).
- `medida`: as sementes e os dias medidos e o viés do acaso. Os perfis (168 médias por campo, uma por hora da semana, de segunda 0h a
  domingo 24h) ficam em `registros/calendario.json`, que `python -m organizacao.mundo.v2.calendario` refaz.

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
| `rota`, `componente` | a rota e o componente que o texto cita (ou `null`); a rota é lida como sempre (nome exato do processo, componente ou palavras); (v2.2) o componente também sai do processo citado ("chamados de notificações", "bugs de infraestrutura") |
| `entendido` | (v2.2) o que a equipe entendeu do texto inteiro: `{processo, campo, rota, componente, tipo, desde, desde_texto}`. `processo` e `campo` pelos nomes de `processos()` (qualquer processo; o campo também pelo nome curto, sem a unidade, e por alguns nomes de uso: "erros", "latência", "percentil 95", "requisições"); `tipo` do pedido: "olhar e dizer", "corrigir ou reverter", "pôr à frente da fila" ou `null` (sem nenhum desses, a equipe faz o que sempre fez); `desde`: o instante de que o texto fala ("desde o dia 12, 10h", "há duas horas", "nas últimas 3 horas", "desde ontem", "desde as 9h", "depois da liberação"), e `desde_texto` o trecho lido |
| `pediu_esclarecimento` | (v2.2) `true` quando o pedido não nomeia nada que a equipe reconheça (rota, componente, processo, campo ou as palavras do trabalho dela) e a equipe respondeu perguntando em vez de agir; aí `efeito.util` é `null` |
| `virou` | `{sistema, item}`: o item criado no fluxo, no CRM ou no quadro |
| `demora_ate_ficar_disponivel_min`, `disponivel_em` | a demora da equipe naquele momento e o instante em que o ato pôde ser pego |
| `equipe_ao_receber`, `equipe_ao_tratar` | o estado da equipe (abaixo) nos dois momentos |
| `pego_em`, `tratado_em`, `minutos_de_trabalho` | quando alguém pegou, quando respondeu, quanto trabalho custou |
| `trabalho_adiado` | `{tarefa, item, minutos_que_faltavam, pessoa}`: o que a pessoa largou para tratar o pedido (atrasou o tempo do pedido); `null` se ela estava livre |
| `efeito` | `{util, acoes, encurta, nao_encurta, colateral}` (abaixo) |
| `confianca_antes`, `confianca_depois` | a confiança da equipe em quem pede, antes e depois deste ato |
| `resposta` | o texto devolvido pela porta (o pedido começa com "Pedido tratado."; (v2.2) o pedido não entendido, com "Pedido não entendido:", e a pergunta "qual rota, qual processo, qual campo?") |
| `desfecho` | "respondido" ou "sem resposta" (com `expirou_em`: o fim do expediente do dia útil seguinte) |
| `horas_extras_atribuidas` | `{t, pessoa, equipe, minutos, onde}`: hora extra que alguém fez porque o dia foi tomado por pedidos |

O **`efeito`**: `util` diz se o pedido resolveu algo (`true`/`false`; `null` em pergunta e convocação); (v2.2) `antecipou_min`, só
nos pedidos, é `reverteria_sozinha_em` menos o instante da saída real do defeito quando a saída veio por este pedido (a reversão que
ele pediu, `saiu_pelo_ato`), e `null` nos outros; `acoes` é o que a equipe fez
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

### `opcoes` e `agenda_calada` (v2.3, só quando alguma opção está ligada)

`opcoes`: `{porta, relogio, agenda_calada}`, as opções com que o mundo foi criado (ver `CONTRATO.md`). Desligadas todas, a chave não
aparece e a verdade é a da v2.2.

`agenda_calada`: `{pedido: {inicio, fim}, datas, inicio, fim, como, onde}`. `pedido` é o trecho declarado; `datas` são os dias do
relógio da porta cuja meia-noite cai nele (os dias de feriado); `inicio` e `fim` são o trecho efetivo, da meia-noite da primeira data
à meia-noite depois da última. Nesses dias `dia_util` da verdade por minuto é 0: ninguém trabalha, a agenda não marca nem realiza
reunião, não há evento de equipe, os clientes usam o produto como num domingo. O que o calendário move em cada campo está em
`calendario.campos`.

Os processos das opções (`porta da equipe de X`, `relógio`) não têm verdade própria: são contagens do que a porta fez (os atos e as
respostas estão em `atos`) e o relógio da porta.

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
| `chamados_de_outra_causa` | chamados abertos neste minuto sem rota por trás (dúvida, fatura, cobrança, nota que não chegou) |
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
| `chamados_por_queda` | (v2.1) chamados abertos neste minuto que nasceram da queda do processo |
| `chamados_por_rota_lenta` | (v2.1) chamados abertos neste minuto que nasceram de lentidão sentida numa rota, sem defeito nem incidente |
| `chamados_por_rota_com_erro` | (v2.1) chamados abertos neste minuto que nasceram de erro numa rota, sem defeito, incidente nem queda |
| `sessoes_com_erro.<rota>` | (v2.1) sessões que desistiram por erro na rota neste minuto (uma coluna por rota) |
| `sessoes_lentas.<rota>` | (v2.1) sessões que sentiram a rota acima de 4 segundos neste minuto (uma coluna por rota) |
| `<equipe>.atos_na_fila` | atos esperando a equipe |
| `<equipe>.atos_em_tratamento` | pessoas da equipe tratando um ato agora |
| `<equipe>.cansaco` | cansaço da equipe (0 descansada; sobe com hora extra e com pedidos) |
| `<equipe>.atencao` | atenção já gasta pela porta na equipe |
| `<equipe>.confianca` | confiança da equipe em quem pede (0,4 a 1,6; 1 neutra) |
| `<equipe>.ocupacao` | ocupação da equipe (gente presa em reunião ou urgência, e a fila regular) |
| `<equipe>.demora_de_pedido` | minutos que um pedido levaria agora até alguém da equipe pegá-lo |

`<equipe>` é uma das sete: produto, desenvolvimento, qualidade, atendimento, vendas, operação, gestão. São 109 colunas (82 até a v2.1; as novas vêm depois, sem mudar a posição das antigas). A descrição
de cada uma também vem em `verdade()["verdade_por_minuto"]["colunas"]`.

## Os nulos na verdade

- **sem_defeito**: nenhuma liberação leva defeito; os episódios de erro seguidos de chamados são só os incidentes.
- **embaralhado**: `ciclos` traz os blocos do calendário sorteado; `data_do_calendario` e `minuto_do_calendario` mostram o calendário
  vivido minuto a minuto.
- **sem_deriva**: sem teto, platô nem expansão (`teto_inicial` nulo, `teto_do_mercado` 0); cada entrada leva a uma saída.
- **surdo**: nenhum ato chega ao mundo; `atos` fica vazio e as colunas das equipes mostram só o trabalho regular.
- **paciente** (v2.2): as equipes não têm atenção, cansaço nem confiança. A demora de um ato é só a base da equipe esticada pela
  ocupação (`base x (1 + 1,5 x ocupação)`), a duração do trabalho não estica, a confiança fica em 1 (não sobe nem desce, e a
  verificação é sempre inteira) e os pedidos não lançam hora extra (`horas_extras_atribuidas` vazio). As colunas `<equipe>.cansaco` e
  `<equipe>.atencao` ficam em 0 e `<equipe>.confianca` em 1. Tudo o mais é a vida normal: sem atos, os minutos são os da vida normal
  da mesma semente, byte a byte (a empresa, os defeitos e a deriva). A ocupação continua: quem trata um ato está ocupado.
