"""O repositório de versões do produto (tipo git), em SQLite. O ramo principal guarda a implementação escolhida para cada função do
código; cada item em desenvolvimento tem o seu ramo com as mudanças que os commits fizeram; a qualidade aprova e o ramo entra no
principal; a operação gera uma versão a partir do principal (ou, numa correção urgente, a partir da versão no ar mais a correção) e a
implanta. Toda execução de testes também fica registrada aqui."""
import json
import sqlite3

from . import codigo
from .arquivo import Marcos, podar

ESQUEMA = """
CREATE TABLE commits (id INTEGER PRIMARY KEY, t INTEGER, item INTEGER, componente TEXT, funcao TEXT, de TEXT, para TEXT,
    linhas INTEGER, equipe TEXT, mensagem TEXT);
CREATE INDEX c_t ON commits(t);
CREATE TABLE versoes (id INTEGER PRIMARY KEY, nome TEXT, t INTEGER, codigo TEXT, origem TEXT, commits INTEGER, itens INTEGER);
CREATE TABLE implantacoes (id INTEGER PRIMARY KEY, t INTEGER, versao TEXT, tipo TEXT, commits INTEGER, itens INTEGER, equipe TEXT);
CREATE INDEX im_t ON implantacoes(t);
CREATE TABLE execucoes_teste (id INTEGER PRIMARY KEY, t INTEGER, componente TEXT, alvo TEXT, testes INTEGER, falhas INTEGER, equipe TEXT);
CREATE INDEX et_t ON execucoes_teste(t);
CREATE TABLE revisoes (id INTEGER PRIMARY KEY, t INTEGER, item INTEGER, resultado TEXT);
CREATE INDEX rv_t ON revisoes(t);
"""


class Repositorio:
    def __init__(self):
        self.db = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False)
        self.db.executescript(ESQUEMA)
        self.principal = dict(codigo.INICIAL)
        self.correta = dict(codigo.INICIAL)          # a implementação sã de cada função, que anda com as funcionalidades
        self.autoria = {}                            # função -> item que pôs a implementação atual no principal
        self.ramos = {}                              # item -> {função: implementação}
        self.commits_ramo = {}                       # item -> número de commits
        self.pendentes_implantacao = [0, 0]          # commits e itens que entraram no principal desde a última versão
        self.n_versoes = 0
        self.versoes = {"1.0": dict(codigo.INICIAL)}
        self.no_ar = "1.0"
        self.anterior = "1.0"
        self.db.execute("INSERT INTO versoes (nome, t, codigo, origem, commits, itens) VALUES (?,?,?,?,?,?)",
                        ("1.0", 0, json.dumps(codigo.INICIAL, sort_keys=True), "inicial", 0, 0))

    # ---------- commits ----------
    def commit(self, t, item, componente, mudancas, linhas, equipe, mensagem):
        ramo = self.ramos.setdefault(item, {})
        if not mudancas:
            self.db.execute("INSERT INTO commits (t, item, componente, funcao, de, para, linhas, equipe, mensagem) VALUES (?,?,?,?,?,?,?,?,?)",
                            (t, item, componente, None, None, None, linhas, equipe, mensagem))
        for funcao, impl in mudancas.items():
            de = ramo.get(funcao, self.principal[funcao])
            ramo[funcao] = impl
            self.db.execute("INSERT INTO commits (t, item, componente, funcao, de, para, linhas, equipe, mensagem) VALUES (?,?,?,?,?,?,?,?,?)",
                            (t, item, componente, funcao, de, impl, linhas, equipe, mensagem))
        self.commits_ramo[item] = self.commits_ramo.get(item, 0) + max(1, len(mudancas))

    def codigo_do_ramo(self, item):
        cod = dict(self.principal)
        cod.update(self.ramos.get(item, {}))
        return cod

    def mesclar(self, item):
        """O ramo aprovado entra no principal. Devolve as funções que mudaram."""
        ramo = self.ramos.pop(item, {})
        n = self.commits_ramo.pop(item, 0)
        mudou = []
        for funcao, impl in ramo.items():
            if self.principal[funcao] != impl:
                mudou.append(funcao)
            self.principal[funcao] = impl
            self.autoria[funcao] = item
            if (funcao, impl) not in codigo.DEFEITOS:
                self.correta[funcao] = impl
        self.pendentes_implantacao[0] += n
        self.pendentes_implantacao[1] += 1
        return mudou

    def descartar_ramo(self, item):
        self.ramos.pop(item, None)
        self.commits_ramo.pop(item, None)

    # ---------- versões e implantações ----------
    def gerar_versao(self, t, base, origem):
        self.n_versoes += 1
        nome = f"1.{self.n_versoes}"
        commits, itens = self.pendentes_implantacao if origem == "regular" else (1, 1)
        self.versoes[nome] = dict(base)
        self.db.execute("INSERT INTO versoes (nome, t, codigo, origem, commits, itens) VALUES (?,?,?,?,?,?)",
                        (nome, t, json.dumps(base, sort_keys=True), origem, commits, itens))
        if origem == "regular":
            self.pendentes_implantacao = [0, 0]
        return nome

    def registrar_implantacao(self, t, versao, tipo, equipe):
        row = self.db.execute("SELECT commits, itens FROM versoes WHERE nome=?", (versao,)).fetchone()
        commits, itens = (row if row else (0, 0)) if tipo != "reversão" else (0, 0)
        self.db.execute("INSERT INTO implantacoes (t, versao, tipo, commits, itens, equipe) VALUES (?,?,?,?,?,?)",
                        (t, versao, tipo, commits, itens, equipe))
        self.anterior = self.no_ar
        self.no_ar = versao

    def registrar_testes(self, t, componente, alvo, testes, falhas, equipe):
        self.db.execute("INSERT INTO execucoes_teste (t, componente, alvo, testes, falhas, equipe) VALUES (?,?,?,?,?,?)",
                        (t, componente, alvo, testes, falhas, equipe))

    def registrar_revisao(self, t, item, resultado):
        self.db.execute("INSERT INTO revisoes (t, item, resultado) VALUES (?,?,?)", (t, item, resultado))

    def defeitos_em(self, cod):
        """Para a verdade: os defeitos presentes num código (função, implementação)."""
        return sorted((f, v) for f, v in cod.items() if (f, v) in codigo.DEFEITOS)

    # ---------- o minuto (para os conectores) ----------
    def minuto(self, t):
        db = self.db
        commits = db.execute("SELECT componente, COUNT(*), COALESCE(SUM(linhas), 0) FROM commits WHERE t=? GROUP BY componente", (t,)).fetchall()
        testes = db.execute("SELECT componente, COUNT(*), SUM(testes), SUM(falhas) FROM execucoes_teste WHERE t=? GROUP BY componente", (t,)).fetchall()
        revisoes = db.execute("SELECT resultado, COUNT(*) FROM revisoes WHERE t=? GROUP BY resultado", (t,)).fetchall()
        impl = db.execute("SELECT COUNT(*), COALESCE(SUM(commits), 0), COALESCE(SUM(itens), 0) FROM implantacoes WHERE t=?", (t,)).fetchone()
        return commits, testes, revisoes, impl

    def arquivar(self, t):
        """(v2) Commits, execuções de teste, revisões e implantações por 120 dias; versões antigas (menos a no ar e a anterior)."""
        if not hasattr(self, "marcos"):
            self.marcos = Marcos()
        db = self.db
        n = podar(db, self.marcos, t, [("commits", 120, None), ("execucoes_teste", 120, None), ("revisoes", 120, None),
                                       ("implantacoes", 120, None)])
        lim = self.marcos.limite(t, 120)
        if lim is not None:
            n += db.execute("DELETE FROM versoes WHERE rowid <= ? AND nome NOT IN (?, ?, '1.0')", (lim["versoes"], self.no_ar, self.anterior)).rowcount
        self.marcos.marcar(t, db, ("commits", "execucoes_teste", "revisoes", "implantacoes", "versoes"))
        self.marcos.esquecer(t, 120)
        return n

    def __getstate__(self):
        d = dict(self.__dict__)
        d["db"] = None
        return d
