# Passo 0: a divergência entre a versão aprovada e a versão em uso, e a reprodução no ambiente novo

Rodado em 12/10/2026 (relógio do sistema), antes de qualquer número público. Medida sobre o núcleo da main be8af00 do repositório do
núcleo: os oito arquivos do detector usados aqui têm o mesmo sha256 dos da main (conferido arquivo a arquivo).

## As duas versões
- inteira (a aprovada): depois de um aviso da entrada (log), a referência da entrada é refeita em todas as faixas.
- faixas (a em uso): depois de um log, a referência é refeita só nas faixas acusadas. É a única linha que difere entre as duas.

## Ambiente
Python 3.11.17, numpy 2.4.6, scipy 1.17.1, scikit-learn 1.9.1, river 0.26.1, uma thread de BLAS, PYTHONHASHSEED=0. São as versões do
kit de reprodução de 07/10. Quatro processos, cada um com os seus fluxos inteiros.

## 1. Reprodução antes de mudar qualquer coisa
| o que | resultado |
|---|---|
| kit de reprodução (partes A e B, sementes 9000, 9001, 600 e 601; comparador do kit, sem mudança) | 50/50 idênticas, item a item: PASSA |
| confirmação final inteira, partes A e B (sementes 9000 a 9029 e 600 a 629), versão aprovada | 750/750 idênticas às saídas congeladas, 782 avisos no mesmo instante, tipo e campos |
| bancada de referência, parte B (sementes 200 a 229), versão aprovada | reproduz o resultado publicado: lenta_todas 22/30 com até 2 avisos, lenta_real 27/30, rampa 30/30, lenta_abrupta local 30/30 |
| bancada contra a concorrência (17 fluxos, sementes 3000 a 3019), a versão que correu nela | 340/340 idênticas à coluna congelada |
| o invólucro de registro em uso contra a decisão "faixas" (75 rodadas) | 75/75 com as mesmas decisões |

Não reproduzido aqui: as partes C e F (os arquivos do INSECTS não estão neste ambiente) e as partes D e E (o gerador de muitas classes
não está no pacote).

## 2. As duas versões lado a lado
Tabelas completas: tabela_passo0.txt (definições no topo do corredor), resumo_final_por_versao.txt (critérios G1 a G5 da confirmação
final, com o resumidor congelado), resumo8b_B_por_versao.txt (critérios B da bancada de referência, com o resumidor congelado),
tabela_porta2.txt (contra a concorrência).

Partes A e B, 1.500 rodadas por versão (as duas sementes de cada parte juntas, 60 por fluxo):

| | inteira (aprovada) | faixas (em uso) |
|---|---|---|
| nulos verdadeiros (nulo_sea, nulo_num, nulo_cat, nulo_mc, nulo lento; 300 rodadas): rodadas com algum aviso | 5/300 | 5/300 (as mesmas) |
| fluxos sem mudança de relação, incluindo deriva lenta (420 rodadas): rodadas com alerta | 0/420 | 0/420 |
| aviso antes da mudança nos fluxos com mudança (fora os lentos, em que a deriva já é mudança) | igual nas duas, rodada a rodada |
| relação quebra, 9 fluxos sem deriva: alerta na janela | idêntico nas duas, rodada a rodada (cat_real 31/60, os outros 57/60 a 60/60) |
| entrada muda (cov, cov_gradual, num_cov, cat_cov, mc_cov, lenta_abrupta, rampa_todas): log na janela | idêntico nas duas (59/60 a 60/60) |
| campo certo no primeiro log (sobre as 419 detecções) | 419/419 | 415/419 (lenta_abrupta 56/60) |
| latência mediana do primeiro log | igual, exceto lenta_abrupta: 50 e 56 | lenta_abrupta: 38 e 40 |
| logs depois da mudança por rodada (mediana): cov, cov_gradual | 1 | 4 (todos no campo verdadeiro: 349 repetições, 0 em outro campo) |
| num_cov, mc_cov | 1 | 2 (113 repetições no campo verdadeiro, 1 em outro) |
| rampa_todas (as 20 sobem juntas) | 1 | 17 (um por campo) |
| deriva lenta em todos os campos (lenta_todas): logs por rodada | 2 | 18,5 e 19 (um por campo, quase todos os 20) |
| deriva lenta em 3 campos (lenta_poucas): logs por rodada | 2 | 4 |
| relação quebra no meio de deriva lenta (lenta_real, o limite L1): alerta na janela | 26/30 e 27/30 (87% ± 6, 90% ± 5) | 9/30 e 5/30 (30% ± 8, 17% ± 7) |
| rodadas com alguma diferença entre as versões | 533/1.500, todas em fluxos em que a entrada muda |
| avisos no total | 1.576 | 5.921 |

Veredito pelos critérios congelados da confirmação final (G1 a G5): as duas REPROVAM nas mesmas duas linhas que já reprovavam
(cat_real e lenta_real); lenta_real cai de 87% para 30% (sementes da confirmação) e de 90% para 17% (sementes da bancada de
referência). Pelos critérios B da bancada de referência: B2 (no máximo 2 avisos por rodada na deriva lenta em pelo menos 27/30) já reprovava na
aprovada (22/30) e vai a 0/30 na em uso; B5 (exatamente 1 aviso na rampa) passava na aprovada (30/30) e vai a 0/30 na em uso.

Contra a concorrência (340 rodadas): as duas versões dão o mesmo resultado em tudo o que aquela bancada mede, porque ela olha o
primeiro aviso: falso 2/340, detecção certa 231/240 (96% ± 1), atraso mediano 338, localização 231/231, XOR 0/20. As listas de avisos
diferem em 57/340 rodadas (cov, cov_gradual, num_cov): em 56, só por repetições do log no campo verdadeiro depois da primeira
detecção; em 1 (num_cov, semente 3001), a aprovada dava um segundo log num campo errado e a em uso dá uma repetição no campo certo.

## 3. Leitura
Nos nulos os falsos não sobem: zero alerta nas duas, e os logs dos nulos verdadeiros são os mesmos. O que muda é o número de logs
quando a entrada muda de verdade: a versão em uso repete o log da mesma mudança no mesmo campo (as outras faixas do campo ainda têm a
referência antiga) e, na deriva lenta, dá um log por campo em vez de um para todos. E muda o limite L1: cada log zera a evidência da
relação e a regra de ordem pede a entrada calma; com um log a cada 480 itens na deriva lenta, a relação quase nunca chega a alerta.
O detector público é o que está em uso, como decidido; a decisão sobre a queda em L1 e o número de logs é de Gabriel.

## 4. Hashes
Listas de avisos (sha256 canônico do JSON ordenado, sem o tempo de máquina; hash_avisos.py 17ea36dc...):
- partes A e B, inteira: a1e65e2206162f613001eb6605ad98dcb4fa742f1537c42e20d61f720c3aa4df (1.500 listas)
- partes A e B, faixas: 9704e10939e66e0612ba4f08c4ca487e4248a462d17d5a966040389979d2258f (1.500 listas)
- invólucro em uso: cb1530cf03bb99dd1d01682d61f0005abcc0ffea0085d4ffa83367f26ccc4ce2 (75 listas)
- contra a concorrência (antiga, inteira, faixas): 588a3fe77e7455762ef5a94a3a12fbb8e3a32cc6f25c204b6e09e3f58adf54e4 (1.020 listas)
- kit: 803c333588cfa95fc9b0f4d03785a6bd22f0006c759f5b5b9cebc0a1b3948386 (50 listas)

Código do núcleo (o mesmo da main be8af00): decisão aprovada e em uso 963be63e...; treino 3f344f7b...; peças de evidência fb74811c...
e 039c5b3d...; gama 379d6b07...; invólucro de registro b5b8647c...; trajetórias d5b60dcb...; parte 875bc6b1.... Geradores:
conf_fluxos.py 9e033304..., conf_fluxos_mc.py 3a631138..., fluxos_lentos.py 0c46546f..., fluxos2.py 45c74d84...; corredores da
bancada de referência 58b7dae4... e b2982512...; resumidores congelados f75f69b2... (confirmação final), 12a12b90... (bancada de
referência), 893bad21... (contra a concorrência). Os corredores deste passo carregam os módulos do núcleo pelos nomes de arquivo
originais e por isso ficam fora deste repositório: rodar_passo0.py 9082c851..., rodar_porta2_passo0.py 9d7eb52f..., passo0_tabela.py
4f64d71c..., porta2_tabela.py 9b9abd45..., lote_passo0.sh dabba975..., lote_kit.sh 3ed369d2....
