"""O CRM próprio da equipe de vendas, em SQLite: negócios que passam por lead, qualificação, proposta, negociação e terminam ganhos
ou perdidos; atividades (ligação, e-mail, reunião, proposta enviada); e as tarefas internas da equipe (o que pedem a vendas de dentro
da empresa). Os leads chegam pelo site, por indicação de clientes e pela prospecção da própria equipe."""
import sqlite3

from .arquivo import Marcos, podar

ESTAGIOS = ("lead", "qualificação", "proposta", "negociação", "ganho", "perdido")
ABERTOS = ("lead", "qualificação", "proposta", "negociação")
ORIGENS = ("site", "indicação", "prospecção")

ESQUEMA = """
CREATE TABLE negocios (id INTEGER PRIMARY KEY, origem TEXT, estagio TEXT, plano TEXT, valor REAL, criado_em INTEGER,
    atualizado_em INTEGER, proxima_acao_em INTEGER, tentativas INTEGER, responsavel INTEGER, compromisso INTEGER, fechado_em INTEGER);
CREATE INDEX n_e ON negocios(estagio, proxima_acao_em);
CREATE TABLE atividades (id INTEGER PRIMARY KEY, negocio INTEGER, tipo TEXT, t INTEGER);
CREATE INDEX a_t ON atividades(t);
CREATE TABLE transicoes (id INTEGER PRIMARY KEY, negocio INTEGER, de TEXT, para TEXT, t INTEGER);
CREATE INDEX tc_t ON transicoes(t);
CREATE TABLE tarefas (id INTEGER PRIMARY KEY, texto TEXT, estado TEXT, criado_em INTEGER, concluido_em INTEGER, protocolo INTEGER);
CREATE INDEX ta_e ON tarefas(estado);
CREATE TABLE contagens (estagio TEXT, origem TEXT, n INTEGER, valor REAL, PRIMARY KEY (estagio, origem));
CREATE TRIGGER cn_novo AFTER INSERT ON negocios BEGIN
    INSERT INTO contagens VALUES (NEW.estagio, NEW.origem, 1, NEW.valor) ON CONFLICT DO UPDATE SET n = n + 1, valor = valor + NEW.valor;
END;
CREATE TRIGGER cn_muda AFTER UPDATE OF estagio ON negocios BEGIN
    UPDATE contagens SET n = n - 1, valor = valor - OLD.valor WHERE estagio = OLD.estagio AND origem = OLD.origem;
    INSERT INTO contagens VALUES (NEW.estagio, NEW.origem, 1, NEW.valor) ON CONFLICT DO UPDATE SET n = n + 1, valor = valor + NEW.valor;
END;
CREATE TRIGGER cn_apaga AFTER DELETE ON negocios BEGIN
    UPDATE contagens SET n = n - 1, valor = valor - OLD.valor WHERE estagio = OLD.estagio AND origem = OLD.origem;
END;
"""


class CRM:
    def __init__(self):
        self.db = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False)
        self.db.executescript(ESQUEMA)
        self.db.row_factory = sqlite3.Row

    def novo(self, t, origem, plano, valor, estagio="lead", proxima=None, compromisso=0):
        cur = self.db.execute("INSERT INTO negocios (origem, estagio, plano, valor, criado_em, atualizado_em, proxima_acao_em, "
                              "tentativas, compromisso) VALUES (?,?,?,?,?,?,?,0,?)",
                              (origem, estagio, plano, valor, t, t, t if proxima is None else proxima, compromisso))
        self.db.execute("INSERT INTO transicoes (negocio, de, para, t) VALUES (?,?,?,?)", (cur.lastrowid, None, estagio, t))
        return cur.lastrowid

    def mover(self, t, negocio, para, proxima=None):
        de = self.db.execute("SELECT estagio FROM negocios WHERE id=?", (negocio,)).fetchone()[0]
        if de == para:
            return
        fechado = t if para in ("ganho", "perdido") else None
        self.db.execute("UPDATE negocios SET estagio=?, atualizado_em=?, proxima_acao_em=COALESCE(?, proxima_acao_em), tentativas=0, "
                        "fechado_em=COALESCE(?, fechado_em) WHERE id=?", (para, t, proxima, fechado, negocio))
        self.db.execute("INSERT INTO transicoes (negocio, de, para, t) VALUES (?,?,?,?)", (negocio, de, para, t))

    def adiar(self, t, negocio, proxima):
        self.db.execute("UPDATE negocios SET proxima_acao_em=?, tentativas=tentativas+1, atualizado_em=? WHERE id=?", (proxima, t, negocio))

    def atividade(self, t, negocio, tipo):
        self.db.execute("INSERT INTO atividades (negocio, tipo, t) VALUES (?,?,?)", (negocio, tipo, t))

    def assumir(self, negocio, pessoa):
        self.db.execute("UPDATE negocios SET responsavel=? WHERE id=?", (pessoa, negocio))

    def proximo(self, t, estagios, responsavel=None):
        q = "SELECT * FROM negocios WHERE estagio IN (%s) AND proxima_acao_em<=?" % ",".join("?" * len(estagios))
        a = list(estagios) + [t]
        if responsavel is not None:
            q += " AND (responsavel IS NULL OR responsavel=?)"
            a.append(responsavel)
        q += " ORDER BY proxima_acao_em, id LIMIT 1"
        return self.db.execute(q, a).fetchone()

    def negocio(self, negocio):
        return self.db.execute("SELECT * FROM negocios WHERE id=?", (negocio,)).fetchone()

    def em_estagio(self, estagio):
        return self.db.execute("SELECT COALESCE(SUM(n), 0) FROM contagens WHERE estagio=?", (estagio,)).fetchone()[0]

    def abertos(self):
        return self.db.execute("SELECT COALESCE(SUM(n), 0), COALESCE(SUM(valor), 0) FROM contagens WHERE estagio IN "
                               "('lead', 'qualificação', 'proposta', 'negociação')").fetchone()

    # ---------- tarefas internas ----------
    def nova_tarefa(self, t, texto, protocolo=None):
        return self.db.execute("INSERT INTO tarefas (texto, estado, criado_em, protocolo) VALUES (?,?,?,?)",
                               (texto, "aberta", t, protocolo)).lastrowid

    def tarefa_aberta(self):
        return self.db.execute("SELECT * FROM tarefas WHERE estado='aberta' ORDER BY id LIMIT 1").fetchone()

    def fechar_tarefa(self, t, tarefa, estado="concluída"):
        self.db.execute("UPDATE tarefas SET estado=?, concluido_em=? WHERE id=?", (estado, t, tarefa))

    # ---------- o minuto ----------
    def minuto(self, t):
        db = self.db
        contagens = db.execute("SELECT estagio, origem, n, valor FROM contagens WHERE n>0").fetchall()
        transicoes = db.execute("SELECT n.origem, tr.de, tr.para FROM transicoes tr JOIN negocios n ON n.id = tr.negocio WHERE tr.t=?", (t,)).fetchall()
        atividades = db.execute("SELECT tipo, COUNT(*) FROM atividades WHERE t=? GROUP BY tipo", (t,)).fetchall()
        tarefas = db.execute("SELECT COUNT(*) FROM tarefas WHERE estado='aberta'").fetchone()[0]
        return contagens, transicoes, atividades, tarefas

    def arquivar(self, t):
        """(v2) Atividades e transições por 120 dias; tarefas concluídas por 120; negócios fechados há mais de 180 dias."""
        if not hasattr(self, "marcos"):
            self.marcos = Marcos()
        n = podar(self.db, self.marcos, t, [("atividades", 120, None), ("transicoes", 120, None), ("tarefas", 120, "estado <> 'aberta'")])
        n += self.db.execute("DELETE FROM negocios WHERE estagio IN ('ganho', 'perdido') AND fechado_em < ?", (t - 180 * 1440,)).rowcount
        self.marcos.marcar(t, self.db, ("atividades", "transicoes", "tarefas"))
        self.marcos.esquecer(t, 120)
        return n

    def __getstate__(self):
        d = dict(self.__dict__)
        d["db"] = None
        return d

    def ligar_banco(self, con):
        con.row_factory = sqlite3.Row
        self.db = con
