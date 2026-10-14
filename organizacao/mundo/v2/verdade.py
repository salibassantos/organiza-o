"""A verdade: o que a empresa tem e quando aconteceu, para a bancada conferir o que o observador percebeu. Nada aqui é lido pelas
pessoas nem pelos sistemas, e nada sai pela porta do mundo: os mecanismos só anotam o que fizeram. O formato está descrito campo a
campo em VERDADE.md.

No v2 a verdade vive em disco, numa pasta de história, ao lado das listas de sempre:
- dia_NNNNN.npz: a verdade por minuto daquele dia (1440 linhas, uma coluna por grandeza interna, ver COLUNAS);
- dia_NNNNN.json: os registros que ficaram definitivos naquele dia (um registro só vai para o disco quando nada mais nele pode mudar,
  sete dias depois de fechado) e os eventos humanos do dia.
Os arquivos de um dia fechado nunca mais mudam. Em memória ficam só os registros abertos ou recentes, de modo que a memória não cresce
com a idade do mundo."""
import json
import os

import numpy as np

from . import codigo
from .cadastro import ROTAS, MINUTOS_DIA, EQUIPES
from . import calendario
from .causas import (Janelas, achar_janela, leis, campos_produto_parado, rota_proc, classificar_par, CATEGORIAS,
                     JUNTA_MIN)

ANTES_DA_SONDA = 10                 # os clientes sentem o produto parado alguns minutos antes de a sonda o declarar
RETENCAO = 7 * MINUTOS_DIA          # um registro fechado fica em memória por uma semana antes de ir para o disco
COMPONENTES_COM_CODIGO = ("login", "catalogo", "pedido", "frete", "pagamento", "fiscal", "relatorio", "notificacao")
FASES_DERIVA = {"crescendo": 0, "platô": 1, "expansão decidida": 2}

# a verdade por minuto: (nome da coluna, o que ela mede)
COLUNAS = [
    ("t", "o minuto da porta"),
    ("data_do_calendario", "a data em que as pessoas e os processos vivem (dias desde a criação; no nulo embaralhado, a data sorteada)"),
    ("minuto_do_calendario", "o minuto do dia em que as pessoas e os processos vivem (0 a 1439)"),
    ("dia_util", "1 se a data do calendário é dia útil"),
    ("defeitos_no_ar", "quantos defeitos estão no código em produção neste minuto"),
] + [(f"defeitos_no_ar.{c}", f"defeitos no ar em funções do componente {c}") for c in COMPONENTES_COM_CODIGO] + [
    ("erros_de_defeito", "respostas com erro neste minuto cuja exceção nasceu numa função com defeito no ar"),
    ("erros_de_outra_causa", "respostas com erro neste minuto sem defeito no ar por trás (entrada inválida, produto parado)"),
    ("produto_parado", "1 enquanto a sonda falha seguidamente (incidente ou queda do processo aberto)"),
    ("incidente_de_volume", "1 enquanto o incidente aberto é o volume do banco cheio"),
    ("volume_paginas", "o tamanho do volume do banco do produto, em páginas de 4096 bytes"),
    ("volume_paginas_livres", "as páginas livres no volume"),
    ("chamados_por_defeito", "chamados abertos neste minuto que nasceram de um defeito no ar"),
    ("chamados_por_incidente", "chamados abertos neste minuto que nasceram do produto parado"),
    ("chamados_de_outra_causa", "chamados abertos neste minuto sem rota por trás (dúvida, fatura, cobrança, nota que não chegou)"),
    ("carteira", "clientes ativos"),
    ("teto_do_mercado", "o teto da carteira que o mercado comporta agora (0 no nulo sem_deriva)"),
    ("fase_da_deriva", "0 crescendo, 1 platô (carteira no teto), 2 expansão decidida e ainda não valendo"),
    ("saturacao", "o fator que multiplica a chegada de leads (1 longe do teto, perto de 0 no teto)"),
    ("campanha", "a força da campanha em curso (0 sem campanha)"),
    ("pressa.PROD", "a pressa do squad de Produto: pontos que faltam no sprint sobre o que ainda dá para fazer (0,5 a 2,5)"),
    ("pressa.PLAT", "a pressa do squad de Plataforma"),
    ("pessoas_presentes", "pessoas trabalhando neste minuto"),
    ("implantacao", "1 se houve implantação neste minuto"),
    ("atos_recebidos", "atos que viraram coisa dentro do mundo neste minuto"),
    ("atos_tratados", "atos tratados (respondidos) neste minuto"),
]
for _e in EQUIPES:
    COLUNAS += [(f"{_e}.atos_na_fila", f"atos esperando a equipe de {_e}"),
                (f"{_e}.atos_em_tratamento", f"pessoas da equipe de {_e} tratando um ato agora"),
                (f"{_e}.cansaco", f"cansaço da equipe de {_e} (0 descansada; sobe com hora extra e com pedidos)"),
                (f"{_e}.atencao", f"atenção já gasta pela porta na equipe de {_e}"),
                (f"{_e}.confianca", f"confiança da equipe de {_e} em quem pede (0,4 a 1,6; 1 neutra)"),
                (f"{_e}.ocupacao", f"ocupação da equipe de {_e} (gente presa e fila regular)"),
                (f"{_e}.demora_de_pedido", f"minutos que um pedido levaria agora até alguém da equipe de {_e} pegá-lo")]
# (v2.1) a causa dos chamados e o que os clientes sentiram em cada rota
COLUNAS += [("chamados_por_queda", "chamados abertos neste minuto que nasceram da queda do processo"),
            ("chamados_por_rota_lenta", "chamados abertos neste minuto que nasceram de lentidão sentida numa rota, sem defeito nem incidente"),
            ("chamados_por_rota_com_erro", "chamados abertos neste minuto que nasceram de erro numa rota, sem defeito, incidente nem queda")]
COLUNAS += [(f"sessoes_com_erro.{r}", f"sessões de clientes que desistiram por erro na rota {r} neste minuto") for r in ROTAS]
COLUNAS += [(f"sessoes_lentas.{r}", f"sessões de clientes que sentiram a rota {r} acima de 4 segundos neste minuto") for r in ROTAS]
NOMES_COLUNAS = [c for c, _ in COLUNAS]
COL = {c: i for i, c in enumerate(NOMES_COLUNAS)}

# as listas de registros e a chave pela qual cada uma é ordenada na leitura
LISTAS = {"liberacoes": "t", "episodios_de_defeito_no_ar": "liberado_em", "defeitos_escritos": "t", "defeitos_barrados_antes_do_ar": "t",
          "incidentes": "inicio", "quedas_do_processo_por_memoria": "inicio", "mudancas_de_regime": "t", "sprints": "inicio",
          "fins_de_sprint": "t", "fins_de_mes": "t", "pessoal": "t", "atos": "recebido", "carteira_por_dia": "t",
          "entradas_e_saidas": "t", "latencia_por_dia": "dia", "platos": "inicio", "expansoes_de_mercado": "decidida_em",
          "campanhas": "inicio", "cadastros_adiados": "t", "erros_no_registro_por_queda": "t", "blocos_do_calendario": "inicio",
          "chamados": "t", "janelas_de_rota": "inicio"}


class Verdade:
    def __init__(self, semente, nulo, pasta):
        self.semente = semente
        self.nulo = nulo
        self.pasta = pasta
        os.makedirs(pasta, exist_ok=True)
        self.mem = {k: [] for k in LISTAS}                # registros em memória (abertos ou fechados há menos de RETENCAO)
        self.no_ar = {}                                    # (função, implementação) -> episódio aberto
        self.incidente_aberto = None
        self.atos = {}                                     # número -> registro do ato (enquanto em memória)
        self._causas = {}                                  # chamado -> (instante, registro que o causou)
        self.latencia_dia = {r: [] for r in ROTAS}         # (dia, média) dos últimos 30 dias, para as mudanças de regime
        self._lat = {r: [0.0, 0] for r in ROTAS}
        self.chamados_por_causa = {"defeito": 0, "incidente": 0, "queda do processo": 0, "rota com erro": 0, "rota lenta": 0, "outros": 0}
        self.janelas = Janelas()
        self._chamados = {}                                # item -> registro do chamado (enquanto em memória)
        self.volume_inicial_folga_dias = None
        self.teto_inicial = None
        self.dia_aberto = 0
        self.linhas = np.full((MINUTOS_DIA, len(COLUNAS)), np.nan, dtype=np.float32)
        self._zerar_minuto()
        self.dias_gravados = 0

    def _zerar_minuto(self):
        self.m_erros_defeito = 0
        self.m_erros_outros = 0
        self.m_chamados = dict.fromkeys(("defeito", "incidente", "queda do processo", "rota com erro", "rota lenta", "outros"), 0)
        self.m_sentidos = {"erro": dict.fromkeys(ROTAS, 0), "lentidão": dict.fromkeys(ROTAS, 0)}
        self.m_implantacao = 0
        self.m_atos_recebidos = 0
        self.m_atos_tratados = 0

    def _novo(self, lista, reg, final):
        reg["_final"] = final
        self.mem[lista].append(reg)
        return reg

    # ---------- o código no ar ----------
    def implantacao(self, t, versao, tipo, antes, depois, funcionalidades, produto, por_ato=None):
        entram = sorted((f, v) for f, v in depois.items() if (f, v) in codigo.DEFEITOS and antes.get(f) != v)
        saem = sorted((f, v) for f, v in antes.items() if (f, v) in codigo.DEFEITOS and depois.get(f) != v)
        regime = []
        for f, v in sorted(depois.items()):
            if antes.get(f) != v and (f, v) not in codigo.DEFEITOS and (f, antes.get(f)) not in codigo.DEFEITOS:
                regime.append(f)
        self.m_implantacao = 1
        self._novo("liberacoes", {"t": t, "versao": versao, "tipo": tipo,
                                  "defeitos_que_entraram": [list(x) for x in entram], "defeitos_que_sairam": [list(x) for x in saem],
                                  "funcoes_que_mudaram_de_comportamento": regime, "funcionalidades": list(funcionalidades),
                                  "pedida_pelo_ato": por_ato}, t)
        for f, v in saem:
            ep = self.no_ar.pop((f, v), None)
            if ep is not None:
                ep["saiu_do_ar"] = t
                ep["duracao_no_ar_min"] = t - ep["liberado_em"]
                ep["saiu_por"] = tipo
                ep["saiu_pelo_ato"] = por_ato
                ep["_final"] = t
        for f, v in entram:
            tipo_def, descricao = codigo.DEFEITOS[(f, v)]
            comp = codigo.COMPONENTE_FUNCAO[f]
            ep = self._novo("episodios_de_defeito_no_ar", {
                "funcao": f, "implementacao": v, "componente": comp, "como_aparece": tipo_def, "descricao": descricao,
                "onde": [[f"rota {r}", "respostas com erro no minuto"] for r in _nomes_rotas(f)] + [[f"chamados de {_nome_comp(comp)}", "abertos"]],
                "liberado_em": t, "versao": versao, "primeiro_erro": None, "erros": 0, "primeiro_chamado": None, "chamados": 0,
                "primeira_escalacao": None, "escalacoes": 0, "saiu_do_ar": None, "duracao_no_ar_min": None, "saiu_por": None,
                "saiu_pelo_ato": None, "atos_que_o_tocaram": []}, None)
            self.no_ar[(f, v)] = ep
        for f in regime:
            rotas = sorted({r for r, fs in ROTAS_FUNCOES.items() if f in fs})
            self._novo("mudancas_de_regime", {"t": t, "versao": versao, "funcao": f, "de": antes.get(f), "para": depois[f], "rotas": rotas,
                                              "onde": [[f"rota {_NOME_ROTA[r]}", "latência média em ms"] for r in rotas if r in _NOME_ROTA],
                                              "tipo": "mudança de regime", "latencia_media_7_dias_antes": None,
                                              "latencia_media_7_dias_depois": None}, None)

    def erros_do_minuto(self, t, erros):
        """Os erros do produto neste minuto (rota, função onde nasceu, tipo da exceção)."""
        for _, rota, funcao, tipo in erros:
            achou = False
            if funcao is not None:
                for (f, v), ep in self.no_ar.items():
                    if f == funcao:
                        achou = True
                        ep["erros"] += 1
                        if ep["primeiro_erro"] is None:
                            ep["primeiro_erro"] = t
                if rota == "processo" and self.incidente_aberto is None:
                    self._novo("erros_no_registro_por_queda", {"t": t}, t)
            if achou:
                self.m_erros_defeito += 1
            else:
                self.m_erros_outros += 1

    def defeito_escrito(self, t, item, projeto, funcao, impl, pressa):
        self._novo("defeitos_escritos", {"t": t, "item": item, "projeto": projeto, "funcao": funcao, "implementacao": impl,
                                         "pressa_do_squad": round(pressa, 2)}, t)

    def defeito_barrado(self, t, item, funcao, por):
        self._novo("defeitos_barrados_antes_do_ar", {"t": t, "item": item, "funcao": funcao, "por": por}, t)

    # ---------- chamados ----------
    def chamado_aberto(self, t, item, cliente, motivo, comp, causa):
        """Um chamado chegou. (v2.1) Ele guarda de onde veio (a rota e o instante do erro ou da lentidão que o cliente sentiu) e a causa:
        defeito, incidente, queda do processo, rota com erro, rota lenta, ou outros (sem rota: dúvida, fatura, cobrança, nota)."""
        funcao = causa[0] if causa else None
        quando = causa[1] if causa else None
        rota = causa[2] if causa and len(causa) > 2 else None
        evento = "erro" if motivo == "erro" else "lentidão"
        reg = {"t": t, "item": item, "componente": comp, "motivo": motivo,
               "origem": {"rota": rota, "processo": rota_proc(rota), "instante": quando, "evento": evento} if rota else None,
               "causa": None, "registro_da_causa": None, "janela_de_rota": None, "escalado_em": None}
        achou = None
        candidatos = list(self.no_ar.items()) + [((e["funcao"], e["implementacao"]), e) for e in self.mem["episodios_de_defeito_no_ar"]
                                                 if e["saiu_do_ar"] is not None and quando is not None
                                                 and e["liberado_em"] <= quando <= e["saiu_do_ar"]]
        if funcao is not None:
            achou = next((ep for (f, v), ep in candidatos if f == funcao), None)
        elif rota is not None and motivo == "lentidão":
            # a lentidão de uma rota que chama uma função com defeito lento no ar nasce do defeito
            achou = next((ep for (f, v), ep in candidatos if ep["como_aparece"] == "lento" and f in ROTAS_FUNCOES.get(rota, ())), None)
        if achou is not None:
            achou["chamados"] += 1
            if achou["primeiro_chamado"] is None:
                achou["primeiro_chamado"] = t
            reg["causa"], reg["registro_da_causa"] = "defeito", {"episodio_de_defeito": achou["funcao"], "liberado_em": achou["liberado_em"]}
            self._causas[item] = (t, achou)
        elif motivo in ("erro", "lentidão") and quando is not None:
            for lista, nome in (("incidentes", "incidente"), ("quedas_do_processo_por_memoria", "queda do processo")):
                inc = next((i for i in reversed(self.mem[lista]) if i["inicio"] - ANTES_DA_SONDA <= quando <= (i["fim"] or t)), None)
                if inc is not None:
                    inc["chamados"] += 1
                    if inc["primeiro_chamado"] is None:
                        inc["primeiro_chamado"] = t
                    if rota is not None:
                        por = inc.setdefault("chamados_por_rota_de_origem", {})
                        por[rota] = por.get(rota, 0) + 1
                    reg["causa"], reg["registro_da_causa"] = nome, {nome: inc["inicio"]}
                    self._causas[item] = (t, inc)
                    break
        if reg["causa"] is None:
            reg["causa"] = ("rota com erro" if evento == "erro" else "rota lenta") if rota is not None else "outros"
        self.chamados_por_causa[reg["causa"]] += 1
        self.m_chamados[reg["causa"]] += 1
        if rota is not None:
            j = achar_janela(self.mem["janelas_de_rota"], rota, evento, quando)
            if j is not None:
                j["chamados_gerados"] += 1
                if len(j["chamados"]) < 100:
                    j["chamados"].append(item)
                reg["janela_de_rota"] = j["inicio"]
        self._chamados[item] = reg
        self._novo("chamados", reg, t + 3 * MINUTOS_DIA)

    def sentido(self, t, rota, tipo, falhou=None):
        """(v2.1) Um cliente sentiu erro (desistiu depois de tentar de novo) ou lentidão (mais de 4 segundos) numa rota."""
        inc = self.incidente_aberto
        if inc is not None:
            contexto = "incidente" if inc["causa"] == "volume do banco cheio" else "queda do processo"
        elif tipo == "erro" and falhou is not None and any(f == falhou for f, _ in self.no_ar):
            contexto = "defeito"
        elif tipo == "lentidão" and any(ep["como_aparece"] == "lento" and f in ROTAS_FUNCOES.get(rota, ()) for (f, _), ep in self.no_ar.items()):
            contexto = "defeito"
        else:
            contexto = "erro sem defeito" if tipo == "erro" else "rota lenta"
        self.m_sentidos[tipo][rota] += 1
        self.janelas.evento(t, rota, tipo, contexto, lambda j: self._novo("janelas_de_rota", j, None))

    def escalado(self, t, chamado, destino):
        par = self._causas.get(chamado)
        if par is not None:
            ep = par[1]
            ep["escalacoes"] = ep.get("escalacoes", 0) + 1
            if ep.get("primeira_escalacao") is None:
                ep["primeira_escalacao"] = t
        reg = self._chamados.get(chamado)
        if reg is not None and reg["escalado_em"] is None:
            reg["escalado_em"] = t
            if reg["origem"] is not None and reg["janela_de_rota"] is not None:
                j = achar_janela(self.mem["janelas_de_rota"], reg["origem"]["rota"], reg["origem"]["evento"], reg["origem"]["instante"])
                if j is not None:
                    j["chamados_escalados"] += 1

    # ---------- o produto parado ----------
    def minuto_da_sonda(self, t, falhando, produto):
        if falhando and self.incidente_aberto is None:
            livre = produto.volume_paginas - produto.paginas_ocupadas()
            cheio = livre < 200
            reg = {"inicio": t, "fim": None, "duracao_min": None, "causa": "volume do banco cheio" if cheio else "processo parado",
                   "onde": ([["sonda de disponibilidade", "verificações com falha no minuto"], ["banco do produto", "espaço livre no volume em MB"]]
                            + [[f"rota {_NOME_ROTA[r]}", "respostas com erro no minuto"] for r in ROTAS])
                   if cheio else [["sonda de disponibilidade", "verificações com falha no minuto"], ["servidor da aplicação", "reinícios do processo no minuto"]],
                   "primeiro_chamado": None, "chamados": 0, "primeira_escalacao": None, "escalacoes": 0,
                   "causa_diagnosticada": None, "folga_dada_em_dias": None, "registros_apagados": None, "tratado_em": None,
                   "volume_paginas_no_inicio": int(produto.volume_paginas), "paginas_livres_no_inicio": int(livre)}
            self.incidente_aberto = self._novo("incidentes" if cheio else "quedas_do_processo_por_memoria", reg, None)
        elif not falhando and self.incidente_aberto is not None:
            self.incidente_aberto["fim"] = t
            self.incidente_aberto["duracao_min"] = t - self.incidente_aberto["inicio"]
            self.incidente_aberto["_final"] = t
            self.incidente_aberto = None

    def incidente_resolvido(self, t, causa, folga, apagados):
        inc = self.incidente_aberto or (self.mem["incidentes"][-1] if self.mem["incidentes"] else None)
        if inc is not None:
            inc["causa_diagnosticada"] = causa
            inc["folga_dada_em_dias"] = folga
            inc["registros_apagados"] = apagados
            inc["tratado_em"] = t

    def cadastro_adiado(self, t, cliente, motivo):
        """O administrativo não conseguiu gravar a conta de um cliente novo no banco do produto (volume cheio): tenta de novo depois."""
        self._novo("cadastros_adiados", {"t": t, "cliente": cliente, "motivo": motivo, "gravado_em": None}, None)

    def cadastro_gravado(self, t, cliente):
        for r in self.mem["cadastros_adiados"]:
            if r["cliente"] == cliente and r["gravado_em"] is None:
                r["gravado_em"] = t
                r["_final"] = t

    # ---------- o calendário ----------
    def bloco_do_calendario(self, b):
        """Nulo embaralhado: um bloco do calendário sorteado (de quando a quando, e que hora e data o calendário mostrava)."""
        self._novo("blocos_do_calendario", dict(b), b["fim"])

    def nova_data(self, t, cal):
        if cal.dia_mes == cal.dias_no_mes and not self.nulo == "embaralhado":
            self._novo("fins_de_mes", {"t": t}, t)

    def dia_vivido(self, t, carteira):
        self._novo("carteira_por_dia", {"t": t, "clientes_ativos": carteira}, t)

    def latencia(self, t, cal, rotas):
        if cal.util and 9 * 60 <= cal.minuto < 18 * 60:
            for r, v in rotas.items():
                if v[0] > 0:
                    acc = self._lat[r]
                    acc[0] += v[3]
                    acc[1] += 1
        if cal.minuto == MINUTOS_DIA - 1:
            d = t // MINUTOS_DIA
            medias = {}
            for r in ROTAS:
                acc = self._lat[r]
                if acc[1]:
                    m = round(acc[0] / acc[1], 1)
                    self.latencia_dia[r].append((d, m))
                    del self.latencia_dia[r][:-30]
                    medias[r] = m
                self._lat[r] = [0.0, 0]
            if medias:
                self._novo("latencia_por_dia", {"dia": d, "t": t, "media_no_horario_comercial_ms": medias}, t)

    # ---------- sprints, pessoal, carteira ----------
    def sprint_planejado(self, t, projeto, numero, meta, capacidade, razao, cal):
        self._novo("sprints", {"projeto": projeto, "numero": numero, "inicio": t, "meta_pontos": meta, "capacidade_pontos": capacidade,
                               "meta_sobre_capacidade": round(razao, 2), "pressa": razao > 1.15, "fim": None, "pontos_feitos": None}, None)

    def sprint_fechado(self, t, projeto, numero, total, feitos):
        for s in self.mem["sprints"]:
            if s["projeto"] == projeto and s["numero"] == numero:
                s["fim"] = t
                s["pontos_feitos"] = feitos
                s["_final"] = t
        self._novo("fins_de_sprint", {"t": t, "projeto": projeto, "numero": numero}, t)

    def pessoal_evento(self, t, tipo, equipe):
        self._novo("pessoal", {"t": t, "tipo": tipo, "equipe": equipe}, t)

    def carteira_evento(self, t, tipo, cliente, plano):
        self._novo("entradas_e_saidas", {"t": t, "tipo": tipo, "cliente": cliente, "plano": plano}, t)

    # ---------- a deriva que assenta e a campanha ----------
    def plato_inicio(self, t, teto, carteira):
        self._novo("platos", {"inicio": t, "fim": None, "duracao_min": None, "teto": teto, "carteira_no_inicio": carteira,
                              "carteira_no_fim": None, "causa": "a carteira chegou perto do teto do mercado e a chegada de leads secou",
                              "onde": [["carteira de clientes", "clientes ativos"], ["leads de site", "novos no minuto"],
                                       ["leads de indicação", "novos no minuto"], ["funil de vendas", "leads"]],
                              "terminou_por": None}, None)

    def plato_fim(self, t, carteira, causa):
        for p in self.mem["platos"]:
            if p["fim"] is None:
                p["fim"] = t
                p["duracao_min"] = t - p["inicio"]
                p["carteira_no_fim"] = carteira
                p["terminou_por"] = causa
                p["_final"] = t

    def expansao(self, t, vale_em, antes, depois, carteira):
        self._novo("expansoes_de_mercado", {"decidida_em": t, "vale_a_partir_de": vale_em, "teto_antes": antes, "teto_depois": depois,
                                            "carteira_na_decisao": carteira,
                                            "causa": "o dono viu a carteira parada e decidiu abrir mercado novo (região e canal)"}, t)

    def campanha(self, inicio, fim, forca, onde):
        self._novo("campanhas", {"inicio": inicio, "fim": fim, "duracao_min": fim - inicio, "forca": forca, "onde": onde,
                                 "causa": "dia de campanha injetado de fora (Mundo.injetar_campanha)"}, fim)

    # ---------- atos ----------
    def ato(self, t, numero, equipe, tipo, texto, rota, comp, sistema, item, demora, estado_equipe):
        self.m_atos_recebidos += 1
        self.atos[numero] = self._novo("atos", {
            "numero": numero, "equipe": equipe, "tipo": tipo, "texto": texto, "recebido": t, "rota": rota, "componente": comp,
            "virou": {"sistema": sistema, "item": item}, "demora_ate_ficar_disponivel_min": demora, "disponivel_em": t + demora,
            "equipe_ao_receber": estado_equipe, "pego_em": None, "tratado_em": None, "minutos_de_trabalho": None,
            "trabalho_adiado": None, "efeito": None, "confianca_antes": None, "confianca_depois": None, "equipe_ao_tratar": None,
            "resposta": None, "desfecho": None, "horas_extras_atribuidas": []}, None)

    def ato_tratado(self, t, numero, pego, minutos, adiada, efeito, antes, depois, estado_equipe, texto):
        self.m_atos_tratados += 1
        a = self.atos.get(numero)
        if a is None:
            return
        a.update({"pego_em": pego, "tratado_em": t, "minutos_de_trabalho": minutos, "trabalho_adiado": adiada, "efeito": efeito,
                  "confianca_antes": round(antes, 4), "confianca_depois": round(depois, 4), "equipe_ao_tratar": estado_equipe,
                  "resposta": texto, "desfecho": "respondido", "_final": t})
        if a["componente"] is not None:
            for ep in self.no_ar.values():
                if ep["componente"] == a["componente"]:
                    ep["atos_que_o_tocaram"].append(numero)

    def ato_sem_resposta(self, t, numero):
        a = self.atos.get(numero)
        if a is not None:
            a["desfecho"] = "sem resposta"
            a["tratado_em"] = None
            a["expirou_em"] = t
            a["_final"] = t

    def extra_por_ato(self, t, pessoa, equipe, minutos, numeros):
        """Hora extra que a pessoa fez porque o dia foi tomado por pedidos da porta."""
        for n in numeros:
            a = self.atos.get(n)
            if a is not None:
                a["horas_extras_atribuidas"].append({"t": t, "pessoa": pessoa, "equipe": equipe, "minutos": minutos,
                                                     "onde": [f"quadro da equipe de {equipe}", "horas extras no dia"]})

    # ---------- o minuto e o dia em disco ----------
    def linha(self, t, valores):
        """Grava a linha do minuto t; no último minuto do dia, o dia vai para o disco."""
        d = t // MINUTOS_DIA
        if d != self.dia_aberto:
            self._gravar_dia(self.dia_aberto, t - 1, [])
            self.dia_aberto = d
        v = self.linhas[t % MINUTOS_DIA]
        v[:] = valores
        v[COL["erros_de_defeito"]] = self.m_erros_defeito
        v[COL["erros_de_outra_causa"]] = self.m_erros_outros
        mc = self.m_chamados
        v[COL["chamados_por_defeito"]], v[COL["chamados_por_incidente"]], v[COL["chamados_de_outra_causa"]] = mc["defeito"], mc["incidente"], mc["outros"]
        v[COL["chamados_por_queda"]], v[COL["chamados_por_rota_lenta"]], v[COL["chamados_por_rota_com_erro"]] = \
            mc["queda do processo"], mc["rota lenta"], mc["rota com erro"]
        for r in ROTAS:
            v[COL[f"sessoes_com_erro.{r}"]] = self.m_sentidos["erro"][r]
            v[COL[f"sessoes_lentas.{r}"]] = self.m_sentidos["lentidão"][r]
        self.janelas.fechar_velhas(t, lambda j: j.__setitem__("_final", j["fim"] + 2 * MINUTOS_DIA))
        v[COL["implantacao"]] = self.m_implantacao
        v[COL["atos_recebidos"]] = self.m_atos_recebidos
        v[COL["atos_tratados"]] = self.m_atos_tratados
        self._zerar_minuto()

    def fechar_dia(self, t, eventos):
        """Chamado depois do último minuto do dia: a linha do dia vai para o disco, e os registros que ficaram definitivos também."""
        self._gravar_dia(t // MINUTOS_DIA, t, eventos)
        self.dia_aberto = t // MINUTOS_DIA + 1

    def _gravar_dia(self, d, t, eventos):
        self._regimes(t)
        definitivos = {}
        for lista, regs in self.mem.items():
            fica = []
            for r in regs:
                if r["_final"] is not None and r["_final"] <= t - RETENCAO:
                    del r["_final"]
                    definitivos.setdefault(lista, []).append(r)
                else:
                    fica.append(r)
            self.mem[lista] = fica
        for n in [n for n, a in self.atos.items() if "_final" not in a]:
            del self.atos[n]
        for c in [c for c, (tt, _) in self._causas.items() if tt < t - 30 * MINUTOS_DIA]:
            del self._causas[c]
        for c in [c for c, r in self._chamados.items() if "_final" not in r]:
            del self._chamados[c]
        base = os.path.join(self.pasta, f"dia_{d:05d}")
        np.savez_compressed(base + ".npz", t=np.arange(d * MINUTOS_DIA, (d + 1) * MINUTOS_DIA, dtype=np.int64), valores=self.linhas,
                            colunas=np.array(NOMES_COLUNAS))
        with open(base + ".json", "w", encoding="utf-8") as f:
            json.dump({"dia": d, "registros": definitivos, "eventos_humanos": [[int(a), b] for a, b in eventos]}, f, ensure_ascii=False)
        self.linhas = np.full((MINUTOS_DIA, len(COLUNAS)), np.nan, dtype=np.float32)
        self.dias_gravados = d + 1

    def _regimes(self, t):
        """A latência antes e depois de cada mudança de regime, calculada quando a semana seguinte já passou."""
        for r in self.mem["mudancas_de_regime"]:
            if r["_final"] is None and t >= r["t"] + 8 * MINUTOS_DIA:
                d = r["t"] // MINUTOS_DIA
                antes, depois = [], []
                for rota in r["rotas"]:
                    serie = self.latencia_dia.get(rota, [])
                    a = [v for dd, v in serie if d - 7 <= dd < d]
                    b = [v for dd, v in serie if d < dd <= d + 7]
                    antes.append(round(sum(a) / len(a), 1) if a else None)
                    depois.append(round(sum(b) / len(b), 1) if b else None)
                r["latencia_media_7_dias_antes"] = antes
                r["latencia_media_7_dias_depois"] = depois
                r["_final"] = t

    # ---------- o que a bancada lê ----------
    def ler_disco(self, ate_dia=None):
        """Os registros e os eventos humanos já gravados na pasta de história."""
        listas = {k: [] for k in LISTAS}
        eventos = []
        for d in range(self.dias_gravados if ate_dia is None else min(ate_dia, self.dias_gravados)):
            caminho = os.path.join(self.pasta, f"dia_{d:05d}.json")
            with open(caminho, encoding="utf-8") as f:
                dia = json.load(f)
            for k, regs in dia["registros"].items():
                listas[k].extend(regs)
            eventos.extend(tuple(e) for e in dia["eventos_humanos"])
        return listas, eventos

    def por_minuto(self, inicio=0, fim=None):
        """A verdade por minuto entre os instantes inicio e fim (inclusive): (instantes, matriz, nomes das colunas)."""
        fim = (self.dias_gravados * MINUTOS_DIA - 1) if fim is None else fim
        ts, vs = [], []
        for d in range(max(0, inicio // MINUTOS_DIA), fim // MINUTOS_DIA + 1):
            if d < self.dias_gravados:
                with np.load(os.path.join(self.pasta, f"dia_{d:05d}.npz")) as z:
                    t, v = z["t"], z["valores"]
            elif d == self.dia_aberto:
                t, v = np.arange(d * MINUTOS_DIA, (d + 1) * MINUTOS_DIA), self.linhas
            else:
                continue
            sel = (t >= inicio) & (t <= fim)
            ts.append(t[sel])
            vs.append(v[sel])
        if not ts:
            return np.zeros(0, dtype=np.int64), np.zeros((0, len(COLUNAS)), dtype=np.float32), list(NOMES_COLUNAS)
        return np.concatenate(ts), np.concatenate(vs), list(NOMES_COLUNAS)

    def como_dict(self, relogio, embaralhado):
        listas, _ = self.ler_disco()
        for k, regs in self.mem.items():
            listas[k].extend({c: v for c, v in r.items() if c != "_final"} for r in regs)
        for k, chave in LISTAS.items():
            listas[k].sort(key=lambda r: (r.get(chave) is None, r.get(chave) or 0))
        carteira = [[r["t"], r["clientes_ativos"]] for r in listas["carteira_por_dia"]]
        semanas = []
        for i in range(7, len(carteira), 7):
            a, b = carteira[i - 7][1], carteira[i][1]
            if a:
                semanas.append(round(100.0 * (b - a) / a, 2))
        ciclos = {
            "dia_util": "as pessoas trabalham das 8h às 18h nos dias úteis; os clientes usam o produto no horário comercial deles, "
                        "com almoço mais vazio e picos às 10h e às 15h; tarefas agendadas do servidor rodam de madrugada (cópia às 2h, "
                        "limpeza de sessões às 3h, reposição de estoque às 4h, resumo às 7h)",
            "semana": "segunda-feira com mais uso e mais chamados (inclusive os guardados do fim de semana); sexta com menos uso e "
                      "gente saindo mais cedo; liberações às terças e quintas a partir das 15h; reindexação aos domingos 4h30",
            "sprint": "sprints de duas semanas que começam às segundas; planejamento no primeiro dia, revisão e retrospectiva na sexta "
                      "da segunda semana, liberação extra nessa sexta de manhã; a pressa cresce no fim quando o sprint está atrasado",
            "mes": "faturamento no dia 1 às 6h (fila de trabalhos cheia); reunião mensal no primeiro dia útil; vendas fecham mais "
                   "nos últimos seis dias do mês; as lojas tiram mais relatórios no fim do mês",
            "fins_de_sprint": listas["fins_de_sprint"],
            "fins_de_mes": [r["t"] for r in listas["fins_de_mes"]],
        }
        if embaralhado:
            ciclos = {"ausentes": "nulo embaralhado: os processos vivem num calendário sorteado em blocos; nenhum ciclo de hora, de "
                                   "dia da semana, de sprint ou de mês corresponde ao relógio da porta",
                      "blocos_do_calendario": listas["blocos_do_calendario"]}
        quedas = listas["quedas_do_processo_por_memoria"]
        saida = {
            "versao_do_mundo": 2,
            "semente": self.semente,
            "nulo": self.nulo,
            "minutos": relogio.t,
            "convencao_do_tempo": "t = 0 é a criação (segunda-feira, 0h); cada passo avança t e faz acontecer o minuto t",
            "ciclos": ciclos,
            "liberacoes": listas["liberacoes"],
            "liberacoes_com_defeito": [l for l in listas["liberacoes"] if l["defeitos_que_entraram"]],
            "episodios_de_defeito_no_ar": listas["episodios_de_defeito_no_ar"],
            "incidentes": listas["incidentes"],
            "cadastros_adiados_por_volume_cheio": listas["cadastros_adiados"],
            "mudancas_de_regime": listas["mudancas_de_regime"],
            "deriva": {"carteira_por_dia": carteira, "crescimento_por_semana_em_porcento": semanas,
                       "entradas_e_saidas": [[r["t"], r["tipo"], r["plano"]] for r in listas["entradas_e_saidas"]],
                       "teto_inicial": self.teto_inicial, "platos": listas["platos"], "expansoes": listas["expansoes_de_mercado"]},
            "campanhas": listas["campanhas"],
            "sprints": listas["sprints"],
            "sprints_de_pressa": [s for s in listas["sprints"] if s["pressa"]],
            "defeitos_escritos": listas["defeitos_escritos"],
            "defeitos_barrados_antes_do_ar": listas["defeitos_barrados_antes_do_ar"],
            "quedas_do_processo_por_memoria": {"erros_no_registro": [r["t"] for r in listas["erros_no_registro_por_queda"]],
                                               "sonda_parada": quedas},
            "pessoal": listas["pessoal"],
            "chamados_por_causa": dict(self.chamados_por_causa),
            "chamados": listas["chamados"],
            "causas": {
                "categorias": {
                    "causa declarada": "há um mecanismo do mundo que leva de um campo ao outro: as leis abaixo (erro ou lentidão numa rota "
                                       "levam a chamados do componente da rota) e o 'onde' dos episódios de defeito",
                    "causa comum (incidente)": "durante um incidente (e até seis horas depois do fim, enquanto os chamados chegam e são "
                                               "escalados), os campos de 'campos_quando_o_produto_para' se mexem juntos porque o produto "
                                               "parou, sem que um cause o outro; o par da lei (rota para o componente dela) continua "
                                               "sendo causa declarada",
                    "causa comum (queda do processo)": "o mesmo, na queda curta do processo por falta de memória",
                    "causa comum (calendário)": "os dois campos são movidos pelo calendário (ver 'calendario'): o mesmo relógio mexe nos dois",
                    "sem relação": "nenhuma das anteriores",
                },
                "ordem": list(CATEGORIAS),
                "leis": leis(),
                "janelas_de_rota": listas["janelas_de_rota"],
                "campos_quando_o_produto_para": campos_produto_parado(),
                "como_classificar": "classificar_par(verdade, [processo, campo], [processo, campo], inicio, fim) em causas.py",
            },
            "calendario": calendario.para_a_verdade(),
            "atos": listas["atos"],
            "latencia_por_dia": listas["latencia_por_dia"],
            "volume_inicial_folga_dias": self.volume_inicial_folga_dias,
            "verdade_por_minuto": {"pasta": self.pasta, "arquivos": "dia_NNNNN.npz (t, valores, colunas)", "dias_gravados": self.dias_gravados,
                                   "colunas": [{"nome": c, "mede": d} for c, d in COLUNAS]},
        }
        if self.nulo == "sem_defeito":
            saida["observacao_do_nulo"] = ("nenhuma liberação levou defeito ao ar; os episódios de erros seguidos de chamados nesse nulo "
                                           "são só os incidentes listados em 'incidentes'")
        if self.nulo == "sem_deriva":
            saida["observacao_do_nulo"] = ("a carteira não cresce nem assenta: cada cliente que entra leva à saída do cliente mais "
                                           "insatisfeito em até dois dias, e não há teto, platô nem expansão; a versão nova continua "
                                           "mudando a latência (está em 'mudancas_de_regime')")
        if self.nulo == "surdo":
            saida["observacao_do_nulo"] = "a porta aceita atos e devolve números, mas nenhum ato chega ao mundo e nada é respondido"
        return saida


def _nome_comp(comp):
    from .cadastro import NOME_COMPONENTE
    return NOME_COMPONENTE[comp]


def _nomes_rotas(funcao):
    return [_NOME_ROTA[r] for r, fs in sorted(ROTAS_FUNCOES.items()) if funcao in fs and r in _NOME_ROTA]


def _rotas_funcoes():
    import inspect
    out = {}
    for rota, f in codigo.ROTAS_CODIGO.items():
        fonte = inspect.getsource(f)
        out[rota] = {fn for fn in codigo.IMPLEMENTACOES if f'cod["{fn}"]' in fonte}
    out["fila"] = {"emitir_nota", "enviar_email"}
    return out


ROTAS_FUNCOES = _rotas_funcoes()
from .cadastro import NOME_ROTA as _NOME_ROTA  # noqa: E402
