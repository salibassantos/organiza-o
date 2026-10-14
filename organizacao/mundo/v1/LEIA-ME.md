# O mundo v1: uma empresa de software de 50 pessoas acontecendo no tempo

O mundo é a empresa inteira, com os seus sistemas funcionando como software de verdade, entregue minuto a minuto pela porta descrita
em `CONTRATO.md`. Ninguém sorteia "eventos" por cima: as pessoas trabalham nos sistemas, os clientes usam o produto, o código roda e
os bancos mudam. O que sai pela porta são medidas do que os sistemas fizeram. O que a empresa tem de verdade fica em `verdade()`,
separado, só para a bancada.

## O que o mundo tem

**O produto** (`produto.py`, `codigo.py`). É uma plataforma de compras para lojas, com doze rotas: login, catálogo, busca, produto,
carrinho, frete, pedido, pagamento, relatório, exportação, notas fiscais e conta. Tem banco de dados real (SQLite em memória, com
clientes, usuários, sessões, produtos, carrinhos, pedidos, pagamentos, notas, e-mails, faturas, fila de trabalhos e auditoria), uma
fila de trabalhos de fundo (nota fiscal, e-mail, fatura), tarefas agendadas pelo relógio da empresa (cópia de segurança às 2h,
limpeza de sessões às 3h, reposição de estoque dos fornecedores às 4h, reindexação aos domingos, resumo às 7h, faturamento no dia 1)
e um volume de disco com tamanho limitado.

Cada rota chama funções. Cada função tem implementações escritas em `codigo.py`, e uma versão do produto é a escolha de uma
implementação para cada função. Algumas implementações têm defeito, e o defeito é código errado de verdade:

| função | defeito | como aparece |
|---|---|---|
| normalizar_login | converte para ASCII | o login quebra para quem tem acento no nome de usuário |
| guardar_sessao | não expira o cache | a memória cresce até o processo cair |
| atualizar_conta | supõe telefone | a conta não salva para cliente sem telefone |
| paginar | cursor da última página | a última página incompleta do catálogo quebra |
| normalizar_termo | converte para ASCII | a busca quebra com termo acentuado |
| ler_quantidade | máscara de um algarismo | carrinho e pedido quebram com 10 ou mais unidades |
| calcular_frete | CEP como número | frete e pedido quebram para CEP que começa com zero (São Paulo) |
| registrar_cobranca | sem verificar pagamento anterior | o clique duplo cobra duas vezes (sem erro: aparece nos pagamentos e, horas depois, nos chamados) |
| emitir_nota | tabela de alíquotas só do Sul e Sudeste | a nota falha fora dessas regiões e a fila cresce; dias depois, chamados |
| montar_relatorio | lê todos os pedidos | o relatório fica lento e estoura quando a tabela cresce |
| exportar_csv | uma consulta por pedido | a exportação fica lenta |
| enviar_email | usa só o nome fantasia | o e-mail falha para cliente sem nome fantasia e a fila cresce |

Outras implementações são funcionalidades. Elas fazem mais (ou menos) trabalho e mudam para sempre o normal de uma rota. São
catorze no roteiro: recomendações no catálogo, antifraude no pedido, notas paginadas, índice de busca, relatório por item, senha
reforçada, duas transportadoras no frete, autenticação do pagador, registro de dispositivos, produtos relacionados, quarenta itens
por página, exportação compactada, busca por sinônimos e recomendações mais leves. Quando o roteiro acaba, ele recomeça como revisão.

A latência é função do que o código fez: idas e voltas ao banco, instruções que o banco executou (o SQLite avisa a cada dez),
trabalho da aplicação, espera pelos serviços de fora (gateway de pagamento, transportadoras, antifraude) e carga do processador.
O processador e a memória também são função do que as requisições, os trabalhos e as tarefas agendadas fizeram e do que o processo
guarda. O erro é a exceção acontecendo. Quando o volume enche, toda escrita falha com o erro do próprio SQLite ("database or disk is
full") e o produto cai.

**O repositório** (`repositorio.py`). Commits trocam a implementação de funções no ramo de cada item. O ramo entra no principal
quando a qualidade aprova. Uma versão sai do principal (liberação regular) ou da versão no ar mais a correção (correção no ar), e a
reversão volta à versão anterior. As execuções de testes e as revisões de código também ficam aqui.

**O fluxo de trabalho** (`fluxo.py`), tipo Jira, em SQLite. Tem os projetos Produto, Plataforma, Suporte e Infraestrutura e itens de
tipo épico, história, tarefa, bug e chamado, com estado por tipo, prioridade, componente, equipe responsável, pontos, prazo,
sprint, comentários, vínculo item-versão, ligações entre itens (chamado escalado para bug, bug causado por história), reaberturas e
o log de toda transição com instante e equipe. Sprints de duas semanas por projeto, com planejamento (meta e capacidade) e
retrospectiva. As contagens por projeto, tipo, estado, prioridade, componente e equipe são mantidas pelo próprio banco (gatilhos).

**Os clientes** (`clientes.py`). Começam entre 380 e 440 lojas, com plano (básico, pro, empresarial), usuários, CEP, horário de
funcionamento, intensidade de uso e satisfação. Os usuários abrem sessões no horário da loja (mais na segunda, menos na sexta, quase
nada no fim de semana, mais no fim do mês) e percorrem jornadas de compra, consulta, gestão, conta e recompra. Cada passo é uma
chamada de verdade ao produto. Quando o produto erra, o usuário tenta de novo e desiste; minutos depois alguns abrem chamado por
chat, e-mail ou telefone. Também abrem chamado por dúvida, fatura, cobrança em dobro e nota que não chegou. Respondem quando o
atendimento pergunta, pagam as faturas, cancelam quando ficam insatisfeitos e respondem a pesquisa de satisfação.

**As 50 pessoas** (`pessoas.py`). Produto (5), desenvolvimento (15, em dois squads), qualidade (6), atendimento (8), vendas (8),
operação (4) e gestão (o dono, o financeiro, pessoas e o administrativo). Cada pessoa tem papel, equipe, horário de chegada,
almoço, jeito de trabalhar, férias marcadas, faltas por doença, horas extras e aviso prévio. O que cada papel faz está no começo de
`pessoas.py`. A chance de um commit trazer defeito cresce com o tamanho do item e com a pressa do squad (o quanto falta no sprint
perto do que ainda dá para fazer). A pressa também encurta os testes e a revisão.

**A agenda** (`agenda.py`): diárias por equipe, planejamento, refinamento, revisão e retrospectiva por sprint, semanal das equipes,
liderança, mensal com o dono, reuniões com clientes (demonstrações e boas-vindas), entrevistas e alinhamentos (pós-incidente,
convocações da direção e da porta). Quem está em reunião não age nos sistemas.

**O quadro de pessoal** (`quadro.py`): pessoas, ponto (entradas e saídas registradas), ausências, horas extras, vagas, candidatos,
entradas e saídas, solicitações à gestão. **O CRM** (`crm.py`): negócios de lead a ganho ou perdido, atividades, tarefas internas.

**O relógio** (`relogio.py`): um instante por minuto, a partir de segunda-feira, 1º de junho de 2026. Os processos vivem pelo
calendário (a hora, o dia da semana, o dia do mês); no nulo "embaralhado" esse calendário é sorteado em blocos.

**A porta** (`mundo.py`, `conectores.py`, `atos.py`): a classe `Mundo` do contrato, os conectores que leem agregados dos sistemas e a
porta dos atos (v1.1).

## O que a empresa tem de verdade (e `verdade()` registra com instantes)

- **Ciclos.** O dia útil e o horário das lojas; a segunda-feira mais cheia (mais uso e chamados, inclusive os guardados do fim de
  semana); a sexta mais lenta; as liberações às terças e quintas a partir das 15h; o fim de sprint (pressa, liberação extra na sexta,
  burndown que zera); o fim do mês (mais vendas, mais relatórios e pedidos, faturamento no dia 1); as tarefas noturnas do servidor e
  a reindexação de domingo.
- **Contingências.** A liberação com defeito faz subir os erros da rota em minutos; depois chegam os chamados do componente (atraso
  humano de minutos), depois as escalações; por fim a reversão (quando o estrago é grande e veio com a liberação) ou a correção no ar
  (quando o desenvolvimento reproduz e corrige), e a volta. Defeitos silenciosos (cobrança em dobro, fila que cresce, consulta
  lenta) chegam por outros caminhos: a fila e a memória sobem, os chamados aparecem horas ou dias depois. O incidente de
  infraestrutura (o volume do banco enche) derruba o produto por dezenas de minutos e inunda o atendimento; a operação apaga
  auditoria velha e aumenta o volume com folga de três a cinco semanas, e o ciclo recomeça.
- **Derivas.** A carteira cresce (perto de 1% por semana, com degraus no fim do mês) e, com ela, o uso, os chamados, o banco e o
  processador.
- **Mudanças de regime.** A liberação que leva uma funcionalidade muda o normal de latência de uma rota para sempre (um degrau). Um
  sprint planejado acima da capacidade (o dono promete; um cliente grande pede) vira sprint de pressa, com horas extras, mais
  defeitos e menos teste.

O arquivo `verdade.json` de cada gravação traz tudo isso com instantes: `ciclos` (com os instantes dos fins de sprint e de mês, ou os
blocos do calendário embaralhado), `liberacoes`, `liberacoes_com_defeito`, `episodios_de_defeito_no_ar` (liberação, primeiro erro,
primeiro chamado, primeira escalação, saída do ar), `incidentes`, `mudancas_de_regime` (com a latência média dos sete dias antes e
depois), `deriva`, `sprints` e `sprints_de_pressa`, `defeitos_escritos`, `defeitos_barrados_antes_do_ar`, `pessoal`,
`chamados_por_causa` e `atos`. Desde a v1.4, também `chamados` (a rota e o instante que motivaram cada chamado e a sua causa) e
`causas` (as leis que ligam rota a chamados, as janelas em que agiram e as categorias de um par de campos; ver `CONTRATO.md`).

## Como se roda

Python 3.11 com numpy; o resto é biblioteca padrão (sqlite3). Nada de rede.

```python
import sys; sys.path.insert(0, "<pasta que contém organizacao>")
from organizacao.mundo.v1 import Mundo

m = Mundo(1)                       # ou Mundo(1, "sem_defeito" | "embaralhado" | "sem_deriva" | "surdo")
for p in m.processos():
    print(p.nome, p.campos)
valores = m.passo()                # o minuto 1: {processo: [valores na ordem dos campos]}
n = m.receber("operação", "pedido", "verifiquem a rota de frete")
...
for t, numero, equipe, texto in m.respostas():
    ...
m.salvar("pausa"); m = Mundo.carregar("pausa")
```

Sem observador:

```
python organizacao/mundo/v1/rodar.py <pasta> <dias> <semente> [nulo] [--atos arquivo.csv]
python organizacao/mundo/v1/conferir.py [minutos]       # confere a porta contra o contrato
```

`rodar.py` grava `minutos.csv.gz` (a linha `i` é o minuto `t = i`; cabeçalho "processo.campo"), `processos.json`, `verdade.json`,
`eventos_humanos.csv`, `custo.json` e, com atos, `atos.csv` e `respostas.csv`. O arquivo de atos tem cabeçalho `t,equipe,tipo,texto`;
há um exemplo em `atos_exemplo.csv`.

## As gravações em `registros/semente1/`

Cada pasta tem `minutos.csv.gz`, `processos.json`, `verdade.json`, `eventos_humanos.csv` e `custo.json`; as corridas com atos têm também `atos.csv` e `respostas.csv`. Todas com a semente 1.

| pasta | o que é | liberações (com defeito) | incidentes | mudanças de regime | sprints de pressa | carteira | tamanho |
|---|---|---|---|---|---|---|---|
| `normal_90_dias` | a empresa normal, 90 dias | 54 (20) | dia 24 09h55, dia 51 22h58, dia 78 08h06 | 8 | 5 | 440 a 493 | 14.4 MB |
| `sem_defeito_30_dias` | nulo sem_defeito, 30 dias | 11 (0) | dia 24 09h50 | 2 | 2 | 440 a 459 | 4.7 MB |
| `embaralhado_30_dias` | nulo embaralhado, 30 dias | 16 (5) | dia 25 17h57 | 2 | 1 | 440 a 454 | 4.7 MB |
| `sem_deriva_30_dias` | nulo sem_deriva, 30 dias | 19 (8) | dia 24 14h37 | 3 | 2 | 440 a 439 | 4.7 MB |
| `surdo_30_dias` | nulo surdo com o arquivo de atos de exemplo, 30 dias | 19 (8) | dia 24 09h55 | 2 | 2 | 440 a 460 | 4.8 MB |
| `atos_30_dias` | a empresa normal com o arquivo de atos de exemplo, 30 dias | 21 (8) | dia 24 10h54 | 3 | 1 | 440 a 464 | 4.7 MB |

A gravação do nulo surdo é idêntica, byte a byte, aos primeiros 30 dias da empresa normal: a porta surda aceita os atos e nada muda.
A corrida com atos usa os 22 atos de `atos_exemplo.csv` (perguntas, pedidos e convocações espalhados pelo mês, várias logo depois das
liberações das terças e quintas) e grava as respostas com instante. Comparada aos primeiros 30 dias da empresa normal, ela mostra o
efeito dos atos (reuniões, verificações, focos e reversões que não aconteceriam sozinhos).

A cópia de `verdade.json` e de `eventos_humanos.csv` da gravação normal de 90 dias também está em `organizacao/mundo/v1/`.

Para olhar uma gravação contra a sua verdade, com números simples (ciclo por hora e por dia da semana, correlação com o dia e a
semana anteriores, carteira, cada liberação com defeito, cada incidente, cada mudança de regime):

```
python organizacao/mundo/v1/olhar.py organizacao/mundo/v1/registros/semente1/normal_90_dias
```

## O que cada equipe faz com cada ato

O ato vira item no sistema da equipe no passo seguinte e entra na fila dela como qualquer item. Quem estiver livre na equipe (no
horário, fora de reunião, entre uma tarefa e outra) pega o primeiro da fila e gasta tempo nele: de 10 a 25 minutos numa pergunta, de
30 a 80 num pedido, de 5 a 12 para marcar uma convocação. Itens urgentes (bug crítico, incidente) passam na frente. O que não for
tratado até o fim do expediente do dia útil seguinte fica sem resposta.

| equipe | onde o ato vira item | pergunta: a resposta diz | pedido: a equipe faz |
|---|---|---|---|
| operação | tarefa no projeto Infraestrutura | versão no ar e há quanto tempo; requisições, erros e latência da rota citada na última meia hora; espaço livre no volume do banco; fila de trabalhos | roda a bateria inteira de testes do componente da rota contra a versão no ar; se algo falha, abre bug crítico e, se a falha veio com a última liberação, reverte para a versão anterior |
| qualidade | tarefa no projeto do componente citado | itens esperando teste; execuções, testes e falhas nas últimas 24 horas | refaz os testes do componente na versão no ar; se falham, abre bug e reabre a história que causou a falha |
| desenvolvimento | tarefa no projeto do componente citado | itens em andamento e em revisão; bugs abertos do componente | passa o bug aberto do componente para crítico (alguém larga o que faz e pega) ou, se não há bug, roda os testes e abre um crítico se algo falha |
| atendimento | chamado no projeto Suporte | chamados abertos e sem primeira resposta; abertos e escalados do componente | responde primeiro os chamados do componente nas quatro horas seguintes |
| produto | tarefa no projeto Produto | histórias no backlog, em refinamento e prontas | registra uma história com o texto do ato, prioridade alta |
| vendas | tarefa interna no CRM | negócios em cada etapa do funil; ganhos nos últimos sete dias | retoma primeiro as propostas e negociações paradas nos dois dias seguintes |
| gestão | solicitação no quadro | pessoas, presentes, de férias, vagas, candidatos, clientes ativos | a direção marca um alinhamento das lideranças no primeiro horário livre |

A convocação, para qualquer equipe, vira uma reunião de 30 minutos ("alinhamento") com todas as pessoas da equipe no primeiro horário
de expediente em que todas estão livres; a resposta diz o dia e a hora. Quem está nela não age nos sistemas enquanto dura.

O ato custa de verdade: a pessoa que o trata deixa de fazer outra coisa, a reunião tira a equipe dos sistemas, o pedido à operação
pode reverter uma versão, o foco do atendimento atrasa os outros chamados.

Na corrida `atos_30_dias` (semente 1):

- pergunta: 9 respondidos; atraso mediano de 27 minutos (de 10 a 89).
- pedido: 10 respondidos; atraso mediano de 62 minutos (de 35 a 127).
- convocacao: 3 respondidos; atraso mediano de 26 minutos (de 13 a 60).
- sem resposta: 0 de 22.

## Os processos e os campos

São 131 processos e 495 campos, sempre na mesma ordem. "No minuto" quer dizer o que aconteceu naquele minuto; os demais campos são
o estado naquele minuto. Nenhum campo é rótulo de normal ou anormal e nenhum vem de uma pessoa só.

**rota**. Uma por rota do produto. Requisições no minuto (dos usuários e da sonda da operação, que chama cada rota uma vez por minuto com dados de ensaio); respostas com erro (exceção no código, processo reiniciando, banco cheio); respostas recusadas pela regra do negócio (sem estoque, cartão recusado, pedido já pago, login desconhecido); latência média e do percentil 95 em milissegundos, calculadas do trabalho que o código fez; clientes distintos que chamaram a rota (sem a conta de monitoramento).

- `rota login`: requisições no minuto; respostas com erro no minuto; respostas recusadas no minuto; latência média em ms; latência do percentil 95 em ms; clientes distintos no minuto
- `rota catálogo`: requisições no minuto; respostas com erro no minuto; respostas recusadas no minuto; latência média em ms; latência do percentil 95 em ms; clientes distintos no minuto
- `rota busca`: requisições no minuto; respostas com erro no minuto; respostas recusadas no minuto; latência média em ms; latência do percentil 95 em ms; clientes distintos no minuto
- `rota produto`: requisições no minuto; respostas com erro no minuto; respostas recusadas no minuto; latência média em ms; latência do percentil 95 em ms; clientes distintos no minuto
- `rota carrinho`: requisições no minuto; respostas com erro no minuto; respostas recusadas no minuto; latência média em ms; latência do percentil 95 em ms; clientes distintos no minuto
- `rota frete`: requisições no minuto; respostas com erro no minuto; respostas recusadas no minuto; latência média em ms; latência do percentil 95 em ms; clientes distintos no minuto
- `rota pedido`: requisições no minuto; respostas com erro no minuto; respostas recusadas no minuto; latência média em ms; latência do percentil 95 em ms; clientes distintos no minuto
- `rota pagamento`: requisições no minuto; respostas com erro no minuto; respostas recusadas no minuto; latência média em ms; latência do percentil 95 em ms; clientes distintos no minuto
- `rota relatório`: requisições no minuto; respostas com erro no minuto; respostas recusadas no minuto; latência média em ms; latência do percentil 95 em ms; clientes distintos no minuto
- `rota exportação`: requisições no minuto; respostas com erro no minuto; respostas recusadas no minuto; latência média em ms; latência do percentil 95 em ms; clientes distintos no minuto
- `rota notas fiscais`: requisições no minuto; respostas com erro no minuto; respostas recusadas no minuto; latência média em ms; latência do percentil 95 em ms; clientes distintos no minuto
- `rota conta`: requisições no minuto; respostas com erro no minuto; respostas recusadas no minuto; latência média em ms; latência do percentil 95 em ms; clientes distintos no minuto

**servidor da aplicação**. Uso de processador (trabalho das requisições, da fila e das tarefas agendadas), memória do processo (base, cache de sessões, fila, registro de erros, linhas carregadas no minuto) e reinícios (liberação ou queda por memória).

- `servidor da aplicação`: uso de processador em %; memória em uso em MB; reinícios do processo no minuto

**banco do produto**. Tamanho ocupado pelo banco (páginas de 4 KB em uso), espaço livre no volume, consultas e escritas no minuto, e instruções que o banco executou, em milhares.

- `banco do produto`: tamanho ocupado em MB; espaço livre no volume em MB; consultas no minuto; escritas no minuto; instruções executadas em milhares

**fila de trabalhos**. A fila de fundo (notas fiscais, e-mails, faturas): pendentes, concluídos e falhas no minuto, e a idade do pendente mais antigo.

- `fila de trabalhos`: trabalhos pendentes; trabalhos concluídos no minuto; falhas de trabalho no minuto; idade do trabalho pendente mais antigo em minutos

**gateway de pagamento**. Chamadas à rota de pagamento e recusas do cartão no minuto.

- `gateway de pagamento`: chamadas no minuto; recusas no minuto

**transportadoras**. Cotações de frete feitas pelos clientes no minuto e as que terminaram em erro.

- `transportadoras`: cotações de frete no minuto; cotações com erro no minuto

**sonda de disponibilidade**. As verificações da operação (uma por rota por minuto) e quantas falharam.

- `sonda de disponibilidade`: verificações no minuto; verificações com falha no minuto

**implantação**. Implantações no minuto (liberação, correção ou reversão), commits e itens que entraram com ela.

- `implantação`: implantações no minuto; commits incluídos no minuto; itens incluídos no minuto

**tarefas agendadas do servidor**. Tarefas agendadas rodando e linhas que processaram no minuto.

- `tarefas agendadas do servidor`: tarefas em execução; linhas processadas no minuto

**e-mails do produto**. E-mails enviados e com falha no minuto.

- `e-mails do produto`: enviados no minuto; com falha no minuto

**pedidos**. Pedidos criados no minuto, o valor e o número de itens.

- `pedidos`: pedidos criados no minuto; valor dos pedidos no minuto em reais; itens nos pedidos do minuto

**pagamentos**. Pagamentos aprovados, pedidos distintos pagos e pagamentos recusados no minuto.

- `pagamentos`: pagamentos aprovados no minuto; pedidos pagos no minuto; pagamentos recusados no minuto

**notas fiscais**. Notas emitidas e emissões com falha no minuto.

- `notas fiscais`: notas emitidas no minuto; emissões com falha no minuto

**estoque**. Produtos sem estoque e unidades repostas pelos fornecedores no minuto.

- `estoque`: produtos sem estoque; unidades repostas no minuto

**sessões dos clientes**. Sessões abertas no minuto, sessões abandonadas depois de erro, sessões ativas e usuários conectados.

- `sessões dos clientes`: sessões iniciadas no minuto; sessões abandonadas depois de erro no minuto; sessões ativas; usuários conectados

**faturamento**. Faturas emitidas e pagas no minuto, faturas em aberto, estornos feitos pelo financeiro no minuto.

- `faturamento`: faturas emitidas no minuto; faturas pagas no minuto; faturas em aberto; estornos feitos no minuto

**região**. Uma por região do CEP: clientes ativos, pedidos, cotações de frete e cotações com erro no minuto.

- `região São Paulo`: clientes ativos; pedidos no minuto; cotações de frete no minuto; cotações com erro no minuto
- `região Rio de Janeiro e Espírito Santo`: clientes ativos; pedidos no minuto; cotações de frete no minuto; cotações com erro no minuto
- `região Minas Gerais`: clientes ativos; pedidos no minuto; cotações de frete no minuto; cotações com erro no minuto
- `região Norte e Nordeste`: clientes ativos; pedidos no minuto; cotações de frete no minuto; cotações com erro no minuto
- `região Centro-Oeste`: clientes ativos; pedidos no minuto; cotações de frete no minuto; cotações com erro no minuto
- `região Sul`: clientes ativos; pedidos no minuto; cotações de frete no minuto; cotações com erro no minuto

**carteira de clientes**. Clientes ativos, entradas e cancelamentos no minuto, pedidos de cancelamento ainda abertos na gestão.

- `carteira de clientes`: clientes ativos; entradas no minuto; cancelamentos no minuto; pedidos de cancelamento abertos

**clientes do plano**. Um por plano: clientes ativos, sessões ativas, pedidos e chamados abertos no minuto.

- `clientes do plano básico`: clientes ativos; sessões ativas; pedidos no minuto; chamados abertos no minuto
- `clientes do plano pro`: clientes ativos; sessões ativas; pedidos no minuto; chamados abertos no minuto
- `clientes do plano empresarial`: clientes ativos; sessões ativas; pedidos no minuto; chamados abertos no minuto

**pesquisa de satisfação**. Respostas à pesquisa depois do fechamento do chamado e a soma das notas (1 a 5) no minuto.

- `pesquisa de satisfação`: respostas no minuto; soma das notas no minuto

**canal de atendimento**. Um por canal: contatos recebidos no minuto.

- `canal de atendimento chat`: contatos recebidos no minuto
- `canal de atendimento e-mail`: contatos recebidos no minuto
- `canal de atendimento telefone`: contatos recebidos no minuto

**projeto Produto**. Os projetos de desenvolvimento no fluxo. Entrada: histórias no backlog e em refinamento, bugs abertos, épicos em andamento, tarefas no backlog. Desenvolvimento: itens em cada etapa. Movimento: criações, transições, liberações, reprovações (da revisão e da qualidade), reaberturas e comentários no minuto. Sprint: itens, pontos planejados (meta), pontos do sprint, concluídos e restantes, itens de prioridade alta ou crítica. Prioridades: itens abertos por prioridade. Idade: itens abertos e a idade média deles em horas.

- `projeto Produto: entrada`: histórias no backlog; histórias em refinamento; bugs abertos ou em triagem; épicos em andamento; tarefas no backlog
- `projeto Produto: desenvolvimento`: prontos para desenvolver; em desenvolvimento; em revisão; em qualidade; prontos para liberar
- `projeto Produto: movimento`: itens criados no minuto; transições no minuto; itens liberados no minuto; reprovações no minuto; reaberturas no minuto; comentários no minuto
- `projeto Produto: sprint`: itens no sprint; pontos planejados; pontos do sprint; pontos concluídos; pontos restantes; itens de prioridade alta ou crítica no sprint
- `projeto Produto: prioridades`: itens abertos de prioridade baixa; itens abertos de prioridade média; itens abertos de prioridade alta; itens abertos de prioridade crítica
- `projeto Produto: idade`: itens abertos; idade média dos itens abertos em horas

**projeto Plataforma**. Os mesmos campos, para o projeto Plataforma.

- `projeto Plataforma: entrada`: histórias no backlog; histórias em refinamento; bugs abertos ou em triagem; épicos em andamento; tarefas no backlog
- `projeto Plataforma: desenvolvimento`: prontos para desenvolver; em desenvolvimento; em revisão; em qualidade; prontos para liberar
- `projeto Plataforma: movimento`: itens criados no minuto; transições no minuto; itens liberados no minuto; reprovações no minuto; reaberturas no minuto; comentários no minuto
- `projeto Plataforma: sprint`: itens no sprint; pontos planejados; pontos do sprint; pontos concluídos; pontos restantes; itens de prioridade alta ou crítica no sprint
- `projeto Plataforma: prioridades`: itens abertos de prioridade baixa; itens abertos de prioridade média; itens abertos de prioridade alta; itens abertos de prioridade crítica
- `projeto Plataforma: idade`: itens abertos; idade média dos itens abertos em horas

**projeto Infraestrutura**. O projeto da operação: tarefas e bugs por estado, movimento, sprint, prioridades e idade.

- `projeto Infraestrutura: itens`: tarefas no backlog; tarefas prontas; em andamento; bugs abertos; concluídos no minuto
- `projeto Infraestrutura: movimento`: itens criados no minuto; transições no minuto; comentários no minuto
- `projeto Infraestrutura: sprint`: itens no sprint; pontos planejados; pontos do sprint; pontos concluídos; pontos restantes; itens de prioridade alta ou crítica no sprint
- `projeto Infraestrutura: prioridades`: itens abertos de prioridade baixa; itens abertos de prioridade média; itens abertos de prioridade alta; itens abertos de prioridade crítica
- `projeto Infraestrutura: idade`: itens abertos; idade média dos itens abertos em horas

**projeto Suporte**. O atendimento no fluxo: chamados por estado, movimento (novos, primeiras respostas, resolvidos, fechados, reabertos, comentários), prazos (fora do prazo de primeira resposta, espera do mais antigo sem resposta), prioridades, sprint e idade.

- `projeto Suporte: chamados por estado`: abertos sem primeira resposta; em atendimento; aguardando cliente; escalados; resolvidos aguardando fechamento
- `projeto Suporte: movimento`: chamados novos no minuto; primeiras respostas no minuto; resolvidos no minuto; fechados no minuto; reabertos no minuto; comentários no minuto
- `projeto Suporte: prazos`: chamados fora do prazo de primeira resposta; espera do chamado mais antigo sem resposta em minutos
- `projeto Suporte: prioridades`: chamados abertos de prioridade baixa; chamados abertos de prioridade média; chamados abertos de prioridade alta; chamados abertos de prioridade crítica
- `projeto Suporte: sprint`: itens no sprint; pontos planejados; pontos do sprint; pontos concluídos; pontos restantes; itens de prioridade alta ou crítica no sprint
- `projeto Suporte: idade`: chamados abertos; idade média dos chamados abertos em horas

**chamados de**. Um por componente: chamados abertos, novos no minuto, escalados, resolvidos no minuto.

- `chamados de login e conta`: abertos; novos no minuto; escalados; resolvidos no minuto
- `chamados de catálogo e busca`: abertos; novos no minuto; escalados; resolvidos no minuto
- `chamados de pedido e carrinho`: abertos; novos no minuto; escalados; resolvidos no minuto
- `chamados de frete`: abertos; novos no minuto; escalados; resolvidos no minuto
- `chamados de pagamento`: abertos; novos no minuto; escalados; resolvidos no minuto
- `chamados de fiscal`: abertos; novos no minuto; escalados; resolvidos no minuto
- `chamados de relatórios`: abertos; novos no minuto; escalados; resolvidos no minuto
- `chamados de notificações`: abertos; novos no minuto; escalados; resolvidos no minuto
- `chamados de infraestrutura`: abertos; novos no minuto; escalados; resolvidos no minuto

**bugs de**. Um por componente: bugs abertos, criados e liberados no minuto.

- `bugs de login e conta`: abertos; criados no minuto; liberados no minuto
- `bugs de catálogo e busca`: abertos; criados no minuto; liberados no minuto
- `bugs de pedido e carrinho`: abertos; criados no minuto; liberados no minuto
- `bugs de frete`: abertos; criados no minuto; liberados no minuto
- `bugs de pagamento`: abertos; criados no minuto; liberados no minuto
- `bugs de fiscal`: abertos; criados no minuto; liberados no minuto
- `bugs de relatórios`: abertos; criados no minuto; liberados no minuto
- `bugs de notificações`: abertos; criados no minuto; liberados no minuto
- `bugs de infraestrutura`: abertos; criados no minuto; liberados no minuto

**fluxo da equipe**. Um por equipe: itens abertos sob responsabilidade da equipe, transições, comentários e itens criados pela equipe no minuto.

- `fluxo da equipe de produto`: itens abertos sob responsabilidade da equipe; transições no minuto; comentários no minuto; itens criados no minuto
- `fluxo da equipe de desenvolvimento`: itens abertos sob responsabilidade da equipe; transições no minuto; comentários no minuto; itens criados no minuto
- `fluxo da equipe de qualidade`: itens abertos sob responsabilidade da equipe; transições no minuto; comentários no minuto; itens criados no minuto
- `fluxo da equipe de atendimento`: itens abertos sob responsabilidade da equipe; transições no minuto; comentários no minuto; itens criados no minuto
- `fluxo da equipe de vendas`: itens abertos sob responsabilidade da equipe; transições no minuto; comentários no minuto; itens criados no minuto
- `fluxo da equipe de operação`: itens abertos sob responsabilidade da equipe; transições no minuto; comentários no minuto; itens criados no minuto
- `fluxo da equipe de gestão`: itens abertos sob responsabilidade da equipe; transições no minuto; comentários no minuto; itens criados no minuto

**épicos**. Épicos abertos, em andamento e concluídos no minuto.

- `épicos`: abertos; em andamento; concluídos no minuto

**repositório de código**. Commits, linhas alteradas, revisões aprovadas e revisões que pediram mudança no minuto, e ramos abertos.

- `repositório de código`: commits no minuto; linhas alteradas no minuto; revisões aprovadas no minuto; revisões que pediram mudança no minuto; ramos abertos

**código de**. Um por componente: commits, testes executados e testes com falha no minuto (qualidade, desenvolvimento, operação).

- `código de login e conta`: commits no minuto; testes executados no minuto; testes com falha no minuto
- `código de catálogo e busca`: commits no minuto; testes executados no minuto; testes com falha no minuto
- `código de pedido e carrinho`: commits no minuto; testes executados no minuto; testes com falha no minuto
- `código de frete`: commits no minuto; testes executados no minuto; testes com falha no minuto
- `código de pagamento`: commits no minuto; testes executados no minuto; testes com falha no minuto
- `código de fiscal`: commits no minuto; testes executados no minuto; testes com falha no minuto
- `código de relatórios`: commits no minuto; testes executados no minuto; testes com falha no minuto
- `código de notificações`: commits no minuto; testes executados no minuto; testes com falha no minuto
- `código de infraestrutura`: commits no minuto; testes executados no minuto; testes com falha no minuto

**funil de vendas**. Negócios em cada etapa, ganhos e perdidos no minuto, valor anual em aberto em milhares de reais.

- `funil de vendas`: leads; em qualificação; propostas; em negociação; ganhos no minuto; perdidos no minuto; valor em aberto em milhares de reais

**atividades de vendas**. Ligações, e-mails e propostas enviadas no minuto, tarefas internas abertas.

- `atividades de vendas`: ligações no minuto; e-mails no minuto; propostas enviadas no minuto; tarefas internas abertas

**leads de**. Uma por origem (site, indicação, prospecção): leads novos no minuto e negócios dessa origem em aberto no funil.

- `leads de site`: novos no minuto; em aberto no funil
- `leads de indicação`: novos no minuto; em aberto no funil
- `leads de prospecção`: novos no minuto; em aberto no funil

**agenda da equipe**. Uma por equipe: pessoas em reunião agora, reuniões da equipe em curso, minutos-pessoa de reunião acumulados no dia.

- `agenda da equipe de produto`: pessoas em reunião; reuniões em curso; minutos de reunião no dia
- `agenda da equipe de desenvolvimento`: pessoas em reunião; reuniões em curso; minutos de reunião no dia
- `agenda da equipe de qualidade`: pessoas em reunião; reuniões em curso; minutos de reunião no dia
- `agenda da equipe de atendimento`: pessoas em reunião; reuniões em curso; minutos de reunião no dia
- `agenda da equipe de vendas`: pessoas em reunião; reuniões em curso; minutos de reunião no dia
- `agenda da equipe de operação`: pessoas em reunião; reuniões em curso; minutos de reunião no dia
- `agenda da equipe de gestão`: pessoas em reunião; reuniões em curso; minutos de reunião no dia

**reuniões do tipo**. Um por tipo de reunião: reuniões em curso e pessoas nelas.

- `reuniões do tipo diária`: em curso; pessoas
- `reuniões do tipo planejamento`: em curso; pessoas
- `reuniões do tipo refinamento`: em curso; pessoas
- `reuniões do tipo revisão e retrospectiva`: em curso; pessoas
- `reuniões do tipo semanal`: em curso; pessoas
- `reuniões do tipo liderança`: em curso; pessoas
- `reuniões do tipo mensal`: em curso; pessoas
- `reuniões do tipo com cliente`: em curso; pessoas
- `reuniões do tipo entrevista`: em curso; pessoas
- `reuniões do tipo alinhamento`: em curso; pessoas

**quadro da equipe**. Uma por equipe: pessoas no quadro, presentes agora (ponto batido), em almoço, ausentes por férias e por falta hoje, horas extras no dia.

- `quadro da equipe de produto`: pessoas no quadro; presentes agora; em almoço; ausentes por férias hoje; ausentes por falta hoje; horas extras no dia
- `quadro da equipe de desenvolvimento`: pessoas no quadro; presentes agora; em almoço; ausentes por férias hoje; ausentes por falta hoje; horas extras no dia
- `quadro da equipe de qualidade`: pessoas no quadro; presentes agora; em almoço; ausentes por férias hoje; ausentes por falta hoje; horas extras no dia
- `quadro da equipe de atendimento`: pessoas no quadro; presentes agora; em almoço; ausentes por férias hoje; ausentes por falta hoje; horas extras no dia
- `quadro da equipe de vendas`: pessoas no quadro; presentes agora; em almoço; ausentes por férias hoje; ausentes por falta hoje; horas extras no dia
- `quadro da equipe de operação`: pessoas no quadro; presentes agora; em almoço; ausentes por férias hoje; ausentes por falta hoje; horas extras no dia
- `quadro da equipe de gestão`: pessoas no quadro; presentes agora; em almoço; ausentes por férias hoje; ausentes por falta hoje; horas extras no dia

**quadro geral**. Pessoas no quadro, entradas e saídas no mês, vagas abertas, candidatos em processo, solicitações abertas à gestão.

- `quadro geral`: pessoas no quadro; entradas no mês; saídas no mês; vagas abertas; candidatos em processo; solicitações abertas à gestão

**ponto**. Entradas e saídas registradas no ponto no minuto.

- `ponto`: entradas registradas no minuto; saídas registradas no minuto

## Custo

Rodando sozinho numa máquina comum, o mundo leva perto de 3,7 segundos de máquina por dia simulado e ocupa menos de 100 MB:
trinta dias em perto de 2 minutos, noventa dias em perto de 6 (a carteira e o banco crescem, e o minuto fica um pouco mais caro com o
tempo). O contrato pede 30 dias em menos de 10 minutos e 90 dias em menos de 30, abaixo de 2 GB. As gravações abaixo rodaram quatro
de cada vez na mesma máquina de quatro núcleos, por isso o tempo por dia é maior:

| corrida | segundos | segundos por dia simulado | memória máxima |
|---|---|---|---|
| `normal_90_dias` | 507 | 5.63 | 126 MB |
| `sem_defeito_30_dias` | 138 | 4.62 | 91 MB |
| `embaralhado_30_dias` | 131 | 4.37 | 88 MB |
| `sem_deriva_30_dias` | 145 | 4.84 | 88 MB |
| `surdo_30_dias` | 145 | 4.82 | 91 MB |
| `atos_30_dias` | 122 | 4.05 | 89 MB |

## O que ficou de fora

- **Rede e servidores de verdade.** As rotas são chamadas de função dentro do processo; a latência é calculada do trabalho que o
  código fez (instruções do banco, idas ao banco, trabalho da aplicação, espera pelos serviços de fora, carga do processador), não
  medida no relógio da máquina, para que a mesma semente repita a mesma vida. `Mundo(semente, tempo_real=True)` faz cada passo
  esperar o minuto de parede correspondente, para quando os sistemas forem de verdade.
- **Os serviços de fora** (gateway de pagamento, transportadoras, antifraude) e a chegada de leads pelo site são sorteados: são o
  mundo lá fora, não a empresa.
- **Feriados, fusos e horário de verão** não existem; o calendário começa em 1º de junho de 2026 e segue a folhinha gregoriana.
- **Um só modo de incidente de infraestrutura** (o volume do banco que enche). Rede, certificado, máquina e provedor não caem.
  Quedas curtas do processo acontecem quando o defeito de memória está no ar; a verdade as lista à parte.
- **Pessoas sem nome e sem vida fora do trabalho.** Têm identificador, papel, horário e jeito de trabalhar; as decisões são regras
  com sorte, sem aprendizado. Salário, avaliação e conflito não existem.
- **Os testes da qualidade** são uma bateria pequena e fixa por função (34 testes); a cobertura é quais deles rodam. Testes de
  desempenho existem só para relatório e exportação.
- **Marketing, financeiro além das faturas e estornos, e compras** ficam de fora. O estoque é reposto pelos fornecedores de madrugada.
- **As respostas aos atos** são frases montadas com os números dos sistemas; não há conversa livre.
- **A mesma vida em outra máquina** depende das mesmas versões de Python, numpy e SQLite: a contagem de instruções do SQLite pode
  mudar entre versões. Na mesma máquina, a mesma semente repete a mesma vida (conferido também entre processos).
- **O nulo embaralhado** sorteia o calendário em blocos de 25 a 240 minutos; dentro de um bloco o calendário corre normal (uma diária
  de 15 minutos continua tendo 15 minutos), mas nada se repete com período no relógio da porta.
- **Corridas maiores que um ano** funcionam, mas o roteiro de funcionalidades e as férias foram pensados para os primeiros meses;
  depois do roteiro, as funcionalidades voltam como revisões.
