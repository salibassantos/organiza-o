"""Escola 2: causa e efeito (contrato das famílias, 22/10/2026).

De dois a oito processos, cada um com um campo (contagem ou nível). Cada processo dispara sozinho de tempos em tempos (o campo sobe de
uma vez e volta em minutos). As ligações, sorteadas pela semente, levam o disparo de um processo a outro com um atraso típico sorteado
(de minutos a horas, com uma folga de 20% para mais ou para menos), em pares e em cadeias (A move B, B move C); quando um processo move
dois, os dois efeitos têm uma causa comum. Uma ligação liga e desliga no meio da vida: existe de t1 (entre o 2º e o 5º dia) a t2 (entre o 9º e o 14º) e some.

A verdade diz cada ligação (de, para, atraso típico, quando nasce e quando morre), as causas comuns e cada disparo (instante, lugar e
causa: sozinho, ou a ligação que o trouxe e o disparo de origem).

Nulos: "embaralhado" (os mesmos disparos de origem e o mesmo número de disparos de efeito, mas estes em instantes sorteados: sem
ligação), "sem_ligacao" (os disparos de efeito não acontecem)."""
import math

from .base import MundoBase, Processo, Campo, sorteio, MINUTOS_DIA, LUGARES, COISAS, TIPOS_DE_CAMPO

FAMILIA = "escola2"
NULOS = ("embaralhado", "sem_ligacao")


class Mundo(MundoBase):
    FAMILIA = FAMILIA
    NULOS = NULOS
    DIAS_PADRAO = 21

    def __init__(self, semente, nulo=None, relogio=None, dias=60):
        super().__init__(semente, nulo, relogio)
        s = sorteio(self.semente, FAMILIA, "estrutura")
        n = s.randint(2, 8)
        coisas, lugares = s.sample(COISAS, n), s.sample(LUGARES, n)
        self.proc = []
        for k in range(n):
            tipo = s.choice(("contagem", "nível"))
            self.proc.append({"nome": f"{coisas[k]} {lugares[k]}", "campo": Campo(s, tipo, s.choice(TIPOS_DE_CAMPO[tipo])),
                              "disparos_por_dia": round(s.uniform(0.5, 3.0), 2), "amplitude_desvios": round(s.uniform(5, 10), 2),
                              "volta_min": s.randint(5, 20)})
        # as ligações: uma ordem sorteada; cada processo depois do primeiro é movido por um anterior (pares e cadeias)
        ordem = list(range(n))
        s.shuffle(ordem)
        fim = dias * MINUTOS_DIA
        self.lig = []
        for i in range(1, n):
            if s.random() < 0.75:
                de = ordem[s.randrange(0, i)]
                self.lig.append({"de": de, "para": ordem[i], "atraso": s.randint(5, 240), "ganho": round(s.uniform(0.7, 1.0), 2),
                                 "nasce": 0, "morre": None})
        if not self.lig:
            self.lig.append({"de": ordem[0], "para": ordem[1], "atraso": s.randint(5, 240), "ganho": 0.9, "nasce": 0, "morre": None})
        alvo = s.choice(self.lig)
        alvo["nasce"] = int(s.uniform(2.0, 5.0) * MINUTOS_DIA)            # nasce entre o 2º e o 5º dia e morre entre o 9º e o 14º
        alvo["morre"] = int(s.uniform(9.0, 14.0) * MINUTOS_DIA)
        alvo["intermitente"] = True
        # os disparos: os espontâneos (uma sorte por processo) e os de efeito, em ordem de tempo
        disparos = []
        for k, p in enumerate(self.proc):
            sk = sorteio(self.semente, FAMILIA, "espontâneos", k)
            t = int(sk.expovariate(p["disparos_por_dia"] / MINUTOS_DIA))
            while t < fim:
                disparos.append({"t": t, "k": k, "causa": "sozinho", "ligacao": None, "origem": None})
                t += max(30, int(sk.expovariate(p["disparos_por_dia"] / MINUTOS_DIA)))
        se = sorteio(self.semente, FAMILIA, "efeitos")
        fila = sorted(disparos, key=lambda d: (d["t"], d["k"]))
        efeitos = []
        i = 0
        while i < len(fila):
            d = fila[i]
            i += 1
            for L in self.lig:
                if L["de"] == d["k"] and L["nasce"] <= d["t"] and (L["morre"] is None or d["t"] < L["morre"]) and se.random() < L["ganho"]:
                    quando = d["t"] + max(1, int(round(L["atraso"] * se.uniform(0.8, 1.2))))
                    if quando < fim:
                        e = {"t": quando, "k": L["para"], "causa": "ligação", "ligacao": self.lig.index(L), "origem": [d["t"], d["k"]]}
                        efeitos.append(e)
                        j = i
                        while j < len(fila) and (fila[j]["t"], fila[j]["k"]) <= (quando, e["k"]):
                            j += 1
                        fila.insert(j, e)
        if self.nulo == "sem_ligacao":
            fila = [d for d in fila if d["causa"] == "sozinho"]
        elif self.nulo == "embaralhado":
            sh = sorteio(self.semente, FAMILIA, "embaralhado")
            for e in efeitos:
                e["t"] = sh.randrange(1, fim)
                e["causa"], e["origem"] = "nulo embaralhado: um disparo de efeito em instante sorteado", None
            fila = sorted(fila, key=lambda d: (d["t"], d["k"]))
        self.disparos = fila
        self._prox = 0
        self.ativos = [[] for _ in range(n)]          # (início, amplitude) dos disparos que ainda pesam
        self.s_ruido = sorteio(self.semente, FAMILIA, "ruído")
        for p in self.proc:
            self._processos.append(Processo(p["nome"], [p["campo"].nome], "", [p["campo"].resolucao]))

    def _minuto(self, t):
        while self._prox < len(self.disparos) and self.disparos[self._prox]["t"] <= t:
            d = self.disparos[self._prox]
            self._prox += 1
            p = self.proc[d["k"]]
            self.ativos[d["k"]].append((t, p["amplitude_desvios"] * p["campo"].desvio()))
        saida = {}
        for k, p in enumerate(self.proc):
            tau = p["volta_min"]
            extra = 0.0
            fica = []
            for t0, a in self.ativos[k]:
                x = a * math.exp(-(t - t0) / tau)
                if x > 0.05:
                    extra += x
                    fica.append((t0, a))
            self.ativos[k] = fica
            saida[p["nome"]] = [p["campo"].valor(self.s_ruido, p["campo"].base + extra)]
        return saida

    def verdade(self):
        nome = lambda k: [self.proc[k]["nome"], self.proc[k]["campo"].nome]
        lig = [{"de": nome(L["de"]), "para": nome(L["para"]), "atraso_tipico_min": L["atraso"], "folga": "de 0,8 a 1,2 vezes o atraso",
                "chance_de_passar": L["ganho"], "nasce": L["nasce"], "morre": L["morre"], "intermitente": bool(L.get("intermitente"))}
               for L in self.lig]
        comuns = []
        for k in range(len(self.proc)):
            filhos = [L["para"] for L in self.lig if L["de"] == k]
            for a in range(len(filhos)):
                for b in range(a + 1, len(filhos)):
                    comuns.append({"origem": nome(k), "efeitos": [nome(filhos[a]), nome(filhos[b])],
                                   "categoria": "causa comum (os dois são movidos pelo mesmo processo, um não move o outro)"})
        return {"familia": FAMILIA, "semente": self.semente, "nulo": self.nulo, "minutos": self.t,
                "estrutura": {"processos": [{"nome": p["nome"], "campo": p["campo"].nome, **p["campo"].lei(), "disparos_por_dia": p["disparos_por_dia"],
                                             "amplitude_desvios": p["amplitude_desvios"], "volta_min": p["volta_min"]} for p in self.proc]},
                "ligacoes": lig if self.nulo is None else [dict(x, aviso=f"nulo {self.nulo}: a ligação não age") for x in lig],
                "causas_comuns": comuns,
                "disparos": [{"t": d["t"], "onde": [nome(d["k"])], "causa": d["causa"], "ligacao": d["ligacao"],
                              "origem": {"t": d["origem"][0], "onde": [nome(d["origem"][1])]} if d["origem"] else None}
                             for d in self.disparos if d["t"] <= self.t],
                "leis": [], "observacao_do_nulo": {None: None, "embaralhado": "os mesmos disparos de origem; os de efeito em instantes sorteados",
                                                   "sem_ligacao": "os disparos de efeito não acontecem"}[self.nulo]}
