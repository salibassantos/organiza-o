"""A agenda da empresa, em SQLite: reuniões com tipo, equipe, início, fim e participantes. Os horários são do calendário da empresa
(o que a folhinha diz; ver relogio.py). Quem está numa reunião em curso não age nos sistemas naquele minuto."""
import sqlite3

from .cadastro import MINUTOS_DIA
from .arquivo import Marcos, podar

TIPOS = ("diária", "planejamento", "refinamento", "revisão e retrospectiva", "semanal", "liderança", "mensal", "com cliente",
         "entrevista", "alinhamento")
INICIO_EXPEDIENTE = 9 * 60
FIM_EXPEDIENTE = 17 * 60 + 30

ESQUEMA = """
CREATE TABLE reunioes (id INTEGER PRIMARY KEY, tipo TEXT, equipe TEXT, inicio INTEGER, fim INTEGER, titulo TEXT, origem TEXT,
    protocolo INTEGER, marcada_em INTEGER);
CREATE INDEX r_i ON reunioes(inicio);
CREATE TABLE participantes (reuniao INTEGER, pessoa INTEGER);
"""


class Agenda:
    def __init__(self):
        self.db = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False)
        self.db.executescript(ESQUEMA)
        self.dias = {}            # data do calendário -> [(início, fim, id, tipo, equipe, pessoas)]
        self.criado = {}          # data -> instante real em que a primeira reunião daquela data foi marcada
        self.geradas = {}         # datas cujas reuniões fixas já foram postas na agenda -> instante em que foram postas
        self.agora = ()           # as reuniões em curso no minuto
        self.ocupados = frozenset()

    def marcar(self, t, tipo, equipe, inicio, duracao, pessoas, titulo, origem="rotina", protocolo=None):
        pessoas = tuple(sorted(set(pessoas)))
        if not pessoas:
            return None
        fim = inicio + duracao
        rid = self.db.execute("INSERT INTO reunioes (tipo, equipe, inicio, fim, titulo, origem, protocolo, marcada_em) VALUES (?,?,?,?,?,?,?,?)",
                              (tipo, equipe, inicio, fim, titulo, origem, protocolo, t)).lastrowid
        self.db.executemany("INSERT INTO participantes (reuniao, pessoa) VALUES (?,?)", [(rid, p) for p in pessoas])
        data = inicio // MINUTOS_DIA
        self.dias.setdefault(data, []).append((inicio, fim, rid, tipo, equipe, pessoas))
        self.criado.setdefault(data, t)
        return rid

    def desmarcar_pessoa(self, pessoa, a_partir):
        """Tira a pessoa das reuniões futuras (quando ela sai da empresa)."""
        for data, lista in self.dias.items():
            nova = []
            for r in lista:
                if r[0] >= a_partir and pessoa in r[5]:
                    r = r[:5] + (tuple(p for p in r[5] if p != pessoa),)
                nova.append(r)
            self.dias[data] = nova

    def minuto(self, t, cal):
        """Atualiza as reuniões em curso e devolve o conjunto de quem está em reunião."""
        lista = self.dias.get(cal.data, ())
        agora = cal.absoluto
        self.agora = tuple(r for r in lista if r[0] <= agora < r[1])
        if self.agora:
            ocupados = set()
            for r in self.agora:
                ocupados.update(r[5])
            self.ocupados = frozenset(ocupados)
        else:
            self.ocupados = frozenset()
        return self.ocupados

    def podar(self, t, cal, embaralhado):
        for data in list(self.dias):
            velho = (t - self.criado.get(data, t) > 20 * MINUTOS_DIA) if embaralhado else (data < cal.data - 1)
            if velho:
                del self.dias[data]
                self.criado.pop(data, None)

    def livre(self, pessoas, inicio, duracao):
        fim = inicio + duracao
        ps = set(pessoas)
        for r in self.dias.get(inicio // MINUTOS_DIA, ()):
            if r[0] < fim and inicio < r[1] and ps.intersection(r[5]):
                return False
        return True

    def primeiro_horario_livre(self, pessoas, agora_abs, duracao, antecedencia=30, dias=6):
        """O primeiro horário de expediente, em dia útil, em que todos estão livres. Procura de meia em meia hora."""
        inicio = agora_abs + antecedencia
        inicio += (-inicio) % 30
        limite = agora_abs + dias * MINUTOS_DIA
        while inicio < limite:
            data, m = divmod(inicio, MINUTOS_DIA)
            if data % 7 >= 5 or m >= FIM_EXPEDIENTE - duracao:
                inicio = (data + 1) * MINUTOS_DIA + INICIO_EXPEDIENTE
                continue
            if m < INICIO_EXPEDIENTE:
                inicio = data * MINUTOS_DIA + INICIO_EXPEDIENTE
                continue
            if 12 * 60 <= m < 13 * 60 + 30:
                inicio = data * MINUTOS_DIA + 13 * 60 + 30
                continue
            if self.livre(pessoas, inicio, duracao):
                return inicio
            inicio += 30
        return None

    def arquivar(self, t):
        """(v2) Reuniões e participantes por 60 dias; as datas já geradas são esquecidas depois de 60 dias."""
        if not hasattr(self, "marcos"):
            self.marcos = Marcos()
        n = podar(self.db, self.marcos, t, [("reunioes", 60, None), ("participantes", 60, None)])
        self.marcos.marcar(t, self.db, ("reunioes", "participantes"))
        self.marcos.esquecer(t, 60)
        for d in [d for d, tt in self.geradas.items() if tt < t - 60 * MINUTOS_DIA]:
            del self.geradas[d]
        return n

    def __getstate__(self):
        d = dict(self.__dict__)
        d["db"] = None
        return d
