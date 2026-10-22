"""Escola 4: o tempo (contrato das famílias, 22/10/2026).

De um a quatro processos, cada um com um ou dois campos. Cada campo é a soma de um nível, de um ou dois ciclos e do ruído do seu tipo.
Os períodos são sorteados de uma escala larga (de 60 minutos a 13 dias), nunca perto de um dia ou de uma semana, com fases e amplitudes
sorteadas (de 3 a 8 desvios do próprio campo). Um dos ciclos muda de período no meio da vida (de 0,6 a 1,6 vez o período), mantendo a
fase contínua no instante da mudança.

A verdade diz, campo a campo, os períodos, as fases (o minuto do primeiro pico), as amplitudes e o instante e o tamanho da mudança: é o
gabarito do calendário como sentido.

Nulos: "embaralhado" (as mesmas amplitudes e o mesmo ruído, mas a fase de cada ciclo pula para um valor sorteado a cada bloco de um
décimo a um terço do período: sem período), "periodo_fixo" (o ciclo que mudaria não muda)."""
import math

from .base import MundoBase, Processo, Campo, sorteio, MINUTOS_DIA, LUGARES, COISAS, TIPOS_DE_CAMPO

FAMILIA = "escola4"
NULOS = ("embaralhado", "periodo_fixo")
PROIBIDOS = (MINUTOS_DIA, 7 * MINUTOS_DIA)


def _periodo(s):
    while True:
        p = int(round(math.exp(s.uniform(math.log(60), math.log(13 * MINUTOS_DIA)))))
        if all(abs(p - x) > 0.12 * x for x in PROIBIDOS) and all(abs(p - x / 2) > 0.06 * x for x in PROIBIDOS[:1]):
            return p


class Mundo(MundoBase):
    FAMILIA = FAMILIA
    NULOS = NULOS
    DIAS_PADRAO = 45

    def __init__(self, semente, nulo=None, relogio=None, dias=60):
        super().__init__(semente, nulo, relogio)
        s = sorteio(self.semente, FAMILIA, "estrutura")
        n = s.randint(1, 4)
        coisas, lugares = s.sample(COISAS, n), s.sample(LUGARES, n)
        self.proc, self.ciclos = [], []
        for k in range(n):
            campos = []
            for j in range(s.randint(1, 2)):
                tipo = s.choice(("contagem", "nível", "latência", "taxa"))
                nomes = [x for x in TIPOS_DE_CAMPO[tipo] if x not in [c.nome for c in campos]]
                c = Campo(s, tipo, s.choice(nomes))
                if tipo == "contagem":
                    c.base = max(c.base, 15.0)                     # para caber o ciclo sem bater no zero
                campos.append(c)
                for _ in range(s.randint(1, 2)):
                    P = _periodo(s)
                    self.ciclos.append({"k": k, "j": j, "periodo": P, "fase": s.randrange(P), "desvios": round(s.uniform(3, 8), 2),
                                        "amplitude": None, "muda_em": None, "periodo_depois": None})
            self.proc.append({"nome": f"{coisas[k]} {lugares[k]}", "campos": campos})
        for c in self.ciclos:
            campo = self.proc[c["k"]]["campos"][c["j"]]
            c["amplitude"] = round(c["desvios"] * campo.desvio(), 4)
        # a mudança de período, com a sua própria sorte
        sm = sorteio(self.semente, FAMILIA, "mudança")
        alvo = sm.choice(self.ciclos)
        alvo["muda_em"] = int(sm.uniform(0.4, 0.6) * self.DIAS_PADRAO * MINUTOS_DIA)
        alvo["periodo_depois"] = max(60, int(round(alvo["periodo"] * sm.uniform(0.6, 1.6))))
        if self.nulo == "periodo_fixo":
            alvo["muda_em"], alvo["periodo_depois"] = None, None
        # o nulo embaralhado: a fase de cada ciclo pula a cada bloco
        self.s_emb = sorteio(self.semente, FAMILIA, "embaralhado")
        for c in self.ciclos:
            c["_bloco_ate"], c["_desloc"] = 0, 0.0
        self.s_ruido = sorteio(self.semente, FAMILIA, "ruído")
        for p in self.proc:
            self._processos.append(Processo(p["nome"], [c.nome for c in p["campos"]], "", [c.resolucao for c in p["campos"]]))

    def _angulo(self, c, t):
        """O ângulo do ciclo no minuto t (fase contínua na mudança de período)."""
        P = c["periodo"]
        if c["muda_em"] is not None and t >= c["muda_em"]:
            a0 = 2 * math.pi * (c["muda_em"] - c["fase"]) / P
            return a0 + 2 * math.pi * (t - c["muda_em"]) / c["periodo_depois"]
        return 2 * math.pi * (t - c["fase"]) / P

    def _minuto(self, t):
        niveis = {(k, j): c.base for k, p in enumerate(self.proc) for j, c in enumerate(p["campos"])}
        for c in self.ciclos:
            ang = self._angulo(c, t)
            if self.nulo == "embaralhado":
                if t >= c["_bloco_ate"]:
                    P = c["periodo"]
                    c["_bloco_ate"] = t + max(5, int(self.s_emb.uniform(P / 10.0, P / 3.0)))
                    c["_desloc"] = self.s_emb.uniform(0, 2 * math.pi)
                ang += c["_desloc"]
            niveis[(c["k"], c["j"])] += c["amplitude"] * math.cos(ang)
        return {p["nome"]: [c.valor(self.s_ruido, niveis[(k, j)]) for j, c in enumerate(p["campos"])] for k, p in enumerate(self.proc)}

    def verdade(self):
        cic = []
        for c in self.ciclos:
            campo = self.proc[c["k"]]["campos"][c["j"]]
            cic.append({"onde": [[self.proc[c["k"]]["nome"], campo.nome]], "periodo_min": c["periodo"], "fase_primeiro_pico": c["fase"],
                        "amplitude": c["amplitude"], "amplitude_em_desvios": c["desvios"],
                        "muda_em": c["muda_em"], "periodo_depois_min": c["periodo_depois"]})
        return {"familia": FAMILIA, "semente": self.semente, "nulo": self.nulo, "minutos": self.t,
                "estrutura": {"processos": [{"nome": p["nome"], "campos": {c.nome: c.lei() for c in p["campos"]}} for p in self.proc]},
                "ciclos": cic, "mudancas_de_periodo": [x for x in cic if x["muda_em"] is not None and x["muda_em"] <= self.t],
                "leis": [{"nome": "o ciclo", "como": "nível + amplitude x cos(2 pi (t - fase) / período); depois da mudança, o período novo com a fase contínua"}],
                "observacao_do_nulo": {None: None, "embaralhado": "as mesmas amplitudes, a fase pulando a cada bloco de um décimo a um terço do período: sem período",
                                       "periodo_fixo": "o ciclo que mudaria de período não muda"}[self.nulo]}
