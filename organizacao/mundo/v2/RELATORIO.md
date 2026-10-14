# Relatório do mundo v2

O v2 é uma pasta nova ao lado do v1 (`organizacao/mundo/v2/`), importada e instanciada do mesmo jeito
(`from organizacao.mundo.v2 import Mundo`; `Mundo(semente, nulo)`). Nada no v1 nem fora da pasta do v2 mudou. A empresa é a mesma do
v1 (as mesmas 50 pessoas, os mesmos sistemas, os mesmos 131 processos e 495 campos), com as mudanças abaixo. O contrato está em
`CONTRATO.md`, a verdade campo a campo em `VERDADE.md` e a descrição completa em `LEIA-ME.md`.

## 1. O que mudou

| pedido | onde | como |
|---|---|---|
| a porta com equipe e resolução | `mundo.py` | `Processo(nome, campos, equipe, resolucao)`; a equipe responsável de cada processo e o passo mínimo de cada campo |
| mundo com consequência | `equipes.py`, `atos.py`, `pessoas.py` | cada equipe é um agente com fila, capacidade, cansaço, atenção e confiança; demoras próprias e estáveis; o pedido passa na frente e a pessoa larga o que fazia (o trabalho largado fica suspenso e atrasa); a pergunta gasta atenção; pedido inútil baixa a confiança (a próxima demora cresce e a equipe verifica por cima), pedido útil a sobe; quem passou o dia em pedidos fica além da hora |
| o efeito na verdade | `atos.py`, `verdade.py` | cada tratamento devolve o que a equipe fez, se resolveu, os campos que encurta, os que não encurta e o custo colateral; a reversão pedida por um ato fica ligada ao episódio do defeito |
| ramos | `mundo.py` | o mundo é função da semente e da sequência de entradas (atos e campanhas, com instantes); cada carga de um estado salvo ganha a sua própria pasta de história |
| deriva que assenta | `mundo.py` | teto do mercado; a chegada de leads seca perto dele; platô; o dono abre mercado novo e a carteira volta a crescer, até 2,6 vezes o teto inicial |
| disco que não mata | `clientes.py` | as escritas dos clientes no banco do produto não levantam exceção com o volume cheio: a conta nova espera e é gravada depois, as atualizações são refeitas de hora em hora; o volume cheio continua sendo um incidente tratado pela operação |
| verdade por minuto em disco | `verdade.py` | `dia_NNNNN.npz` (1440 x 82) e `dia_NNNNN.json` (os registros que ficaram definitivos e os eventos humanos do dia) |
| campanha | `mundo.py`, `clientes.py` | `injetar_campanha(inicio, duracao, forca)`: sessões, catálogo, dúvidas que viram chamado e leads do site |
| vida longa | `arquivo.py` e um `arquivar` em cada sistema; `pessoas.py`, `clientes.py` | retenção nos seis bancos (marcos semanais), expurgo semanal do produto como tarefa agendada, a empresa esquece itens fechados, pessoas que saíram e versões velhas, os clientes que saíram são esquecidos depois de 90 dias e as suas vagas nos vetores são reaproveitadas, as contagens da carteira andam com as entradas e saídas, as férias são sorteadas ano a ano, e o produto prepara as tarefas do backlog (no v1 elas ficavam paradas para sempre) e limpa o backlog parado há mais de 60 dias quando ele passa de 40 itens |
| testes, provas e medidas | `test_mundo_v2.py`, `provas.py`, `vida_longa.py` | 15 testes do próprio mundo; as provas e a medida deste relatório |

Também veio do consumidor a mudança da v1.3 (a sorte própria de cada pessoa para os atos e a sorte das histórias), para que um ato não
mude a sorte do trabalho regular de quem o trata.

## 2. A verdade, campo a campo

Está inteira em `VERDADE.md`. Em resumo, cada registro diz o que aconteceu, onde (`onde`: pares `[processo, campo]` com os nomes da
porta), quando (instantes `t`), por quanto tempo (`duracao_min`, `saiu_do_ar`, `fim`) e por causa de quê (`causa`, `saiu_por`,
`pedida_pelo_ato`, `saiu_pelo_ato`). Os registros novos do v2: `atos` completos (demora, quem pegou, o trabalho adiado, o efeito, a
confiança antes e depois, as horas extras atribuídas), `platos` e `expansoes` da deriva, `campanhas`, `cadastros_adiados_por_volume_cheio`
e a verdade por minuto (82 colunas: defeitos no ar por componente, causa dos erros e dos chamados, produto parado, volume, teto do
mercado e fase da deriva, campanha, pressa, e o estado de cada equipe).

## 3. Vida longa: memória e custo a 365 dias

`python -m organizacao.mundo.v2.vida_longa --dias 365 --semente 1 --saida <pasta>` (resultado em `registros/vida_longa.json` e
`registros/verdade_resumo.json`). A vida recebe um ato por dia útil às 10h (em rodízio pelas sete equipes, quase todos sem problema
de verdade por trás) e um dia de campanha por mês. Medidas a cada 30 dias, numa máquina de quatro núcleos (nos primeiros 40 dias
outras corridas dividiam a máquina):

| até o dia | clientes ativos | segundos por dia simulado | ms por cliente por dia | memória do processo (MB) | banco do produto (MB) | fluxo (MB) | pasta de história (MB) | linhas: pedidos | auditoria | itens abertos no fluxo | clientes em memória | registros da verdade em memória |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 30 | 463 | 3.75 | 8.1 | 79.7 | 25.44 | 0.8 | 3.2 | 30679 | 332259 | 237 | 467 | 63 |
| 60 | 481 | 5.54 | 11.5 | 96.7 | 39.2 | 1.46 | 6.7 | 64041 | 622128 | 221 | 488 | 52 |
| 90 | 508 | 5.81 | 11.4 | 117.4 | 56.67 | 2.16 | 10.2 | 97528 | 679164 | 231 | 518 | 66 |
| 120 | 514 | 6.33 | 12.3 | 135.9 | 65.07 | 2.84 | 13.7 | 133250 | 807680 | 224 | 526 | 39 |
| 150 | 542 | 7.38 | 13.6 | 146.7 | 80.5 | 3.29 | 17.2 | 171532 | 898212 | 271 | 553 | 56 |
| 180 | 573 | 8.05 | 14.0 | 166.4 | 97.53 | 3.68 | 20.8 | 212467 | 1048468 | 314 | 586 | 63 |
| 210 | 580 | 8.45 | 14.6 | 184.8 | 109.64 | 3.93 | 24.3 | 224884 | 972480 | 174 | 592 | 44 |
| 240 | 603 | 8.67 | 14.4 | 197.9 | 118.61 | 4.0 | 27.8 | 239965 | 695924 | 291 | 622 | 69 |
| 270 | 628 | 9.16 | 14.6 | 197.0 | 119.13 | 4.31 | 31.3 | 254907 | 468103 | 310 | 646 | 57 |
| 300 | 645 | 9.05 | 14.0 | 197.2 | 119.13 | 4.54 | 34.9 | 266905 | 616305 | 306 | 661 | 57 |
| 330 | 657 | 10.05 | 15.3 | 202.3 | 123.3 | 4.75 | 38.4 | 272961 | 693800 | 282 | 673 | 43 |
| 360 | 667 | 9.78 | 14.7 | 205.7 | 126.38 | 4.82 | 41.9 | 285805 | 831281 | 301 | 681 | 39 |

Total: 365 dias em 2.810 segundos (7,7 segundos por dia simulado em média), memória máxima do processo 227 MB, pasta de história de
45 MB (730 arquivos, perto de 0,12 MB por dia).

**O que a medida mostra.**
- **Nada cresce com a idade por construção.** Os pedidos, notas e e-mails param de crescer por cliente quando a retenção de 180 dias
  passa a valer; a auditoria sobe e desce com o ciclo dos incidentes (cada incidente a corta para os últimos dias); os itens abertos
  no fluxo ficam entre 170 e 320; os registros da verdade em memória ficam entre 39 e 69; os clientes em memória são os ativos mais
  os que saíram há menos de 90 dias.
- **O custo por minuto é o custo da carteira.** Do dia 180 em diante o custo por cliente por dia fica entre 14,0 e 15,3 ms; o que
  ainda sobe é a carteira (de 573 para 667 clientes), e com ela o tempo por dia e o banco do produto. A carteira tem teto: o mercado
  para em 2,6 vezes o teto inicial (1.240 clientes nesta semente), o que dá, pela mesma proporção, perto de 18 segundos por dia e
  perto de 350 MB no limite (projeção, não medida). O custo de cada minuto também varia com a versão no ar: funcionalidades e defeitos
  mudam o trabalho do código (é a lei das mudanças de regime).
- **Uma medida anterior achou um vazamento real** e ele foi corrigido antes desta: o backlog do produto crescia sem limite (as tarefas
  do backlog nunca andavam e o produto escrevia histórias sem teto), e os itens abertos passavam de mil no fim do ano. Com a
  preparação das tarefas e a limpeza do backlog (seção 1), eles ficam estáveis.

**O que a vida teve** (de `registros/verdade_resumo.json`): 13 incidentes de volume cheio, todos tratados (dias 24, 49, 78, 101,
130, 161, 191, 226, 262, 291, 317 e 344, com duas quedas seguidas no dia 191), nenhum derrubou o mundo; teto inicial de 477
clientes, platô do dia 29 ao 105, expansão decidida no dia 79 (teto 640, valendo no dia 105), segundo platô do dia 257 ao 348,
expansão decidida no dia 329 (teto 740); 205 liberações (71 com defeito) e 28 mudanças de regime; 12 campanhas; 261 atos, todos
respondidos, só 5 pedidos úteis. A memória das equipes ficou: a confiança caiu nas que receberam pedidos sem problema por trás
(operação 0,58, produto 0,63, desenvolvimento e qualidade 0,67) e ficou em 1 onde os pedidos eram úteis ou eram perguntas.

## 4. Prova de determinismo e de retomada

`python -m organizacao.mundo.v2.provas <pasta>` (resultado em `registros/provas.json`). Semente 1, sete dias (t = 1 a 10.080), os
cinco atos de exemplo da primeira semana e um dia de campanha (dia 3, das 8h às 18h):

| vida | o que é | resultado |
|---|---|---|
| A | corrida inteira | hash dos 10.080 minutos `5de1ae313e404305...` |
| B | outra corrida inteira, outro objeto | o mesmo hash, as mesmas 5 respostas, a mesma verdade, a mesma verdade por minuto, os mesmos eventos |
| C | corre até t = 4.980 (no meio do dia de campanha, com atos ainda na fila), salva, carrega numa pasta de história nova e continua | os mesmos 10.080 hashes por minuto que A, as mesmas respostas, a mesma `verdade()`, a mesma verdade por minuto, os mesmos eventos humanos |

Os testes repetem a prova numa vida menor (`TesteDeterminismo`), e `conferir.py` repete a vida em outro processo do sistema, com
outra semente de hash do Python.

## 5. Prova de ramos

Tronco: semente 2, salvo em t = 4.800 (dia 3, quinta-feira, 8h). Cada ramo carrega o mesmo estado salvo, numa pasta de história
própria, e anda até t = 7.680:

| ramo | atos | hash dos minutos |
|---|---|---|
| A | t = 4.860: pedido à operação "Verifiquem a rota pagamento"; t = 4.920: pedido à qualidade "Refaçam os testes do catálogo" | `cb61cfef9994ba54...` |
| A, de novo | os mesmos | `cb61cfef9994ba54...` (igual) |
| B | t = 4.860: pedido ao atendimento "Priorizem os chamados de frete"; t = 4.890: convocação à gestão | `c08f54b613e73637...` |
| B, de novo | os mesmos | `c08f54b613e73637...` (igual) |
| C | nenhum (o caminho surdo daquele ponto) | `fde3862ab2905988...` |

A e B são reproduzíveis, os três caminhos são diferentes, e A e B se separam de C exatamente no minuto 4.860, quando o primeiro ato
vira coisa dentro do mundo; antes disso os três são o mesmo mundo. O que custou cada ato (da verdade de cada ramo):

| ramo | ato | demora até ficar disponível | pego | tratado | trabalho | trabalho adiado | hora extra atribuída | resolveu |
|---|---|---|---|---|---|---|---|---|
| A | pedido à operação | 31 min | 4.891 | 4.979 | 74 min | uma tarefa interna com 38 min por fazer | 35 min | não (nenhum defeito em pagamento) |
| A | pedido à qualidade | 115 min | 5.035 | 5.066 | 32 min | nenhum (a pessoa estava livre) | nenhuma | não |
| B | pedido ao atendimento | 71 min | 4.931 | 4.966 | 36 min | uma tarefa interna com 19 min por fazer | 18 min | não (havia menos de três chamados de frete) |
| B | convocação à gestão | 144 min | 5.084 | 5.088 | 5 min | nenhum | nenhuma | (reunião marcada para 13h30 com 4 pessoas) |

## 6. Prova de consequência: o pedido certo encurta, o inútil custa

Para medir o efeito com um problema de verdade, a prova anda a semente 1 até haver um defeito que quebra (exceção), no ar há pelo
menos uma hora, vindo com a última liberação, num dia útil entre 9h e 17h. O primeiro é `calcular_frete` na implementação que lê o
CEP como número (o frete quebra para CEP que começa com zero), liberado em t = 25.395. Do estado em t = 25.455 saem três ramos, e
cada um anda dois dias:

| ramo | o defeito ficou no ar depois do ramo | saiu por | erros da rota frete em 2 dias | chamados novos de frete | confiança da operação no fim | demora de um pedido à operação no fim |
|---|---|---|---|---|---|---|
| pedido certo ("Verifiquem a rota frete") | 88 min | reversão pedida pelo ato 1 | 98 | 3 | 1,135 | 46,3 min |
| pedido inútil ("Verifiquem a rota login") | 1.023 min | correção do desenvolvimento | 228 | 10 | 0,82 | 64,1 min |
| sem ato | 1.087 min | correção do desenvolvimento | 290 | 11 | 1,0 | 52,5 min |

No ramo do pedido certo a operação pegou o ato 21 minutos depois, rodou os testes de frete na versão no ar, viu a falha, abriu o bug
como crítico e reverteu; a verdade do ato diz `util: true` e lista como encurtados os erros das rotas do componente e o abandono de
sessões, e como não encurtados os chamados já abertos e escalados (que continuaram: 2,0 abertos em média, contra 2,8 sem ato). O
pedido inútil custou o mesmo trabalho, não encurtou nada, baixou a confiança da operação em quem pede e deixou a próxima resposta
mais lenta. As pequenas diferenças entre o ramo inútil e o ramo sem ato (o defeito saiu 64 minutos antes) são o caminho que se
separou: o trabalho largado e retomado muda o resto do dia.


## 7. Testes

`python -m unittest organizacao.mundo.v2.test_mundo_v2`: 15 testes, perto de dois minutos, todos passam. Cobrem o contrato da porta
(equipe, resolução, valores na grade da resolução, erros de entrada), duas vidas iguais e a retomada no meio, os ramos (reproduzíveis,
diferentes entre si, iguais até o minuto do ato, cada um com a sua pasta), o nulo surdo como o caminho sem atos, a equipe ocupada,
cansada ou desconfiada que demora mais, a verdade inteira de cada ato com campos que existem na porta, o volume cheio com conta de
cliente adiada e gravada depois sem exceção, a campanha com início, fim e efeito, o platô e a expansão, o nulo sem_deriva sem teto, os
arquivos de um dia que não mudam mais, e os quatro nulos andando. `conferir.py` também passa inteiro.

## 8. Limites

- A medida do efeito de um ato é a comparação de ramos; o trabalho largado e retomado muda o resto do dia, então o ramo com o ato e o
  ramo sem ele se afastam também em campos que o ato não toca. A verdade diz o mecanismo (o que encurta, o que não encurta, o custo
  colateral); o tamanho do efeito se mede comparando.
- O custo cresce com a carteira até o teto do mercado; a medida de um ano não chegou ao teto.
- A mesma vida em outra máquina depende das mesmas versões de Python, numpy e SQLite (a contagem de instruções do SQLite entra na
  latência), como no v1.
- Sem a opção `historia`, cada mundo escreve a sua história numa pasta temporária que o sistema não apaga sozinho.

## 9. v2.1: a causa dos chamados e o que o calendário move

Só a verdade mudou; o mundo é o mesmo. Os minutos e as respostas de dez vidas de três dias (os cinco nulos, sementes 1 e 2, com atos)
deram os mesmos hashes antes e depois, e as provas da seção 4 e 5 dão os mesmos hashes de minutos.

- **A causa dos chamados.** Cada chamado guarda a rota e o instante em que o cliente sentiu o erro ou a lentidão que o motivou, e a sua
  causa (defeito, incidente, queda do processo, rota com erro, rota lenta, outros). A verdade declara a lei que liga o erro e a
  lentidão de cada rota aos chamados do componente da rota (novos, abertos, escalados, resolvidos) e às sessões abandonadas, com o
  mecanismo e o atraso, e registra as janelas em que a lei agiu e os chamados que gerou. Um par de campos cai em uma de três
  categorias: causa declarada, causa comum (incidente, queda do processo, calendário) ou sem relação; `causas.classificar_par` faz a
  conta. O gabarito do pesquisador (19 pares em três vidas sem defeito, todos em incidentes) bate: "rota login → chamados de login e
  conta" é causa declarada; os outros são causa comum pelo incidente. O contador "queda do processo" passou a contar.
- **O calendário.** Onze motores declarados com os números do código e, para cada um dos 495 campos, os motores que chegam a ele e
  por qual caminho. A força foi medida em três sementes de 42 dias na empresa normal e no nulo embaralhado: 185 campos são movidos
  pelo calendário (fração da variância explicada pela hora da semana acima de 0,05, ao menos o dobro do controle e 0,05 acima dele);
  nenhum campo aparece movido sem motor declarado. Os perfis por hora da semana estão em `registros/calendario.json`.
- **No v1.** A mesma correção da causa dos chamados (v1.4), com as gravações de `registros/semente1/` regravadas: os minutos ficaram
  idênticos e só `verdade.json` mudou.
