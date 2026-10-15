# O mundo do serviço (família "servico")

Um serviço de modelo de linguagem usado por clientes, visto só por medidas. O modelo é uma caixa com comportamento sorteado pela
semente; os clientes (de dezenas a milhares, em dois a cinco segmentos) mandam chamadas de várias classes no seu horário, esperam até a
paciência acabar e reenviam depois de erro. Nenhum texto sai pela porta: nem pedidos, nem respostas, nem instruções.

## A porta (a mesma do contrato dos mundos)

```python
from servico import Mundo, NULOS, FAMILIA, classificar_par

m = Mundo(1)                                  # ou Mundo(1, "embaralhado" | "sem_troca" | "sem_degradacao" | "surdo")
for p in m.processos():                       # de 20 a 60 processos: nome, campos, equipe, resolução por campo
    ...
valores = m.passo()                           # o minuto 1: {processo: [valores na ordem dos campos]}
n = m.receber("operação do serviço", "pedido", "aumentem a capacidade")
for t, numero, equipe, texto in m.respostas():
    ...
m.salvar("pausa"); m = Mundo.carregar("pausa")
v = m.verdade()                               # só para a bancada; formato em VERDADE.md
```

`m.t`, `m.dia()`, `m.minuto_do_dia()`, `m.dia_da_semana()` (0 = segunda), `m.equipes()` ("operação do serviço", "produto",
"atendimento") e `m.eventos_humanos()` como nos outros mundos.

## Os processos

Compostos pela semente: para cada classe de pedido, `pedidos de <classe>` (chamadas recebidas e atendidas, tokens de entrada e de
saída, latência média e percentil 95) e `qualidade de <classe>` (recusas, repetições, tempo esgotado, erros internos); para cada
segmento, `clientes de <segmento>` (clientes distintos, chamadas enviadas, reenvios, desistências); para cada ferramenta, `ferramenta
<nome>` (chamadas e falhas); e oito processos do serviço: `porta de entrada`, `serviço do modelo`, `erros do serviço`, `tokens do
serviço`, `custo do serviço`, `implantação`, `atendimento` e `avaliações dos clientes`. Equipes: operação do serviço, produto,
atendimento. Resolução: 1 para contagens, milissegundos e tokens; 0,1 para porcentagens e milhares de tokens; 0,01 para GB e reais.

## Conferir

```
python -m servico.conferir 60 1,2,3
```

Confere três sementes de 60 dias contra a verdade (trocas, incidentes, degradações, classe nova, ciclos), que cada nulo tira só a lei
dele, que as estruturas das sementes são diferentes, a mesma vida repetida e retomada, o nulo surdo e um ato útil. Grava
`registros/conferencia.json` e `registros/hashes.json` (o hash dos minutos de cada semente e de cada nulo). Um dia de mundo leva perto
de 0,6 segundo de máquina. Python 3.11 e numpy; nada de rede.
