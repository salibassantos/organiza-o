# A verdade das famílias das escolas (v2.3)

`mundo.verdade()` existe só para a bancada: nada dela sai pela porta. Convenções de todas as famílias: instantes são minutos `t` da
porta (`t = 0` é a criação, segunda-feira, 0h; cada `passo()` faz o minuto `t`); durações em minutos; `onde` é uma lista de pares
`[processo, campo]` com os nomes de `processos()`; `null` quer dizer "ainda não aconteceu" ou "não se aplica". O topo de toda verdade
tem `familia`, `semente`, `nulo`, `minutos`, `estrutura` (a lei sorteada pela semente), `leis` (as ligações declaradas: de onde, para
onde, com que atraso) e `observacao_do_nulo`.

O relógio como campo vale em todas: com `relogio=True` (ou `MUNDO_RELOGIO=1`) o último processo é `relógio` (hora do dia, dia da
semana, minuto do mundo); desligado, o mundo é o mesmo, byte a byte.

As famílias com voz entregam as linhas por `vozes() -> [(t, canal, texto)]` (as que chegaram desde a última chamada), e a contagem
delas como campo do processo do canal. Os atos de quem observa entram por `receber(equipe, tipo, texto)` e as respostas saem por
`respostas() -> [(t, número, equipe, texto)]`, como no mundo.

## Os tipos de campo (`base.py`)

O vocabulário comum: `contagem` (por minuto, ruído de Poisson), `nível` (fila, abertos, presentes, volume; ruído normal), `latência`
(em ms, ruído de 8% para cada lado), `taxa` (em %, ruído normal) e `carteira` (uma contagem grande que anda devagar). O nome do campo
é do mundo; o tipo é da família. `estrutura` traz, por campo, `{tipo, base, desvio_do_ruido}`: o "desvio" de todo tamanho declarado é
o desvio do ruído no nível daquele instante.

## Escola 1: um campo (`escola1.py`)

Processos (de 1 a 3): `<coisa> <do lugar>`, de tipos diferentes, com 1 a 4 campos. Nulos: `sem_incidente`, `sem_regime`, `sem_deriva`
(cada um tira só a sua lei; as outras ficam nos mesmos instantes).

| campo | o que é |
|---|---|
| `incidentes` | `{inicio, fim, duracao_min, onde, sentido ("subiu" ou "caiu"), tamanho_em_desvios, nivel_antes, lei}`: o campo sai do lugar de repente e volta |
| `mudancas_de_regime` | `{t, onde, sentido, tamanho_em_desvios, patamar_antes, patamar_depois, lei}`: um patamar novo para sempre |
| `deriva` | `{onde, inicio, taxa_por_semana, sentido, lei}`: o nível multiplicado por (1 + taxa) a cada semana; `null` no nulo |
| `estrutura.leis` | as faixas sorteadas: incidente a cada 2 a 6 dias, de 30 a 300 minutos, de 4 a 12 desvios; 1 ou 2 regimes de 3 a 8 desvios; deriva de 3% a 12% por semana |

Um acontecimento para baixo que levaria o campo abaixo de 40% da base, ou a menos de três desvios do zero, vai para cima (o tamanho
declarado é o que aconteceu).

## Escola 2: causa e efeito (`escola2.py`)

Processos (de 2 a 8): `<coisa> <do lugar>`, um campo cada (contagem ou nível). Nulos: `embaralhado`, `sem_ligacao`.

| campo | o que é |
|---|---|
| `estrutura.processos` | `{nome, campo, tipo, base, desvio_do_ruido, disparos_por_dia (os espontâneos), amplitude_desvios, volta_min}` |
| `ligacoes` | `{de, para, atraso_tipico_min, folga (de 0,8 a 1,2 vezes), chance_de_passar, nasce, morre, intermitente}`; a intermitente nasce entre o 2º e o 5º dia e morre entre o 9º e o 14º |
| `causas_comuns` | `{origem, efeitos}`: dois processos movidos pelo mesmo, sem que um mova o outro |
| `disparos` | `{t, onde, causa ("sozinho", "ligação" ou o do nulo), ligacao (o índice em ligacoes), origem {t, onde}}` |

## Escola 4: o tempo (`escola4.py`)

Processos (de 1 a 4): `<coisa> <do lugar>`, com 1 ou 2 campos, cada um com 1 ou 2 ciclos. Nulos: `embaralhado`, `periodo_fixo`.

| campo | o que é |
|---|---|
| `ciclos` | `{onde, periodo_min, fase_primeiro_pico, amplitude, amplitude_em_desvios, muda_em, periodo_depois_min}`: o nível mais amplitude vezes cos(2 pi (t - fase) / período); os períodos vão de 60 minutos a 13 dias, longe de um dia e de uma semana |
| `mudancas_de_periodo` | os ciclos que já mudaram de período (a fase continua no instante da mudança) |

## Escola 3: gente que responde (`escola3.py`)

Processos (de 7 a 12): por equipe, `quadro da <equipe>` (presentes agora; horas extras no dia), `fluxo da <equipe>` (itens abertos;
itens criados no minuto) e `porta da <equipe>` (textos chegados no minuto; itens abertos); por máquina, `<máquina>` (produção no
minuto; falhas no minuto; fila). Nulos: `surdo`, `paciente`, `ninguem_resolve`.

| campo | o que é |
|---|---|
| `estrutura.equipes.<nome>` | `pessoas`, `expediente` (minuto do dia de chegada e de saída), `almoco`, `trabalha_sabado_de_manha`, `rendimento` ("resolve", "às vezes", "nunca"), `chance_de_resolver`, `sabe_tratar_o_defeito`, `demora_base_resposta_min`, `demora_base_tratamento_min`, `itens_regulares_por_minuto_de_expediente` |
| `estrutura.maquinas`, `estrutura.defeito` | as máquinas (produção e falha de base) e a lei do defeito recorrente: a máquina, o intervalo entre episódios, as falhas a mais por minuto, a manutenção programada |
| `leis` | por equipe: o ato volta como texto em `porta`; o ato vira item em `fluxo` e em `porta: itens abertos`; o pedido custa hora extra em `quadro` (não no paciente); a presença decide quando ela responde; e o pedido certo tira o defeito |
| `episodios_de_defeito` | `{inicio, fim, maquina, onde, manutencao_programada_em, saiu_por ("ato" ou "manutenção"), saiu_pelo_ato, reverteria_sozinha_em, antecipou_min, causa}`; o ramo sem ato é a manutenção programada |
| `atos` | `{numero, equipe, tipo, texto, recebido, demora_min, disponivel_em, prazo, pego_em, tratado_em, desfecho ("respondido" ou "sem resposta"), efeito {util, encurta, colateral}, equipe_ao_receber, equipe_ao_tratar, confianca_antes, confianca_depois, horas_extras_atribuidas, resposta}` |
| `quartis_da_resposta` | por equipe, os quartis de `tratado_em - recebido` dos atos respondidos: a janela em que a sinapse "mandei a X, textos de X" tem de nascer (O1) |
| `interior_por_hora` | o estado de dentro de cada equipe, de hora em hora: fila, cansaço, atenção, confiança, ocupação (nunca sai pela porta) |

A demora de um ato é `base x (1 + 1,5 x ocupação) x (1 + 0,8 x cansaço) x (1 + 0,6 x atenção) / confiança`; a pergunta gasta 0,25 de
atenção e o pedido 0,5; pedido útil soma 0,15 à confiança (até 1,6), inútil tira 0,2 (até 0,4); o trabalho em curso só anda com gente
presente. No paciente nada disso existe e os pedidos não lançam hora extra.

Exemplo (semente 1, 3 dias):

```json
{"familia": "escola3", "semente": 1, "nulo": null, "minutos": 4320,
 "estrutura": {"equipes": {"equipe da Estação": {"pessoas": 3, "expediente": [425, 956], "rendimento": "nunca", "chance_de_resolver": 0.0,
                                                 "sabe_tratar_o_defeito": false, "demora_base_resposta_min": 72.0, "...": "..."},
                           "equipe do Farol": {"pessoas": 2, "rendimento": "resolve", "chance_de_resolver": 0.905, "sabe_tratar_o_defeito": true, "...": "..."}},
               "maquinas": [{"nome": "tear da Fonte", "producao": 2.19, "falha_base": 0.0131}],
               "defeito": {"maquina": "tear da Fonte", "intervalo_dias": [2.0, 6.0], "falhas_a_mais_por_minuto": 3.29, "manutencao_depois_de_horas": [10, 60]}},
 "episodios_de_defeito": [{"inicio": 2029, "fim": 2925, "maquina": "tear da Fonte", "onde": [["tear da Fonte", "falhas no minuto"], ["tear da Fonte", "fila"]],
                           "manutencao_programada_em": 2925, "saiu_por": "manutenção", "saiu_pelo_ato": null, "reverteria_sozinha_em": 2925, "antecipou_min": 0}],
 "atos": [{"numero": 1, "equipe": "equipe da Estação", "tipo": "pedido", "recebido": 2041, "...": "..."}]}
```

## A escola da presença (`presenca.py`)

Processos: `canal <do canto>` (linhas chegadas no minuto) e `luz <do canto>` (nível, que segue o dia). As linhas por `vozes()`. Quem
observa escreve no canal com `receber(<canal>, "linha", texto)`. Nulos: `sorteado`, `surdo`, `calada`.

| campo | o que é |
|---|---|
| `estrutura.costume` | `dias_da_semana` em que ela vem, `chega_em_min` (minuto do dia), `variacao_da_chegada_min`, `fica_min` (de quanto a quanto), `linhas_por_minuto_presente`, `chance_de_faltar_num_dia_dela`, `semanas_fora` |
| `estrutura.contingencia` | `chance_de_responder` a uma linha dele quando ela está e `atraso_min` |
| `estrutura.vocabulario` | as palavras das linhas dela (sem sentido: sorteadas sem relação com nada) |
| `presencas` | `{inicio, fim, onde, causa}`: cada vez que ela veio |
| `linhas` | `{t, texto, causa}`: cada linha dela; a causa é "o costume dela" ou "resposta à linha N dele" |
| `linhas_dele` | `{numero, t, canal, texto, chegou, ela_presente, respondida_em}` |

## A escola do corpo (`corpo.py`)

Processos (de 2 a 4): `<coisa> <do lugar>` (nível; avisos no minuto). Cada um tem a sua mão (`mão <coisa> <do lugar>`, a equipe de
`receber`). Nulos: `surda`, `calma`. A eferência embaralhada é nulo da bancada.

| campo | o que é |
|---|---|
| `estrutura.processos` | `{nome, mao, lei ("volta sozinho" ou "só volta com ato"), lugar, ruido, desvio (de quanto a quanto), constante_de_tempo_min ou atraso_do_ato_min}` |
| `estrutura.rajadas`, `rajadas` | a lei das rajadas (intervalo, duração, um desvio a cada quantos minutos) e cada rajada `{inicio, fim}` (vazia no nulo calma) |
| `episodios` | `{inicio, processo, lei, onde, tamanho (a soma dos desvios do episódio), na_rajada, fim, saiu_por ("sozinho" ou "ato"), saiu_pelo_ato, reverteria_sozinha_em, antecipou_min, atos_que_o_tocaram}`. O ramo sem ato: um campo que volta sozinho voltaria em `reverteria_sozinha_em` (a volta exata do desvio somado, minuto a minuto); um que só volta com ato não voltaria (`null`) |
| `atos` | `{numero, equipe, tipo, texto, recebido, processo, efeito {util, por_que, encurta, efetivo_em, reverteria_sozinha_em, antecipou_min, sem_o_ato}, resposta, respondido_em}` |

## A família da voz, o berçário (`voz.py`)

Processos (de 2 a 4): de um a três `<coisa> <do lugar>` (nível) e `canal da voz` (linhas chegadas no minuto). As linhas por `vozes()`.
Nulos: `hora_sorteada`, `vocabulario_permutado`, `voz_surda`.

| campo | o que é |
|---|---|
| `estrutura.processos` | `{nome, palavra (o nome curto que a voz usa), patamar, ruido, intervalo_horas}` |
| `estrutura.vocabulario` | cada palavra e o que ela significa: o processo, o acontecimento ("subiu", "desceu", "pulou", "parou", "voltou"), "agora", "de novo", "muito", os artigos |
| `acontecimentos` | `{t, processo, campo, acontecimento, tamanho, de_novo}` |
| `linhas` | `{t, texto, refere {processo, campo, acontecimento, instante}}`: a referência de cada linha (no nulo de hora sorteada, a linha não fala do seu instante) |

Exemplo (semente 1, 1 dia): `{"t": 42, "texto": "turbina pulou", "refere": {"processo": "turbina da Várzea", "campo": "nível",
"acontecimento": "pico", "instante": 41}}`.

## Conferir e identidade

`python -m organizacao.escolas.familias.conferir [sementes] [dias]` confere as três sementes de cada família (ver o próprio arquivo) e
grava `registros/conferencia.json` e `registros/hashes.json`, o hash dos minutos de cada semente sem atos. Um dia de mundo leva de 0,01
a 0,05 segundo de máquina. As escolas 1, 2 e 4 entraram em 22/10 depois das outras quatro; os hashes destas não mudaram.

No corredor de escolas (`organizacao/escolas.py`), o módulo se chama `familias.<nome>` com `organizacao/escolas` no caminho (o nome
`escolas` sozinho já é o arquivo `escolas.py`): por exemplo `PYTHONPATH=organizacao/escolas python organizacao/escolas.py corredor
<pasta> familias.escola3 7 1`. As sete passaram pelo corredor em sequência (liga, vive, desliga), com o ser de hoje, sem erro.
