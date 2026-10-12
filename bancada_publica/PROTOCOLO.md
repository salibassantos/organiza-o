# Bancada pública do detector: protocolo

Rascunho v0, escrito em 12/10/2026 (relógio do sistema), antes de qualquer rodada de qualquer método sobre os dados desta bancada.
NÃO CONGELADO. Vira v1 quando as decisões pendentes forem tomadas e o congelado (seção 9) for gravado; a partir daí, qualquer mudança
é versão nova, por escrito, antes de rodar de novo.

## 1. O que se prova

O detector recebe, a cada instante, os valores de um conjunto de campos e, quando existe, a resposta y de um modelo. Ele alega:

| | alegação | onde se mede |
|---|---|---|
| A1 | onde: qual campo saiu do normal, entre N campos | fluxos sintéticos, SMD (rótulo de interpretação), empresa simulada |
| A2 | quando: o instante em que a mudança começou (o começo que ele registra, "desde"), não só o instante do aviso | todas as bases (o começo verdadeiro) |
| A3 | o quê: subiu ou desceu; quanto, em desvios do normal do próprio campo; a trajetória (parou de crescer, voltou, foi substituído, virou o normal novo) | fluxos sintéticos, empresa simulada |
| A4 | alerta e log: com resposta y, separa relação que quebrou (alerta) de entrada que mudou (log) | fluxos sintéticos com resposta |
| A5 | deriva lenta: guarda no log e, quando ela para, vira o normal novo; não vira alerta | fluxos lentos, empresa simulada (carteira) |
| A6 | poucos falsos: em série sem mudança, poucos avisos | os nulos de cada linha |

Limites declarados antes desta bancada (01_HISTORIA.md, seção 11). Entram como estão, para serem medidos:
- L1: relação que quebra no meio de uma deriva lenta da mesma parte (a regra de ordem segura o alerta).
- L2: categórico real: a mudança está só na combinação de categorias.
- L3: XOR: a mudança está só no mecanismo; as margens não mudam.

## 2. O detector que roda

- É a versão em uso: decisão por faixa (8 faixas de quantis por campo, aprendidas no costume), fator de Bayes de duas amostras por
  faixa, média de e-valores contra A = 200.000, eixo da entrada (log) e eixo da relação (alerta) com a regra de ordem; depois de um
  aviso da entrada, a referência é refeita só nas faixas acusadas; o registro vivo (fases 0, 200 e 500); as trajetórias.
- Parâmetros: os de uso, iguais em todas as linhas e em todas as bases, sem ajuste nenhum: costume W = 2.000 itens, 8 faixas, A =
  200.000, costume mínimo por faixa 176 itens, K = 2 quando não há resposta, trajetórias com H = 5.000, janela 300, passo 100, base
  1.000. O detector não tem configuração "ajustada": roda uma vez, como está em uso.
- Sem resposta (todas as bases públicas e a empresa simulada), y = 0 em todo item, como em uso: só o eixo da entrada age, nenhum
  alerta é possível, e a linha mede o log.
- Campo que nasce parado (menos de 3 bordas distintas nas faixas do costume): a escada de escala a partir da resolução declarada,
  como em uso. Nas bases públicas, a resolução de cada campo é declarada pelo carregador da base com uma regra fixa: a menor diferença
  positiva entre valores distintos do campo no costume (1,0 se o campo é constante no costume). Na empresa simulada, 1,0 em todo
  campo, como em uso (o contrato não declara resolução). A mesma resolução é o menor desvio do normal das trajetórias, como em uso.
- O aviso do detector é o registro de fase 0. Onde: os campos acusados. Quando: o "desde" do registro (no alerta, que não traz
  "desde", o instante do aviso). O quê: a direção e o tamanho do registro de fase 500 (refeito 500 itens depois, com a mudança já
  na janela), e os eventos da trajetória do campo.
- Código: os arquivos do núcleo em uso com os nomes internos trocados por nomes neutros, sem mudar nenhuma conta. Antes do
  congelamento, a equivalência é provada e registrada: o código desta bancada e o original dão os mesmos avisos, item por item
  (instante, tipo, campos, "desde"), em todas as rodadas da versão em uso do passo 0. Sem equivalência total, não há congelamento.

## 3. Os dados

### 3.1 Públicos

| base | origem fixada | tamanho | o que a verdade marca | o que não marca |
|---|---|---|---|---|
| NAB | numenta/NAB, commit ea702d7 (data/, labels/combined_windows.json) | 58 séries univariadas, 365.558 pontos, 116 janelas | uma janela por anomalia (quando, com folga larga, centrada na anomalia) | onde (série de um campo), o começo exato, direção, tamanho, tipo, trajetória |
| UCR (arquivo de anomalias de 2021, Wu e Keogh) | o zip do arquivo, sha256 registrado no congelado | 250 séries univariadas, uma anomalia cada; o fim do trecho de treino no nome do arquivo | início e fim da única anomalia | direção, tamanho, trajetória; o "onde" não se aplica |
| Yahoo S5 (A1 a A4) | o pacote da Yahoo Webscope, sha256 registrado no congelado | 367 séries univariadas (67 reais, 300 sintéticas) | ponto a ponto, se o ponto é anômalo; nas sintéticas, também os pontos de mudança | direção, tamanho, trajetória, começo de um trecho (só pontos) |
| SMD | NetManAIOps/OmniAnomaly, commit 7fb0e0a (ServerMachineDataset/) | 28 máquinas, 38 campos, 708.405 pontos de treino e 708.420 de teste, 327 eventos (duração mediana 11 pontos) | ponto a ponto no teste; por evento, quais campos o explicam (interpretation_label): onde | direção, tamanho, trajetória |
| SMAP e MSL | os dados do telemanom (o endereço original nega acesso hoje); espelho imperial-qore/TranAD, commit 7ffb98d, data/SMAP_MSL; os rótulos têm o mesmo sha256 do original (057ce2d6...) | SMAP 55 canais, 25 campos, 69 eventos; MSL 27 canais, 55 campos, 36 eventos; treino e teste por canal | os trechos anômalos de cada canal e a classe (pontual ou de contexto) | onde dentro do canal, direção, tamanho, trajetória |

O que nenhuma base pública marca é registrado como "não medido nesta base", nunca como acerto.

### 3.2 Nossos (onde "onde" e "o quê" se medem de verdade)

- Fluxos sintéticos da bancada de referência, com os geradores congelados (conf_fluxos.py, conf_fluxos_mc.py, fluxos_lentos.py e o
  gerador do XOR): 20.000 itens, mudança em T = 10.000, verdade exata de tipo (alerta ou log), campos, direção e tamanho.
  - com resposta, relação quebra: sea, sea_grande, sea_gradual, stagger, num_real, num_desbal, num_ruido, mc_real, mc_cat;
  - com resposta, entrada muda: cov, cov_gradual, num_cov, cat_cov, mc_cov, lenta_abrupta, rampa_todas;
  - deriva lenta sem mudança de relação: lenta_todas, lenta_poucas;
  - limites declarados: lenta_real (L1), cat_real (L2), xor (L3);
  - nulos: nulo_sea, nulo_num, nulo_cat, nulo_mc, nulo (lento), nulo_xor.
- A empresa simulada (contrato em organizacao/mundo/v1/CONTRATO.md): 131 processos, 495 campos, um item por minuto; verdade
  conferível em verdade.json (liberações e quais tinham defeito, cada episódio de defeito no ar com primeiro erro, primeiro chamado e
  saída do ar, incidentes, mudanças de regime com a latência antes e depois, deriva da carteira). O "onde" de cada item da verdade é
  o campo que a bancada da empresa já usa (o campo de erros da rota atingida, os de chamados do componente, o de latência da rota, o
  da carteira); a lista é gravada no congelado.

### 3.3 Nulos

Toda linha tem o seu nulo, rodado por todos os métodos com a mesma configuração:
- as mesmas séries sem mudança: os nulos sintéticos; nas bases com treino (UCR, SMD, SMAP, MSL), o trecho de treino, que a verdade
  declara sem anomalia; no NAB, as 5 séries artificialNoAnomaly; na empresa, os mundos nulos do contrato (sem_defeito, embaralhado,
  sem_deriva) com a mesma semente da vida normal;
- as séries embaralhadas: cada série de aprovação com a ordem dos itens sorteada (semente da série); o embaralhamento tira toda
  mudança no tempo e deixa as margens.

### 3.4 Desenvolvimento e aprovação (disjuntos, declarados agora)

- Bases públicas: uma série (canal, máquina) é de desenvolvimento quando int(sha256(nome do arquivo)[:8], 16) % 3 == 0; as outras
  são de aprovação. A lista das duas partes é gravada no congelado antes de qualquer método rodar.
- Fluxos sintéticos: desenvolvimento nas sementes 20.000 a 20.009 (nunca usadas); aprovação em 30 sementes por fluxo sorteadas do
  sha256 do congelado (seção 9), no intervalo de 100.000 a 999.999, que não cruza nenhuma semente já usada.
- Empresa simulada: desenvolvimento nas gravações da semente 1 (organizacao/mundo/v1/registros/semente1/); aprovação em 3 sementes
  sorteadas do sha256 do congelado, 30 dias cada, e os três nulos com a primeira delas.

## 4. Os concorrentes

Todos rodam neste corredor, sobre as mesmas séries, com o mesmo costume (os mesmos primeiros itens que o detector usa para aprender),
nas mesmas máquinas. Cada um em duas configurações: a padrão (a da biblioteca ou do artigo) e a ajustada por busca em grade no
conjunto de desenvolvimento da mesma base (seção 4.3). Versões fixadas no congelado.

### 4.1 Lista

| método | origem | padrão | entra como |
|---|---|---|---|
| Page-Hinkley | river 0.26.1 | os da biblioteca | por campo, sobre o valor padronizado pelo costume |
| CUSUM bilateral | implementação de referência deste corredor (Montgomery) | k = 0,5 dp, h = 5 dp | por campo, padronizado pelo costume |
| EWMA (carta de controle) | implementação de referência deste corredor | lambda = 0,2, L = 3 | por campo, padronizado pelo costume |
| ADWIN | river 0.26.1 | delta = 0,002 | por campo |
| KSWIN | river 0.26.1 | os da biblioteca, semente fixa | por campo |
| DDM, HDDM_A, HDDM_W | river 0.26.1 | os da biblioteca | com resposta: sobre o erro 0/1 de uma regressão logística em fluxo (como na bancada de referência); sem resposta: por campo, sobre o indicador 0/1 "valor fora da faixa de 0,5% a 99,5% do costume" |
| teste por campo (padrão Evidently e NannyML) | scipy (KS e qui-quadrado), Bonferroni 0,05/d | referência 2.000, janela 1.000 a cada 250 | todos os campos |
| CJSD | a reimplementação da bancada de referência (arquivo de métodos com sha256 49e1f363...), sem mudança | tau e tau_x calibrados nos nulos de desenvolvimento até zero alarme, como na bancada de referência | com resposta: os dois eixos; sem resposta: só o eixo da entrada (y = 0) |
| WATCH e CTM | código original (aaronhan223/watch, commit fixado no congelado), adaptado como na bancada de referência | os do artigo | com resposta: como na bancada de referência; sem resposta: só a martingale da entrada (X-CTM) |
| floresta de isolamento | scikit-learn 1.9.1 | 100 árvores, contamination "auto", ajustada no costume | o vetor de campos (com resposta, o vetor com y) |
| perfil de matriz | stumpy 1.14.1, perfil à esquerda (só o passado) | m = 100; aviso quando passa do maior valor visto no costume | por campo |
| HTM | Numenta (htm.core ou o detector do NAB) | os parâmetros do detector do NAB | por campo |

### 4.2 Regras comuns

- Tipo do aviso de cada método, para a regra alerta e log: Page-Hinkley, CUSUM, EWMA, ADWIN, KSWIN, DDM e HDDM sobre o erro do modelo
  contam como alerta (a ação implícita deles é re-treinar), como na bancada de referência; o teste por campo conta como log; CJSD e
  WATCH dizem o tipo; floresta de isolamento, perfil de matriz e HTM contam como log. Em série sem resposta, todo aviso é log.
- Onde: o método aplicado por campo acusa os campos que dispararam; os outros não dizem campo e ficam sem acerto de campo.
- Quando: o instante do aviso; o método que estima o começo (o detector, CUSUM pelo ponto de mínimo da soma) usa a própria estimativa.
- O quê: só o detector traz direção e tamanho. Como base de comparação, o relato padrão (média do campo acusado nos 500 itens depois
  do aviso menos a dos 1.000 antes do começo, em desvios destes) é aplicado aos avisos do melhor concorrente que diz campo.
- Pontos marcados a menos de 10 itens do anterior pertencem ao mesmo aviso (o primeiro); a regra vale para todos os métodos.

### 4.3 Busca em grade (configuração ajustada)

Objetivo: maior F1 por evento (seção 5) no desenvolvimento da base; empate, menos falsos por 1.000 itens. Grades declaradas:
Page-Hinkley corte {5, 10, 20, 50, 100, 200} x delta {0,0005, 0,005, 0,05}; CUSUM k {0,25, 0,5, 1} x h {3, 4, 5, 8, 12}; EWMA
lambda {0,05, 0,1, 0,2, 0,3} x L {2,5, 3, 3,5, 4}; ADWIN delta {1e-6, 1e-5, 1e-4, 0,002, 0,01, 0,05}; KSWIN alfa {1e-6, 1e-5, 1e-4,
0,005} x janela {100, 300, 1.000} x estatística {30, 100}; DDM corte de deriva {2, 3, 4, 5} x aquecimento {30, 100}; HDDM_A e HDDM_W
confiança de deriva {1e-5, 1e-4, 1e-3, 0,01}; teste por campo alfa {0,001, 0,01, 0,05} x janela {250, 500, 1.000} x passo {50, 250};
CJSD tau e tau_x nos quantis {0,9, 0,99, 1} dos nulos de desenvolvimento; WATCH corte da martingale {20, 100, 1.000} x corte do SR
{1e2, 1e3, 1e4, 1e5, 1e6}; floresta de isolamento corte no quantil {0,99, 0,995, 0,999, 0,9999} do escore no costume; perfil de
matriz m {32, 64, 128, 256} x corte {3, 4, 5, 6} desvios acima da média do perfil no costume; HTM corte da verossimilhança {0,5,
0,9, 0,99, 0,999, 0,9999}.

## 5. As métricas

- Evento: um trecho da verdade (janela do NAB; anomalia do UCR; sequência de pontos marcados seguidos no Yahoo, SMD, SMAP e MSL; a
  mudança em T nos sintéticos; cada item da verdade na empresa).
- Janela de tolerância de um evento: NAB, a janela oficial; UCR, [início - 100, fim + 100] (a tolerância do próprio arquivo);
  Yahoo, SMD, SMAP e MSL, [início, fim + max(10, duração)]; sintéticos, as janelas da confirmação final ([T, T + 2.000) para alerta,
  [T, T + 4.000) para alerta nos graduais e no sea, e para log); empresa, as janelas da bancada da empresa (aviso em até 60 minutos;
  incidente em até 10 minutos, com o começo atribuído entre 30 minutos antes e 10 depois; normal novo em até 15 dias).
- Sensibilidade por evento: eventos com pelo menos um aviso dentro da janela, sobre os eventos. Precisão por evento: eventos
  detectados sobre (eventos detectados + avisos fora de toda janela); vários avisos na mesma janela contam um evento. F1 por evento.
  Nada de "point adjust": nenhum ponto é dado como detectado por estar no mesmo trecho de um ponto detectado, e nenhuma métrica por
  ponto entra no veredito.
- Latência: instante do primeiro aviso dentro da janela menos o início verdadeiro, em itens; mediana e quartis.
- Quando: |começo atribuído - início verdadeiro|, em itens; acerto se dentro da tolerância da base.
- Falsos: avisos fora de toda janela por 1.000 itens, e por dia onde a base tem relógio (NAB, Yahoo, SMD, empresa).
- Onde: entre os eventos detectados, a fração em que os campos acusados estão todos entre os verdadeiros (precisão do campo) e em que
  algum acusado é verdadeiro (cobertura), com N (o número de campos) ao lado; no SMD, também a taxa de acerto da interpretação
  (HitRate@100%) que a literatura da base usa.
- O quê: direção certa (subiu ou desceu); erro do tamanho em desvios; nas trajetórias, cada evento esperado da verdade (parou de
  crescer, voltou ao normal, virou o normal novo) aconteceu na janela declarada da linha.
- NAB: também a pontuação própria do NAB (perfil padrão, com o código do próprio NAB), porque é a que a comunidade conhece.
- Intervalos: toda proporção com n e erro-padrão binomial (raiz de p(1 - p)/n); F1 e diferenças entre métodos com erro-padrão por
  reamostragem pareada das séries (1.000 reamostragens, semente fixa no congelado).

## 6. As linhas e os critérios

Uma linha é uma base (ou um grupo de fluxos) e uma alegação. Cada linha tem uma métrica principal, o seu nulo e um teto de falsos
para o nulo, todos fixados aqui.

| linha | dados (aprovação) | alegação | métrica principal | nulo e teto |
|---|---|---|---|---|
| S1 relação quebra | 9 fluxos com resposta | A4 alerta | F1 por evento dos alertas | nulos sintéticos: rodadas com alerta <= 2% |
| S2 entrada muda | 7 fluxos com resposta | A4 log, A1, A3 | F1 por evento dos logs; alerta indevido <= 10% por fluxo | nulos sintéticos: rodadas com aviso <= 5% |
| S3 onde (sintéticos) | os fluxos de S1 e S2 com campo na verdade | A1 | precisão do campo entre N | o mesmo de S1 e S2 |
| S4 o quê (sintéticos) | os fluxos de S2 | A3 | direção certa; tamanho a menos de 0,25 dp; normal novo nos degraus que ficam | direção ao acaso (50%) |
| S5 deriva lenta | lenta_todas, lenta_poucas | A5 | rodadas sem alerta e com a deriva no log | rodadas com alerta <= 2% |
| S6 limites | lenta_real, cat_real, xor | L1, L2, L3 | F1 por evento dos alertas | como S1 |
| S7 nulos | todos os nulos sintéticos e os fluxos embaralhados | A6 | avisos por 1.000 itens | é o próprio nulo |
| P1 a P6 | NAB, UCR, Yahoo, SMD, SMAP, MSL (aprovação) | A2, A6 (e A1 no SMD) | F1 por evento | trecho sem anomalia e séries embaralhadas: avisos por 1.000 itens <= 0,1 |
| P4o onde no SMD | SMD | A1 | HitRate@100% e precisão do campo entre 38 | o mesmo de P4 |
| M1 contingência | empresa, 3 sementes | A1, A2, A3 | sensibilidade no campo de erros da rota, começo atribuído | sem_defeito: no máximo 0,3 das liberações com aviso no mesmo conjunto de campos |
| M2 incidente | empresa | A1, A2 | aviso em até 10 minutos e começo atribuído na janela | embaralhado e sem_defeito: os mesmos campos fora dos incidentes |
| M3 mudança de regime | empresa | A3 | direção certa e normal novo em até 15 dias | sem_deriva: o mesmo |
| M4 deriva | empresa | A5 | normal novo da carteira ao menos uma vez | sem_deriva: nenhuma vez |
| M5 volta | empresa | A3 | episódio do campo de erros com "voltou ao normal" depois da saída do ar | sem_defeito |

Veredito de cada linha, contra o melhor concorrente da linha (o maior valor da métrica principal entre todos os métodos e as duas
configurações de cada um, contando só os que respeitam o teto de falsos do nulo da linha):
- GANHOU se o detector está acima por mais de 2 erros-padrão da diferença; EMPATOU se a diferença está dentro de 2 erros-padrão;
  PERDEU se está abaixo por mais de 2 erros-padrão. Nas linhas sem concorrente aplicável (S4, M3 a M5, onde só o detector diz o quê),
  o critério é contra o nulo da linha.
- O nulo do detector passa do teto: a linha REPROVA, qualquer que seja o resto.
- Linha de limite declarado (S6): PERDEU é registrado como "limite confirmado" e não reprova; GANHOU ou EMPATOU é registrado como
  "limite não confirmado nesta amostra".
- Qualquer outra linha com PERDEU: REPROVADA, registrada como reprovada.
- A bancada APROVA se nenhuma linha reprova. O resultado de toda linha é publicado, aprovada ou não.

## 7. As rodadas

- Desenvolvimento (passo 2): só nos conjuntos de desenvolvimento, para achar erro de construção (formato, janela, parâmetro, carregador)
  e para a busca em grade dos concorrentes. Nada dali vale como prova. Cada erro de construção achado vira versão nova deste
  protocolo, por escrito, com a justificativa, antes do congelamento.
- Aprovação (passo 3): uma rodada só, sobre o congelado, serial ou com processos separados por série; cada série grava a sua saída
  inteira num arquivo próprio e uma linha no registro de retomada; se a máquina cair, a rodada continua das séries sem saída, sem
  refazer as feitas, e a queda fica registrada. Nada mais roda na máquina durante a aprovação. O detector não muda durante a bancada:
  se precisar mudar, é outra versão do detector e a bancada recomeça do passo 1. Nenhuma série sai e nenhum concorrente sai depois de
  visto o resultado.

## 8. O que não se faz

Ajustar o detector; escolher séries, sementes ou janelas depois de ver resultados; tirar concorrente que ganhe; usar "point adjust" ou
qualquer métrica que infle; citar número sem o hash do congelado e da main.

## 9. O congelado

Entram no sha256 (congelado.sha256), antes da rodada de aprovação: este protocolo; o código do detector; o corredor; os instrumentos
(métricas, pontuação do NAB, resumo); os geradores sintéticos e a empresa simulada (organizacao/mundo/v1/); os carregadores das bases
e o sha256 de cada arquivo de dados; as listas de desenvolvimento e aprovação; as configurações padrão e as ajustadas dos concorrentes;
as versões de Python, numpy, scipy, scikit-learn, river e stumpy (AMBIENTE.txt); o hash da main do repositório do núcleo. As sementes
de aprovação saem do sha256 do congelado depois de gravado: os oito primeiros hexadecimais de cada bloco de oito, módulo 900.000, mais
100.000, na ordem, pulando repetidas.

## 10. O pacote público

Uma pasta (ou um repositório) em que qualquer pessoa clona, roda um comando e sai a tabela inteira, com os hashes iguais aos da ata.
Dependências fixadas. Um LEIA-ME em português e em inglês com a tabela, os limites declarados e como acrescentar um concorrente pelo
mesmo protocolo. Nenhum número no LEIA-ME que não saia do comando. As bases que não podem ser redistribuídas (Yahoo S5) não entram no
pacote: o comando diz onde obtê-las e confere o sha256.
