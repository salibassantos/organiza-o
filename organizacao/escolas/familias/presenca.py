"""A escola da presença (22/10/2026, item 22 do plano vivo; contrato das famílias): uma voz que vem e vai num canal, sem significado
ainda, antes da língua. Ensina o costume dela (quando ela costuma estar) e a contingência (o que ele escreve muda quando ela fala).

O mundo tem dois processos e um canal:
- "canal <do canto>": linhas chegadas no minuto (a contagem; o texto chega por `vozes()` como (t, canal, texto));
- "luz <do canto>": nível de 0 a 100, que segue o dia (claro de dia, escuro à noite), sem nenhuma ligação com a voz.

A voz tem um costume sorteado pela semente: em que dias da semana ela costuma vir, a que horas chega, quanto fica, quantas linhas por
minuto quando está, e semanas em que some (viagem). Quando está, as linhas chegam em rajadas; quando não está, nada chega. As linhas são
palavras de um vocabulário pequeno, sorteadas sem relação com nada que ele vê: a voz ainda não significa. Quem observa escreve pelo
mesmo canal (`receber(<canal>, "linha", texto)`); se ela está, responde com uma chance e um atraso sorteados (a contingência); se não
está, a linha fica sem resposta.

Nulos: "sorteado" (as mesmas sessões, do mesmo tamanho, em instantes sorteados: sem costume), "surdo" (o que ele escreve não chega a
ela: sem contingência), "calada" (a voz nunca vem)."""
import math

from .base import MundoBase, Processo, sorteio, MINUTOS_DIA, CANTOS

FAMILIA = "presenca"
NULOS = ("sorteado", "surdo", "calada")
PALAVRAS = ("manhã", "chuva", "café", "ponte", "verde", "pedra", "longe", "janela", "barco", "tarde", "sal", "vento", "linha",
            "folha", "copo", "rua", "areia", "noite", "fio", "casa", "lago", "mapa", "pão", "sino", "trem", "nuvem", "porta", "lua",
            "fumo", "cedo")


class Mundo(MundoBase):
    FAMILIA = FAMILIA
    NULOS = NULOS
    DIAS_PADRAO = 28

    def __init__(self, semente, nulo=None, relogio=None):
        super().__init__(semente, nulo, relogio)
        s = sorteio(self.semente, FAMILIA, "estrutura")
        canto, canto_luz = s.sample(CANTOS, 2)
        self.canal = f"canal {canto}"
        self.luz = f"luz {canto_luz}"
        dias = sorted(s.sample(range(7), s.randint(3, 6)))
        self.costume = {"dias_da_semana": dias, "chega_em_min": s.randint(7 * 60, 20 * 60), "variacao_da_chegada_min": s.randint(10, 60),
                        "fica_min": [s.randint(30, 90), s.randint(120, 300)], "linhas_por_minuto_presente": round(s.uniform(0.04, 0.2), 3),
                        "chance_de_faltar_num_dia_dela": round(s.uniform(0.05, 0.25), 3), "semanas_fora": sorted(s.sample(range(2, 12), 1))}
        self.contingencia = {"chance_de_responder": round(s.uniform(0.6, 0.95), 3), "atraso_min": [1, s.randint(3, 15)]}
        self.vocab = s.sample(PALAVRAS, s.randint(12, 20))
        self.s_costume = sorteio(self.semente, FAMILIA, "costume")
        self.s_linhas = sorteio(self.semente, FAMILIA, "linhas")
        self.s_resposta = sorteio(self.semente, FAMILIA, "resposta")
        self.s_luz = sorteio(self.semente, FAMILIA, "luz")
        self.s_sorteado = sorteio(self.semente, FAMILIA, "sorteado")
        self.sessao = None                       # (início, fim) da presença em curso ou marcada para hoje
        self.reg = {"presencas": [], "linhas": [], "linhas_dele": []}
        self.respostas_marcadas = []             # (t, número da linha dele)
        self._linhas_no_minuto = 0
        self._processos = [Processo(self.canal, ["linhas chegadas no minuto"], "", [1.0]),
                           Processo(self.luz, ["nível"], "", [1.0])]

    def equipes(self):
        return [self.canal]

    # ---------- o costume ----------
    def _marcar_dia(self, t):
        d = t // MINUTOS_DIA
        c, s = self.costume, self.s_costume
        semana_fora = (d // 7) in c["semanas_fora"]
        vem = (d % 7) in c["dias_da_semana"] and not semana_fora and s.random() >= c["chance_de_faltar_num_dia_dela"]
        dur = s.randint(*c["fica_min"])
        ini = d * MINUTOS_DIA + c["chega_em_min"] + s.randint(-c["variacao_da_chegada_min"], c["variacao_da_chegada_min"])
        if self.nulo == "sorteado":
            ini = d * MINUTOS_DIA + self.s_sorteado.randrange(0, MINUTOS_DIA - dur)
        dur = min(dur, (d + 1) * MINUTOS_DIA - 1 - ini)          # a sessão acaba no mesmo dia
        if self.nulo == "calada" or not vem:
            self.sessao = None
            return
        self.sessao = (ini, ini + dur)
        self.reg["presencas"].append({"inicio": ini, "fim": ini + dur, "onde": [[self.canal, "linhas chegadas no minuto"]],
                                      "causa": "o costume dela" if self.nulo != "sorteado" else "nulo sorteado: a sessão em instante sorteado"})

    def presente(self, t):
        return self.sessao is not None and self.sessao[0] <= t < self.sessao[1]

    def _linha(self, t, causa):
        s = self.s_linhas
        texto = " ".join(s.choice(self.vocab) for _ in range(s.randint(2, 7)))
        self._vozes.append((t, self.canal, texto))
        self._linhas_no_minuto += 1
        self.reg["linhas"].append({"t": t, "texto": texto, "causa": causa})

    # ---------- a porta: ele escreve no canal ----------
    def _receber(self, numero, equipe, tipo, texto):
        reg = {"numero": numero, "t": self.t + 1, "canal": equipe, "texto": texto, "ela_presente": None, "respondida_em": None}
        self.reg["linhas_dele"].append(reg)
        if self.nulo == "surdo" or equipe != self.canal:
            reg["chegou"] = False
            return
        reg["chegou"] = True
        self._por_ver = getattr(self, "_por_ver", []) + [reg]

    # ---------- um minuto ----------
    def _minuto(self, t):
        self._linhas_no_minuto = 0
        if t % MINUTOS_DIA == 1:
            self._marcar_dia(t)
        presente = self.presente(t)
        for reg in getattr(self, "_por_ver", []):
            reg["ela_presente"] = presente
            if presente and self.s_resposta.random() < self.contingencia["chance_de_responder"]:
                self.respostas_marcadas.append((t + self.s_resposta.randint(*self.contingencia["atraso_min"]), reg))
        self._por_ver = []
        if presente and self.s_linhas.random() < self.costume["linhas_por_minuto_presente"] * _rajada(t, self.sessao):
            self._linha(t, "o costume dela")
        for par in [p for p in self.respostas_marcadas if p[0] <= t]:
            self.respostas_marcadas.remove(par)
            if self.presente(t):
                self._linha(t, f"resposta à linha {par[1]['numero']} dele")
                par[1]["respondida_em"] = t
        m = t % MINUTOS_DIA
        luz = 50 + 45 * math.sin(2 * math.pi * (m - 6 * 60) / MINUTOS_DIA) + self.s_luz.gauss(0, 3)
        return {self.canal: [float(self._linhas_no_minuto)], self.luz: [float(round(max(0.0, min(100.0, luz))))]}

    # ---------- a verdade ----------
    def verdade(self):
        return {"familia": FAMILIA, "semente": self.semente, "nulo": self.nulo, "minutos": self.t,
                "estrutura": {"canal": self.canal, "luz": self.luz, "costume": self.costume, "contingencia": self.contingencia,
                              "vocabulario": list(self.vocab)},
                "leis": [{"nome": "o costume dela", "de": "o calendário", "para": [self.canal, "linhas chegadas no minuto"],
                          "como": "ela vem nos dias e na hora do costume e fala em rajadas enquanto está (estrutura.costume)"},
                         {"nome": "a contingência", "de": "linha dele no canal", "para": [self.canal, "linhas chegadas no minuto"],
                          "como": "se ela está, responde com a chance e o atraso de estrutura.contingencia; se não está, nada"},
                         {"nome": "a luz segue o dia", "de": "o calendário", "para": [self.luz, "nível"], "como": "sem ligação com a voz"}],
                "presencas": [dict(p) for p in self.reg["presencas"] if p["inicio"] <= self.t],
                "linhas": list(self.reg["linhas"]), "linhas_dele": [dict(x) for x in self.reg["linhas_dele"]],
                "observacao_do_nulo": {None: None, "sorteado": "as sessões dela em instantes sorteados: o mesmo tamanho, sem costume",
                                       "surdo": "o que ele escreve não chega a ela", "calada": "a voz nunca vem"}[self.nulo]}


def _rajada(t, sessao):
    """Dentro da sessão as linhas vêm em rajadas: mais no começo e em ondas de uns 20 minutos."""
    i = t - sessao[0]
    return 1.0 + 0.8 * math.exp(-i / 15.0) + 0.6 * math.sin(2 * math.pi * i / 20.0)
