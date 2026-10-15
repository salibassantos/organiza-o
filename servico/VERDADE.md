# A verdade do mundo do serviço, campo a campo

`Mundo.verdade()` devolve o que o serviço teve de fato, do minuto 1 ao minuto atual: o que aconteceu, onde (pares
`[processo, campo]` com os nomes de `processos()`), quando (instantes `t`), por quanto tempo e por causa de quê. É só para a bancada:
nada dela sai pela porta.

**Convenções.** `t = 0` é a criação (segunda-feira, 0h); cada `passo()` avança `t` e faz acontecer o minuto `t`. Durações em minutos
(`_min`) ou dias (`_dias`). `onde` lista os campos em que o acontecimento aparece. `null` quer dizer "ainda não aconteceu" (um incidente
ou uma degradação em curso tem `fim: null`). Os efeitos de troca são multiplicadores sobre o que estava no ar.

## O topo

| campo | o que é |
|---|---|
| `familia`, `semente`, `nulo`, `minutos`, `convencao_do_tempo` | o mundo e o minuto atual |
| `estrutura` | o que a semente sorteou: `modelo` (latência fixa e por token, espalhamento, taxas de erro, recusa e repetição), `classes` (tokens de entrada e saída, ferramentas por pedido, fator de recusa, se é a classe nova), `segmentos` (clientes, chamadas por cliente por minuto, paciência, chance de reenvio e de chamado, fuso, perfil por hora em cada dia da semana), `ferramentas` (chance de falha), capacidade inicial e preços |
| `ciclos` | o ciclo do dia e da semana (o perfil de cada segmento está em `estrutura.segmentos`); no nulo embaralhado, os blocos do calendário sorteado |
| `trocas_de_versao` | cada troca da versão do modelo |
| `mudancas_de_instrucao` | cada mudança das instruções do sistema |
| `incidentes_de_carga` | cada incidente de carga |
| `degradacoes` | cada degradação lenta |
| `classes_novas` | a classe de pedido que aparece |
| `mudancas_de_capacidade` | as mudanças de capacidade pedidas por atos |
| `atos` | cada ato recebido pela porta |
| `causas` | as leis declaradas, os campos do ciclo, a atividade por hora e as três categorias de ligação |
| `observacao_do_nulo` | nos nulos, o que muda |

### `trocas_de_versao` e `mudancas_de_instrucao`

| campo | o que é |
|---|---|
| `t` | o minuto da troca |
| `de`, `para` | a versão (ou as instruções) antes e depois |
| `efeito` | o multiplicador de cada variável: `latencia`, `erro`, `recusa`, `repeticao`, `tamanho_saida`, `ferramentas` (as instruções só mexem em `recusa` e `tamanho_saida`); 1 quer dizer sem mudança |
| `sobem`, `descem` | as variáveis que subiram e as que desceram |
| `onde` | os campos dessas variáveis: latência média e percentil 95 de cada classe; erros internos de cada classe e do serviço; recusas e repetições de cada classe; tokens de saída de cada classe, do serviço e o custo de processamento; chamadas de cada ferramenta |
| `causa` | "troca programada da versão do modelo", "mudança programada das instruções do sistema", ou a reversão pedida por um ato |
| `pedida_pelo_ato` | o número do ato que pediu a troca, ou `null` |
| `reinicio` (só versão) | `{inicio, fim, onde}`: por dois minutos o serviço tem 60% da capacidade (fila e tempo esgotado) |

As versões sobem às terças e quintas entre 14h e 17h, de 10 a 30 dias uma da outra; as instruções mudam em dias úteis entre 10h e 17h,
de 5 a 20 dias uma da outra. Cada troca mexe em pelo menos duas variáveis (uma, nas instruções), cada uma de 25% a 75% para cima ou
para baixo; nenhuma variável sai de 0,41 a 2,46 vezes o valor da criação.

### `incidentes_de_carga`

`{inicio, fim, duracao_min, tipo, segmento, forca, chamadas_a_mais_por_minuto, onde, causa}`. Dois tipos, no horário de movimento (9h
a 17h), de 4 a 14 dias um do outro, de 20 a 180 minutos: **pico de chamadas** (os clientes de um segmento mandam chamadas a mais que
somam de 0,8 a 2 vezes a capacidade em trabalho; `forca` é esse múltiplo) e **perda de capacidade** (o serviço fica com 15% a 35% da
capacidade; `forca` é essa fração). `onde`: a fila, a espera, o tempo esgotado, o processador, a latência e o tempo esgotado de cada
classe e, no pico, as chamadas recebidas, as rejeitadas por limite e as chamadas do segmento.

### `degradacoes`

`{inicio, fim, duracao_dias, variavel, aumento_no_fim, forma, onde, causa}`. A `latencia` ou a `repeticao` cresce em linha reta do
início ao fim, até `1 + aumento_no_fim` vezes, e volta ao normal no fim (a manutenção). Duram de 14 a 35 dias, a primeira começa entre
o 3º e o 20º dia, e as seguintes de 20 a 60 dias depois do fim da anterior.

### `classes_novas`

`{t, classe, rampa_ate, processos, onde, causa}`. A classe nova está em `processos()` desde o minuto 0 (a lista não muda enquanto o
mundo anda), com todos os campos a zero até `t`; de `t` a `rampa_ate` o tráfego dela cresce em linha reta até a parte sorteada de cada
segmento. Aparece entre o 8º e o 35º dia, às 10h.

### `atos`

| campo | o que é |
|---|---|
| `numero`, `equipe`, `tipo`, `texto`, `recebido` | o ato como chegou (no passo seguinte ao `receber()`) |
| `acao` | "pergunta", "reverter versão", "voltar instruções", "aumentar capacidade" ou "sem ação" |
| `executado_em`, `efetivo_em` | quando a equipe agiu (a operação em 5 a 25 minutos, as outras em 20 a 120) e quando a mudança valeu |
| `util`, `por_que` | se o ato resolveu algo, e por quê: a versão no ar era pior que a anterior; as instruções no ar recusavam mais; o serviço estava apertado na última hora (uso acima de 90%, fila ou mais de 2% de falhas) |
| `encurtou` | os campos que o ato encurta |
| `piorou_de_lado` | os campos que pioram por causa dele: as melhoras da versão desfeita, o reinício, o custo de capacidade |
| `custo` | o custo dito em palavras (o reinício, os reais por minuto a mais) |
| `resposta`, `respondido_em` | o texto que voltou pela porta e quando |

Os pedidos que a porta entende: à operação, reverter a versão ("reverter", "voltar" com "versão" ou "modelo") e aumentar a capacidade
("capacidade", "escala", "máquina", "servidor"); à operação ou ao produto, voltar as instruções ("instruções", "prompt"). Toda pergunta
é respondida com as medidas da última hora daquela equipe.

### `causas`: três categorias de ligação

- `leis`: cada lei com `nome`, `de`, `para`, `atraso`, `mecanismo` e `fonte` (a atividade que a faz agir). As leis: a falha de uma
  classe volta como reenvio (de 1 a 4 minutos); a recusa pelo limite volta como reenvio; a falha vira chamado no atendimento (atraso
  lognormal de mediana 30 minutos); a resposta ruim vira avaliação negativa (de 1 a 10 minutos); a fila atrasa as respostas e leva ao
  tempo esgotado; a carga ocupa o servidor e custa; a capacidade custa e encurta a fila; a falha de uma ferramenta vira erro; a
  implantação reinicia o serviço; as chamadas de cada segmento entram pela porta.
- `campos_do_ciclo`: os campos que se mexem com a hora e o dia da semana (todos, menos a capacidade, o custo de capacidade e as
  implantações).
- `atividade_por_hora`: por hora, a soma de cada fonte (falhas, recusas e repetições, fila, falhas de ferramenta, implantações).
- `categorias` e `ordem`: um par `[processo, campo] → [processo, campo]` olhado num intervalo é, na ordem:
  1. **causa declarada**, quando uma lei o liga e a fonte dela teve atividade no intervalo;
  2. **causa comum**: incidente de carga (os dois no `onde` de um incidente que encosta no intervalo, até quatro horas depois do fim),
     troca de versão ou mudança de instrução (os dois no `onde`, do instante a um dia depois), degradação (os dois no `onde`, durante
     ela), classe nova (os dois da classe nova, na rampa) ou **ciclo** (os dois em `campos_do_ciclo`);
  3. **sem relação**, nenhuma das anteriores.
  `servico.classificar_par(verdade, de, para, inicio, fim)` devolve a primeira categoria que vale, todas as que valem e as provas.

## Os nulos

- **embaralhado**: os clientes e o atendimento vivem num calendário sorteado em blocos de 25 a 240 minutos; nenhum ciclo corresponde
  ao relógio da porta; as leis com instante e as leis causais ficam (os instantes são os mesmos do mundo normal).
- **sem_troca**: nenhuma troca programada de versão nem de instruções; incidentes, degradações e a classe nova nos mesmos instantes.
- **sem_degradacao**: nenhuma degradação; o resto nos mesmos instantes.
- **surdo**: `receber()` devolve número e nada chega ao mundo; `atos` fica vazio e `respostas()` também.

## Exemplo (semente 1, 21 dias, com um ato; listas cortadas em "...")

```json
{
 "familia": "servico", "semente": 1, "nulo": null, "minutos": 30240,
 "incidentes_de_carga": [
  {"inicio": 16627, "fim": 16764, "duracao_min": 137, "tipo": "pico de chamadas", "segmento": "uso pessoal", "forca": 1.939,
   "chamadas_a_mais_por_minuto": 36.1,
   "onde": [["porta de entrada", "fila de espera"], ["porta de entrada", "espera na fila em ms"], ["erros do serviço", "tempo esgotado no minuto"], "..."],
   "causa": "os clientes de uso pessoal mandaram chamadas a mais que somam 1.9 vezes a capacidade do serviço em trabalho"}],
 "degradacoes": [
  {"inicio": 14970, "fim": null, "duracao_dias": 28.9, "variavel": "repeticao", "aumento_no_fim": 0.664,
   "forma": "cresce em linha reta do início ao fim e volta ao normal no fim",
   "onde": [["qualidade de agente com ferramentas", "repetições"], ["qualidade de extração de dados", "repetições"], "..."],
   "causa": "desgaste lento do serviço (repetições), corrigido na manutenção do fim"}],
 "classes_novas": [
  {"t": 12120, "classe": "resumo de documentos", "rampa_ate": 22200,
   "processos": ["pedidos de resumo de documentos", "qualidade de resumo de documentos"],
   "onde": [["pedidos de resumo de documentos", "chamadas recebidas"], ["pedidos de resumo de documentos", "chamadas atendidas"], "..."],
   "causa": "os clientes passaram a pedir resumo de documentos; o tráfego dela cresce em linha reta por 7 dias"}],
 "atos": [
  {"numero": 1, "equipe": "operação do serviço", "tipo": "pedido", "texto": "aumentem a capacidade do serviço", "recebido": 16628,
   "acao": "aumentar capacidade", "executado_em": 16648, "efetivo_em": 16648, "util": true,
   "por_que": "na última hora o serviço passou de 90% de uso, teve fila ou mais de 2% de falhas",
   "encurtou": [["porta de entrada", "fila de espera"], ["porta de entrada", "espera na fila em ms"], "..."],
   "piorou_de_lado": [["custo do serviço", "custo de capacidade no minuto em reais"], ["serviço do modelo", "capacidade em mil tokens por minuto"]],
   "custo": "o custo de capacidade sobe de 0.05 para 0.07 reais por minuto",
   "resposta": "Pedido tratado. A capacidade passou de 13.0 para 19.4 mil tokens por minuto.", "respondido_em": 16653}],
 "causas": {"leis": [
  {"nome": "falha de agente com ferramentas volta como reenvio",
   "de": [["qualidade de agente com ferramentas", "tempo esgotado"], ["qualidade de agente com ferramentas", "erros internos"]],
   "para": [["clientes de uso pessoal", "reenvios no minuto"], ["clientes de integrações automáticas", "reenvios no minuto"],
            ["pedidos de agente com ferramentas", "chamadas recebidas"], ["porta de entrada", "chamadas recebidas"]],
   "atraso": "de 1 a 4 minutos (45% no minuto seguinte)", "fonte": "falhas",
   "mecanismo": "o cliente que recebe tempo esgotado ou erro reenvia a mesma chamada com a chance de reenvio do seu segmento"}, "..."]}
}
```

No intervalo desse incidente, `classificar_par` dá:

| de | para | categorias |
|---|---|---|
| qualidade de agente com ferramentas, tempo esgotado | clientes de uso pessoal, reenvios no minuto | causa declarada (e ciclo) |
| porta de entrada, fila de espera | qualidade de tradução, tempo esgotado | causa declarada (e incidente de carga, e ciclo) |
| porta de entrada, fila de espera | avaliações dos clientes, avaliações positivas no minuto | causa comum (ciclo) |
| implantação, implantações no minuto | clientes de uso pessoal, clientes distintos no minuto | sem relação |
