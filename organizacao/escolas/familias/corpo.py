"""A escola do corpo (22/10/2026, item 22 do plano vivo; contrato das famílias): um mundo pequeno com rajadas e calmarias, em que uns
campos voltam sozinhos e outros só voltam com ato. O efeito de cada ato está na verdade, com o ramo sem ato (como na v2.2 do mundo):
o instante em que o campo voltaria sem ele.

De dois a quatro processos, cada um com um campo "nível" (o estado, com ruído) e um campo "avisos no minuto" (uma contagem que sobe
quando o nível sai do lugar). A semente sorteia, para cada processo, a lei da volta:
- "volta sozinho": um desvio decai com uma constante de tempo sorteada (de 20 minutos a 6 horas); volta ao lugar sem ninguém fazer
  nada, e um ato não muda a volta;
- "só volta com ato": o desvio fica até alguém pedir à mão daquele processo (`receber("mão <do processo>", "pedido", ...)`), que o
  desfaz depois de um atraso sorteado; sem ato, não volta.
Os desvios chegam em rajadas: de tempos em tempos (de dois a cinco dias) uma rajada de 3 a 12 horas traz um desvio a cada meia hora
a uma hora, em processos sorteados; entre as rajadas, a calmaria (quase nada). A mão responde ao pedido com um texto curto ("Feito.",
ou "Não havia nada para desfazer.").

Nulos: "surda" (a porta aceita e nada chega: os campos que só voltam com ato ficam fora do lugar), "calma" (os mesmos desvios, do
mesmo tamanho e da mesma lei, espalhados no tempo de maneira uniforme: sem rajada). A eferência embaralhada é nulo da bancada."""
import math

from .base import MundoBase, Processo, sorteio, MINUTOS_DIA, LUGARES, COISAS

FAMILIA = "corpo"
NULOS = ("surda", "calma")


class Mundo(MundoBase):
    FAMILIA = FAMILIA
    NULOS = NULOS
    DIAS_PADRAO = 21

    def __init__(self, semente, nulo=None, relogio=None, dias=60):
        super().__init__(semente, nulo, relogio)
        s = sorteio(self.semente, FAMILIA, "estrutura")
        n = s.randint(2, 4)
        coisas, lugares = s.sample(COISAS, n), s.sample(LUGARES, n)
        leis = ["volta sozinho", "só volta com ato"] + [s.choice(["volta sozinho", "só volta com ato"]) for _ in range(n - 2)]
        s.shuffle(leis)
        self.proc = []
        for k in range(n):
            p = {"nome": f"{coisas[k]} {lugares[k]}", "mao": f"mão {coisas[k]} {lugares[k]}", "lei": leis[k],
                 "lugar": round(s.uniform(20, 80), 1), "ruido": round(s.uniform(0.5, 2.5), 2),
                 "desvio": [round(s.uniform(10, 20), 1), round(s.uniform(25, 45), 1)]}
            if leis[k] == "volta sozinho":
                p["constante_de_tempo_min"] = s.randint(20, 360)
            else:
                p["atraso_do_ato_min"] = [s.randint(3, 10), s.randint(15, 60)]
            self.proc.append(p)
        self.lei_rajadas = {"intervalo_dias": [2.0, 5.0], "duracao_horas": [3, 12], "um_desvio_a_cada_min": [30, 60]}
        # o calendário dos desvios, sorteado inteiro de antemão (o nulo calma espalha os mesmos desvios)
        sr = sorteio(self.semente, FAMILIA, "rajadas")
        self.rajadas, desvios = [], []
        t = int(sr.uniform(0.5, 2.0) * MINUTOS_DIA)
        while t < dias * MINUTOS_DIA:
            dur = sr.randint(3 * 60, 12 * 60)
            self.rajadas.append({"inicio": t, "fim": t + dur})
            u = t + sr.randint(5, 30)
            while u < t + dur:
                k = sr.randrange(n)
                sinal = sr.choice((1, -1))
                desvios.append([u, k, sinal * round(sr.uniform(*self.proc[k]["desvio"]), 1)])
                u += sr.randint(*self.lei_rajadas["um_desvio_a_cada_min"])
            t += dur + int(sr.uniform(*self.lei_rajadas["intervalo_dias"]) * MINUTOS_DIA)
        if self.nulo == "calma":
            sc = sorteio(self.semente, FAMILIA, "calma")
            fim = dias * MINUTOS_DIA
            for d in desvios:
                d[0] = sc.randrange(60, fim)
            desvios.sort()
            self.rajadas = []
        self.desvios = desvios
        self.prox = 0
        self.desvio_agora = [0.0] * n                # o desvio em curso de cada processo
        self.episodio = [None] * n
        self.s_ruido = sorteio(self.semente, FAMILIA, "ruído")
        self.s_porta = sorteio(self.semente, FAMILIA, "porta")
        self.chegando, self.pendentes = [], []       # atos a materializar; (instante do efeito, k, ato)
        self.reg = {"episodios": [], "atos": []}
        for p in self.proc:
            self._processos.append(Processo(p["nome"], ["nível", "avisos no minuto"], p["mao"], [0.1, 1.0]))

    def equipes(self):
        return [p["mao"] for p in self.proc]

    # ---------- a porta ----------
    def _receber(self, numero, equipe, tipo, texto):
        if self.nulo == "surda":
            return
        self.chegando.append((numero, equipe, tipo, texto))

    def _ato(self, t, numero, equipe, tipo, texto):
        k = next((i for i, p in enumerate(self.proc) if p["mao"] == equipe), None)
        a = {"numero": numero, "equipe": equipe, "tipo": tipo, "texto": texto, "recebido": t, "processo": None, "efeito": None, "resposta": None}
        self.reg["atos"].append(a)
        if k is None:
            a["efeito"] = {"util": False, "por_que": "não há essa mão"}
            return
        p = self.proc[k]
        a["processo"] = p["nome"]
        ep = self.episodio[k]
        if tipo != "pedido" or ep is None or p["lei"] == "volta sozinho":
            if ep is not None:
                ep["atos_que_o_tocaram"].append(numero)
            por_que = ("não é pedido" if tipo != "pedido" else "o campo estava no lugar" if ep is None
                       else "este campo volta sozinho; o ato não muda a volta")
            a["efeito"] = {"util": False, "por_que": por_que, "encurta": [], "reverteria_sozinha_em": ep["reverteria_sozinha_em"] if ep else None,
                           "antecipou_min": 0 if ep else None}
            self._responder(t, a, "Não havia nada para desfazer." if ep is None or p["lei"] == "volta sozinho" else "Recebido.")
            return
        quando = t + self.s_porta.randint(*p["atraso_do_ato_min"])
        ep["atos_que_o_tocaram"].append(numero)
        self.pendentes.append((quando, k, a))
        a["efeito"] = {"util": True, "por_que": "o campo só volta com ato; a mão o desfaz", "encurta": [[p["nome"], "nível"], [p["nome"], "avisos no minuto"]],
                       "efetivo_em": quando, "reverteria_sozinha_em": None, "antecipou_min": None}
        self._responder(t, a, "Feito.")

    def _responder(self, t, a, texto):
        quando = t + self.s_porta.randint(1, 5)
        a["resposta"], a["respondido_em"] = texto, quando
        self.saida.append((quando, a["numero"], a["equipe"], texto))

    # ---------- um minuto ----------
    def _minuto(self, t):
        for x in self.chegando:
            self._ato(t, *x)
        self.chegando = []
        while self.prox < len(self.desvios) and self.desvios[self.prox][0] <= t:
            _, k, tam = self.desvios[self.prox]
            self.prox += 1
            p = self.proc[k]
            self.desvio_agora[k] += tam
            if self.episodio[k] is None:
                volta = _volta(t, self.desvio_agora[k], p["constante_de_tempo_min"]) if p["lei"] == "volta sozinho" else None
                self.episodio[k] = {"inicio": t, "processo": p["nome"], "lei": p["lei"], "onde": [[p["nome"], "nível"], [p["nome"], "avisos no minuto"]],
                                    "tamanho": tam, "na_rajada": any(r["inicio"] <= t < r["fim"] for r in self.rajadas),
                                    "fim": None, "saiu_por": None, "saiu_pelo_ato": None, "reverteria_sozinha_em": volta, "antecipou_min": None,
                                    "atos_que_o_tocaram": []}
                self.reg["episodios"].append(self.episodio[k])
            else:
                self.episodio[k]["tamanho"] = round(self.episodio[k]["tamanho"] + tam, 1)
                if p["lei"] == "volta sozinho":
                    self.episodio[k]["reverteria_sozinha_em"] = _volta(t, self.desvio_agora[k], p["constante_de_tempo_min"])
        for item in [x for x in self.pendentes if x[0] <= t]:
            self.pendentes.remove(item)
            _, k, a = item
            ep = self.episodio[k]
            if ep is not None and abs(self.desvio_agora[k]) > 0:
                self.desvio_agora[k] = 0.0
                self._fim(k, t, "ato", a["numero"])
        saida = {}
        sr = self.s_ruido
        for k, p in enumerate(self.proc):
            if p["lei"] == "volta sozinho" and self.desvio_agora[k]:
                self.desvio_agora[k] *= math.exp(-1.0 / p["constante_de_tempo_min"])
                if abs(self.desvio_agora[k]) < 2.0:
                    self.desvio_agora[k] = 0.0
                    self._fim(k, t, "sozinho", None)
            nivel = p["lugar"] + self.desvio_agora[k] + sr.gauss(0, p["ruido"])
            lam = 0.02 + 0.08 * abs(self.desvio_agora[k]) / 10.0
            avisos = 1 if sr.random() < min(0.95, lam) else 0
            saida[p["nome"]] = [float(round(nivel, 1)), float(avisos)]
        return saida

    def _fim(self, k, t, como, ato):
        ep = self.episodio[k]
        if ep is None:
            return
        ep["fim"], ep["saiu_por"], ep["saiu_pelo_ato"] = t, como, ato
        if ep["reverteria_sozinha_em"] is not None:
            ep["antecipou_min"] = ep["reverteria_sozinha_em"] - t
        self.episodio[k] = None
        if ato is not None:
            for a in self.reg["atos"]:
                if a["numero"] == ato and a["efeito"]:
                    a["efeito"]["antecipou_min"] = None if ep["reverteria_sozinha_em"] is None else ep["reverteria_sozinha_em"] - t
                    a["efeito"]["sem_o_ato"] = "não voltaria" if ep["reverteria_sozinha_em"] is None else ep["reverteria_sozinha_em"]

    # ---------- a verdade ----------
    def verdade(self):
        return {"familia": FAMILIA, "semente": self.semente, "nulo": self.nulo, "minutos": self.t,
                "estrutura": {"processos": self.proc, "rajadas": self.lei_rajadas},
                "rajadas": [r for r in self.rajadas if r["inicio"] <= self.t],
                "episodios": [dict(e) for e in self.reg["episodios"]], "atos": [dict(a) for a in self.reg["atos"]],
                "leis": [{"nome": f"o pedido à {p['mao']} desfaz o desvio", "de": f"pedido a {p['mao']}", "para": [[p["nome"], "nível"], [p["nome"], "avisos no minuto"]],
                          "atraso": p["atraso_do_ato_min"], "so_com_desvio": True} for p in self.proc if p["lei"] == "só volta com ato"]
                + [{"nome": f"{p['nome']} volta sozinho", "de": "o desvio", "para": [p["nome"], "nível"],
                    "constante_de_tempo_min": p["constante_de_tempo_min"], "o_ato_nao_muda": True} for p in self.proc if p["lei"] == "volta sozinho"],
                "ramo_sem_ato": "um campo que volta sozinho voltaria em reverteria_sozinha_em (a constante de tempo do desvio somado); um campo que só volta "
                                "com ato não voltaria (reverteria_sozinha_em nulo)",
                "observacao_do_nulo": {None: None, "surda": "nenhum ato chega ao mundo", "calma": "os mesmos desvios espalhados no tempo, sem rajada"}[self.nulo]}


def _volta(t, desvio, tau):
    """O minuto em que um desvio que decai sozinho volta ao lugar (fica abaixo de 2), contado como o mundo conta: o decaimento começa
    no próprio minuto do desvio."""
    r, x, u = math.exp(-1.0 / tau), abs(desvio), t
    while True:
        x *= r
        if x < 2.0:
            return u
        u += 1
