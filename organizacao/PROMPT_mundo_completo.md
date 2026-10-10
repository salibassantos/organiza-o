# Prompt: construir a organização completa (o mundo) que um observador vai acompanhar

## Contexto (você começa do zero; tudo o que precisa está no zip anexo)
Gabriel (Limiar Research) tem um observador: um núcleo que percebe mudanças de regime, episódios, ligações entre o que vem depois
de quê, pressentimentos, ideias e dúvidas, a partir de medidas numéricas minuto a minuto, sem que ninguém lhe diga o que importa.
Esse observador não está neste pacote e não é seu trabalho: você não o toca, não o simula e não o imita. O seu trabalho é o mundo:
uma empresa de software de 50 pessoas, com os seus sistemas funcionando como software real, acontecendo no tempo, que entrega por
uma porta definida (mundo/v1/CONTRATO.md) as medidas de cada processo a cada minuto. A ligação do mundo ao observador é feita por
outra pessoa, depois, por essa porta.

Regras de tudo o que você escrever: português; sem travessão; sem autorreferência de assistente em código, nome de arquivo,
comentário ou registro; nada de endereço de servidor, e-mail ou nome de projeto privado; nenhum campo que conte a resposta (um
campo "houve liberação com defeito" é a verdade disfarçada; o que sai pela porta são medidas do que os sistemas fazem).

## O que está no zip (organizacao/mundo/)
- v1/CONTRATO.md: a porta. Leia primeiro; é o que a sua entrega tem de cumprir.
- empresa.py: um mundo pequeno v0 (oito fluxos agregados sorteados, 27 campos), só como referência do formato dos itens e dos
  nomes; o seu mundo o substitui por completo.
- v1/fluxo.py e v1/produto.py: um começo do mundo grande (fluxo de trabalho tipo Jira em SQLite; o software do produto com rotas e
  bugs que são exceções do código). Use, complete ou refaça; mantenha a ideia: software de verdade, erro de verdade, nada sorteado
  onde o código pode acontecer.

## O que construir (organizacao/mundo/v1/)
1. **O sistema de fluxo de trabalho, completo, tipo Jira**: projetos (Produto, Plataforma, Suporte, Infraestrutura), itens com
   tipo (épico, história, tarefa, bug, chamado), estado por tipo, prioridade, componente, equipe, SLA, sprint de duas semanas por
   projeto (planejamento, meta, retrospectiva), comentários, vínculo item-versão, reaberturas, e o log de toda transição com
   instante e equipe. Em SQLite, com API em Python (criar, transitar, comentar, abrir e fechar sprint, consultas).
2. **O software da empresa, software mesmo**: um serviço com rotas (login, catálogo, pedido, pagamento, relatório, e mais o que
   fizer sentido), banco de dados real, repositório de versões. Liberar é trocar a versão em uso. Cada versão é código; algumas
   carregam defeito real (exceção numa rota para certos pedidos, consulta lenta, gravação dupla, fila que cresce). As métricas por
   minuto por rota (requisições, erros, latência), a fila, o tamanho do banco, o uso de processador e memória como função do que o
   código fez. Pode rodar em processo (chamadas de função), sem rede, para ser rápido; o que importa é que o erro é o código errando.
3. **Clientes**: centenas (crescendo devagar), com ciclos de uso por hora e dia, planos diferentes, que geram o tráfego do produto e
   abrem chamados no fluxo quando um erro os atinge (com atraso humano de minutos), respondem ao atendimento, cancelam ou entram.
4. **As 50 pessoas como agentes com papel, equipe e horário**, agindo nos sistemas: produto refina o backlog e abre histórias;
   desenvolvimento puxa, transita, comenta e comete versões (com uma taxa de defeito que depende de pressa e de tamanho); qualidade
   testa, reprova e reabre; atendimento responde chamados dentro do SLA, escala para desenvolvimento, fecha; vendas trabalha um
   funil (lead, qualificação, proposta, fechado, perdido) num CRM próprio; operação libera versões (terças e quintas à tarde) e
   corrige quando o produto erra; o dono convoca reuniões. Férias, faltas, horas extras, uma contratação e uma saída no mês.
   Ninguém é observado como pessoa: os conectores só leem agregados por equipe, projeto, fila, rota e etapa.
5. **Agenda**: diárias por equipe, planejamento e retrospectiva por sprint, mensal com o dono, reuniões com clientes; quem está em
   reunião não age nos sistemas naquele tempo.
6. **Quadro de pessoal**: presentes, ausentes, horas extras, entradas e saídas.
7. **O relógio**: um instante por minuto, correndo sem dormir; 30 dias em poucos minutos de máquina. Determinístico pela semente:
   a mesma semente, a mesma empresa; sementes diferentes, empresas diferentes com as mesmas leis.
8. **O play**: a organização é um processo no tempo, não uma tabela. Um laço de tempo faz cada minuto acontecer (pessoas agem,
   clientes batem no produto, o código roda, os bancos mudam), e o mundo só dá o minuto seguinte quando o observador chama
   `passo()`: os dois andam travados, e o mundo nunca anda sozinho. Velocidade: em simulação, sem dormir; preparado para tempo real
   (um minuto por minuto) quando os sistemas forem de verdade. Pausa e retomada: o mundo guarda o seu estado nos bancos
   (`salvar`, `carregar`). Repetição: a mesma semente repete a mesma vida. Quem observa nunca vê o futuro: a verdade fica em
   `verdade()`, separada, só para a bancada.

## O que a empresa tem de verdade (e você registra em verdade.json, com instantes)
Ciclos: dia útil, segunda-feira mais cheia, sexta mais lenta, fim de sprint com mais liberações e reaberturas, fim de mês com mais
vendas. Contingências: liberação com defeito faz os erros da rota subirem, minutos depois os chamados do componente, depois as
escalações, depois a correção e a volta; incidente de infraestrutura derruba o produto por dezenas de minutos e inunda o atendimento.
Derivas: a carteira cresce 1% por semana e os chamados com ela; uma versão nova muda o normal de latência de uma rota para sempre.
Regimes: um sprint de muita pressa com mais defeitos. Tudo isso tem de emergir da simulação (as pessoas e o código fazem), não de
um gerador de eventos por cima; e verdade.json diz quando cada coisa aconteceu, para a bancada conferir se ele percebeu.
Nulos, por parâmetro: a mesma empresa sem liberação com defeito (a sinapse "erros, depois chamados" não pode nascer); a mesma empresa
com o tempo dos processos embaralhado (nenhum ciclo); a mesma empresa sem deriva.

## Entregas
- organizacao/mundo/v1/: mundo.py (a classe Mundo do contrato) e os módulos do mundo (fluxo de trabalho, produto, clientes,
  pessoas, agenda, quadro, CRM, relógio), com os bancos em SQLite.
- organizacao/mundo/v1/verdade.json gerado por semente (o que a empresa tem e quando), e eventos_humanos por semente.
- organizacao/mundo/v1/rodar.py <pasta> <dias> <semente> [nulo]: faz o mundo acontecer sem observador e grava, por minuto, os
  valores de todos os processos num arquivo (jsonl ou csv) e a verdade; serve para conferir o mundo sozinho.
- organizacao/mundo/v1/registros/semente1/: trinta dias gravados assim, e os três nulos.
- organizacao/mundo/v1/LEIA-ME.md: o que o mundo tem, como se roda, a lista dos processos e dos campos com o que cada um mede, o
  custo (minutos por dia simulado, memória), e o que ficou de fora.
- Entregue tudo num zip com a mesma árvore (organizacao/mundo/...), e um relatório curto do que fez, do que conferiu e do que ficou
  de fora. Python 3.11, numpy e sqlite3 da biblioteca padrão; nada de rede.

## Como saber que ficou bom
- As 50 pessoas e os clientes movem os sistemas sem gerador de eventos por cima; as regularidades aparecem nos dados porque o
  código e as pessoas as produzem; verdade.json bate com o que se vê nos bancos e nas gravações.
- A porta cumpre o contrato: `Mundo(semente).passo()` devolve os mesmos processos e campos a cada minuto, na mesma ordem; salvar e
  carregar devolvem o mesmo mundo; a mesma semente repete a mesma vida; os nulos mudam só o que dizem mudar.
- Trinta dias em menos de dez minutos de máquina, abaixo de 2 GB.
- Nas gravações dá para ver, a olho, sem rótulo: a liberação com defeito subindo os erros da rota e, minutos depois, os chamados do
  componente; o incidente; a versão nova mudando a latência; a carteira crescendo; a segunda-feira e o fim do mês.
