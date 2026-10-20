# Vidas de 90 dias sem atos, sementes 1 a 8

Gerado por `python -m organizacao.mundo.v2.noventa` (v2.2): oito vidas de 90 dias, sem atos, nulo normal, uma por semente
(`noventa vida <semente> <saida.json>`), e a tabela (`noventa tabela <pasta>`). Sem atos, a saída vivida é a saída sozinha
(`reverteria_sozinha_em` = `saiu_do_ar`).

O que a bancada precisa saber antes de dimensionar as vidas de aprovação:

- **Duas rotas não têm defeito nenhum em 90 dias**: rota produto e rota notas fiscais (nenhuma função com defeito no código é chamada
  por elas; os defeitos fiscais aparecem na fila de trabalhos, não na rota). A linha N não mede nelas.
- **Rotas com poucos defeitos**: catálogo (11 em 8 sementes), busca (12), relatório (10) e exportação (11), de 0 a 4 por semente.
  Em várias sementes ficam com zero ou um episódio em 90 dias.
- **Rotas com mais defeitos**: pedido (42), login (30), carrinho (22), frete (20), pagamento (20), conta (15).
- **Saídas que um pedido pode antecipar**: a reversão própria (a operação reverte sozinha em menos de uma hora e meia: sobra pouco
  para antecipar) é 75 dos 95 defeitos de exceção. Pagamento nunca é revertido sozinho em 90 dias (os defeitos dele são gravação
  dupla, que não dá erro, e saem por correção no ar em perto de um dia). As correções no ar levam de algumas horas a três dias (90%);
  a lentidão, até 21 dias; a memória fica até a liberação regular em 6 de 15 episódios.

Cada célula: episódios de defeito que chegam à rota (a rota chama a função com defeito) em 90 dias; entre parênteses, reversão própria / reversão de carona / correção no ar / liberação regular, e os que ainda estavam no ar no fim, se houver.

| rota | semente 1 | semente 2 | semente 3 | semente 4 | semente 5 | semente 6 | semente 7 | semente 8 | total |
|---|---|---|---|---|---|---|---|---|---|
| rota login | 2 (2/0/0/0) | 3 (2/0/1/0) | 4 (1/0/1/2) | 4 (3/1/0/0) | 4 (1/0/1/2) | 4 (1/1/0/2) | 6 (1/1/4/0) | 3 (3/0/0/0) | 30 (14/3/7/6) |
| rota catálogo | 1 (1/0/0/0) | 0 (0/0/0/0) | 1 (1/0/0/0) | 2 (2/0/0/0) | 2 (1/0/1/0) | 2 (2/0/0/0) | 0 (0/0/0/0) | 3 (3/0/0/0) | 11 (10/0/1/0) |
| rota busca | 1 (1/0/0/0) | 1 (1/0/0/0) | 0 (0/0/0/0) | 2 (1/0/1/0) | 1 (1/0/0/0) | 1 (1/0/0/0) | 2 (2/0/0/0) | 4 (4/0/0/0) | 12 (11/0/1/0) |
| rota produto | 0 (0/0/0/0) | 0 (0/0/0/0) | 0 (0/0/0/0) | 0 (0/0/0/0) | 0 (0/0/0/0) | 0 (0/0/0/0) | 0 (0/0/0/0) | 0 (0/0/0/0) | 0 (0/0/0/0) |
| rota carrinho | 3 (3/0/0/0) | 4 (4/0/0/0) | 0 (0/0/0/0) | 3 (2/0/1/0) | 4 (3/0/1/0) | 2 (2/0/0/0) | 2 (2/0/0/0) | 4 (3/0/1/0) | 22 (19/0/3/0) |
| rota frete | 2 (1/0/1/0) | 1 (1/0/0/0) | 1 (1/0/0/0) | 7 (7/0/0/0) | 2 (1/0/1/0) | 2 (0/0/2/0) | 4 (1/0/3/0) | 1 (0/0/1/0) | 20 (12/0/8/0) |
| rota pedido | 5 (4/0/1/0) | 5 (5/0/0/0) | 1 (1/0/0/0) | 10 (9/0/1/0) | 6 (4/0/2/0) | 4 (2/0/2/0) | 6 (3/0/3/0) | 5 (3/0/2/0) | 42 (31/0/11/0) |
| rota pagamento | 1 (0/0/1/0) | 3 (0/1/2/0) | 4 (0/0/4/0) | 4 (0/2/2/0) | 1 (0/0/1/0) | 5 (0/1/4/0) | 1 (0/0/1/0) | 1 (0/0/1/0) | 20 (0/4/16/0) |
| rota relatório | 1 (1/0/0/0) | 0 (0/0/0/0) | 0 (0/0/0/0) | 3 (1/1/1/0) | 2 (2/0/0/0) | 2 (0/1/1/0) | 2 (0/0/2/0) | 0 (0/0/0/0) | 10 (4/2/4/0) |
| rota exportação | 4 (0/3/1/0) | 0 (0/0/0/0) | 1 (0/0/1/0) | 4 (0/2/1/1) | 0 (0/0/0/0) | 0 (0/0/0/0) | 2 (0/0/2/0) | 0 (0/0/0/0) | 11 (0/5/5/1) |
| rota notas fiscais | 0 (0/0/0/0) | 0 (0/0/0/0) | 0 (0/0/0/0) | 0 (0/0/0/0) | 0 (0/0/0/0) | 0 (0/0/0/0) | 0 (0/0/0/0) | 0 (0/0/0/0) | 0 (0/0/0/0) |
| rota conta | 0 (0/0/0/0) | 2 (2/0/0/0) | 2 (0/0/2/0) | 3 (2/0/1/0) | 2 (1/0/1/0) | 6 (0/1/4/1) | 0 (0/0/0/0) | 0 (0/0/0/0) | 15 (5/1/8/1) |
| sem rota (fila de trabalhos, memória) | 13 (0/2/11/0) | 7 (0/1/6/0) | 12 (0/3/9/0) | 7 (0/4/3/0) | 11 (0/4/7/0) | 5 (0/1/4/0) | 10 (0/2/7/1) | 13 (0/3/10/0) | 78 (0/20/57/1) |
| todos os episódios | 28 (9/5/14/0) | 21 (10/2/9/0) | 25 (3/3/17/2) | 39 (18/10/10/1) | 29 (10/4/13/2) | 29 (6/5/15/3) | 29 (6/3/19/1) | 29 (13/3/13/0) | 229 (75/35/110/9) |

Um episódio que chega a duas rotas (frete e pedido, por exemplo) conta nas duas; a última linha conta cada um uma vez.

| semente | liberações | com defeito | reversões | correções no ar | carteira no fim | s por dia (média) | dias 1 a 10 | dias 81 a 90 | pior dia | memória máxima |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 54 | 22 | 9 | 14 | 489 | 5.77 | 3.84 | 7.49 | 15.21 | 151 MB |
| 2 | 47 | 13 | 6 | 9 | 473 | 5.65 | 3.85 | 6.45 | 8.67 | 133 MB |
| 3 | 50 | 20 | 3 | 17 | 465 | 5.76 | 3.89 | 6.64 | 8.92 | 136 MB |
| 4 | 55 | 18 | 13 | 10 | 457 | 6.00 | 4.15 | 7.04 | 11.76 | 140 MB |
| 5 | 53 | 17 | 9 | 13 | 470 | 6.39 | 4.10 | 8.22 | 20.41 | 145 MB |
| 6 | 52 | 20 | 6 | 15 | 456 | 6.53 | 4.06 | 6.62 | 23.09 | 136 MB |
| 7 | 56 | 18 | 5 | 19 | 482 | 6.27 | 4.13 | 7.20 | 14.86 | 142 MB |
| 8 | 56 | 21 | 11 | 13 | 471 | 6.20 | 4.27 | 7.47 | 10.01 | 138 MB |

Custo do mundo sozinho: 6.07 s de processador por dia simulado em média (9.1 minutos por vida de 90 dias), crescendo com a carteira.

## A saída sozinha, por classe de defeito

| classe | episódios | reversão própria | reversão de carona | correção no ar | liberação regular | no ar no fim | tempo no ar (mediana; 90%) por saída |
|---|---|---|---|---|---|---|---|
| exceção | 95 | 71 | 1 | 22 | 1 | 0 | reversão própria: 0.8 h; 1.3 h<br>reversão de carona: 0.7 h; 0.7 h<br>correção: 17.4 h; 3.0 dias<br>regular: 47.8 h; 47.8 h |
| lento | 21 | 4 | 7 | 9 | 1 | 0 | reversão própria: 1.0 h; 1.1 h<br>reversão de carona: 0.7 h; 2.8 h<br>correção: 2.9 dias; 21.0 dias<br>regular: 19.9 h; 19.9 h |
| fila | 78 | 0 | 20 | 57 | 1 | 0 | reversão de carona: 1.0 h; 1.8 h<br>correção: 23.1 h; 3.0 dias<br>regular: 20.1 h; 20.1 h |
| gravação dupla | 20 | 0 | 4 | 16 | 0 | 0 | reversão de carona: 0.8 h; 2.8 h<br>correção: 20.9 h; 3.1 dias |
| memória | 15 | 0 | 3 | 6 | 6 | 0 | reversão de carona: 0.8 h; 1.2 h<br>correção: 4.4 dias; 9.0 dias<br>regular: 6.0 dias; 12.0 dias |
