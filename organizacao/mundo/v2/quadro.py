"""O quadro de pessoal, em SQLite: quem está na empresa e em que equipe, o ponto (entradas e saídas registradas), as ausências do dia
(férias, falta), as horas extras, as vagas abertas e os candidatos, as entradas e as saídas de gente. Também guarda as solicitações
que chegam à gestão (cancelamentos de clientes, pedidos de dentro da empresa). Os agregados saem por equipe."""
import sqlite3

from .cadastro import EQUIPES
from .arquivo import Marcos, podar

ESQUEMA = """
CREATE TABLE pessoas (id INTEGER PRIMARY KEY, equipe TEXT, papel TEXT, projeto TEXT, entrada_em INTEGER, saida_em INTEGER, ativo INTEGER);
CREATE TABLE ponto (pessoa INTEGER, t INTEGER, tipo TEXT);
CREATE INDEX po_t ON ponto(t);
CREATE TABLE ausencias (pessoa INTEGER, data INTEGER, motivo TEXT);
CREATE TABLE extras (pessoa INTEGER, data INTEGER, minutos INTEGER);
CREATE TABLE vagas (id INTEGER PRIMARY KEY, equipe TEXT, papel TEXT, projeto TEXT, aberta_em INTEGER, fechada_em INTEGER, estado TEXT, motivo TEXT);
CREATE TABLE candidatos (id INTEGER PRIMARY KEY, vaga INTEGER, estagio TEXT, t INTEGER, nota REAL);
CREATE TABLE solicitacoes (id INTEGER PRIMARY KEY, t INTEGER, tipo TEXT, texto TEXT, estado TEXT, protocolo INTEGER, cliente INTEGER,
    concluida_em INTEGER);
CREATE INDEX so_e ON solicitacoes(estado);
"""


class Quadro:
    def __init__(self):
        self.db = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False)
        self.db.executescript(ESQUEMA)
        self.ponto_min = [0, 0]                           # entradas e saídas registradas no minuto
        self.dia = {e: {"férias": 0, "falta": 0, "extras": 0.0} for e in EQUIPES}
        self.mes = {"entradas": 0, "saídas": 0, "mes": 0}

    def admitir(self, t, pessoa, equipe, papel, projeto):
        self.db.execute("INSERT INTO pessoas (id, equipe, papel, projeto, entrada_em, ativo) VALUES (?,?,?,?,?,1)",
                        (pessoa, equipe, papel, projeto, t))

    def desligar(self, t, pessoa):
        self.db.execute("UPDATE pessoas SET ativo=0, saida_em=? WHERE id=?", (t, pessoa))

    def bater_ponto(self, t, pessoa, tipo):
        self.db.execute("INSERT INTO ponto (pessoa, t, tipo) VALUES (?,?,?)", (pessoa, t, tipo))
        self.ponto_min[0 if tipo == "entrada" else 1] += 1

    def ausencia(self, pessoa, equipe, data, motivo):
        self.db.execute("INSERT INTO ausencias (pessoa, data, motivo) VALUES (?,?,?)", (pessoa, data, motivo))
        self.dia[equipe][motivo] += 1

    def hora_extra(self, pessoa, equipe, data, minutos):
        self.db.execute("INSERT INTO extras (pessoa, data, minutos) VALUES (?,?,?)", (pessoa, data, minutos))
        self.dia[equipe]["extras"] += minutos / 60.0

    def novo_dia(self, cal):
        self.dia = {e: {"férias": 0, "falta": 0, "extras": 0.0} for e in EQUIPES}
        if cal.mes != self.mes["mes"]:
            self.mes = {"entradas": 0, "saídas": 0, "mes": cal.mes}

    # ---------- vagas ----------
    def abrir_vaga(self, t, equipe, papel, projeto, motivo):
        return self.db.execute("INSERT INTO vagas (equipe, papel, projeto, aberta_em, estado, motivo) VALUES (?,?,?,?,?,?)",
                               (equipe, papel, projeto, t, "aberta", motivo)).lastrowid

    def vagas_abertas(self):
        return self.db.execute("SELECT * FROM vagas WHERE estado IN ('aberta', 'em contratação') ORDER BY id").fetchall()

    def mudar_vaga(self, t, vaga, estado):
        fechada = t if estado in ("preenchida", "cancelada") else None
        self.db.execute("UPDATE vagas SET estado=?, fechada_em=COALESCE(?, fechada_em) WHERE id=?", (estado, fechada, vaga))

    def candidato(self, t, vaga, estagio, nota):
        return self.db.execute("INSERT INTO candidatos (vaga, estagio, t, nota) VALUES (?,?,?,?)", (vaga, estagio, t, nota)).lastrowid

    def mover_candidato(self, t, candidato, estagio):
        self.db.execute("UPDATE candidatos SET estagio=?, t=? WHERE id=?", (estagio, t, candidato))

    def candidatos(self, vaga, estagio):
        return self.db.execute("SELECT * FROM candidatos WHERE vaga=? AND estagio=? ORDER BY id", (vaga, estagio)).fetchall()

    # ---------- solicitações à gestão ----------
    def solicitar(self, t, tipo, texto, protocolo=None, cliente=None):
        return self.db.execute("INSERT INTO solicitacoes (t, tipo, texto, estado, protocolo, cliente) VALUES (?,?,?,?,?,?)",
                               (t, tipo, texto, "aberta", protocolo, cliente)).lastrowid

    def proxima_solicitacao(self, t, tipos=None):
        if tipos:
            return self.db.execute("SELECT * FROM solicitacoes WHERE estado='aberta' AND t<=? AND tipo IN (%s) ORDER BY id LIMIT 1"
                                   % ",".join("?" * len(tipos)), [t] + list(tipos)).fetchone()
        return self.db.execute("SELECT * FROM solicitacoes WHERE estado='aberta' AND t<=? ORDER BY id LIMIT 1", (t,)).fetchone()

    def concluir_solicitacao(self, t, sid, estado="concluída"):
        self.db.execute("UPDATE solicitacoes SET estado=?, concluida_em=? WHERE id=?", (estado, t, sid))

    def solicitacoes_abertas(self):
        return self.db.execute("SELECT COUNT(*) FROM solicitacoes WHERE estado='aberta'").fetchone()[0]

    def contagem_vagas(self):
        v = self.db.execute("SELECT COUNT(*) FROM vagas WHERE estado IN ('aberta', 'em contratação')").fetchone()[0]
        c = self.db.execute("SELECT COUNT(*) FROM candidatos WHERE estagio IN ('triagem', 'entrevista', 'proposta')").fetchone()[0]
        return v, c

    def arquivar(self, t):
        """(v2) Ponto, ausências e horas extras por 120 dias; solicitações concluídas por 120; vagas fechadas, os seus candidatos e
        as pessoas que saíram, por um ano."""
        if not hasattr(self, "marcos"):
            self.marcos = Marcos()
        db = self.db
        n = podar(db, self.marcos, t, [("ponto", 120, None), ("ausencias", 120, None), ("extras", 120, None),
                                       ("solicitacoes", 120, "estado NOT IN ('aberta', 'em andamento')")])
        ano = t - 365 * 1440
        n += db.execute("DELETE FROM candidatos WHERE vaga IN (SELECT id FROM vagas WHERE estado NOT IN ('aberta', 'em contratação') "
                        "AND fechada_em < ?)", (ano,)).rowcount
        n += db.execute("DELETE FROM vagas WHERE estado NOT IN ('aberta', 'em contratação') AND fechada_em < ?", (ano,)).rowcount
        n += db.execute("DELETE FROM pessoas WHERE ativo = 0 AND saida_em < ?", (ano,)).rowcount
        self.marcos.marcar(t, db, ("ponto", "ausencias", "extras", "solicitacoes"))
        self.marcos.esquecer(t, 120)
        return n

    def __getstate__(self):
        d = dict(self.__dict__)
        d["db"] = None
        return d
