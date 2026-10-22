"""Escola 3: gente que responde (reescrita em 22/10/2026, contrato das famílias e item 22 do plano vivo).

Um mundo pequeno com duas ou três equipes de gente e uma a três máquinas. As equipes são agentes com estado, como no mundo v2: fila de
atos, presença (expediente, almoço, sábado de algumas, faltas), cansaço, atenção e confiança em quem pede. O estado interior fica só
na verdade; pela porta saem os rastros físicos dele:

- "quadro de <equipe>": presentes agora; horas extras no dia (o dia tomado por pedidos faz a equipe ficar além da hora);
- "fluxo de <equipe>": itens abertos; itens criados no minuto (o trabalho regular que chega e o ato que vira item);
- "porta de <equipe>": textos chegados no minuto (respostas, avisos de tratado); itens abertos (os atos de quem pede ainda sem
  resposta). Só contagens: o campo não diz a que ato uma chegada responde. O texto chega por `respostas()`;
- "<máquina> do <lugar>": produção no minuto; falhas no minuto; fila. Um defeito recorrente faz uma máquina falhar muito, de tempos em
  tempos; só uma equipe sabe tratá-lo; sem ninguém pedir, a manutenção programada o tira horas ou dias depois.

As equipes têm rendimento sorteado: uma sabe tratar o defeito e resolve quase sempre; outra às vezes; outra nunca. Um ato é uma
pergunta ou um pedido a uma equipe; vira item no fluxo dela no passo seguinte e só fica disponível depois da demora dela (a base
esticada pela ocupação, pelo cansaço e pela atenção já gasta, encurtada pela confiança); alguém presente e livre o trata; a resposta
volta pela porta. O pedido certo, à equipe que sabe, com o defeito no ar, o tira (com a chance da equipe). Pedido útil sobe a
confiança; inútil a baixa. O dia em que a equipe tratou pedidos a faz ficar além da hora (as horas extras atribuídas aos atos ficam na
verdade). O que não for tratado até o fim do expediente do dia útil seguinte fica sem resposta.

Nulos: "surdo" (a porta aceita e nada chega ao mundo), "paciente" (as equipes sem atenção, cansaço nem confiança, e os pedidos não
lançam hora extra), "ninguem_resolve" (as equipes respondem, mas nenhum pedido tira o defeito)."""
import math

from .base import MundoBase, Processo, sorteio, MINUTOS_DIA, LUGARES, COISAS

FAMILIA = "escola3"
NULOS = ("surdo", "paciente", "ninguem_resolve")
RENDIMENTOS = {"resolve": (0.85, 0.95), "às vezes": (0.35, 0.6), "nunca": (0.0, 0.0)}
CONF_MIN, CONF_MAX = 0.4, 1.6


class Equipe:
    def __init__(self, nome, s, rendimento, sabe):
        self.nome = nome
        self.membros = s.randint(2, 6)
        self.chega = s.randint(7 * 60, 10 * 60)
        self.jornada = s.randint(8 * 60, 9 * 60)
        self.sabado = s.random() < 0.3
        self.rendimento = rendimento
        lo, hi = RENDIMENTOS[rendimento]
        self.chance = round(s.uniform(lo, hi), 3)
        self.sabe = sabe
        self.demora_resposta = round(s.uniform(15, 90), 1)
        self.demora_tratamento = round(s.uniform(25, 150), 1)
        self.trabalho_regular = round(s.uniform(0.004, 0.012), 4)     # itens regulares por minuto de expediente
        self.cansaco, self.atencao, self.confianca, self.ocupacao = 0.0, 0.0, 1.0, 0.0
        self.fila = []                                                  # atos esperando, em ordem (pedidos antes de perguntas)
        self.ocupados = []                                              # [fim, ato ou None] de cada pessoa trabalhando
        self.regulares = 0                                              # itens regulares abertos
        self.presentes = 0
        self.extra_hoje = 0.0                                           # horas extras do dia
        self.porta_hoje = 0                                             # minutos gastos hoje em pedidos de quem observa
        self.atos_hoje = []
        self.ficar_ate = None

    def lei(self):
        return {"pessoas": self.membros, "expediente": [self.chega, self.chega + self.jornada], "almoco": [12 * 60, 13 * 60 + 30],
                "trabalha_sabado_de_manha": self.sabado, "rendimento": self.rendimento, "chance_de_resolver": self.chance,
                "sabe_tratar_o_defeito": self.sabe, "demora_base_resposta_min": self.demora_resposta,
                "demora_base_tratamento_min": self.demora_tratamento, "itens_regulares_por_minuto_de_expediente": self.trabalho_regular}

    def estado(self):
        return {"fila": len(self.fila), "cansaco": round(self.cansaco, 4), "atencao": round(self.atencao, 4),
                "confianca": round(self.confianca, 4), "ocupacao": round(self.ocupacao, 4)}


class Mundo(MundoBase):
    FAMILIA = FAMILIA
    NULOS = NULOS
    DIAS_PADRAO = 21

    def __init__(self, semente, nulo=None, relogio=None):
        super().__init__(semente, nulo, relogio)
        s = sorteio(self.semente, FAMILIA, "estrutura")
        lugares = s.sample(LUGARES, 6)
        n_eq = s.randint(2, 3)
        rend = ["resolve", s.choice(["às vezes", "nunca"])] + (["nunca" if s.random() < 0.5 else "às vezes"] if n_eq == 3 else [])
        s.shuffle(rend)
        sabe = rend.index("resolve")
        self.eq = [Equipe(f"equipe {lugares[i]}", s, rend[i], i == sabe) for i in range(n_eq)]
        n_maq = s.randint(1, 3)
        coisas = s.sample(COISAS, n_maq)
        self.maq = [{"nome": f"{coisas[k]} {lugares[3 + k]}", "producao": round(s.uniform(2.0, 12.0), 2),
                     "falha_base": round(s.uniform(0.002, 0.02), 4)} for k in range(n_maq)]
        self.defeito_em = s.randrange(n_maq)
        self.lei_defeito = {"maquina": self.maq[self.defeito_em]["nome"], "intervalo_dias": [2.0, 6.0],
                            "falhas_a_mais_por_minuto": round(s.uniform(1.5, 4.0), 2), "manutencao_depois_de_horas": [10, 60]}
        self.s_def = sorteio(self.semente, FAMILIA, "defeito")
        self.s_maq = sorteio(self.semente, FAMILIA, "máquinas")
        self.s_eq = sorteio(self.semente, FAMILIA, "equipes")
        self.s_porta = sorteio(self.semente, FAMILIA, "porta")
        self.proximo_defeito = int(self.s_def.uniform(1.0, 4.0) * MINUTOS_DIA)
        self.defeito = None                          # o episódio no ar
        self.filas_maq = [0.0] * n_maq
        self.chegando, self.atos = [], {}
        self.reg = {"episodios": [], "atos": [], "interior_por_hora": []}
        for e in self.eq:
            self._processos += [Processo(f"quadro da {e.nome}", ["presentes agora", "horas extras no dia"], e.nome, [1.0, 0.01]),
                                Processo(f"fluxo da {e.nome}", ["itens abertos", "itens criados no minuto"], e.nome, [1.0, 1.0]),
                                Processo(f"porta da {e.nome}", ["textos chegados no minuto", "itens abertos"], e.nome, [1.0, 1.0])]
        dono = self.eq[sabe].nome
        for m in self.maq:
            self._processos.append(Processo(m["nome"], ["produção no minuto", "falhas no minuto", "fila"], dono, [1.0, 1.0, 1.0]))

    def equipes(self):
        return [e.nome for e in self.eq]

    # ---------- o calendário das pessoas ----------
    def _no_turno(self, e, t):
        d, m = divmod(t, MINUTOS_DIA)
        dow = d % 7
        if dow < 5:
            fim = e.chega + e.jornada
        elif dow == 5 and e.sabado:
            fim = 12 * 60
        else:
            return False
        if 12 * 60 <= m < 13 * 60 + 30 and dow < 5:
            return False
        return e.chega <= m < fim or (e.ficar_ate is not None and m < e.ficar_ate)

    def _util_seguinte_fim(self, t, e):
        d = t // MINUTOS_DIA + 1
        while d % 7 >= 5:
            d += 1
        return d * MINUTOS_DIA + e.chega + e.jornada

    # ---------- a porta ----------
    def _receber(self, numero, equipe, tipo, texto):
        if self.nulo == "surdo":
            return
        self.chegando.append((numero, equipe, tipo, texto))

    def _materializar(self, t):
        for numero, equipe, tipo, texto in self.chegando:
            e = next((x for x in self.eq if x.nome == equipe), None)
            if e is None or tipo not in ("pergunta", "pedido"):
                self.reg["atos"].append({"numero": numero, "equipe": equipe, "tipo": tipo, "texto": texto, "recebido": t,
                                         "desfecho": "não entregue (equipe ou tipo desconhecido)"})
                continue
            base = e.demora_tratamento if tipo == "pedido" else e.demora_resposta
            demora = base * (1 + 1.5 * e.ocupacao) * (1 + 0.8 * e.cansaco) * (1 + 0.6 * e.atencao) / e.confianca
            a = {"numero": numero, "equipe": equipe, "tipo": tipo, "texto": texto, "recebido": t, "demora_min": round(demora, 1),
                 "disponivel_em": t + int(round(demora)), "prazo": self._util_seguinte_fim(t, e), "pego_em": None, "tratado_em": None,
                 "desfecho": None, "efeito": None, "equipe_ao_receber": e.estado(), "equipe_ao_tratar": None,
                 "confianca_antes": None, "confianca_depois": None, "horas_extras_atribuidas": [], "resposta": None}
            self.atos[numero] = a
            self.reg["atos"].append(a)
            if tipo == "pedido":
                k = 0
                while k < len(e.fila) and self.atos[e.fila[k]]["tipo"] == "pedido":
                    k += 1
                e.fila.insert(k, numero)
            else:
                e.fila.append(numero)
            self._criados[e.nome] += 1
        self.chegando = []

    def _tratar(self, e, a, t):
        a["tratado_em"] = t
        a["desfecho"] = "respondido"
        abertos = len(e.fila) + e.regulares
        if a["tipo"] == "pergunta":
            texto = f"Na {e.nome} há {abertos} itens abertos e {e.presentes} pessoas presentes."
            efeito = {"util": None, "encurta": [], "colateral": []}
        else:
            d = self.defeito
            ninguem = self.nulo == "ninguem_resolve"
            if d is not None and e.sabe and not ninguem and self.s_porta.random() < e.chance:
                self._fim_do_defeito(t + self.s_porta.randint(5, 20), "ato", a["numero"])
                texto = f"Pedido tratado. A {e.nome} encontrou a falha na máquina {self.maq[self.defeito_em]['nome']} e está consertando."
                util = True
            elif d is not None and e.chance > 0 and not ninguem:
                texto = f"Pedido tratado. A {e.nome} olhou a máquina {self.maq[self.defeito_em]['nome']} e não conseguiu consertar."
                util = False
            else:
                texto = "Pedido tratado. Não encontramos nada para fazer."
                util = False
            onde = [[self.maq[self.defeito_em]["nome"], "falhas no minuto"]] if util else []
            efeito = {"util": util, "encurta": onde, "colateral": [[f"quadro da {e.nome}", "horas extras no dia"], [f"fluxo da {e.nome}", "itens abertos"]]}
            if self.nulo != "paciente":
                a["confianca_antes"] = round(e.confianca, 4)
                e.confianca = min(CONF_MAX, e.confianca + 0.15) if util else max(CONF_MIN, e.confianca - 0.2)
                a["confianca_depois"] = round(e.confianca, 4)
        if self.nulo != "paciente":
            e.atencao += 0.25 if a["tipo"] == "pergunta" else 0.5
        a["efeito"] = efeito
        a["resposta"] = texto
        a["equipe_ao_tratar"] = e.estado()
        self.saida.append((t, a["numero"], e.nome, texto))
        self._chegados[e.nome] += 1

    # ---------- o defeito recorrente ----------
    def _inicio_do_defeito(self, t):
        s = self.s_def
        manut = t + int(s.uniform(*self.lei_defeito["manutencao_depois_de_horas"]) * 60)
        maq = self.maq[self.defeito_em]["nome"]
        self.defeito = {"inicio": t, "fim": None, "maquina": maq, "onde": [[maq, "falhas no minuto"], [maq, "fila"]],
                        "manutencao_programada_em": manut, "saiu_por": None, "saiu_pelo_ato": None,
                        "reverteria_sozinha_em": manut, "antecipou_min": None,
                        "causa": "o defeito recorrente da máquina; só a equipe que sabe tratá-lo o tira, ou a manutenção programada"}
        self.reg["episodios"].append(self.defeito)
        self.eventos.append((t, f"a máquina {maq} começou a falhar"))
        self.proximo_defeito = manut + int(s.uniform(*self.lei_defeito["intervalo_dias"]) * MINUTOS_DIA)

    def _fim_do_defeito(self, t, como, ato=None):
        d = self.defeito
        if d is None or d["fim"] is not None:
            return
        d["fim_previsto"] = t
        d["saiu_por"] = como
        d["saiu_pelo_ato"] = ato

    # ---------- um minuto ----------
    def _minuto(self, t):
        m = t % MINUTOS_DIA
        self._criados = {e.nome: 0 for e in self.eq}
        self._chegados = {e.nome: 0 for e in self.eq}
        if m == 0:
            for e in self.eq:
                e.extra_hoje, e.porta_hoje, e.atos_hoje, e.ficar_ate = 0.0, 0, [], None
        if self.chegando:
            self._materializar(t)
        # o defeito: começa, sai pela manutenção ou pelo ato
        d = self.defeito
        if d is None and t >= self.proximo_defeito:
            self._inicio_do_defeito(t)
        d = self.defeito
        if d is not None:
            if d.get("fim_previsto") is not None and t >= d["fim_previsto"]:
                d["fim"] = t
            elif t >= d["manutencao_programada_em"]:
                d["fim"], d["saiu_por"] = t, "manutenção"
            if d["fim"] is not None:
                d["antecipou_min"] = d["reverteria_sozinha_em"] - d["fim"]
                self.eventos.append((t, f"a máquina {d['maquina']} voltou ao normal"))
                self.defeito = None
        # as máquinas
        saida = {}
        sm = self.s_maq
        for k, mq in enumerate(self.maq):
            ciclo = 0.75 + 0.25 * math.cos(2 * math.pi * (m - 14 * 60) / MINUTOS_DIA)
            prod = _poisson(sm, mq["producao"] * ciclo)
            fal = _poisson(sm, mq["falha_base"] * mq["producao"] + (self.lei_defeito["falhas_a_mais_por_minuto"] if self.defeito is not None and k == self.defeito_em else 0.0))
            self.filas_maq[k] = max(0.0, self.filas_maq[k] * 0.97 + fal - 0.3)
            saida[mq["nome"]] = [float(prod), float(fal), float(round(self.filas_maq[k]))]
        # as equipes
        se = self.s_eq
        dow = (t // MINUTOS_DIA) % 7
        for e in self.eq:
            no_turno = self._no_turno(e, t)
            if m == 0:
                e._faltas = sum(1 for _ in range(e.membros) if se.random() < 0.03)
            presentes = max(0, e.membros - getattr(e, "_faltas", 0)) if no_turno else 0
            if presentes == 0:
                for x in e.ocupados:                                    # o trabalho em curso só anda com gente presente
                    x[0] += 1
            e.ocupados = [x for x in e.ocupados if x[0] > t or self._concluir(e, x, t)]
            e.presentes = presentes
            if no_turno and dow < 6 and se.random() < e.trabalho_regular * presentes:
                e.regulares += 1
                self._criados[e.nome] += 1
            livres = presentes - len(e.ocupados)
            while livres > 0:
                a = next((self.atos[n] for n in e.fila if self.atos[n]["disponivel_em"] <= t), None)
                if a is not None:
                    e.fila.remove(a["numero"])
                    a["pego_em"] = t
                    dur = (self.s_porta.randint(20, 60) if a["tipo"] == "pedido" else self.s_porta.randint(5, 15))
                    if self.nulo != "paciente":
                        dur = dur * (1 + 0.5 * e.cansaco)
                    e.ocupados.append([t + max(1, int(round(dur))), a["numero"]])
                elif e.regulares > 0 and se.random() < 0.05:
                    e.regulares -= 1
                    e.ocupados.append([t + se.randint(30, 120), None])
                else:
                    break
                livres -= 1
            # quem ficou além da hora por causa dos pedidos do dia
            fim_turno = e.chega + e.jornada
            if dow < 5 and m == fim_turno and e.porta_hoje > 0 and self.nulo != "paciente":
                extra = int(e.porta_hoje * self.s_porta.uniform(0.4, 0.9))
                if extra > 0:
                    e.ficar_ate = fim_turno + extra
                    presentes = e.presentes = max(0, e.membros - getattr(e, "_faltas", 0))     # quem estava no turno fica
                    h = round(extra * presentes / 60.0, 2)
                    e.extra_hoje += h
                    for n in e.atos_hoje:
                        self.atos[n]["horas_extras_atribuidas"].append({"t": t, "horas": round(h / len(e.atos_hoje), 3),
                                                                       "onde": [f"quadro da {e.nome}", "horas extras no dia"]})
            # o estado interior
            if self.nulo != "paciente":
                if e.ficar_ate is not None and m >= fim_turno:
                    e.cansaco = min(3.0, e.cansaco + 0.002 * presentes / max(1, e.membros))
                e.cansaco *= 0.99995 if presentes else 0.9985
                e.atencao *= 0.995
            e.ocupacao = min(2.0, (len(e.ocupados) / presentes if presentes else 1.0) + len(e.fila) / (4.0 * e.membros))
            abertos_porta = sum(1 for n in e.fila) + sum(1 for x in e.ocupados if x[1] is not None)
            saida[f"quadro da {e.nome}"] = [float(presentes), float(round(e.extra_hoje, 2))]
            saida[f"fluxo da {e.nome}"] = [float(e.regulares + abertos_porta), float(self._criados[e.nome])]
            saida[f"porta da {e.nome}"] = [float(self._chegados[e.nome]), float(abertos_porta)]
        # o que não foi tratado até o prazo fica sem resposta
        for e in self.eq:
            for n in [n for n in e.fila if self.atos[n]["prazo"] <= t]:
                e.fila.remove(n)
                self.atos[n]["desfecho"] = "sem resposta"
                self.atos[n]["expirou_em"] = t
        if m == 59 or m % 60 == 59:
            self.reg["interior_por_hora"].append({"t": t, **{e.nome: e.estado() for e in self.eq}})
        # a saída na ordem dos processos
        return {p.nome: saida[p.nome] for p in self._processos}

    def _concluir(self, e, x, t):
        if x[1] is not None:
            a = self.atos[x[1]]
            if a["tipo"] == "pedido":
                e.porta_hoje += t - a["pego_em"]
                e.atos_hoje.append(a["numero"])
            self._tratar(e, a, t)
        return False

    # ---------- a verdade ----------
    def verdade(self):
        atos = [dict(a) for a in self.reg["atos"]]
        quartis = {}
        for e in self.eq:
            xs = sorted(a["tratado_em"] - a["recebido"] for a in atos if a.get("equipe") == e.nome and a.get("tratado_em") is not None)
            quartis[e.nome] = [_q(xs, 0.25), _q(xs, 0.5), _q(xs, 0.75)] if xs else None
        leis = []
        for e in self.eq:
            leis.append({"nome": f"o ato a {e.nome} volta como texto", "de": "ato a " + e.nome, "para": [f"porta da {e.nome}", "textos chegados no minuto"],
                         "atraso": "a demora da equipe mais o trabalho (os quartis de tratado menos recebido estão em quartis_da_resposta)"})
            leis.append({"nome": f"o ato a {e.nome} vira item", "de": "ato a " + e.nome,
                         "para": [[f"fluxo da {e.nome}", "itens criados no minuto"], [f"porta da {e.nome}", "itens abertos"]],
                         "atraso": "no passo seguinte ao receber; o item aberto fica até a resposta ou o prazo"})
            if self.nulo != "paciente":
                leis.append({"nome": f"o pedido a {e.nome} custa hora extra", "de": "pedido a " + e.nome, "para": [f"quadro da {e.nome}", "horas extras no dia"],
                             "atraso": "no fim do expediente do dia em que foi tratado (as horas atribuídas estão em cada ato)"})
            leis.append({"nome": f"a presença de {e.nome} decide quando ela responde", "de": [f"quadro da {e.nome}", "presentes agora"],
                         "para": [f"porta da {e.nome}", "textos chegados no minuto"], "atraso": "só com gente presente e livre"})
        sabe = next(e.nome for e in self.eq if e.sabe)
        leis.append({"nome": "o pedido certo tira o defeito", "de": "pedido a " + sabe, "para": [self.lei_defeito["maquina"], "falhas no minuto"],
                     "atraso": "de 5 a 20 minutos depois do tratamento, com a chance da equipe", "so_com_o_defeito_no_ar": True})
        return {"familia": FAMILIA, "semente": self.semente, "nulo": self.nulo, "minutos": self.t,
                "estrutura": {"equipes": {e.nome: e.lei() for e in self.eq}, "maquinas": self.maq, "defeito": self.lei_defeito},
                "leis": leis, "episodios_de_defeito": [dict(d) for d in self.reg["episodios"]], "atos": atos,
                "quartis_da_resposta": quartis, "interior_por_hora": self.reg["interior_por_hora"],
                "ciclos": {"dia": "expediente de cada equipe (estrutura.equipes.*.expediente), almoço das 12h às 13h30, produção das máquinas "
                                  "com pico às 14h", "semana": "dias úteis; algumas equipes no sábado de manhã"},
                "observacao_do_nulo": {None: None, "surdo": "nenhum ato chega ao mundo; nada volta pela porta",
                                       "paciente": "as equipes sem atenção, cansaço nem confiança; os pedidos não lançam hora extra",
                                       "ninguem_resolve": "as equipes respondem, mas nenhum pedido tira o defeito"}[self.nulo]}


def _poisson(s, lam):
    if lam <= 0:
        return 0
    L, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= s.random()
        if p < L:
            return k
        k += 1


def _q(xs, p):
    return xs[min(len(xs) - 1, int(p * len(xs)))] if xs else None
