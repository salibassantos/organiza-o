"""A classe Mundo: a porta entre a empresa e quem a observa (ver CONTRATO.md).

O mundo é a empresa inteira acontecendo no tempo: o relógio, o produto no ar com o seu banco, a fila e o disco, o repositório de
versões, o fluxo de trabalho, o CRM, a agenda, o quadro de pessoal, os clientes e as 50 pessoas. Cada chamada de passo() faz
acontecer um minuto (as pessoas agem, os clientes batem no produto, o código roda, os bancos mudam) e devolve as medidas de cada
processo naquele minuto. O mundo só anda quando passo() é chamado.

Uso:
    from organizacao.mundo.v1 import Mundo
    m = Mundo(1)
    for p in m.processos(): ...
    valores = m.passo()          # o minuto 1
    m.salvar("pasta"); m2 = Mundo.carregar("pasta")
"""
import os
import pickle
import sqlite3
from dataclasses import dataclass, field

from .cadastro import EQUIPES, PLANOS, MINUTOS_DIA, sorteio
from .relogio import Relogio
from .clientes import Clientes
from .produto import Produto
from .fluxo import Fluxo
from .repositorio import Repositorio
from .crm import CRM
from .agenda import Agenda
from .quadro import Quadro
from .verdade import Verdade
from .atos import Porta
from .pessoas import Empresa, VALOR_PLANO, COMPONENTES_SQUAD, TEMAS
from .conectores import Conectores

NULOS = (None, "sem_defeito", "embaralhado", "sem_deriva", "surdo")
PAGINAS_POR_CLIENTE_DIA = 0.62       # o crescimento do banco por cliente por dia que a operação estimou ao montar o volume
BANCOS = ("produto", "fluxo", "repositorio", "crm", "agenda", "quadro")


@dataclass(frozen=True)
class Processo:
    nome: str
    campos: list = field(default_factory=list)


class Mundo:
    def __init__(self, semente: int, nulo: str | None = None, tempo_real: bool = False):
        if nulo not in NULOS:
            raise ValueError(f"nulo desconhecido: {nulo}; os nulos são {', '.join(n for n in NULOS if n)}")
        self.semente = int(semente)
        self.nulo = nulo
        self.relogio = Relogio(self.semente, embaralhado=(nulo == "embaralhado"), tempo_real=tempo_real)
        partida = sorteio(self.semente, "partida")
        self.clientes = Clientes(self.semente, partida.randint(380, 440), nulo)
        regs, usuarios = self.clientes.registros_iniciais
        self.clientes.registros_iniciais = ([], [])
        folga = partida.uniform(9.0, 24.0)
        self.produto = Produto(self.semente, regs, usuarios, PAGINAS_POR_CLIENTE_DIA * len(regs), folga)
        self.clientes.categorias = list(self.produto.categorias)
        self.clientes.n_produtos = len(self.produto.produtos_iniciais)
        palavras = sorted({w for nome, *_ in self.produto.produtos_iniciais for w in nome.split() if len(w) > 3 and not w[0].isdigit()})
        self.clientes.palavras = palavras
        self.fluxo = Fluxo()
        self.repo = Repositorio()
        self.crm = CRM()
        self.agenda = Agenda()
        self.quadro = Quadro()
        self.registro = Verdade(self.semente, nulo)
        self.registro.volume_inicial_folga_dias = round(folga, 1)
        self.porta = Porta(surdo=(nulo == "surdo"))
        self.eventos = []
        self.sis = {"produto": self.produto, "fluxo": self.fluxo, "repo": self.repo, "crm": self.crm, "agenda": self.agenda,
                    "quadro": self.quadro, "clientes": self.clientes, "verdade": self.registro, "porta": self.porta,
                    "eventos": self.eventos, "relogio": self.relogio, "estornos": [0]}
        self.empresa = Empresa(self.semente, nulo, self.sis)
        self.conectores = Conectores()
        self.mercado = sorteio(self.semente, "mercado")
        self.indicacoes = []
        self.proximo_dia_vivido = 0
        self.sorte_dia = sorteio(self.semente, "dias vividos")
        self._estado_inicial()
        self._processos = [Processo(n, list(c)) for n, c in self.conectores.processos]

    # ======================================================================================================== a porta
    @property
    def t(self):
        return self.relogio.t

    def dia(self):
        return self.relogio.dia()

    def minuto_do_dia(self):
        return self.relogio.minuto_do_dia()

    def dia_da_semana(self):
        return self.relogio.dia_da_semana()

    def processos(self):
        return [Processo(p.nome, list(p.campos)) for p in self._processos]

    def equipes(self):
        return list(EQUIPES)

    def passo(self):
        rel = self.relogio
        novo_dia = rel.avancar()
        t = rel.t
        cal = rel.cal
        rel.esperar()
        sis = self.sis
        self.porta.materializar(t, cal, sis)
        if novo_dia:
            if not rel.embaralhado or t >= self.proximo_dia_vivido:
                self._dia_vivido(t, cal)
                if rel.embaralhado:
                    self.proximo_dia_vivido = t + self.sorte_dia.randint(720, 2160)
            self._nova_data(t, cal)
        if cal.minuto % 60 == 5:
            self._automacoes(t)
        prod = self.produto
        prod.agendadas(t, cal)
        prod.processar_fila(t, cal.mes)
        self.clientes.minuto(t, cal, prod, self.fluxo, self.registro, rel.embaralhado)
        self._mercado(t, cal)
        self.empresa.minuto(t, cal)
        self.porta.expirar(t, sis)
        prod.sondar(t)
        erros = []
        for e in reversed(prod.erros):
            if e[0] != t:
                break
            erros.append(e)
        if erros:
            self.registro.erros_do_minuto(t, erros)
        contas = prod.fechar_minuto(t, cal)
        self.registro.minuto_da_sonda(t, contas["sonda"][1] >= 6, prod)
        self.registro.latencia(t, cal, contas["rotas"])
        return self.conectores.ler(t, cal, self, contas)

    def receber(self, equipe: str, tipo: str, texto: str) -> int:
        return self.porta.receber(equipe, tipo, texto)

    def respostas(self):
        return self.porta.respostas()

    def verdade(self) -> dict:
        """Só para a bancada: o que a empresa tem e quando aconteceu, até o minuto atual."""
        return self.registro.como_dict(self.relogio, self.relogio.embaralhado)

    def eventos_humanos(self):
        return list(self.eventos)

    # ======================================================================================================== pausa e retomada
    def _bancos(self):
        return {"produto": self.produto.db.con, "fluxo": self.fluxo.db, "repositorio": self.repo.db, "crm": self.crm.db,
                "agenda": self.agenda.db, "quadro": self.quadro.db}

    def salvar(self, pasta):
        os.makedirs(pasta, exist_ok=True)
        for nome, con in self._bancos().items():
            caminho = os.path.join(pasta, nome + ".sqlite")
            if os.path.exists(caminho):
                os.remove(caminho)
            destino = sqlite3.connect(caminho)
            con.backup(destino)
            destino.close()
        with open(os.path.join(pasta, "estado.pickle"), "wb") as f:
            pickle.dump(self, f, protocol=pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def carregar(pasta):
        with open(os.path.join(pasta, "estado.pickle"), "rb") as f:
            m = pickle.load(f)
        cons = {}
        for nome in BANCOS:
            mem = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False,
                                  cached_statements=0 if nome == "produto" else 128)
            origem = sqlite3.connect(os.path.join(pasta, nome + ".sqlite"))
            origem.backup(mem)
            origem.close()
            cons[nome] = mem
        m.produto.ligar(cons["produto"])
        m.fluxo.ligar_banco(cons["fluxo"])
        m.repo.db = cons["repositorio"]
        m.crm.ligar_banco(cons["crm"])
        m.agenda.db = cons["agenda"]
        m.quadro.db = cons["quadro"]
        return m

    def __getstate__(self):
        return dict(self.__dict__)

    # ======================================================================================================== o que move o mundo de fora
    def _nova_data(self, t, cal):
        """A folhinha virou: planos de presença, agenda, contadores do dia."""
        self.empresa.nova_data(t, cal)
        self.clientes.nova_data(t, cal)
        self.agenda.podar(t, cal, self.relogio.embaralhado)
        self.conectores.novo_dia()
        self.registro.nova_data(t, cal)

    def _automacoes(self, t):
        """A automação do fluxo, de hora em hora: chamado resolvido há dois dias se fecha sozinho."""
        for r in self.fluxo.db.execute("SELECT id FROM itens WHERE projeto='SUP' AND tipo='chamado' AND estado='resolvido' AND resolvido_em < ? ORDER BY id",
                                       (t - 2 * MINUTOS_DIA,)).fetchall():
            self.fluxo.transitar(t, r[0], "fechado", "atendimento")
            self.clientes.chamado_fechado(t, r[0])

    def _dia_vivido(self, t, cal):
        """Uma vez por dia vivido: o que tem taxa por dia (doença, demissão, cancelamento, indicação)."""
        self.empresa.dia_vivido(t, cal)
        self.clientes.dia_vivido(t, cal, self.produto, self.registro)
        self.registro.dia_vivido(t, self.clientes.ativos())
        # as indicações do dia: clientes satisfeitos indicam a plataforma a conhecidos
        self.indicacoes = []
        if cal.util:
            n = self.clientes.ativos()
            sats = [self.clientes.info[c]["satisfacao"] for c in range(1, self.clientes.n + 1) if self.clientes.info[c]["ativo"]]
            media = sum(sats) / len(sats) if sats else 0.7
            esperado = 0.6 * n / 400.0 * (media / 0.8) ** 2
            k = int(esperado) + (1 if self.mercado.random() < esperado - int(esperado) else 0)
            for _ in range(k):
                self.indicacoes.append(t + self.mercado.randint(8 * 60, 18 * 60) - cal.minuto)
            self.indicacoes.sort()

    def _mercado(self, t, cal):
        """Os leads que chegam pelo site (mais no horário comercial, proporcionais ao tamanho da carteira) e as indicações."""
        s = self.mercado
        n = self.clientes.ativos() if t % 60 == 0 or not hasattr(self, "_n_cache") else self._n_cache
        self._n_cache = n
        lam = (0.0019 if (cal.util and 8 * 60 <= cal.minuto < 20 * 60) else 0.0003) * n / 400.0
        if s.random() < lam:
            plano = _plano(s)
            self.crm.novo(t, "site", plano, VALOR_PLANO[plano], proxima=t + s.randint(10, 180))
        while self.indicacoes and self.indicacoes[0] <= t:
            self.indicacoes.pop(0)
            plano = _plano(s)
            self.crm.novo(t, "indicação", plano, VALOR_PLANO[plano], proxima=t + s.randint(10, 120))

    def _estado_inicial(self):
        """A empresa já existe no instante 0: backlog, sprints anteriores, funil de vendas, épicos em curso."""
        s = sorteio(self.semente, "estado inicial")
        fluxo = self.fluxo
        emp = self.empresa
        for projeto in ("PROD", "PLAT"):
            comps = COMPONENTES_SQUAD[projeto]
            for estado, n in (("backlog", 14), ("refinamento", 5), ("pronto para desenvolver", 16)):
                for _ in range(n):
                    comp = s.choice(comps)
                    tipo = "história" if s.random() < 0.8 else "tarefa"
                    est = estado if tipo == "história" or estado != "refinamento" else "backlog"
                    fluxo.criar(-s.randint(60, 40 * MINUTOS_DIA), projeto, tipo, s.choice(TEMAS[comp]),
                                prioridade=s.choice(("baixa", "média", "média", "média", "alta")), componente=comp,
                                equipe="desenvolvimento", ator="produto", pontos=s.choice((1, 2, 3, 3, 5, 8)), estado=est)
            for _ in range(3):
                comp = s.choice(comps)
                fluxo.criar(-s.randint(60, 20 * MINUTOS_DIA), projeto, "bug", f"comportamento estranho em {comp}", prioridade="média",
                            componente=comp, equipe="desenvolvimento", ator="atendimento", pontos=s.choice((1, 2)),
                            estado="pronto para desenvolver", origem="atendimento")
            # o primeiro épico do roteiro, já refinado
            emp._fim_epico_roteiro(None, {"projeto": projeto}, 0, None)
            ep = emp.epico_ativo[projeto]
            historias = fluxo.itens(projeto=projeto, tipo="história", extra=f" AND epico={ep}")
            for i, r in enumerate(historias):
                # o épico já vinha andando: as primeiras histórias foram liberadas antes da criação
                feita = i < len(historias) - 3 and r["id"] not in emp.func_historia
                fluxo.transitar(0, r["id"], "liberado" if feita else "pronto para desenvolver", "produto")
        for _ in range(5):
            fluxo.criar(-s.randint(60, 30 * MINUTOS_DIA), "INFRA", "tarefa", s.choice(TEMAS["infra"]), prioridade="média",
                        componente="infra", equipe="operação", ator="operação", pontos=s.choice((1, 2, 3)))
        execs = [p for p in emp.pessoas if p.papel == "executivo de vendas"]
        for estagio, n in (("lead", 6), ("qualificação", 5), ("proposta", 5), ("negociação", 4)):
            for i in range(n):
                plano = _plano(s)
                nid = self.crm.novo(-s.randint(60, 20 * MINUTOS_DIA), s.choice(("site", "site", "indicação", "prospecção")), plano,
                                    VALOR_PLANO[plano], estagio=estagio, proxima=s.randint(9 * 60, 3 * MINUTOS_DIA))
                if estagio != "lead":
                    self.crm.assumir(nid, execs[i % len(execs)].id)


def _plano(s):
    r = s.random()
    return "básico" if r < 0.55 else ("pro" if r < 0.87 else "empresarial")

