"""A família da voz, o berçário (22/10/2026, item 23 do plano vivo; contrato das famílias): de um a três processos e uma voz que
narra só o que acontece agora nos campos. Ensina o significado como ligação entre a palavra e a unidade que já dispara; a verdade das
referências fica só para a bancada.

Cada processo ("<coisa> <do lugar>") tem um campo "nível" com acontecimentos sorteados, de hora em hora a cada poucas horas: subir
(um patamar novo mais alto), descer (mais baixo), pico (sobe e volta em minutos), parar (vai a zero e fica) e voltar (sai do zero para
o patamar de antes). A voz fala só no instante em que algo acontece (de 0 a 2 minutos depois), com um vocabulário pequeno (de 12 a 20
palavras: o nome curto de cada processo, uma palavra para cada acontecimento, "agora", "de novo", "muito"), por exemplo "turbina subiu
agora" ou "a prensa parou". As linhas chegam pelo canal "canal da voz": a contagem por minuto como campo, o texto por `vozes()`.

A verdade diz, de cada linha, a que processo, campo, acontecimento e instante ela se refere, e o significado de cada palavra.

Nulos: "hora_sorteada" (as mesmas linhas, em instantes sorteados sem relação com os campos), "vocabulario_permutado" (as mesmas linhas
nos mesmos instantes, com as palavras de cada linha trocadas por palavras sorteadas do vocabulário: nenhuma palavra fica presa a um
sentido), "voz_surda" (a voz nunca fala)."""
from .base import MundoBase, Processo, sorteio, MINUTOS_DIA, LUGARES, COISAS

FAMILIA = "voz"
NULOS = ("hora_sorteada", "vocabulario_permutado", "voz_surda")
ACONTECIMENTOS = {"subir": "subiu", "descer": "desceu", "pico": "pulou", "parar": "parou", "voltar": "voltou"}


class Mundo(MundoBase):
    FAMILIA = FAMILIA
    NULOS = NULOS
    DIAS_PADRAO = 21

    def __init__(self, semente, nulo=None, relogio=None, dias=60):
        super().__init__(semente, nulo, relogio)
        s = sorteio(self.semente, FAMILIA, "estrutura")
        n = s.randint(1, 3)
        coisas, lugares = s.sample([c for c in COISAS if " " not in c], n), s.sample(LUGARES, n)
        self.proc = [{"nome": f"{coisas[k]} {lugares[k]}", "palavra": coisas[k], "patamar": round(s.uniform(20, 60), 1),
                      "ruido": round(s.uniform(0.5, 2.0), 2), "intervalo_horas": [round(s.uniform(0.7, 2.0), 1), round(s.uniform(3.0, 6.0), 1)]}
                     for k in range(n)]
        self.canal = "canal da voz"
        self.vocab = {p["palavra"]: {"refere": "processo", "processo": p["nome"]} for p in self.proc}
        for ev, w in ACONTECIMENTOS.items():
            self.vocab[w] = {"refere": "acontecimento", "acontecimento": ev}
        for w, sentido in (("agora", "o instante da fala"), ("de", "parte de 'de novo'"), ("novo", "o mesmo acontecimento outra vez no processo"),
                           ("muito", "o tamanho grande do acontecimento"), ("a", "artigo"), ("o", "artigo")):
            self.vocab[w] = {"refere": sentido}
        # os acontecimentos de cada processo, sorteados de antemão (as falas vêm deles)
        se = sorteio(self.semente, FAMILIA, "acontecimentos")
        self.acontecimentos = []
        for k, p in enumerate(self.proc):
            t, nivel, parado, ultimo = int(se.uniform(30, 300)), p["patamar"], False, None
            while t < dias * MINUTOS_DIA:
                if parado:
                    ev = "voltar"
                else:
                    ev = se.choice(["subir", "descer", "pico", "pico", "parar"])
                tam = round(se.uniform(8, 25), 1)
                self.acontecimentos.append({"t": t, "k": k, "processo": p["nome"], "campo": "nível", "acontecimento": ev, "tamanho": tam,
                                            "de_novo": ev == ultimo})
                parado = ev == "parar"
                ultimo = ev
                t += int(se.uniform(*p["intervalo_horas"]) * 60)
        self.acontecimentos.sort(key=lambda a: (a["t"], a["k"]))
        # as linhas da voz
        sv = sorteio(self.semente, FAMILIA, "voz")
        self.linhas = []
        if self.nulo != "voz_surda":
            palavras = list(self.vocab)
            for a in self.acontecimentos:
                p = self.proc[a["k"]]
                partes = ([artigo(p["palavra"])] if sv.random() < 0.4 else []) + [p["palavra"], ACONTECIMENTOS[a["acontecimento"]]]
                if a["tamanho"] > 20 and a["acontecimento"] in ("subir", "descer", "pico"):
                    partes.append("muito")
                if a["de_novo"]:
                    partes += ["de", "novo"]
                elif sv.random() < 0.5:
                    partes.append("agora")
                quando = a["t"] + sv.randint(0, 2)
                if self.nulo == "vocabulario_permutado":
                    partes = [sv.choice(palavras) for _ in partes]
                self.linhas.append({"t": quando, "texto": " ".join(partes), "refere": {"processo": a["processo"], "campo": a["campo"],
                                    "acontecimento": a["acontecimento"], "instante": a["t"]}})
            if self.nulo == "hora_sorteada":
                sh = sorteio(self.semente, FAMILIA, "hora sorteada")
                for x in self.linhas:
                    x["t"] = sh.randrange(1, dias * MINUTOS_DIA)
                    x["refere"] = dict(x["refere"], aviso="nulo hora_sorteada: a linha não fala do seu instante")
                self.linhas.sort(key=lambda x: x["t"])
        self.prox_ac, self.prox_linha = 0, 0
        self.nivel = [p["patamar"] for p in self.proc]
        self.base = [p["patamar"] for p in self.proc]
        self.pico_ate = [0] * n
        self.s_ruido = sorteio(self.semente, FAMILIA, "ruído")
        self._processos = [Processo(p["nome"], ["nível"], "", [0.1]) for p in self.proc] + [Processo(self.canal, ["linhas chegadas no minuto"], "", [1.0])]

    def _minuto(self, t):
        while self.prox_ac < len(self.acontecimentos) and self.acontecimentos[self.prox_ac]["t"] <= t:
            a = self.acontecimentos[self.prox_ac]
            self.prox_ac += 1
            k = a["k"]
            if a["acontecimento"] == "subir":
                self.base[k] += a["tamanho"]
            elif a["acontecimento"] == "descer":
                self.base[k] = max(1.0, self.base[k] - a["tamanho"])
            elif a["acontecimento"] == "pico":
                self.pico_ate[k] = t + 8
                self.nivel[k] = self.base[k] + 2 * a["tamanho"]
            elif a["acontecimento"] == "parar":
                self.guardado = getattr(self, "guardado", {})
                self.guardado[k] = self.base[k]
                self.base[k] = 0.0
            elif a["acontecimento"] == "voltar":
                self.base[k] = getattr(self, "guardado", {}).get(k, self.proc[k]["patamar"])
        n_linhas = 0
        while self.prox_linha < len(self.linhas) and self.linhas[self.prox_linha]["t"] <= t:
            x = self.linhas[self.prox_linha]
            self.prox_linha += 1
            self._vozes.append((t, self.canal, x["texto"]))
            n_linhas += 1
        saida = {}
        for k, p in enumerate(self.proc):
            if t < self.pico_ate[k]:
                self.nivel[k] += (self.base[k] - self.nivel[k]) * 0.3
            else:
                self.nivel[k] = self.base[k]
            ruido = self.s_ruido.gauss(0, p["ruido"]) if self.base[k] > 0 else 0.0
            saida[p["nome"]] = [float(round(max(0.0, self.nivel[k] + ruido), 1))]
        saida[self.canal] = [float(n_linhas)]
        return saida

    def verdade(self):
        return {"familia": FAMILIA, "semente": self.semente, "nulo": self.nulo, "minutos": self.t,
                "estrutura": {"processos": self.proc, "canal": self.canal, "vocabulario": self.vocab},
                "acontecimentos": [dict(a) for a in self.acontecimentos if a["t"] <= self.t],
                "linhas": [dict(x) for x in self.linhas if x["t"] <= self.t],
                "leis": [{"nome": "a voz fala do que acontece agora", "de": "um acontecimento num campo", "para": [self.canal, "linhas chegadas no minuto"],
                          "atraso": "de 0 a 2 minutos", "o_que_diz": "o nome curto do processo e a palavra do acontecimento (estrutura.vocabulario)"}],
                "observacao_do_nulo": {None: None, "hora_sorteada": "as mesmas linhas em instantes sorteados, sem relação com os campos",
                                       "vocabulario_permutado": "as mesmas linhas nos mesmos instantes, com as palavras sorteadas: nenhuma presa a um sentido",
                                       "voz_surda": "a voz nunca fala"}[self.nulo]}


MASCULINOS = {"forno", "guindaste", "tear", "tanque", "elevador"}


def artigo(palavra):
    return "o" if palavra in MASCULINOS else "a"
