# O contrato das famílias de mundos das escolas (para o construtor de mundos)

Rascunho de 15/10/2026, item 27 do plano vivo; reescrito pelo construtor em 22/10/2026 (v2.3, itens 22 e 23 do plano vivo): a escola 3
reescrita, a escola da presença, a escola do corpo e a família da voz, entregues em `organizacao/escolas/familias/`. Vale junto com o contrato do mundo (`organizacao/mundo/v1/CONTRATO.md`) e com a verdade
v2.1 (itens 18 e 19 do plano); o que está aqui acrescenta, não substitui. Quem constrói não toca em nada fora da pasta que criar e
não lê nada do que o observa.

## 1. O que é uma família

Uma família é um gerador de mundos pequenos, todos cumprindo o contrato do mundo (`Mundo(semente, nulo)`, `processos()`, `passo()`,
`verdade()`, `eventos_humanos()`, `salvar`/`carregar`, `receber` para os atos), em que a semente sorteia a estrutura, não só o ruído:
quantos processos, de que tipos, com que nomes, que ligações, com que atrasos, que ciclos, que equipes. Duas sementes da mesma
família são duas empresas diferentes com as mesmas leis. Uma escola é uma família; a prova é sempre outra semente (nunca um mundo
de escola) e também roda sob a visão da linha I (outra ordem, outros nomes, outras escalas).

Regras que valem para todas as famílias:

- Nomes próprios de cada mundo: os processos, os campos e as equipes têm nomes em português, legíveis, únicos, sorteados ou
  compostos a partir da semente (nenhum nome fixo repetido entre sementes, exceto o vocabulário dos tipos de campo abaixo).
- Nada entra pela porta que não seja medida: nenhum rótulo, nenhum campo que diga "anormal", nenhuma verdade disfarçada.
- A verdade é conferível: cada acontecimento declarado tem instante, lugar (`[processo, campo]`), atraso típico e sentido; a verdade
  diz também a lei que gerou o acontecimento (o parâmetro sorteado), para a bancada medir "nada inventado".
- Três categorias de ligação na verdade, como na v2.1: causa (declarada, com atraso), causa comum (duas coisas movidas pela mesma
  lei: um incidente, um ciclo, um sprint) e sem relação. O que o calendário move em cada campo é declarado campo a campo
  (motores e caminho), e a força é medida, não escrita à mão.
- Nulos por família (abaixo), sempre com a mesma semente: o mesmo mundo sem a lei que a escola ensina.
- Um item por minuto por processo pela porta (o conector do observador agrega rajadas; o mundo não precisa delas). Os tipos de campo
  usam um vocabulário comum e pequeno: contagem por minuto, nível (fila, abertos, presentes), latência, taxa, carteira. O nome do
  campo é próprio do mundo; o tipo é da família.
- Tamanho: de 1 a 12 processos por mundo nas escolas 1 a 4; entre 100 e 300 na escola 5 (a empresa, que é o mundo v2). Dias por
  vida: de 7 a 45, conforme a escola.
- Custo: um dia de mundo tem de rodar em menos de 1 s de máquina, sem o observador.
- (22/10) O relógio como campo, em toda família: com `relogio=True` (ou `MUNDO_RELOGIO=1`) o último processo é `relógio` (hora do
  dia, dia da semana, minuto do mundo); desligado por padrão, o mundo é o mesmo byte a byte.
- (22/10) A voz: uma família com voz entrega as linhas por `vozes() -> [(t, canal, texto)]` (as que chegaram desde a última chamada,
  como `respostas()`) e a contagem delas como campo do processo do canal ("linhas chegadas no minuto"). As palavras entram no
  organismo pela porta das palavras; o mundo não sabe nada disso.
- (22/10) O interior de quem responde (fila, cansaço, atenção, confiança) fica só na verdade; pela porta saem os rastros físicos: a
  presença, as horas extras, os itens do fluxo, os textos chegados e os itens abertos da porta de cada equipe, só contagens.

## 2. As famílias

### Escola 1: um campo
- Mundo: de 1 a 3 processos de tipos diferentes (contagem, latência, fila, carteira), cada um com 1 a 4 campos; acontecimentos
  sorteados no tempo: incidente (queda e volta), mudança de regime (um patamar novo para sempre), deriva (uma taxa por semana).
- Verdade: cada acontecimento com instante, lugar, sentido e tamanho em desvios do próprio campo.
- Nulos: `sem_incidente`, `sem_regime`, `sem_deriva` (cada um tira só a sua lei).
- O que a escola ensina: abrir e fechar episódios, o normal novo, a deriva. Diploma: as linhas C, D, E e "nada inventado".

### Escola 2: causa e efeito
- Mundo: de 2 a 8 processos ligados em pares e cadeias (A move B com atraso sorteado, de minutos a horas; B pode mover C), com uma
  ligação que liga e desliga no meio da vida (existe de t1 a t2 e some).
- Verdade: cada ligação com origem, destino, atraso típico, instante em que nasce e em que morre; e as causas comuns (dois efeitos da
  mesma origem) marcadas como tais.
- Nulos: `embaralhado` (os mesmos disparos de A e de B sem a ligação), `sem_ligacao`.
- Ensina: a sinapse com atraso, a morte da sinapse quando a ligação some, o pressentimento. Diploma: A, B (o atraso dentro de um
  terço a três vezes o sorteado), e "a ligação desligada morre em até N dias".

### Escola 3: gente que responde (reescrita em 22/10: `familias/escola3.py`)
- Mundo: duas ou três equipes de gente e uma a três máquinas (de 7 a 12 processos). As equipes são agentes com estado, como no mundo
  v2: fila de atos, presença (expediente sorteado, almoço, sábado de algumas, faltas), cansaço, atenção e confiança em quem pede; a
  demora de um ato cresce com a ocupação, o cansaço e a atenção gasta e encolhe com a confiança. Rendimento sorteado: uma equipe
  sabe tratar o defeito recorrente de uma máquina e resolve quase sempre; outra às vezes; outra nunca. Sem pedido, a manutenção
  programada tira o defeito horas ou dias depois. O dia tomado por pedidos faz a equipe ficar além da hora.
- Os campos reaferentes: `quadro da <equipe>` (presentes agora, horas extras no dia), `fluxo da <equipe>` (itens abertos, itens
  criados no minuto) e `porta da <equipe>` (textos chegados no minuto, itens abertos), mais as máquinas (produção, falhas, fila).
- Verdade: por equipe, a lei (rendimento, chance, demoras de base, expediente); cada ato com o que fez, o estado da equipe ao receber e
  ao tratar, as horas extras atribuídas; os episódios do defeito com o ramo sem ato (a manutenção) e `antecipou_min`; os quartis de
  tratado menos recebido por equipe; o interior de hora em hora.
- Nulos: `surdo` (a porta não recebe), `paciente` (sem atenção, cansaço nem confiança, e os pedidos não lançam hora extra),
  `ninguem_resolve` (as equipes respondem, nenhum pedido tira o defeito).
- Ensina: o outro pelos rastros. Diploma (percepção, não conduta): O1, a sinapse do efetor para os textos da equipe nasce na vida
  normal com o atraso dentro dos quartis da verdade, nunca no surdo; O2, o custo ("mandei a X, horas extras de X") nasce no normal e
  não no paciente; O3, a presença ("presentes em X, textos de X").

### A escola da presença (22/10: `familias/presenca.py`)
- Mundo: um canal e uma luz. Uma voz vem e vai no canal com um costume sorteado (dias da semana, hora de chegada, quanto fica, linhas
  por minuto em rajadas, faltas, uma semana fora); as linhas são palavras sem sentido ainda. Quem observa escreve no canal; se ela
  está, responde com a chance e o atraso sorteados (a contingência); se não está, nada.
- Verdade: o costume e a contingência; cada presença; cada linha com a causa (o costume ou a resposta a uma linha dele); cada linha
  dele com se ela estava e quando respondeu.
- Nulos: `sorteado` (as mesmas sessões em instantes sorteados), `surdo` (o que ele escreve não chega a ela), `calada` (ela não vem).
- Ensina: o costume dela e a contingência (O5), antes da língua.

### A escola do corpo (22/10: `familias/corpo.py`)
- Mundo: de dois a quatro processos com um nível e uma contagem de avisos. Desvios chegam em rajadas (de 3 a 12 horas, a cada dois a
  cinco dias) e somem na calmaria. A semente sorteia a lei de cada processo: volta sozinho (o desvio decai com uma constante de tempo
  sorteada, e o ato não muda a volta) ou só volta com ato (o desvio fica até um pedido à mão daquele processo).
- Verdade: a lei de cada processo, as rajadas, cada episódio com `reverteria_sozinha_em` (o ramo sem ato: a volta exata, ou nulo se
  não voltaria), `saiu_por` e `antecipou_min`; cada ato com o efeito declarado.
- Nulos: `surda` (nenhum ato chega), `calma` (os mesmos desvios espalhados, sem rajada); a eferência embaralhada é da bancada.
- Ensina: o efeito do próprio ato, onde a verdade é conhecida, e o episódio do corpo só na rajada. Diploma: N(a) e N(b).

### A família da voz, o berçário (22/10: `familias/voz.py`)
- Mundo: de um a três processos com um nível e acontecimentos sorteados (subir, descer, pico, parar, voltar), e o canal da voz. A voz
  fala só no instante em que algo acontece (de 0 a 2 minutos depois), com um vocabulário de 12 a 20 palavras: o nome curto de cada
  processo, a palavra de cada acontecimento, "agora", "de novo", "muito", os artigos.
- Verdade: o significado de cada palavra; cada acontecimento; cada linha com a referência (processo, campo, acontecimento, instante),
  só para a bancada.
- Nulos: `hora_sorteada` (as mesmas linhas em instantes sem relação com os campos), `vocabulario_permutado` (as palavras de cada linha
  sorteadas do vocabulário: nenhuma presa a um sentido), `voz_surda` (a voz não fala).
- Ensina: o significado como sinapse da palavra para a unidade que já dispara. Diploma: F1 (compreensão por palavra numa cena nova),
  F3 (o desmame).

### Escola 4: o tempo
- Mundo: processos com ciclos de períodos sorteados (não só dia e semana: 90 minutos, 7 horas, 3 dias, 11 dias), fases e
  amplitudes sorteadas, somados a um ruído; um ciclo que muda de período no meio da vida.
- Verdade: os períodos, as fases, as amplitudes e o instante da mudança, campo a campo (é o gabarito do calendário como sentido).
- Nulos: `embaralhado` (as mesmas amplitudes sem período), `periodo_fixo`.
- Ensina: a ideia de retorno com o período certo, o costume de si nas escalas longas. Diploma: F com o período sorteado, não 1.440.

### Escola 5: a empresa
É o mundo v2 (já entregue), com semente nova a cada prova e a verdade v2.1. Não é desta entrega.

## 3. O que o construtor entrega

- Uma pasta `organizacao/escolas/familias/` com um módulo por família (`escola1.py` a `escola4.py`), cada um com `Mundo(semente,
  nulo)` que cumpre o contrato, mais `NULOS` (a lista dos nulos da família) e `FAMILIA` (o nome). (22/10) Entregues: `escola3.py`,
  `presenca.py`, `corpo.py` e `voz.py`, sobre `base.py` (o relógio, a porta, a pausa); as escolas 1, 2 e 4 ainda não.
- `VERDADE.md` da pasta: o formato de `verdade()` de cada família, com os campos acima e um exemplo por família.
- Um teste por família (`conferir.py`): gera três sementes, confere que a verdade bate com o que saiu pela porta (os acontecimentos
  declarados aparecem nos campos onde a verdade diz, com o atraso declarado), que o nulo tira só a lei dele, e que duas sementes dão
  estruturas diferentes.
- Hashes dos minutos de cada semente de exemplo, para a identidade.
- Nenhum arquivo fora dessa pasta; nenhuma leitura do observador; nenhum nome de assistente, de modelo ou de pessoa no que sai.

## 4. Como se aceita

- As três sementes de cada família passam no `conferir.py`.
- Cada família passa pelo corredor de escolas (`organizacao/escolas.py`: liga, vive, desliga) sem erro, com o ser de hoje.
- A prova da escola (item 34 do plano) roda sobre a família: o educado iguala ou vence o nascido em tudo e vence a idade casada em
  pelo menos uma linha, em três sementes novas. Isso é aceite da escola, não do mundo; o mundo se aceita pelos dois pontos acima.
