"""O software da empresa no ar: um serviço com rotas, banco de dados real (SQLite em memória), fila de trabalhos de fundo, tarefas
agendadas e o volume de disco onde o banco mora. Quem chama as rotas são os clientes (clientes.py), a sonda de disponibilidade da
operação (uma chamada de ensaio por rota a cada minuto) e a qualidade, num ambiente de ensaio separado.

O que roda é o código da versão no ar (codigo.py). As métricas saem do que o código fez: cada requisição conta as consultas e as
instruções que o banco executou (o banco avisa a cada dez instruções), o trabalho da aplicação e a espera pelos serviços de fora
(gateway de pagamento, transportadoras, antifraude); a latência é função disso e da carga do processador. O processador e a memória
são função do que as requisições e os trabalhos fizeram e do que o processo guarda (o cache de sessões, a fila). O tamanho do banco é
o número de páginas que o SQLite ocupa; quando o volume enche, toda escrita falha com o erro do próprio SQLite, e o produto cai.

Os serviços de fora são o mundo lá fora: o seu tempo de resposta e as suas recusas são sorteados."""
import collections
import sqlite3

from . import codigo
from .codigo import Recusa
from .cadastro import ROTAS, DIGITO_REGIAO, sorteio, MINUTOS_DIA
from .arquivo import Marcos, podar

PAGINA_BYTES = 4096
BASE_ROTA_MS = {"login": 38.0, "catalogo": 30.0, "busca": 42.0, "produto": 22.0, "carrinho": 26.0, "frete": 18.0, "pedido": 55.0,
                "pagamento": 40.0, "relatorio": 95.0, "exportacao": 120.0, "notas": 28.0, "conta": 30.0}
MS_CONSULTA = 1.1          # a ida e volta até o banco
MS_INSTRUCOES = 0.02       # por dez instruções do banco
MS_TRABALHO = 0.1          # por unidade de trabalho da aplicação
MEMORIA_LIMITE_MB = 2048.0
CAPACIDADE_FILA = 40       # trabalhos por minuto


class Banco:
    """A conexão do produto com o seu banco, contando o que ele faz."""

    def __init__(self, con):
        self.instr = 0
        self.consultas = 0
        self.escritas = 0
        self.ligar(con)

    def ligar(self, con):
        self.con = con
        con.set_progress_handler(self._dez, 10)

    def _dez(self):
        self.instr += 1
        return 0

    def um(self, sql, a=()):
        self.consultas += 1
        return self.con.execute(sql, a).fetchone()

    def todos(self, sql, a=()):
        self.consultas += 1
        return self.con.execute(sql, a).fetchall()

    def cursor(self, sql, a=()):
        self.consultas += 1
        return self.con.execute(sql, a)

    def exe(self, sql, a=()):
        self.escritas += 1
        return self.con.execute(sql, a)

    def __getstate__(self):
        d = dict(self.__dict__)
        d["con"] = None
        return d


class Execucao:
    """O contexto de uma requisição ou de um trabalho: quem pede, com que código, quanto trabalho e quanta espera."""
    __slots__ = ("db", "cod", "produto", "t", "cliente", "usuario", "simulacao", "mes", "trab", "ext")

    def trabalho(self, n):
        self.trab += n

    def externo(self, ms):
        self.ext += ms


# ---------------------------------------------------------------------------------------------------- o mundo lá fora
class Gateway:
    def __init__(self, sorte):
        self.s = sorte

    def cobrar(self, valor):
        espera = self.s.lognormvariate(5.75, 0.35)            # perto de 300 ms
        return self.s.random() > 0.04, espera

    def autenticar(self):
        return self.s.lognormvariate(5.3, 0.4)

    def consultar(self):
        return self.s.lognormvariate(4.3, 0.3)


class Transportadoras:
    def __init__(self, sorte):
        self.s = sorte
        self.falhas = 0

    def cotar(self):
        if self.s.random() < 0.0015:
            self.falhas += 1
            raise ConnectionError("transportadora não respondeu")
        return self.s.lognormvariate(5.1, 0.35)


class Antifraude:
    def __init__(self, sorte):
        self.s = sorte

    def consultar(self):
        return self.s.lognormvariate(4.9, 0.3)


class _ForaDeEnsaio:
    """Os serviços de fora no ambiente de ensaio: sempre aprovam, com espera fixa."""
    falhas = 0

    def cobrar(self, valor): return True, 300.0
    def autenticar(self): return 200.0
    def consultar(self): return 80.0
    def cotar(self): return 160.0


# ---------------------------------------------------------------------------------------------------- o esquema e os dados de partida
ESQUEMA = """
CREATE TABLE clientes (id INTEGER PRIMARY KEY, nome_fantasia TEXT, razao TEXT, plano TEXT, cep TEXT, uf TEXT, regiao INTEGER,
    telefone TEXT, criado_em INTEGER, ativo INTEGER);
CREATE TABLE usuarios (id INTEGER PRIMARY KEY, cliente INTEGER, login TEXT, ativo INTEGER);
CREATE UNIQUE INDEX u_login ON usuarios(login);
CREATE TABLE sessoes (token TEXT PRIMARY KEY, usuario INTEGER, criada_em INTEGER);
CREATE INDEX s_t ON sessoes(criada_em);
CREATE TABLE dispositivos (id INTEGER PRIMARY KEY, usuario INTEGER, t INTEGER);
CREATE INDEX d_u ON dispositivos(usuario);
CREATE TABLE produtos (id INTEGER PRIMARY KEY, nome TEXT, nome_busca TEXT, categoria TEXT, preco REAL, estoque INTEGER,
    estoque_alvo INTEGER, peso REAL, vendidos INTEGER);
CREATE INDEX p_cat ON produtos(categoria, nome);
CREATE TABLE palavras (palavra TEXT, produto INTEGER);
CREATE INDEX w_p ON palavras(palavra);
CREATE TABLE carrinhos (id INTEGER PRIMARY KEY, usuario INTEGER, produto INTEGER, quantidade INTEGER, t INTEGER);
CREATE INDEX c_u ON carrinhos(usuario);
CREATE TABLE pedidos (id INTEGER PRIMARY KEY, cliente INTEGER, usuario INTEGER, valor REAL, itens INTEGER, estado TEXT, cep TEXT, t INTEGER);
CREATE INDEX pe_c ON pedidos(cliente, t);
CREATE INDEX pe_t ON pedidos(t);
CREATE TABLE itens_pedido (pedido INTEGER, produto INTEGER, quantidade INTEGER, preco REAL);
CREATE INDEX ip_p ON itens_pedido(pedido);
CREATE TABLE pagamentos (id INTEGER PRIMARY KEY, pedido INTEGER, valor REAL, estado TEXT, t INTEGER);
CREATE INDEX pg_p ON pagamentos(pedido);
CREATE TABLE notas (id INTEGER PRIMARY KEY, pedido INTEGER, cliente INTEGER, uf TEXT, valor REAL, imposto REAL, estado TEXT, t INTEGER);
CREATE INDEX n_c ON notas(cliente, t);
CREATE TABLE emails (id INTEGER PRIMARY KEY, cliente INTEGER, tipo TEXT, assunto TEXT, t INTEGER);
CREATE TABLE faturas (id INTEGER PRIMARY KEY, cliente INTEGER, mes INTEGER, valor REAL, estado TEXT, t INTEGER);
CREATE INDEX f_c ON faturas(cliente, estado);
CREATE INDEX f_e ON faturas(estado);
CREATE TABLE trabalhos (id INTEGER PRIMARY KEY, tipo TEXT, ref INTEGER, estado TEXT, tentativas INTEGER, proxima_em INTEGER, criado_em INTEGER);
CREATE INDEX tr_e ON trabalhos(estado, proxima_em);
CREATE TABLE auditoria (id INTEGER PRIMARY KEY, t INTEGER, rota TEXT, usuario INTEGER);
"""

CATEGORIAS = {
    "mercearia": (["arroz", "feijão", "açúcar", "café", "macarrão", "farinha de trigo", "óleo de soja", "sal refinado", "fubá",
                   "aveia", "lentilha", "grão-de-bico", "tapioca", "molho de tomate", "milho"], ["1kg", "5kg", "500g", "tipo 1", "integral"]),
    "bebidas": (["refrigerante", "suco de laranja", "água mineral", "guaraná", "chá mate", "água de coco", "cerveja"], ["350ml", "2l", "1l", "lata", "caixa"]),
    "limpeza": (["detergente", "sabão em pó", "água sanitária", "desinfetante", "esponja", "álcool", "limpa-vidros", "sabão em barra"], ["500ml", "1l", "5l", "pacote", "neutro"]),
    "higiene": (["sabonete", "xampu", "creme dental", "papel higiênico", "desodorante", "condicionador", "fio dental"], ["90g", "300ml", "pacote", "família", "sem perfume"]),
    "padaria": (["pão de forma", "pão de queijo", "bolacha", "biscoito", "torrada", "bolo"], ["integral", "tradicional", "500g", "pacote"]),
    "frios": (["queijo muçarela", "presunto", "requeijão", "manteiga", "iogurte", "margarina"], ["200g", "500g", "fatiado", "pote"]),
    "hortifrúti": (["batata", "cebola", "tomate", "maçã", "banana", "limão", "mamão", "alho"], ["kg", "bandeja", "orgânico"]),
    "papelaria": (["caderno", "caneta", "lápis", "papel sulfite", "envelope", "grampeador", "pasta"], ["unidade", "caixa", "pacote", "A4"]),
    "utilidades": (["copo", "prato", "talher", "panela", "pote", "garrafa térmica", "lixeira"], ["plástico", "vidro", "inox", "grande", "pequeno"]),
    "pet": (["ração", "areia higiênica", "petisco", "coleira"], ["cão", "gato", "1kg", "10kg", "filhote"]),
    "congelados": (["pizza", "lasanha", "hambúrguer", "batata palito", "pão de alho", "sorvete"], ["congelado", "família", "500g", "1kg"]),
    "descartáveis": (["guardanapo", "copo descartável", "sacola", "papel toalha", "luva", "touca"], ["pacote", "caixa", "100 unidades", "50 unidades"]),
}


def _sem_acento(texto):
    return codigo.normalizar_termo__correta(texto)


def gerar_produtos(sorte):
    produtos = []
    for categoria, (bases, variantes) in CATEGORIAS.items():
        alvo = sorte.randint(26, 74)
        nomes = []
        for base in bases:
            for v in variantes:
                nomes.append(f"{base} {v}")
        sorte.shuffle(nomes)
        for nome in sorted(nomes[:alvo]):
            preco = round(sorte.uniform(2.0, 90.0), 2)
            estoque = sorte.randint(300, 2500)
            produtos.append((nome, _sem_acento(nome), categoria, preco, estoque, estoque, round(sorte.uniform(0.1, 6.0), 2)))
    return produtos


def criar_banco(produtos, clientes, usuarios):
    con = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False, cached_statements=0)
    con.executescript(ESQUEMA)
    con.executemany("INSERT INTO produtos (nome, nome_busca, categoria, preco, estoque, estoque_alvo, peso, vendidos) "
                    "VALUES (?,?,?,?,?,?,?,0)", produtos)
    for pid, nome_busca in con.execute("SELECT id, nome_busca FROM produtos").fetchall():
        for palavra in nome_busca.split():
            if len(palavra) > 2:
                con.execute("INSERT INTO palavras (palavra, produto) VALUES (?,?)", (palavra, pid))
    con.executemany("INSERT INTO clientes (id, nome_fantasia, razao, plano, cep, uf, regiao, telefone, criado_em, ativo) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?)", clientes)
    con.executemany("INSERT INTO usuarios (id, cliente, login, ativo) VALUES (?,?,?,1)", usuarios)
    return con


# ---------------------------------------------------------------------------------------------------- o serviço
class Produto:
    def __init__(self, semente, clientes, usuarios, paginas_por_dia_estimadas, folga_dias):
        sorte = sorteio(semente, "catalogo de produtos")
        self.sorte_rede = sorteio(semente, "rede")
        fora = sorteio(semente, "servicos de fora")
        self.gateway, self.frete, self.antifraude = Gateway(fora), Transportadoras(fora), Antifraude(fora)
        self.produtos_iniciais = gerar_produtos(sorte)
        con = criar_banco(self.produtos_iniciais, [(0, "Monitoramento", "Conta de monitoramento", "empresarial", "30140-071", "MG", 2,
                                                    "31 3000-0000", 0, 1)] + clientes,
                          [(0, 0, "monitoramento")] + usuarios)
        con.execute("INSERT INTO pedidos (id, cliente, usuario, valor, itens, estado, cep, t) VALUES (1, 0, 0, 10.0, 1, 'criado', '30140-071', 0)")
        con.executemany("INSERT INTO notas (pedido, cliente, uf, valor, imposto, estado, t) VALUES (1, 0, 'MG', 10.0, 1.8, 'emitida', ?)",
                        [(-i * 97,) for i in range(1, 181)])
        self.db = Banco(con)
        self.categorias = list(CATEGORIAS)
        self.codigo = dict(codigo.INICIAL)
        self._resolver()
        self.versao = "1.0"
        self.cache_sessoes = {}
        self.tokens = 0
        self.no_ar_ate = 0                    # enquanto t < no_ar_ate o processo está reiniciando
        self.reinicios_min = 0
        self.erros = collections.deque(maxlen=4000)        # (t, rota, função, tipo da exceção)
        self.lentas = collections.deque(maxlen=2000)       # (t, rota, função mais funda, instruções)
        self.fila_pendentes = 0
        self.fila_concluidos = self.fila_falhas = self.emails_ok = self.emails_falha = self.notas_ok = self.notas_falha = 0
        self.faturas_emitidas = 0
        self.primeira_auditoria_do_dia = []               # (t, id): para apagar auditoria antiga sem varrer a tabela
        self.cron_trabalho_ms = 0.0
        self.cron_em_curso = 0
        self.cron_linhas = 0
        self.repostas = 0
        self.rho = 0.05
        self.memoria = 400.0
        self.paginas_dia = collections.deque(maxlen=15)   # (dia, páginas ocupadas) para a operação estimar o crescimento
        usadas = self.paginas_ocupadas()
        self.volume_paginas = int(usadas + paginas_por_dia_estimadas * folga_dias)
        self._aplicar_volume()
        self._zerar_minuto()
        self.sonda_falhas_seguidas = 0
        self.janela = collections.deque(maxlen=30)          # os últimos minutos, para o monitoramento
        self.historico_latencia = {r: collections.deque(maxlen=7 * 24) for r in ROTAS}   # médias por hora, para alertas
        self._lat_hora = {r: [0.0, 0] for r in ROTAS}

    # ---------- o código no ar ----------
    def _resolver(self):
        self.cod = {f: codigo.IMPLEMENTACOES[f][v] for f, v in self.codigo.items()}

    def implantar(self, t, codigo_novo, versao):
        """Troca o código no ar. O processo reinicia (o cache de sessões se perde) sem derrubar as requisições."""
        self.codigo = dict(codigo_novo)
        self._resolver()
        self.versao = versao
        self.cache_sessoes = {}
        self.reinicios_min += 1
        self._x.cod = self.cod

    def novo_token(self):
        self.tokens += 1
        return f"s{self.tokens:09d}"

    # ---------- o disco ----------
    def paginas_ocupadas(self):
        c = self.db.con
        return c.execute("PRAGMA page_count").fetchone()[0] - c.execute("PRAGMA freelist_count").fetchone()[0]

    def _aplicar_volume(self):
        atual = self.db.con.execute("PRAGMA page_count").fetchone()[0]
        self.db.con.execute(f"PRAGMA max_page_count = {max(self.volume_paginas, atual)}")

    def aumentar_volume(self, paginas):
        self.volume_paginas = int(paginas)
        self._aplicar_volume()

    def apagar_auditoria_antiga(self, t, dias):
        """Apaga a auditoria mais velha que `dias` dias; devolve quantos registros saíram."""
        limite = None
        for tt, ident in self.primeira_auditoria_do_dia:
            if tt <= t - dias * MINUTOS_DIA:
                limite = ident
        if limite is None:
            return 0
        n = self.db.con.execute("DELETE FROM auditoria WHERE id < ?", (limite,)).rowcount
        self.primeira_auditoria_do_dia = [(tt, i) for tt, i in self.primeira_auditoria_do_dia if i >= limite]
        return n

    TABELAS_ARQUIVO = ("pedidos", "itens_pedido", "pagamentos", "notas", "emails", "faturas", "trabalhos", "dispositivos")

    def arquivar(self, t):
        """A política de retenção do produto: pedidos, pagamentos e notas por 180 dias, e-mails e dispositivos por 90, faturas
        quitadas por 400, trabalhos que falharam por 30. A auditoria não entra: ela só sai quando a operação a apaga."""
        if not hasattr(self, "marcos"):
            self.marcos = Marcos()
        db = self.db.con
        n = podar(db, self.marcos, t, [("pedidos", 180, None), ("itens_pedido", 180, None), ("pagamentos", 180, None),
                                       ("notas", 180, None), ("emails", 90, None), ("dispositivos", 90, None),
                                       ("faturas", 400, "estado <> 'aberta'"), ("trabalhos", 30, "estado = 'falha'")])
        self.marcos.marcar(t, db, self.TABELAS_ARQUIVO)
        self.marcos.esquecer(t, 400)
        return n

    def apagar_cliente(self, cliente):
        """Um cliente que saiu há muito tempo tem a conta apagada do produto."""
        try:
            self.db.con.execute("DELETE FROM usuarios WHERE cliente=?", (cliente,))
            self.db.con.execute("DELETE FROM clientes WHERE id=?", (cliente,))
        except sqlite3.Error:
            pass

    # ---------- uma requisição ----------
    def chamar(self, t, rota, req, cliente, usuario, simulacao=False):
        """Uma requisição a uma rota. Devolve (estado, latência em ms, função que falhou) com estado "ok", "erro" ou "recusa"."""
        m = self.m
        i = self._ri[rota]
        m_req, m_err, m_rec, m_lat, m_lats, m_cli = m["req"], m["erro"], m["recusa"], m["lat"], m["lats"][i], m["cli"][i]
        m_req[i] += 1
        if cliente:
            m_cli.add(cliente)
        if t < self.no_ar_ate:                               # o processo está reiniciando: o balanceador devolve erro na hora
            m_err[i] += 1
            m_lat[i] += 4.0
            m_lats.append(4.0)
            return "erro", 4.0, None
        db = self.db
        i0, c0, e0 = db.instr, db.consultas, db.escritas
        x = self._x
        x.t, x.cliente, x.usuario, x.simulacao, x.trab, x.ext = t, cliente, usuario, simulacao, 0, 0.0
        estado, falhou = "ok", None
        try:
            db.exe("INSERT INTO auditoria (t, rota, usuario) VALUES (?,?,?)", (t, rota, usuario))
            codigo.ROTAS_CODIGO[rota](x, req)
        except Recusa:
            estado = "recusa"
        except Exception as e:
            estado = "erro"
            falhou = codigo.funcao_que_falhou(e.__traceback__)
            self.erros.append((t, rota, falhou, type(e).__name__))
        instr = db.instr - i0
        servico = BASE_ROTA_MS[rota] + MS_CONSULTA * ((db.consultas - c0) + (db.escritas - e0)) + MS_INSTRUCOES * instr + MS_TRABALHO * x.trab
        if estado == "erro":
            servico += 15.0
        lat = (servico * (1.0 + 2.5 * self.rho * self.rho) + x.ext) * self.sorte_rede.lognormvariate(0.0, 0.12)
        self.cpu_ms += servico * 4.0
        if instr > 2000:
            self.lentas.append((t, rota, None, instr))
        if estado == "erro":
            m_err[i] += 1
        elif estado == "recusa":
            m_rec[i] += 1
        m_lat[i] += lat
        m_lats.append(lat)
        if not simulacao:
            if rota == "frete" or rota == "pedido":
                reg = DIGITO_REGIAO.get(req["cep"][:1], 0)
                if rota == "frete":
                    m["frete_reg"][reg] += 1
                    if estado == "erro":
                        m["frete_reg_erro"][reg] += 1
            if estado == "ok":
                if rota == "pagamento":
                    m["pag_ok"] += 1
                    m["pag_pedidos"].add(req["pedido"])
                elif rota == "pedido":
                    m["carrinho_fechado"] += 1
            elif estado == "recusa" and rota == "pagamento":
                m["pag_recusa"] += 1
        return estado, lat, falhou

    # ---------- a fila de trabalhos ----------
    def enfileirar(self, tipo, ref, t):
        self.db.exe("INSERT INTO trabalhos (tipo, ref, estado, tentativas, proxima_em, criado_em) VALUES (?,?,?,?,?,?)",
                    (tipo, ref, "pendente", 0, t, t))
        self.fila_pendentes += 1

    def processar_fila(self, t, mes):
        if t < self.no_ar_ate:
            return
        db = self.db
        try:
            lote = db.todos("SELECT id, tipo, ref, tentativas FROM trabalhos WHERE estado='pendente' AND proxima_em<=? ORDER BY proxima_em, id LIMIT ?",
                            (t, CAPACIDADE_FILA))
        except sqlite3.Error:
            return
        x = self._x
        for ident, tipo, ref, tentativas in lote:
            i0, c0, e0 = db.instr, db.consultas, db.escritas
            x.t, x.cliente, x.usuario, x.simulacao, x.trab, x.ext, x.mes = t, 0, 0, False, 0, 0.0, mes
            try:
                codigo.TRABALHOS_CODIGO[tipo](x, ref)
                db.exe("DELETE FROM trabalhos WHERE id=?", (ident,))
                self.fila_pendentes -= 1
                self.fila_concluidos += 1
                if tipo == "nota":
                    self.notas_ok += 1
                elif tipo == "fatura":
                    self.faturas_emitidas += 1
                    self.emails_ok += 1
                else:
                    self.emails_ok += 1
            except Exception as e:
                self.fila_falhas += 1
                falhou = codigo.funcao_que_falhou(e.__traceback__)
                self.erros.append((t, "fila", falhou, type(e).__name__))
                if tipo == "nota":
                    self.notas_falha += 1
                else:
                    self.emails_falha += 1
                try:
                    if tentativas + 1 >= 12:
                        db.exe("UPDATE trabalhos SET estado='falha', tentativas=? WHERE id=?", (tentativas + 1, ident))
                        self.fila_pendentes -= 1
                    else:
                        db.exe("UPDATE trabalhos SET tentativas=?, proxima_em=? WHERE id=?",
                               (tentativas + 1, t + min(720, 5 * 2 ** tentativas), ident))
                except sqlite3.Error:
                    pass
            self.cpu_ms += 4.0 * (8.0 + MS_CONSULTA * ((db.consultas - c0) + (db.escritas - e0)) + MS_INSTRUCOES * (db.instr - i0) + MS_TRABALHO * x.trab)

    # ---------- as tarefas agendadas do servidor (pelo calendário) ----------
    def agendadas(self, t, cal):
        m = cal.minuto
        db = self.db.con
        self.cron_em_curso = 0
        try:
            if 120 <= m < 136:                               # cópia de segurança noturna: lê o banco inteiro
                self.cron_em_curso += 1
                paginas = db.execute("PRAGMA page_count").fetchone()[0]
                self.cron_trabalho_ms += paginas * 0.35
                self.cron_linhas += paginas // 16
            if m == 180:                                     # limpeza de sessões e carrinhos velhos
                self.cron_em_curso += 1
                n = db.execute("DELETE FROM sessoes WHERE criada_em < ?", (t - 2 * MINUTOS_DIA,)).rowcount
                n += db.execute("DELETE FROM carrinhos WHERE t < ?", (t - 2 * MINUTOS_DIA,)).rowcount
                self.cron_linhas += n
                self.cron_trabalho_ms += 200.0 + n * 0.05
            if m == 240:                                     # os fornecedores repõem o estoque
                self.cron_em_curso += 1
                falta = db.execute("SELECT COALESCE(SUM(estoque_alvo - estoque), 0) FROM produtos WHERE estoque < estoque_alvo / 2").fetchone()[0]
                db.execute("UPDATE produtos SET estoque = estoque_alvo WHERE estoque < estoque_alvo / 2")
                self.repostas += falta
                self.cron_trabalho_ms += 300.0
            if m == 270 and cal.dia_semana == 6:             # reconstrução semanal dos índices
                self.cron_em_curso += 1
                db.execute("REINDEX pe_c")
                db.execute("REINDEX ip_p")
                self.cron_trabalho_ms += 9000.0
            if m == 210 and cal.dia_semana == 6:             # (v2) o expurgo semanal: dados velhos saem pela política de retenção
                self.cron_em_curso += 1
                n = self.arquivar(t)
                self.cron_linhas += n
                self.cron_trabalho_ms += 1500.0 + n * 0.05
            if m == 420:                                     # o resumo do dia anterior
                self.cron_em_curso += 1
                r = db.execute("SELECT COUNT(*), COALESCE(SUM(valor), 0) FROM pedidos WHERE t >= ?", (t - MINUTOS_DIA,)).fetchone()
                self.cron_linhas += r[0]
                self.cron_trabalho_ms += 400.0 + r[0] * 0.3
            if m == 360 and cal.dia_mes == 1:                 # o faturamento do mês
                self.cron_em_curso += 1
                for (cid,) in db.execute("SELECT id FROM clientes WHERE ativo=1 AND id>0 ORDER BY id").fetchall():
                    self.enfileirar("fatura", cid, t)
                self.cron_trabalho_ms += 2000.0
        except sqlite3.Error:
            pass

    # ---------- a sonda da operação ----------
    SONDA = {"login": {"login": "monitoramento"}, "catalogo": {"categoria": "mercearia", "pagina": 1}, "busca": {"termo": "arroz"},
             "produto": {"produto": 1}, "carrinho": {"produto": 1, "quantidade": "1"}, "frete": {"cep": "30140-071"},
             "pedido": {"itens": [(1, "1")], "cep": "30140-071"}, "pagamento": {"pedido": 1}, "relatorio": {}, "exportacao": {},
             "notas": {}, "conta": {"telefone": "31 3000-0000", "nome_fantasia": "Monitoramento"}}

    def sondar(self, t):
        falhas = 0
        for rota in ROTAS:
            estado, _, _ = self.chamar(t, rota, self.SONDA[rota], 0, 0, simulacao=True)
            if estado == "erro":
                falhas += 1
        self.m["sonda"] = len(ROTAS)
        self.m["sonda_falhas"] = falhas
        self.sonda_falhas_seguidas = self.sonda_falhas_seguidas + 1 if falhas >= len(ROTAS) // 2 else 0

    # ---------- o fim do minuto ----------
    def _zerar_minuto(self):
        n = len(ROTAS)
        self._ri = {r: i for i, r in enumerate(ROTAS)}
        self._x = Execucao()
        self._x.db, self._x.cod, self._x.produto, self._x.mes = self.db, self.cod, self, 0
        self.m = {"req": [0] * n, "erro": [0] * n, "recusa": [0] * n, "lat": [0.0] * n, "lats": [[] for _ in range(n)],
                  "cli": [set() for _ in range(n)], "frete_reg": [0] * 6, "frete_reg_erro": [0] * 6, "pag_ok": 0, "pag_recusa": 0,
                  "pag_pedidos": set(), "carrinho_fechado": 0, "sonda": 0, "sonda_falhas": 0}
        self.cpu_ms = 0.0
        self.db.instr = self.db.consultas = self.db.escritas = 0

    def fechar_minuto(self, t, cal):
        """Fecha as contas do minuto: métricas por rota, processador, memória, disco, fila."""
        m = self.m
        db = self.db
        rotas = {}
        for i, r in enumerate(ROTAS):
            n = m["req"][i]
            lats = m["lats"][i]
            if lats:
                lats.sort()
                p95 = lats[min(len(lats) - 1, int(0.95 * len(lats)))]
                media = m["lat"][i] / n
            else:
                p95 = media = 0.0
            cli = m["cli"][i]
            rotas[r] = (n, m["erro"][i], m["recusa"][i], media, p95, len(cli))
            acc = self._lat_hora[r]
            acc[0] += media
            acc[1] += 1
        if cal.minuto % 60 == 59:
            for r in ROTAS:
                acc = self._lat_hora[r]
                if acc[1]:
                    self.historico_latencia[r].append(acc[0] / acc[1])
                self._lat_hora[r] = [0.0, 0]
        cpu_ms = self.cpu_ms + self.cron_trabalho_ms
        self.cron_trabalho_ms = 0.0
        cpu = min(100.0, cpu_ms / 600.0 + 2.0)
        self.rho = cpu / 100.0
        # a memória do processo: o que ele guarda agora
        self.memoria = 410.0 + 0.30 * len(self.cache_sessoes) + 0.004 * self.fila_pendentes + 0.004 * len(self.erros) + 0.0004 * db.instr
        reinicios = self.reinicios_min
        if self.memoria > MEMORIA_LIMITE_MB and t >= self.no_ar_ate:
            self.no_ar_ate = t + 2                       # o sistema mata o processo e o supervisor o levanta de novo
            self.cache_sessoes = {}
            reinicios += 1
            self.erros.append((t, "processo", "guardar_sessao", "MemoryError"))
        con = db.con
        paginas = con.execute("PRAGMA page_count").fetchone()[0]
        livres = con.execute("PRAGMA freelist_count").fetchone()[0]
        ocupadas = paginas - livres
        if cal.minuto == 0:
            r = con.execute("SELECT MAX(id) FROM auditoria").fetchone()[0]
            if r is not None:
                self.primeira_auditoria_do_dia.append((t, r))
            self.paginas_dia.append((t, ocupadas))
        try:
            fila_mais_velha = con.execute("SELECT MIN(criado_em) FROM trabalhos WHERE estado='pendente'").fetchone()[0]
            sem_estoque = con.execute("SELECT COUNT(*) FROM produtos WHERE estoque < 1").fetchone()[0]
            pedidos = con.execute("SELECT COUNT(*), COALESCE(SUM(valor), 0), COALESCE(SUM(itens), 0) FROM pedidos WHERE t=?", (t,)).fetchone()
            pedidos_reg = con.execute("SELECT c.regiao, COUNT(*) FROM pedidos p JOIN clientes c ON c.id = p.cliente WHERE p.t=? GROUP BY c.regiao", (t,)).fetchall()
            pedidos_plano = con.execute("SELECT c.plano, COUNT(*) FROM pedidos p JOIN clientes c ON c.id = p.cliente WHERE p.t=? GROUP BY c.plano", (t,)).fetchall()
        except sqlite3.Error:
            fila_mais_velha, sem_estoque, pedidos, pedidos_reg, pedidos_plano = None, 0, (0, 0.0, 0), [], []
        saida = {
            "rotas": rotas,
            "cpu": cpu,
            "memoria": self.memoria,
            "reinicios": reinicios,
            "paginas": ocupadas,
            "livre_paginas": self.volume_paginas - paginas + livres,
            "consultas": db.consultas,
            "escritas": db.escritas,
            "instrucoes": db.instr,
            "fila": (self.fila_pendentes, self.fila_concluidos, self.fila_falhas,
                     (t - fila_mais_velha) if fila_mais_velha is not None else 0),
            "emails": (self.emails_ok, self.emails_falha),
            "notas": (self.notas_ok, self.notas_falha),
            "faturas_emitidas": self.faturas_emitidas,
            "gateway": (m["req"][self._ri["pagamento"]], m["pag_recusa"]),
            "frete_reg": (m["frete_reg"], m["frete_reg_erro"]),
            "sonda": (m["sonda"], m["sonda_falhas"]),
            "cron": (self.cron_em_curso, self.cron_linhas),
            "repostas": self.repostas,
            "sem_estoque": sem_estoque,
            "pedidos": pedidos,
            "pedidos_reg": pedidos_reg,
            "pedidos_plano": pedidos_plano,
            "pag": (m["pag_ok"], len(m["pag_pedidos"]), m["pag_recusa"]),
            "lentas": sum(1 for x in self.lentas if x[0] == t),
        }
        self.janela.append((t, rotas, m["sonda_falhas"]))
        self.reinicios_min = 0
        self.fila_concluidos = self.fila_falhas = self.emails_ok = self.emails_falha = self.notas_ok = self.notas_falha = 0
        self.faturas_emitidas = 0
        self.cron_linhas = 0
        self.repostas = 0
        self._zerar_minuto()
        return saida

    # ---------- o que o monitoramento lê ----------
    def erros_na_janela(self, rota, minutos):
        req = err = 0
        i = self._ri[rota]
        for item in list(self.janela)[-minutos:]:
            v = item[1][rota]
            req += v[0]
            err += v[1]
        return req, err

    def latencia_na_janela(self, rota, minutos):
        vals = [item[1][rota][3] for item in list(self.janela)[-minutos:]]
        return sum(vals) / len(vals) if vals else 0.0

    def latencia_habitual(self, rota):
        h = self.historico_latencia[rota]
        if len(h) < 24:
            return None
        v = sorted(h)
        return v[len(v) // 2]

    def ligar(self, con):
        con.execute("SELECT name FROM sqlite_master").fetchall()     # lê o esquema antes de o contador de instruções ligar
        self.db.ligar(con)
        self._aplicar_volume()
        self._x = Execucao()
        self._x.db, self._x.cod, self._x.produto, self._x.mes = self.db, self.cod, self, 0

    def __getstate__(self):
        d = dict(self.__dict__)
        d["cod"] = None
        d["_x"] = None
        return d

    def __setstate__(self, d):
        self.__dict__.update(d)
        self._resolver()


# ---------------------------------------------------------------------------------------------------- o ambiente de ensaio da qualidade
class Ensaio:
    """Um banco pequeno com dados conhecidos, para rodar os testes contra um código candidato."""
    _desempenho = None

    def __init__(self, codigo_candidato):
        self.cod = {f: codigo.IMPLEMENTACOES[f][v] for f, v in codigo_candidato.items()}
        produtos = []
        for i in range(45):
            nome = ["arroz", "feijão", "açúcar", "café", "farinha"][i % 5] + f" ensaio {i:02d}"
            produtos.append((nome, _sem_acento(nome), "mercearia", 10.0 + i, 500, 500, 1.0))
        for i in range(12):
            nome = ["detergente", "sabão em pó", "esponja"][i % 3] + f" ensaio {i:02d}"
            produtos.append((nome, _sem_acento(nome), "limpeza", 5.0 + i, 500, 500, 0.5))
        clientes = [(1, "Loja Ensaio", "Loja Ensaio Ltda", "pro", "30140-071", "MG", 2, "31 3333-0000", 0, 1),
                    (2, "Mercado Ensaio", "Mercado Ensaio Ltda", "básico", "80010-000", "PR", 5, None, 0, 1),
                    (3, "Empório Ensaio", "Empório Ensaio Ltda", "pro", "40020-000", "BA", 3, "71 3333-0000", 0, 1),
                    (4, None, "Comércio Ensaio Ltda", "básico", "01310-100", "SP", 0, "11 3333-0000", 0, 1)]
        usuarios = [(1, 1, "maria.ensaio"), (2, 1, "joão.ensaio"), (3, 2, "ana.ensaio"), (4, 3, "pedro.ensaio"), (5, 4, "luís.ensaio")]
        self.con = criar_banco(produtos, clientes, usuarios)
        self.db = Banco(self.con)
        self._prep()

    def _prep(self):
        x = Execucao()
        x.db, x.cod, x.produto, x.mes = self.db, self.cod, self, 0
        self.x = x
        self.gateway = self.frete = self.antifraude = _ForaDeEnsaio()
        self.cache_sessoes = {}
        self.tokens = 0

    def novo_token(self):
        self.tokens += 1
        return f"e{self.tokens}"

    def enfileirar(self, tipo, ref, t):
        return None

    def rota(self, rota, req, cliente=1, usuario=1):
        x = self.x
        x.t, x.cliente, x.usuario, x.simulacao, x.trab, x.ext = 5000, cliente, usuario, False, 0, 0.0
        return codigo.ROTAS_CODIGO[rota](x, req)

    def trabalho(self, tipo, ref):
        x = self.x
        x.t, x.cliente, x.usuario, x.simulacao, x.trab, x.ext = 5000, 0, 0, False, 0, 0.0
        codigo.TRABALHOS_CODIGO[tipo](x, ref)

    def desempenho(self, rota, req, limite_instrucoes, limite_consultas):
        base = Ensaio._banco_de_desempenho()
        db = Banco(base)
        x = Execucao()
        x.db, x.cod, x.produto, x.mes = db, self.cod, self, 0
        x.t, x.cliente, x.usuario, x.simulacao, x.trab, x.ext = 60 * MINUTOS_DIA, 1, 1, True, 0, 0.0
        codigo.ROTAS_CODIGO[rota](x, req)
        base.set_progress_handler(None, 10)
        assert db.instr <= limite_instrucoes, f"{db.instr} dezenas de instruções"
        assert db.consultas <= limite_consultas, f"{db.consultas} consultas"

    @staticmethod
    def _banco_de_desempenho():
        """Um banco de ensaio grande (30 mil pedidos), montado uma vez e só lido."""
        if Ensaio._desempenho is None:
            con = criar_banco([("arroz ensaio", "arroz ensaio", "mercearia", 10.0, 9999, 9999, 1.0)],
                              [(c, f"Loja {c}", f"Loja {c} Ltda", "pro", "30140-071", "MG", 2, None, 0, 1) for c in range(1, 201)],
                              [(1, 1, "maria.ensaio")])
            linhas = []
            itens = []
            for i in range(30000):
                linhas.append((i + 1, 1 + (i * 7) % 200, 1, 50.0, 2, "pago", "30140-071", 60 * MINUTOS_DIA - (i * 3) % (90 * MINUTOS_DIA)))
                itens.append((i + 1, 1, 2, 25.0))
            con.executemany("INSERT INTO pedidos (id, cliente, usuario, valor, itens, estado, cep, t) VALUES (?,?,?,?,?,?,?,?)", linhas)
            con.executemany("INSERT INTO itens_pedido (pedido, produto, quantidade, preco) VALUES (?,?,?,?)", itens)
            Ensaio._desempenho = con
        return Ensaio._desempenho


def rodar_testes(codigo_candidato, componente, sorte, cobertura, todos=False):
    """A qualidade roda os testes do componente contra o código candidato. Cada teste roda com probabilidade `cobertura` (todos, se
    `todos`). Devolve (testes executados, [(função, teste, mensagem)] dos que falharam)."""
    testes = codigo.testes_do_componente(componente)
    escolhidos = [tt for tt in testes if todos or sorte.random() < cobertura]
    if not escolhidos:
        return 0, []
    ensaio = Ensaio(codigo_candidato)
    falhas = []
    for funcao, nome, f, tipo in escolhidos:
        try:
            f(ensaio)
        except Exception as e:
            falhas.append((funcao, nome, f"{type(e).__name__}: {e}"))
    ensaio.con.close()
    return len(escolhidos), falhas
