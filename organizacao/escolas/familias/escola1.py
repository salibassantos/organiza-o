"""Escola 1: um campo (contrato das famílias, 22/10/2026).

De um a três processos de tipos diferentes (contagem, latência, nível, carteira), cada um com um a quatro campos. Três leis com
instante, cada uma com a sua sorte (um nulo tira só a sua):
- o incidente: um campo sai do lugar de repente (sobe ou cai de 4 a 12 desvios) e volta depois de meia hora a cinco horas;
  um acontecimento para baixo que levaria o campo abaixo de 40% da base, ou a menos de três desvios do zero, vai para cima;
- a mudança de regime: um campo muda de patamar de uma vez, para sempre (de 3 a 8 desvios);
- a deriva: um campo cresce (ou míngua) devagar, a uma taxa por semana (de 3% a 12%).
O resto é o ruído de cada tipo de campo. A verdade diz cada acontecimento com instante, lugar, sentido, tamanho em desvios do próprio
campo (o desvio do ruído no nível daquele instante) e a lei sorteada.

Nulos: "sem_incidente", "sem_regime", "sem_deriva"."""
import math

from .base import MundoBase, Processo, Campo, sorteio, MINUTOS_DIA, LUGARES, COISAS, TIPOS_DE_CAMPO

FAMILIA = "escola1"
NULOS = ("sem_incidente", "sem_regime", "sem_deriva")
TIPOS = ("contagem", "latência", "nível", "carteira")


class Mundo(MundoBase):
    FAMILIA = FAMILIA
    NULOS = NULOS
    DIAS_PADRAO = 21

    def __init__(self, semente, nulo=None, relogio=None, dias=60):
        super().__init__(semente, nulo, relogio)
        s = sorteio(self.semente, FAMILIA, "estrutura")
        n = s.randint(1, 3)
        tipos = s.sample(TIPOS, n)
        coisas, lugares = s.sample(COISAS, n), s.sample(LUGARES, n)
        self.proc = []
        for k in range(n):
            ncampos = s.randint(1, 4)
            campos, usados = [], set()
            for j in range(ncampos):
                tipo = tipos[k] if j == 0 else s.choice(TIPOS + ("taxa",))
                nomes = [x for x in TIPOS_DE_CAMPO[tipo] if x not in usados]
                if not nomes:
                    continue
                nome = s.choice(nomes)
                usados.add(nome)
                campos.append(Campo(s, tipo, nome))
            self.proc.append({"nome": f"{coisas[k]} {lugares[k]}", "campos": campos})
        self.lugares = [(k, j) for k, p in enumerate(self.proc) for j in range(len(p["campos"]))]
        fim = dias * MINUTOS_DIA
        # o incidente
        si = sorteio(self.semente, FAMILIA, "incidentes")
        self.incidentes = []
        t = int(si.uniform(1.0, 3.0) * MINUTOS_DIA)
        while t < fim:
            k, j = si.choice(self.lugares)
            self.incidentes.append({"inicio": t, "duracao": si.randint(30, 300), "k": k, "j": j, "sentido": si.choice((1, -1)),
                                    "desvios": round(si.uniform(4, 12), 2)})
            t += int(si.uniform(2.0, 6.0) * MINUTOS_DIA)
        # a mudança de regime
        sr = sorteio(self.semente, FAMILIA, "regimes")
        self.regimes = []
        for _ in range(sr.randint(1, 2)):
            k, j = sr.choice(self.lugares)
            self.regimes.append({"t": sr.randrange(2 * MINUTOS_DIA, max(3 * MINUTOS_DIA, fim // 2)), "k": k, "j": j,
                                 "sentido": sr.choice((1, -1)), "desvios": round(sr.uniform(3, 8), 2)})
        self.regimes.sort(key=lambda x: x["t"])
        # a deriva
        sd = sorteio(self.semente, FAMILIA, "deriva")
        k, j = sd.choice(self.lugares)
        self.deriva = {"k": k, "j": j, "inicio": sd.randrange(0, 3 * MINUTOS_DIA), "taxa_por_semana": round(sd.choice((1, -1)) * sd.uniform(0.03, 0.12), 4)}
        if self.nulo == "sem_incidente":
            self.incidentes = []
        if self.nulo == "sem_regime":
            self.regimes = []
        if self.nulo == "sem_deriva":
            self.deriva = None
        self.patamar = {(k, j): c.base for k, p in enumerate(self.proc) for j, c in enumerate(p["campos"])}
        self.s_ruido = sorteio(self.semente, FAMILIA, "ruído")
        self.reg = {"incidentes": [], "regimes": []}
        self._ativo = {}
        self._pi = self._pr = 0
        for p in self.proc:
            self._processos.append(Processo(p["nome"], [c.nome for c in p["campos"]], "", [c.resolucao for c in p["campos"]]))

    def _nivel_sem_incidente(self, k, j, t):
        nivel = self.patamar[(k, j)]
        d = self.deriva
        if d is not None and d["k"] == k and d["j"] == j and t >= d["inicio"]:
            nivel *= math.exp(math.log1p(d["taxa_por_semana"]) * (t - d["inicio"]) / (7 * MINUTOS_DIA))
        return nivel

    def _minuto(self, t):
        while self._pr < len(self.regimes) and self.regimes[self._pr]["t"] <= t:
            r = self.regimes[self._pr]
            self._pr += 1
            c = self.proc[r["k"]]["campos"][r["j"]]
            antes = self._nivel_sem_incidente(r["k"], r["j"], t)
            delta = r["sentido"] * r["desvios"] * c.desvio(antes)
            if antes + delta < _piso(c, antes):
                delta = -delta                                       # para baixo o campo bateria no chão: o regime sobe
            self.patamar[(r["k"], r["j"])] = self.patamar[(r["k"], r["j"])] * (antes + delta) / antes
            self.reg["regimes"].append({"t": t, "onde": [[self.proc[r["k"]]["nome"], c.nome]], "sentido": "subiu" if delta > 0 else "desceu",
                                        "tamanho_em_desvios": round(abs(delta) / c.desvio(antes), 2), "patamar_antes": round(antes, 3),
                                        "patamar_depois": round(self._nivel_sem_incidente(r["k"], r["j"], t), 3), "lei": "um patamar novo para sempre"})
        while self._pi < len(self.incidentes) and self.incidentes[self._pi]["inicio"] <= t:
            i = self.incidentes[self._pi]
            self._pi += 1
            c = self.proc[i["k"]]["campos"][i["j"]]
            nivel = self._nivel_sem_incidente(i["k"], i["j"], t)
            delta = i["sentido"] * i["desvios"] * c.desvio(nivel)
            if nivel + delta < _piso(c, nivel):
                delta = -delta                                       # para baixo o campo bateria no chão: o incidente sobe
            self._ativo[(i["k"], i["j"])] = (t + i["duracao"], delta)
            self.reg["incidentes"].append({"inicio": t, "fim": t + i["duracao"], "duracao_min": i["duracao"], "onde": [[self.proc[i["k"]]["nome"], c.nome]],
                                           "sentido": "subiu" if delta > 0 else "caiu", "tamanho_em_desvios": round(abs(delta) / c.desvio(nivel), 2),
                                           "nivel_antes": round(nivel, 3), "lei": "sai do lugar de repente e volta"})
        saida = {}
        for k, p in enumerate(self.proc):
            vals = []
            for j, c in enumerate(p["campos"]):
                nivel = self._nivel_sem_incidente(k, j, t)
                a = self._ativo.get((k, j))
                if a is not None:
                    if t < a[0]:
                        nivel += a[1]
                    else:
                        del self._ativo[(k, j)]
                vals.append(c.valor(self.s_ruido, nivel))
            saida[p["nome"]] = vals
        return saida

    def verdade(self):
        d = self.deriva
        deriva = None
        if d is not None:
            c = self.proc[d["k"]]["campos"][d["j"]]
            deriva = {"onde": [[self.proc[d["k"]]["nome"], c.nome]], "inicio": d["inicio"], "taxa_por_semana": d["taxa_por_semana"],
                      "sentido": "subiu" if d["taxa_por_semana"] > 0 else "desceu", "lei": "o nível multiplicado por (1 + taxa) a cada semana"}
        return {"familia": FAMILIA, "semente": self.semente, "nulo": self.nulo, "minutos": self.t,
                "estrutura": {"processos": [{"nome": p["nome"], "campos": {c.nome: c.lei() for c in p["campos"]}} for p in self.proc],
                              "leis": {"incidente": {"intervalo_dias": [2.0, 6.0], "duracao_min": [30, 300], "desvios": [4, 12]},
                                       "regime": {"quantos": [1, 2], "desvios": [3, 8]}, "deriva": {"taxa_por_semana": [0.03, 0.12]}}},
                "incidentes": [dict(x) for x in self.reg["incidentes"]], "mudancas_de_regime": [dict(x) for x in self.reg["regimes"]],
                "deriva": deriva, "leis": [],
                "observacao_do_nulo": {None: None, "sem_incidente": "nenhum incidente; o regime e a deriva nos mesmos instantes",
                                       "sem_regime": "nenhuma mudança de regime; o resto igual", "sem_deriva": "nenhuma deriva; o resto igual"}[self.nulo]}


def _piso(c, nivel):
    """O menor nível a que um acontecimento pode levar o campo: 40% da base e três desvios acima do zero."""
    return max(0.4 * c.base, 3.0 * c.desvio(nivel))
