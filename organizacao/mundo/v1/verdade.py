"""A verdade: o que a empresa tem e quando aconteceu, para a bancada conferir o que o observador percebeu. Nada aqui é lido pelas
pessoas nem pelos sistemas, e nada sai pela porta do mundo: os mecanismos só anotam o que fizeram.

O que se anota:
- ciclos: as leis do calendário (dia útil, segunda mais cheia, sexta mais lenta, liberações às terças e quintas, fim de sprint, fim de
  mês) e os instantes em que cada fim de sprint e cada fim de mês caiu; no nulo embaralhado, os blocos do calendário sorteado;
- liberações: toda implantação, com os defeitos que entraram e saíram do ar e as funcionalidades que vieram;
- episódios de defeito: para cada defeito que chegou ao ar, a liberação, o primeiro erro, o primeiro chamado que ele causou, a
  primeira escalação, a correção (ou reversão) que o tirou do ar;
- incidentes: quando o produto parou de responder, por quê, quando voltou, quantos chamados vieram dele;
- mudanças de regime: as liberações que mudaram para sempre o trabalho de uma rota (a versão nova), com a latência antes e depois;
- deriva: a carteira de clientes dia a dia e a taxa de crescimento por semana;
- sprints: meta, capacidade e a razão entre elas (o sprint de pressa é o que passa da capacidade), e os defeitos escritos nele;
- pessoal: contratações e saídas;
- atos recebidos pela porta e as respostas."""
from . import codigo
from .cadastro import ROTAS, MINUTOS_DIA
from .causas import Janelas, achar_janela, leis, campos_produto_parado, rota_proc, CATEGORIAS

ANTES_DA_SONDA = 10                 # (v1.4) os clientes sentem o produto parado alguns minutos antes de a sonda o declarar


class Verdade:
    def __init__(self, semente, nulo):
        self.semente = semente
        self.nulo = nulo
        self.liberacoes = []
        self.episodios = []                 # defeitos no ar
        self.no_ar = {}                     # (função, implementação) -> episódio aberto
        self.defeitos_escritos = []
        self.defeitos_barrados = []
        self.incidentes = []
        self.incidente_aberto = None
        self.regimes = []
        self.carteira = []
        self.carteira_eventos = []
        self.sprints = []
        self.pessoal = []
        self.fins_de_sprint = []
        self.fins_de_mes = []
        self.atos = {}
        self.latencia_dia = {r: [] for r in ROTAS}     # (dia, média da latência no horário comercial)
        self._lat = {r: [0.0, 0] for r in ROTAS}
        self.queda_processo = []
        self.quedas = []
        self._caindo = None
        self.chamados_por_causa = {"defeito": 0, "incidente": 0, "queda do processo": 0, "rota com erro": 0, "rota lenta": 0, "outros": 0}
        self.chamados = []                  # (v1.4) cada chamado com a sua origem e a sua causa
        self._chamados = {}
        self.janelas = Janelas()
        self.janelas_de_rota = []

    # ---------- o código no ar ----------
    def implantacao(self, t, versao, tipo, antes, depois, funcionalidades, produto):
        entram = sorted((f, v) for f, v in depois.items() if (f, v) in codigo.DEFEITOS and antes.get(f) != v)
        saem = sorted((f, v) for f, v in antes.items() if (f, v) in codigo.DEFEITOS and depois.get(f) != v)
        regime = []
        for f, v in sorted(depois.items()):
            if antes.get(f) != v and (f, v) not in codigo.DEFEITOS and (f, antes.get(f)) not in codigo.DEFEITOS:
                regime.append(f)
        self.liberacoes.append({"t": t, "versao": versao, "tipo": tipo,
                                "defeitos_que_entraram": [list(x) for x in entram], "defeitos_que_sairam": [list(x) for x in saem],
                                "funcoes_que_mudaram_de_comportamento": regime})
        for f, v in saem:
            ep = self.no_ar.pop((f, v), None)
            if ep is not None:
                ep["saiu_do_ar"] = t
                ep["saiu_por"] = tipo
        for f, v in entram:
            tipo_def, descricao = codigo.DEFEITOS[(f, v)]
            ep = {"funcao": f, "implementacao": v, "componente": codigo.COMPONENTE_FUNCAO[f], "como_aparece": tipo_def,
                  "descricao": descricao, "liberado_em": t, "versao": versao, "primeiro_erro": None, "erros": 0,
                  "primeiro_chamado": None, "chamados": 0, "primeira_escalacao": None, "escalacoes": 0, "saiu_do_ar": None,
                  "saiu_por": None}
            self.episodios.append(ep)
            self.no_ar[(f, v)] = ep
        for f in regime:
            rotas = sorted({r for r, fs in ROTAS_FUNCOES.items() if f in fs})
            self.regimes.append({"t": t, "versao": versao, "funcao": f, "de": antes.get(f), "para": depois[f], "rotas": rotas,
                                 "tipo": "mudança de regime"})

    def erros_do_minuto(self, t, erros):
        """Os erros do produto neste minuto (rota, função onde nasceu, tipo da exceção)."""
        for _, rota, funcao, tipo in erros:
            if funcao is None:
                continue
            for (f, v), ep in self.no_ar.items():
                if f == funcao:
                    ep["erros"] += 1
                    if ep["primeiro_erro"] is None:
                        ep["primeiro_erro"] = t
            if rota == "processo" and self._caindo is None:
                self.queda_processo.append(t)

    def defeito_escrito(self, t, item, projeto, funcao, impl, pressa):
        self.defeitos_escritos.append({"t": t, "item": item, "projeto": projeto, "funcao": funcao, "implementacao": impl,
                                       "pressa_do_squad": round(pressa, 2)})

    def defeito_barrado(self, t, item, funcao, por):
        self.defeitos_barrados.append({"t": t, "item": item, "funcao": funcao, "por": por})

    # ---------- chamados ----------
    def chamado_aberto(self, t, item, cliente, motivo, comp, causa):
        """Um chamado chegou. (v1.4) Ele guarda de onde veio (a rota e o instante do erro ou da lentidão que o cliente sentiu) e a causa:
        defeito, incidente, queda do processo, rota com erro, rota lenta, ou outros (sem rota: dúvida, fatura, cobrança, nota)."""
        funcao = causa[0] if causa else None
        quando = causa[1] if causa else None
        rota = causa[2] if causa and len(causa) > 2 else None
        evento = "erro" if motivo == "erro" else "lentidão"
        reg = {"t": t, "item": item, "componente": comp, "motivo": motivo,
               "origem": {"rota": rota, "processo": rota_proc(rota), "instante": quando, "evento": evento} if rota else None,
               "causa": None, "registro_da_causa": None, "janela_de_rota": None, "escalado_em": None}
        candidatos = list(self.no_ar.items()) + [((e["funcao"], e["implementacao"]), e) for e in self.episodios
                                                 if e["saiu_do_ar"] is not None and quando is not None
                                                 and e["liberado_em"] <= quando <= e["saiu_do_ar"]]
        achou = None
        if funcao is not None:
            achou = next((ep for (f, v), ep in candidatos if f == funcao), None)
        elif rota is not None and motivo == "lentidão":
            achou = next((ep for (f, v), ep in candidatos if ep["como_aparece"] == "lento" and f in ROTAS_FUNCOES.get(rota, ())), None)
        if achou is not None:
            achou["chamados"] += 1
            if achou["primeiro_chamado"] is None:
                achou["primeiro_chamado"] = t
            reg["causa"], reg["registro_da_causa"] = "defeito", {"episodio_de_defeito": achou["funcao"], "liberado_em": achou["liberado_em"]}
            self._causa_chamado(item, achou)
        elif motivo in ("erro", "lentidão") and quando is not None:
            for lista, nome in ((self.incidentes, "incidente"), (self.quedas, "queda do processo")):
                inc = next((i for i in reversed(lista) if i["inicio"] - ANTES_DA_SONDA <= quando <= (i["fim"] or t)), None)
                if inc is not None:
                    inc["chamados"] += 1
                    if inc["primeiro_chamado"] is None:
                        inc["primeiro_chamado"] = t
                    if rota is not None:
                        por = inc.setdefault("chamados_por_rota_de_origem", {})
                        por[rota] = por.get(rota, 0) + 1
                    reg["causa"], reg["registro_da_causa"] = nome, {nome: inc["inicio"]}
                    self._causa_chamado(item, inc)
                    break
        if reg["causa"] is None:
            reg["causa"] = ("rota com erro" if evento == "erro" else "rota lenta") if rota is not None else "outros"
        self.chamados_por_causa[reg["causa"]] += 1
        if rota is not None:
            j = achar_janela(self.janelas_de_rota, rota, evento, quando)
            if j is not None:
                j["chamados_gerados"] += 1
                if len(j["chamados"]) < 100:
                    j["chamados"].append(item)
                reg["janela_de_rota"] = j["inicio"]
        self._chamados[item] = reg
        self.chamados.append(reg)

    def sentido(self, t, rota, tipo, falhou=None):
        """(v1.4) Um cliente sentiu erro (desistiu depois de tentar de novo) ou lentidão (mais de 4 segundos) numa rota."""
        inc = self.incidente_aberto
        if inc is not None:
            contexto = "incidente" if inc["causa"] == "volume do banco cheio" else "queda do processo"
        elif tipo == "erro" and falhou is not None and any(f == falhou for f, _ in self.no_ar):
            contexto = "defeito"
        elif tipo == "lentidão" and any(ep["como_aparece"] == "lento" and f in ROTAS_FUNCOES.get(rota, ()) for (f, _), ep in self.no_ar.items()):
            contexto = "defeito"
        else:
            contexto = "erro sem defeito" if tipo == "erro" else "rota lenta"
        self.janelas.evento(t, rota, tipo, contexto, self.janelas_de_rota.append)

    def _causa_chamado(self, item, ep):
        self._causas = getattr(self, "_causas", {})
        self._causas[item] = ep

    def escalado(self, t, chamado, destino):
        ep = getattr(self, "_causas", {}).get(chamado)
        if ep is not None:
            ep["escalacoes"] = ep.get("escalacoes", 0) + 1
            if ep.get("primeira_escalacao") is None:
                ep["primeira_escalacao"] = t
        reg = self._chamados.get(chamado)
        if reg is not None and reg["escalado_em"] is None:
            reg["escalado_em"] = t
            if reg["origem"] is not None and reg["janela_de_rota"] is not None:
                j = achar_janela(self.janelas_de_rota, reg["origem"]["rota"], reg["origem"]["evento"], reg["origem"]["instante"])
                if j is not None:
                    j["chamados_escalados"] += 1

    # ---------- o produto parado ----------
    def minuto_da_sonda(self, t, falhando, produto):
        self.janelas.fechar_velhas(t)                 # (v1.4) as janelas de rota sem evento há mais de uma hora se fecham
        if falhando and self.incidente_aberto is None:
            livre = produto.volume_paginas - produto.paginas_ocupadas()
            self.incidente_aberto = {"inicio": t, "fim": None, "causa": "volume do banco cheio" if livre < 200 else "processo parado",
                                     "primeiro_chamado": None, "chamados": 0, "primeira_escalacao": None, "escalacoes": 0,
                                     "folga_dada_em_dias": None, "registros_apagados": None}
            if self.incidente_aberto["causa"] == "volume do banco cheio":
                self.incidentes.append(self.incidente_aberto)
            else:
                self.quedas.append(self.incidente_aberto)        # a queda curta do processo por falta de memória (um defeito no ar)
        elif not falhando and self.incidente_aberto is not None:
            self.incidente_aberto["fim"] = t
            self.incidente_aberto["duracao_min"] = t - self.incidente_aberto["inicio"]
            self.incidente_aberto = None

    def incidente_resolvido(self, t, causa, folga, apagados):
        inc = self.incidente_aberto or (self.incidentes[-1] if self.incidentes else None)
        if inc is not None:
            inc["causa_diagnosticada"] = causa
            inc["folga_dada_em_dias"] = folga
            inc["registros_apagados"] = apagados

    # ---------- o calendário ----------
    def nova_data(self, t, cal):
        if cal.dia_mes == cal.dias_no_mes and not self.nulo == "embaralhado":
            self.fins_de_mes.append(t)

    def dia_vivido(self, t, carteira):
        self.carteira.append((t, carteira))

    def latencia(self, t, cal, rotas):
        if cal.util and 9 * 60 <= cal.minuto < 18 * 60:
            for r, v in rotas.items():
                if v[0] > 0:
                    acc = self._lat[r]
                    acc[0] += v[3]
                    acc[1] += 1
        if cal.minuto == MINUTOS_DIA - 1:
            for r in ROTAS:
                acc = self._lat[r]
                if acc[1]:
                    self.latencia_dia[r].append((t // MINUTOS_DIA, round(acc[0] / acc[1], 1)))
                self._lat[r] = [0.0, 0]

    # ---------- sprints, pessoal, carteira, atos ----------
    def sprint_planejado(self, t, projeto, numero, meta, capacidade, razao, cal):
        self.sprints.append({"projeto": projeto, "numero": numero, "inicio": t, "meta_pontos": meta, "capacidade_pontos": capacidade,
                             "meta_sobre_capacidade": round(razao, 2), "pressa": razao > 1.15, "fim": None, "pontos_feitos": None})

    def sprint_fechado(self, t, projeto, numero, total, feitos):
        for s in self.sprints:
            if s["projeto"] == projeto and s["numero"] == numero:
                s["fim"] = t
                s["pontos_feitos"] = feitos
        self.fins_de_sprint.append({"t": t, "projeto": projeto, "numero": numero})

    def pessoal_evento(self, t, tipo, equipe):
        self.pessoal.append({"t": t, "tipo": tipo, "equipe": equipe})

    def carteira_evento(self, t, tipo, cliente, plano):
        self.carteira_eventos.append((t, tipo, plano))

    def ato(self, t, numero, equipe, tipo):
        self.atos[numero] = {"recebido": t, "equipe": equipe, "tipo": tipo, "respondido": None}

    def ato_respondido(self, t, numero):
        if numero in self.atos:
            self.atos[numero]["respondido"] = t

    # ---------- o que a bancada lê ----------
    def como_dict(self, relogio, embaralhado):
        defeitos_no_ar = [e for e in self.episodios]
        eventos_cart = self.carteira
        semanas = []
        for i in range(7, len(eventos_cart), 7):
            a, b = eventos_cart[i - 7][1], eventos_cart[i][1]
            if a:
                semanas.append(round(100.0 * (b - a) / a, 2))
        regimes = []
        for r in self.regimes:
            d = r["t"] // MINUTOS_DIA
            antes, depois = [], []
            for rota in r["rotas"]:
                serie = self.latencia_dia.get(rota, [])
                a = [v for dd, v in serie if d - 7 <= dd < d]
                b = [v for dd, v in serie if d < dd <= d + 7]
                antes.append(round(sum(a) / len(a), 1) if a else None)
                depois.append(round(sum(b) / len(b), 1) if b else None)
            regimes.append(dict(r, latencia_media_7_dias_antes=antes, latencia_media_7_dias_depois=depois))
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
            "fins_de_sprint": self.fins_de_sprint,
            "fins_de_mes": self.fins_de_mes,
        }
        if embaralhado:
            ciclos = {"ausentes": "nulo embaralhado: os processos vivem num calendário sorteado em blocos; nenhum ciclo de hora, de "
                                   "dia da semana, de sprint ou de mês corresponde ao relógio da porta",
                      "blocos_do_calendario": relogio.blocos}
        saida = {
            "semente": self.semente,
            "nulo": self.nulo,
            "minutos": relogio.t,
            "convencao_do_tempo": "t = 0 é a criação (segunda-feira, 0h); cada passo avança t e faz acontecer o minuto t",
            "ciclos": ciclos,
            "liberacoes": self.liberacoes,
            "liberacoes_com_defeito": [l for l in self.liberacoes if l["defeitos_que_entraram"]],
            "episodios_de_defeito_no_ar": defeitos_no_ar,
            "incidentes": self.incidentes,
            "mudancas_de_regime": regimes,
            "deriva": {"carteira_por_dia": self.carteira, "crescimento_por_semana_em_porcento": semanas,
                       "entradas_e_saidas": self.carteira_eventos},
            "sprints": self.sprints,
            "sprints_de_pressa": [s for s in self.sprints if s["pressa"]],
            "defeitos_escritos": self.defeitos_escritos,
            "defeitos_barrados_antes_do_ar": self.defeitos_barrados,
            "quedas_do_processo_por_memoria": {"erros_no_registro": self.queda_processo, "sonda_parada": self.quedas},
            "pessoal": self.pessoal or [],
            "chamados_por_causa": self.chamados_por_causa,
            "chamados": self.chamados,
            "causas": {
                "categorias": {
                    "causa declarada": "há um mecanismo do mundo que leva de um campo ao outro: as leis abaixo (erro ou lentidão numa rota "
                                       "levam a chamados do componente da rota) e o 'onde' dos episódios de defeito",
                    "causa comum (incidente)": "durante um incidente (e até seis horas depois do fim, enquanto os chamados chegam e são "
                                               "escalados), os campos de 'campos_quando_o_produto_para' se mexem juntos porque o produto "
                                               "parou, sem que um cause o outro; o par da lei (rota para o componente dela) continua "
                                               "sendo causa declarada",
                    "causa comum (queda do processo)": "o mesmo, na queda curta do processo por falta de memória",
                    "sem relação": "nenhuma das anteriores",
                },
                "ordem": [c for c in CATEGORIAS if c != "causa comum (calendário)"],
                "leis": leis(),
                "janelas_de_rota": self.janelas_de_rota,
                "campos_quando_o_produto_para": campos_produto_parado(),
                "como_classificar": "classificar_par(verdade, [processo, campo], [processo, campo], inicio, fim) em causas.py",
            },
            "atos": self.atos,
        }
        if self.nulo == "sem_defeito":
            saida["observacao_do_nulo"] = ("nenhuma liberação levou defeito ao ar; os episódios de erros seguidos de chamados nesse nulo "
                                           "são só os incidentes listados em 'incidentes'")
        if self.nulo == "sem_deriva":
            saida["observacao_do_nulo"] = ("a carteira não cresce: cada cliente que entra leva à saída do cliente mais insatisfeito em até "
                                           "dois dias; a versão nova continua mudando a latência (está em 'mudancas_de_regime')")
        if self.nulo == "surdo":
            saida["observacao_do_nulo"] = "a porta aceita atos e devolve números, mas nada acontece e nada é respondido"
        return saida


def _rotas_funcoes():
    import inspect
    out = {}
    for rota, f in codigo.ROTAS_CODIGO.items():
        fonte = inspect.getsource(f)
        out[rota] = {fn for fn in codigo.IMPLEMENTACOES if f'cod["{fn}"]' in fonte}
    out["fila"] = {"emitir_nota", "enviar_email"}
    return out


ROTAS_FUNCOES = _rotas_funcoes()
