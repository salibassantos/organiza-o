"""A base comum das famílias das escolas (contrato das famílias, organizacao/escolas/CONTRATO_familias.md): o relógio, a semente, os
nomes, os processos, a pausa e a retomada, o relógio como campo (opção) e a porta dos atos. Cada família herda daqui e escreve só a
sua lei. Nada aqui lê o observador.

O contrato de cada mundo: `Mundo(semente, nulo)`, `processos()`, `passo()`, `verdade()`, `eventos_humanos()`, `salvar(pasta)` e
`Mundo.carregar(pasta)`, `receber(equipe, tipo, texto) -> int` e `respostas()` para os atos, `equipes()`, `t`, `dia()`,
`minuto_do_dia()` e `dia_da_semana()`. As famílias com voz acrescentam `vozes() -> [(t, canal, texto)]`: as linhas que chegaram por um
canal desde a última chamada (a contagem delas também sai como campo do processo do canal).

O relógio como campo: com `relogio=True` (ou MUNDO_RELOGIO=1) o último processo é "relógio" (hora do dia, dia da semana, minuto do
mundo). Desligado por padrão: o mundo é o mesmo, byte a byte."""
import hashlib
import json
import os
import pickle
import random
import zlib
from dataclasses import dataclass, field

MINUTOS_DIA = 1440
CAMPOS_RELOGIO = ["hora do dia", "dia da semana", "minuto do mundo"]


@dataclass(frozen=True)
class Processo:
    nome: str
    campos: list = field(default_factory=list)
    equipe: str = ""
    resolucao: list = field(default_factory=list)


def sorteio(semente, *partes):
    """Uma sequência aleatória própria de cada lei: a mesma semente e o mesmo nome dão sempre a mesma sequência, e uma lei não mexe na
    sorte de outra (por isso um nulo tira só a sua lei)."""
    chave = zlib.crc32(json.dumps([int(semente)] + [str(p) for p in partes], ensure_ascii=False).encode())
    return random.Random(chave)


def relogio_ligado(valor):
    if valor is not None:
        return bool(valor)
    return os.environ.get("MUNDO_RELOGIO", "").strip().lower() in ("1", "sim", "true", "ligado")


class MundoBase:
    FAMILIA = ""
    NULOS = ()
    DIAS_PADRAO = 14

    def __init__(self, semente, nulo=None, relogio=None):
        if nulo is not None and nulo not in self.NULOS:
            raise ValueError(f"nulo desconhecido: {nulo}; os nulos de {self.FAMILIA} são {', '.join(self.NULOS)}")
        self.semente, self.nulo, self.t = int(semente), nulo, 0
        self.com_relogio = relogio_ligado(relogio)
        self.eventos, self.saida, self._vozes, self.numero = [], [], [], 0
        self._processos = []                    # cada família põe os seus, na ordem fixa

    # ---------- a porta ----------
    def processos(self):
        ps = list(self._processos)
        if self.com_relogio:
            ps.append(Processo("relógio", list(CAMPOS_RELOGIO), "", [1.0, 1.0, 1.0]))
        return [Processo(p.nome, list(p.campos), p.equipe, list(p.resolucao)) for p in ps]

    def dia(self):
        return self.t // MINUTOS_DIA

    def minuto_do_dia(self):
        return self.t % MINUTOS_DIA

    def dia_da_semana(self):
        return self.dia() % 7

    def equipes(self):
        return []

    def passo(self):
        self.t += 1
        saida = self._minuto(self.t)
        if self.com_relogio:
            t = self.t
            saida["relógio"] = [float((t % MINUTOS_DIA) // 60), float((t // MINUTOS_DIA) % 7), float(t)]
        return saida

    def receber(self, equipe, tipo, texto):
        self.numero += 1
        self._receber(self.numero, str(equipe), str(tipo), str(texto))
        return self.numero

    def respostas(self):
        prontas = [r for r in self.saida if r[0] <= self.t]
        self.saida = [r for r in self.saida if r[0] > self.t]
        return prontas

    def vozes(self):
        prontas = [v for v in self._vozes if v[0] <= self.t]
        self._vozes = [v for v in self._vozes if v[0] > self.t]
        return prontas

    def eventos_humanos(self):
        return [(t, x) for t, x in self.eventos if t <= self.t]

    def salvar(self, pasta):
        os.makedirs(pasta, exist_ok=True)
        with open(os.path.join(pasta, "estado.pickle"), "wb") as f:
            pickle.dump(self, f, protocol=pickle.HIGHEST_PROTOCOL)

    @classmethod
    def carregar(cls, pasta):
        with open(os.path.join(pasta, "estado.pickle"), "rb") as f:
            return pickle.load(f)

    # ---------- o que cada família escreve ----------
    def _minuto(self, t):
        raise NotImplementedError

    def _receber(self, numero, equipe, tipo, texto):
        pass


def hash_dos_minutos(m, dias):
    """O sha256 dos minutos de uma vida sem atos: a identidade de uma semente."""
    h = hashlib.sha256()
    for _ in range(dias * MINUTOS_DIA):
        h.update(json.dumps(m.passo(), sort_keys=True, ensure_ascii=False).encode())
    return h.hexdigest()


# ---------------------------------------------------------------------------------------------------- nomes próprios de cada mundo
LUGARES = ("da Torre", "da Ponte", "do Farol", "do Vale", "do Porto", "da Serra", "do Moinho", "do Pátio", "do Cais", "do Jardim",
           "do Mirante", "da Várzea", "da Colina", "do Arco", "da Fonte", "do Rio", "do Campo", "da Ilha", "da Muralha", "da Estação")
CANTOS = ("da cozinha", "da sala", "da varanda", "da oficina", "do escritório", "do corredor", "do quintal", "da garagem",
          "da biblioteca", "do ateliê")
COISAS = ("prensa", "caldeira", "esteira", "forno", "bomba", "turbina", "balança", "comporta", "guindaste", "tear", "moenda",
          "secadora", "peneira", "misturadora", "serra", "tanque", "torre de resfriamento", "câmara fria", "fornalha", "elevador")
def nomes_sem_repetir(s, lista, n):
    return s.sample(list(lista), n)
