"""O sistema de fluxo de trabalho da empresa (tipo Jira), em banco de dados real (SQLite). Projetos (Produto, Plataforma, Suporte,
Infraestrutura), itens com tipo (épico, história, tarefa, bug, chamado), estado por tipo, prioridade, componente, equipe responsável,
pontos, prazo, sprint, comentários, vínculo item-versão, ligações entre itens (o chamado escalado para o bug, o bug causado por uma
história), reaberturas, e o log de toda transição com instante e equipe. Sprints de duas semanas por projeto, com planejamento
(meta e capacidade) e retrospectiva.

Quem age aqui são as pessoas (pessoas.py) e os clientes, por meio do atendimento. As contagens por projeto, tipo, estado,
prioridade, componente e equipe são mantidas pelo próprio banco (gatilhos), como o painel de um sistema desses; os conectores leem
só agregados."""
import sqlite3

from .cadastro import PROJETOS, MINUTOS_DIA
from .arquivo import Marcos, podar

ESTADOS = {
    "épico": ("aberto", "em andamento", "concluído"),
    "história": ("backlog", "refinamento", "pronto para desenvolver", "em desenvolvimento", "em revisão", "em qualidade",
                 "pronto para liberar", "liberado", "descartado"),
    "tarefa": ("backlog", "pronto para desenvolver", "em andamento", "em revisão", "pronto para liberar", "liberado", "concluído",
               "descartado"),
    "bug": ("aberto", "triagem", "pronto para desenvolver", "em desenvolvimento", "em revisão", "em qualidade", "pronto para liberar",
            "liberado", "não reproduzido"),
    "chamado": ("aberto", "em atendimento", "aguardando cliente", "escalado", "resolvido", "fechado", "descartado"),
}
FINAIS = ("liberado", "concluído", "fechado", "descartado", "não reproduzido")
ENTREGUES = ("liberado", "concluído", "resolvido", "fechado")
PRIORIDADES = ("baixa", "média", "alta", "crítica")
SLA_PRIMEIRA_RESPOSTA = {"crítica": 60, "alta": 240, "média": 1440, "baixa": 4320}     # minutos

ESQUEMA = """
CREATE TABLE itens (id INTEGER PRIMARY KEY, chave TEXT, projeto TEXT, tipo TEXT, titulo TEXT, estado TEXT, prioridade TEXT,
    componente TEXT, equipe TEXT, responsavel INTEGER, sprint INTEGER, pontos INTEGER, prazo INTEGER, criado_em INTEGER,
    atualizado_em INTEGER, resolvido_em INTEGER, primeira_resposta_em INTEGER, cliente INTEGER, canal TEXT, versao TEXT,
    reaberto INTEGER DEFAULT 0, epico INTEGER, origem TEXT, protocolo INTEGER);
CREATE INDEX i_estado ON itens(projeto, tipo, estado);
CREATE INDEX i_sprint ON itens(sprint);
CREATE INDEX i_epico ON itens(epico);
CREATE INDEX i_protocolo ON itens(protocolo);
CREATE TABLE transicoes (id INTEGER PRIMARY KEY, item INTEGER, de TEXT, para TEXT, t INTEGER, equipe TEXT, reabertura INTEGER);
CREATE INDEX tr_t ON transicoes(t);
CREATE INDEX tr_item ON transicoes(item);
CREATE TABLE comentarios (id INTEGER PRIMARY KEY, item INTEGER, t INTEGER, equipe TEXT, texto TEXT);
CREATE INDEX co_t ON comentarios(t);
CREATE INDEX co_item ON comentarios(item);
CREATE TABLE sprints (id INTEGER PRIMARY KEY, projeto TEXT, numero INTEGER, inicio INTEGER, fim_previsto INTEGER,
    fechado_em INTEGER, meta_pontos INTEGER, capacidade_pontos INTEGER, meta TEXT, retrospectiva TEXT);
CREATE TABLE vinculos (item INTEGER, versao TEXT, tipo TEXT, t INTEGER);
CREATE TABLE ligacoes (de INTEGER, para INTEGER, tipo TEXT, t INTEGER);
CREATE INDEX l_de ON ligacoes(de);
CREATE INDEX l_para ON ligacoes(para);
CREATE TABLE contagens (projeto TEXT, tipo TEXT, estado TEXT, prioridade TEXT, componente TEXT, equipe TEXT, n INTEGER,
    soma_criado INTEGER, PRIMARY KEY (projeto, tipo, estado, prioridade, componente, equipe));
CREATE TRIGGER conta_novo AFTER INSERT ON itens BEGIN
    INSERT INTO contagens VALUES (NEW.projeto, NEW.tipo, NEW.estado, NEW.prioridade, COALESCE(NEW.componente, ''),
        COALESCE(NEW.equipe, ''), 1, NEW.criado_em)
    ON CONFLICT DO UPDATE SET n = n + 1, soma_criado = soma_criado + NEW.criado_em;
END;
CREATE TRIGGER conta_muda AFTER UPDATE OF estado, prioridade, componente, equipe ON itens BEGIN
    UPDATE contagens SET n = n - 1, soma_criado = soma_criado - OLD.criado_em
        WHERE projeto = OLD.projeto AND tipo = OLD.tipo AND estado = OLD.estado AND prioridade = OLD.prioridade
        AND componente = COALESCE(OLD.componente, '') AND equipe = COALESCE(OLD.equipe, '');
    INSERT INTO contagens VALUES (NEW.projeto, NEW.tipo, NEW.estado, NEW.prioridade, COALESCE(NEW.componente, ''),
        COALESCE(NEW.equipe, ''), 1, NEW.criado_em)
    ON CONFLICT DO UPDATE SET n = n + 1, soma_criado = soma_criado + NEW.criado_em;
END;
CREATE TRIGGER conta_apaga AFTER DELETE ON itens BEGIN
    UPDATE contagens SET n = n - 1, soma_criado = soma_criado - OLD.criado_em
        WHERE projeto = OLD.projeto AND tipo = OLD.tipo AND estado = OLD.estado AND prioridade = OLD.prioridade
        AND componente = COALESCE(OLD.componente, '') AND equipe = COALESCE(OLD.equipe, '');
END;
"""


class Fluxo:
    def __init__(self):
        self.db = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(ESQUEMA)
        self.seq = {p: 0 for p in PROJETOS}

    # ---------- a API que as pessoas usam ----------
    def criar(self, t, projeto, tipo, titulo, prioridade="média", componente=None, equipe=None, ator=None, pontos=None, prazo=None,
              cliente=None, canal=None, epico=None, sprint=None, origem="equipe", protocolo=None, estado=None):
        self.seq[projeto] += 1
        chave = f"{projeto}-{self.seq[projeto]}"
        estado = estado or ESTADOS[tipo][0]
        cur = self.db.execute(
            "INSERT INTO itens (chave, projeto, tipo, titulo, estado, prioridade, componente, equipe, sprint, pontos, prazo, criado_em, "
            "atualizado_em, cliente, canal, epico, origem, protocolo) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (chave, projeto, tipo, titulo, estado, prioridade, componente, equipe, sprint, pontos, prazo, t, t, cliente, canal, epico,
             origem, protocolo))
        self.db.execute("INSERT INTO transicoes (item, de, para, t, equipe, reabertura) VALUES (?,?,?,?,?,0)",
                        (cur.lastrowid, None, estado, t, ator or equipe))
        return cur.lastrowid

    def transitar(self, t, item, para, ator, equipe=None):
        r = self.db.execute("SELECT estado, tipo, primeira_resposta_em FROM itens WHERE id=?", (item,)).fetchone()
        if r is None or r["estado"] == para:
            return False
        if para not in ESTADOS[r["tipo"]]:
            raise ValueError(f"estado {para} não existe para {r['tipo']}")
        de = r["estado"]
        reabertura = 1 if (de in ENTREGUES or de in FINAIS) and para not in ENTREGUES and para not in FINAIS else 0
        resolvido = t if para in ENTREGUES else None
        primeira = r["primeira_resposta_em"]
        if primeira is None and r["tipo"] == "chamado" and para != "aberto":
            primeira = t
        self.db.execute("UPDATE itens SET estado=?, atualizado_em=?, resolvido_em=COALESCE(?, resolvido_em), reaberto=reaberto+?, "
                        "primeira_resposta_em=?, equipe=COALESCE(?, equipe) WHERE id=?",
                        (para, t, resolvido, reabertura, primeira, equipe, item))
        self.db.execute("INSERT INTO transicoes (item, de, para, t, equipe, reabertura) VALUES (?,?,?,?,?,?)",
                        (item, de, para, t, ator, reabertura))
        return True

    def comentar(self, t, item, equipe, texto):
        self.db.execute("INSERT INTO comentarios (item, t, equipe, texto) VALUES (?,?,?,?)", (item, t, equipe, texto))
        self.db.execute("UPDATE itens SET atualizado_em=? WHERE id=?", (t, item))

    def atribuir(self, item, pessoa, equipe=None):
        if equipe is None:
            self.db.execute("UPDATE itens SET responsavel=? WHERE id=?", (pessoa, item))
        else:
            self.db.execute("UPDATE itens SET responsavel=?, equipe=? WHERE id=?", (pessoa, equipe, item))

    def priorizar(self, item, prioridade):
        self.db.execute("UPDATE itens SET prioridade=? WHERE id=?", (prioridade, item))

    def por_no_sprint(self, item, sprint):
        self.db.execute("UPDATE itens SET sprint=? WHERE id=?", (sprint, item))

    def estimar(self, item, pontos):
        self.db.execute("UPDATE itens SET pontos=? WHERE id=?", (pontos, item))

    def vincular_versao(self, t, item, versao, tipo="corrigido em"):
        self.db.execute("INSERT INTO vinculos (item, versao, tipo, t) VALUES (?,?,?,?)", (item, versao, tipo, t))
        if tipo == "corrigido em":
            self.db.execute("UPDATE itens SET versao=? WHERE id=?", (versao, item))

    def ligar(self, t, de, para, tipo):
        self.db.execute("INSERT INTO ligacoes (de, para, tipo, t) VALUES (?,?,?,?)", (de, para, tipo, t))

    # ---------- sprints ----------
    def abrir_sprint(self, t, projeto, numero, fim_previsto, meta_pontos, capacidade, meta):
        cur = self.db.execute("INSERT INTO sprints (projeto, numero, inicio, fim_previsto, meta_pontos, capacidade_pontos, meta) "
                              "VALUES (?,?,?,?,?,?,?)", (projeto, numero, t, fim_previsto, meta_pontos, capacidade, meta))
        return cur.lastrowid

    def fechar_sprint(self, t, sprint, retrospectiva):
        self.db.execute("UPDATE sprints SET fechado_em=?, retrospectiva=? WHERE id=?", (t, retrospectiva, sprint))

    def sprint_aberto(self, projeto):
        r = self.db.execute("SELECT * FROM sprints WHERE projeto=? AND fechado_em IS NULL ORDER BY id DESC LIMIT 1", (projeto,)).fetchone()
        return r

    def pontos_do_sprint(self, sprint):
        r = self.db.execute("SELECT COALESCE(SUM(pontos), 0) AS total, COALESCE(SUM(CASE WHEN estado IN ('liberado', 'concluído', "
                            "'pronto para liberar', 'não reproduzido') THEN pontos ELSE 0 END), 0) AS feitos, COUNT(*) AS n "
                            "FROM itens WHERE sprint=?", (sprint,)).fetchone()
        return r["total"], r["feitos"], r["n"]

    # ---------- consultas ----------
    def item(self, item):
        return self.db.execute("SELECT * FROM itens WHERE id=?", (item,)).fetchone()

    def itens(self, projeto=None, tipo=None, estados=None, sprint=None, responsavel=-1, componente=None, ordem="id", limite=None,
              extra=""):
        q = "SELECT * FROM itens WHERE 1=1"
        a = []
        if projeto:
            q += " AND projeto=?"
            a.append(projeto)
        if tipo:
            if isinstance(tipo, str):
                q += " AND tipo=?"
                a.append(tipo)
            else:
                q += " AND tipo IN (%s)" % ",".join("?" * len(tipo))
                a += list(tipo)
        if estados:
            q += " AND estado IN (%s)" % ",".join("?" * len(estados))
            a += list(estados)
        if sprint is not None:
            q += " AND sprint=?"
            a.append(sprint)
        if responsavel is None:
            q += " AND responsavel IS NULL"
        elif responsavel != -1:
            q += " AND responsavel=?"
            a.append(responsavel)
        if componente:
            q += " AND componente=?"
            a.append(componente)
        q += extra + " ORDER BY " + ordem + (f" LIMIT {int(limite)}" if limite else "")
        return self.db.execute(q, a).fetchall()

    def contar(self, projeto=None, tipo=None, estados=None, componente=None):
        q = "SELECT COALESCE(SUM(n), 0) FROM contagens WHERE 1=1"
        a = []
        if projeto:
            q += " AND projeto=?"
            a.append(projeto)
        if tipo:
            q += " AND tipo=?"
            a.append(tipo)
        if estados:
            q += " AND estado IN (%s)" % ",".join("?" * len(estados))
            a += list(estados)
        if componente:
            q += " AND componente=?"
            a.append(componente)
        return self.db.execute(q, a).fetchone()[0]

    def ligados(self, item, tipo):
        return [r[0] for r in self.db.execute("SELECT para FROM ligacoes WHERE de=? AND tipo=? ORDER BY para", (item, tipo)).fetchall()]

    def ligados_a(self, item, tipo):
        return [r[0] for r in self.db.execute("SELECT de FROM ligacoes WHERE para=? AND tipo=? ORDER BY de", (item, tipo)).fetchall()]

    # ---------- (v2) a retenção ----------
    def arquivar(self, t):
        """Transições e comentários por 120 dias; itens terminados há mais de 180 dias saem com os seus vínculos e ligações;
        épicos concluídos e sprints fechados, depois de um ano."""
        if not hasattr(self, "marcos"):
            self.marcos = Marcos()
        db = self.db
        n = podar(db, self.marcos, t, [("transicoes", 120, None), ("comentarios", 120, None)])
        velhos = [r[0] for r in db.execute("SELECT id FROM itens WHERE estado IN ('liberado', 'concluído', 'fechado', 'descartado', "
                                           "'não reproduzido') AND atualizado_em < ? AND tipo <> 'épico'", (t - 180 * MINUTOS_DIA,))]
        if velhos:
            db.execute("CREATE TEMP TABLE IF NOT EXISTS _velhos (id INTEGER PRIMARY KEY)")
            db.execute("DELETE FROM _velhos")
            db.executemany("INSERT INTO _velhos VALUES (?)", [(i,) for i in velhos])
            db.execute("DELETE FROM vinculos WHERE item IN (SELECT id FROM _velhos)")
            db.execute("DELETE FROM ligacoes WHERE de IN (SELECT id FROM _velhos) OR para IN (SELECT id FROM _velhos)")
            n += db.execute("DELETE FROM itens WHERE id IN (SELECT id FROM _velhos)").rowcount
            db.execute("DELETE FROM _velhos")
        n += db.execute("DELETE FROM itens WHERE tipo = 'épico' AND estado = 'concluído' AND atualizado_em < ?", (t - 365 * MINUTOS_DIA,)).rowcount
        n += db.execute("DELETE FROM sprints WHERE fechado_em IS NOT NULL AND fechado_em < ?", (t - 365 * MINUTOS_DIA,)).rowcount
        self.marcos.marcar(t, db, ("transicoes", "comentarios"))
        self.marcos.esquecer(t, 120)
        return n

    # ---------- o minuto (para os conectores) ----------
    def minuto(self, t):
        db = self.db
        contagens = db.execute("SELECT projeto, tipo, estado, prioridade, componente, equipe, n, soma_criado FROM contagens WHERE n>0").fetchall()
        transicoes = db.execute("SELECT i.projeto, i.tipo, i.componente, i.canal, tr.de, tr.para, tr.equipe, tr.reabertura "
                                "FROM transicoes tr JOIN itens i ON i.id = tr.item WHERE tr.t=?", (t,)).fetchall()
        comentarios = db.execute("SELECT i.projeto, c.equipe, COUNT(*) FROM comentarios c JOIN itens i ON i.id = c.item WHERE c.t=? "
                                 "GROUP BY i.projeto, c.equipe", (t,)).fetchall()
        sprints = db.execute("SELECT s.projeto, s.meta_pontos, COALESCE(SUM(i.pontos), 0), COALESCE(SUM(CASE WHEN i.estado IN "
                             "('liberado', 'concluído', 'pronto para liberar', 'não reproduzido') THEN i.pontos ELSE 0 END), 0), "
                             "COUNT(i.id), COALESCE(SUM(CASE WHEN i.prioridade IN ('alta', 'crítica') THEN 1 ELSE 0 END), 0) "
                             "FROM sprints s LEFT JOIN itens i ON i.sprint = s.id WHERE s.fechado_em IS NULL GROUP BY s.id").fetchall()
        sem_resposta = db.execute("SELECT prioridade, criado_em FROM itens WHERE projeto='SUP' AND tipo='chamado' AND estado='aberto'").fetchall()
        return contagens, transicoes, comentarios, sprints, sem_resposta

    def __getstate__(self):
        d = dict(self.__dict__)
        d["db"] = None
        return d

    def ligar_banco(self, con):
        con.row_factory = sqlite3.Row
        self.db = con
