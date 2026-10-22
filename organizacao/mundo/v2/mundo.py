"""A classe Mundo (v2): a porta entre a empresa e quem a observa (ver CONTRATO.md).

O mundo é a empresa inteira acontecendo no tempo: o relógio, o produto no ar com o seu banco, a fila e o disco, o repositório de
versões, o fluxo de trabalho, o CRM, a agenda, o quadro de pessoal, os clientes, as 50 pessoas e as sete equipes como agentes. Cada
chamada de passo() faz acontecer um minuto e devolve as medidas de cada processo naquele minuto.

O mundo é uma função determinística da semente e da sequência de entradas recebidas (atos pela porta e campanhas injetadas, cada um
no seu instante). De qualquer estado salvo, alimentado com outra sequência, ele anda por outro caminho, sempre o mesmo para a mesma
sequência. A verdade por minuto e os registros fechados vão para uma pasta de história, um arquivo por dia.

Uso:
    from organizacao.mundo.v2 import Mundo
    m = Mundo(1)
    for p in m.processos(): ...          # nome, campos, equipe, resolução por campo
    valores = m.passo()                  # o minuto 1
    m.salvar("pasta"); m2 = Mundo.carregar("pasta")
"""
import os
import pickle
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass, field

import numpy as np

from .cadastro import EQUIPES, PLANOS, MINUTOS_DIA, sorteio
from .relogio import Relogio
from .clientes import Clientes
from .produto import Produto
from .fluxo import Fluxo
from .repositorio import Repositorio
from .crm import CRM
from .agenda import Agenda
from .quadro import Quadro
from .verdade import Verdade, COLUNAS, COL, COMPONENTES_COM_CODIGO, FASES_DERIVA
from .atos import Porta
from .pessoas import Empresa, VALOR_PLANO, COMPONENTES_SQUAD, TEMAS
from .conectores import Conectores
from .ouvinte import Ouvinte, Painel
from . import opcoes as _opcoes
from . import codigo

NULOS = (None, "sem_defeito", "embaralhado", "sem_deriva", "surdo", "paciente")
HORIZONTE_RAMO = 28 * MINUTOS_DIA    # (v2.2) o ramo sem ato anda até o defeito sair ou até 28 dias depois de ele ter entrado no ar
PAGINAS_POR_CLIENTE_DIA = 0.62       # o crescimento do banco por cliente por dia que a operação estimou ao montar o volume
BANCOS = ("produto", "fluxo", "repositorio", "crm", "agenda", "quadro")
TETO_MAXIMO = 2.6                    # o mercado nunca passa de 2,6 vezes o teto inicial: a carteira não cresce sem limite
LARGURA_SATURACAO = 0.10             # a chegada de leads começa a secar a 10% do teto
LIMIAR_PLATO = 0.965                 # a carteira entra no platô quando passa de 96,5% do teto
ONDE_CAMPANHA = ([["sessões dos clientes", "sessões iniciadas no minuto"], ["sessões dos clientes", "sessões ativas"],
                  ["sessões dos clientes", "usuários conectados"], ["rota catálogo", "requisições no minuto"],
                  ["rota catálogo", "latência média em ms"], ["rota busca", "requisições no minuto"], ["rota produto", "requisições no minuto"],
                  ["pedidos", "pedidos criados no minuto"], ["projeto Suporte: movimento", "chamados novos no minuto"],
                  ["chamados de catálogo e busca", "novos no minuto"], ["leads de site", "novos no minuto"], ["funil de vendas", "leads"]]
                 + [[f"clientes do plano {p}", "sessões ativas"] for p in PLANOS])


def equipe_do_processo(nome):
    """A equipe responsável por cada processo."""
    n = nome.lower()
    for eq in EQUIPES:
        if n.endswith("equipe de " + eq):
            return eq
    if n.startswith(("rota ", "servidor", "banco", "fila", "gateway", "transportadoras", "sonda", "implantação", "tarefas agendadas",
                     "e-mails", "projeto infraestrutura", "pedidos", "pagamentos", "notas fiscais", "estoque", "sessões")):
        return "operação"
    if n.startswith(("região", "carteira", "clientes do plano", "pesquisa", "canal de atendimento", "projeto suporte", "chamados de")):
        return "atendimento"
    if n.startswith(("projeto produto", "épicos")):
        return "produto"
    if n.startswith(("projeto plataforma", "bugs de", "repositório", "código de")):
        return "desenvolvimento"
    if n.startswith(("funil", "atividades de vendas", "leads")):
        return "vendas"
    return "gestão"


def resolucao_do_campo(campo):
    """O menor passo que o campo pode dar (a quantização com que ele sai pela porta)."""
    c = campo.lower()
    if "em ms" in c or "em %" in c or "em horas" in c or "em milhares" in c:
        return 0.1
    if c == "memória em uso em mb":
        return 0.1
    if "em mb" in c or "em reais" in c or c == "horas extras no dia":
        return 0.01
    return 1.0


@dataclass(frozen=True)
class Processo:
    nome: str
    campos: list = field(default_factory=list)
    equipe: str = "gestão"
    resolucao: list = field(default_factory=list)


class Mundo:
    def __init__(self, semente: int, nulo: str | None = None, tempo_real: bool = False, historia: str | None = None,
                 porta: bool | None = None, relogio: bool | None = None, agenda_calada=None):
        if nulo not in NULOS:
            raise ValueError(f"nulo desconhecido: {nulo}; os nulos são {', '.join(n for n in NULOS if n)}")
        self.semente = int(semente)
        self.nulo = nulo
        self.relogio = Relogio(self.semente, embaralhado=(nulo == "embaralhado"), tempo_real=tempo_real)
        # (v2.3) as opções, desligadas por padrão (ver opcoes.py)
        self.opcoes = _opcoes.ler(porta, relogio, agenda_calada)
        if self.opcoes["agenda_calada"]:
            self.relogio.feriados = _opcoes.datas_do_feriado(self.opcoes["agenda_calada"])
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
        pasta = historia or tempfile.mkdtemp(prefix="mundo_v2_historia_")
        self.registro = Verdade(self.semente, nulo, pasta)
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
        # (v2) o teto do mercado: a deriva cresce, assenta num platô e pode voltar a crescer
        self.sorte_teto = sorteio(self.semente, "teto do mercado")
        n0 = self.clientes.ativos()
        self.teto = 0 if nulo == "sem_deriva" else int(round(n0 * self.sorte_teto.uniform(1.08, 1.15)))
        self.teto_inicial = self.teto
        self.registro.teto_inicial = self.teto or None
        self.fase = "crescendo"
        self.decidir_em = None
        self.expansao = None                     # (vale a partir de, teto novo)
        self.saturacao = 1.0
        # (v2) as campanhas injetadas: entradas do mundo como os atos
        self.campanhas = []
        self.campanha_forca = 0.0
        # (v2.2) os ramos sem ato: o estado guardado logo antes do primeiro ato que chegou com um defeito no ar
        self.campanhas_injetadas = []            # (injetada_em, inicio, duracao, forca), para repetir as campanhas nos ramos
        self.ramos = []                          # {"t", "estado", "bancos", "eps"}
        self.com_ramos = True
        self._estado_inicial()
        self._processos = [Processo(n, list(c), equipe_do_processo(n), [resolucao_do_campo(x) for x in c])
                           for n, c in self.conectores.processos + _opcoes.processos_novos(self.opcoes)]
        # (v2.2) o ouvinte da porta e o painel que as equipes olham quando lhes pedem um campo
        self.porta.ouvinte = Ouvinte(self._processos)
        self.painel = Painel(self._processos)
        self.sis["painel"] = self.painel

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
        return [Processo(p.nome, list(p.campos), p.equipe, list(p.resolucao)) for p in self._processos]

    def equipes(self):
        return list(EQUIPES)

    def passo(self):
        if self.registro.ramos_a_calcular:
            self._calcular_ramos()
        if self.com_ramos and self.registro.no_ar and (self.porta.chegando or self.porta.abertos()):
            self._guardar_ramo()
        rel = self.relogio
        novo_dia = rel.avancar()
        t = rel.t
        cal = rel.cal
        rel.esperar()
        sis = self.sis
        if rel.blocos:
            for b in rel.blocos:
                self.registro.bloco_do_calendario(b)
            rel.blocos.clear()
        self._campanha(t)
        self.porta.materializar(t, cal, sis, self.empresa.equipes)
        if novo_dia:
            if not rel.embaralhado or t >= self.proximo_dia_vivido:
                self._dia_vivido(t, cal)
                if rel.embaralhado:
                    self.proximo_dia_vivido = t + self.sorte_dia.randint(720, 2160)
            self._nova_data(t, cal)
        if cal.minuto % 60 == 5:
            self._automacoes(t)
        if t % MINUTOS_DIA == 30 and (t // MINUTOS_DIA) % 7 == 6:
            self._arquivar(t)
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
        saida = self.conectores.ler(t, cal, self, contas)
        if self.opcoes["porta"] or self.opcoes["relogio"]:
            _opcoes.ler_minuto(self, t, saida)
        self.porta.textos_do_minuto.clear()
        self.painel.guardar(t, saida)
        self.registro.linha(t, self._linha_da_verdade(t, cal, contas))
        if t % MINUTOS_DIA == MINUTOS_DIA - 1:
            self.registro.fechar_dia(t, self.eventos)
            self.eventos.clear()
        return saida

    def receber(self, equipe: str, tipo: str, texto: str) -> int:
        return self.porta.receber(equipe, tipo, texto)

    def respostas(self):
        return self.porta.respostas()

    def injetar_campanha(self, inicio: int, duracao: int = MINUTOS_DIA, forca: float = 1.0):
        """(v2) Um dia de campanha: mexe ao mesmo tempo nas sessões, na rota do catálogo, nos chamados e no funil, de inicio a
        inicio + duracao. É uma entrada do mundo como os atos: entra no caminho e fica na verdade (início, fim, força, onde)."""
        inicio, duracao = int(inicio), int(duracao)
        if inicio <= self.t:
            raise ValueError(f"a campanha precisa começar depois do minuto atual ({self.t})")
        if duracao <= 0 or not (0.0 < forca <= 3.0):
            raise ValueError("a duração precisa ser positiva e a força estar entre 0 e 3")
        self.campanhas.append({"inicio": inicio, "fim": inicio + duracao, "forca": float(forca), "anotada": False})
        self.campanhas_injetadas.append((self.t, inicio, duracao, float(forca)))
        self.campanhas.sort(key=lambda c: (c["inicio"], c["fim"]))

    def verdade(self) -> dict:
        """Só para a bancada: o que a empresa tem e quando aconteceu, até o minuto atual."""
        if self.registro.ramos_a_calcular:
            self._calcular_ramos()
        v = self.registro.como_dict(self.relogio, self.relogio.embaralhado)
        v.update(_opcoes.para_a_verdade(self))
        return v

    def verdade_por_minuto(self, inicio: int = 0, fim: int | None = None):
        """Só para a bancada: a verdade minuto a minuto entre inicio e fim (instantes, matriz, nomes das colunas)."""
        return self.registro.por_minuto(inicio, self.t if fim is None else fim)

    def eventos_humanos(self):
        _, gravados = self.registro.ler_disco()
        return gravados + list(self.eventos)

    def pasta_da_historia(self):
        return self.registro.pasta

    # ======================================================================================================== pausa, retomada e ramos
    def _bancos(self):
        return {"produto": self.produto.db.con, "fluxo": self.fluxo.db, "repositorio": self.repo.db, "crm": self.crm.db,
                "agenda": self.agenda.db, "quadro": self.quadro.db}

    def salvar(self, pasta):
        """Guarda o estado inteiro em `pasta`: os seis bancos, o estado em memória e a história até aqui (pasta/historia)."""
        os.makedirs(pasta, exist_ok=True)
        for nome, con in self._bancos().items():
            caminho = os.path.join(pasta, nome + ".sqlite")
            if os.path.exists(caminho):
                os.remove(caminho)
            destino = sqlite3.connect(caminho)
            con.backup(destino)
            destino.close()
        destino = os.path.join(pasta, "historia")
        if os.path.abspath(destino) != os.path.abspath(self.registro.pasta):
            if os.path.isdir(destino):
                shutil.rmtree(destino)
            _copiar_historia(self.registro.pasta, destino, self.registro.dias_gravados)
        with open(os.path.join(pasta, "estado.pickle"), "wb") as f:
            pickle.dump(self, f, protocol=pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def carregar(pasta, historia=None):
        """Retoma um estado salvo. Cada carga ganha a sua própria pasta de história (`historia`, ou uma pasta temporária nova), com o
        passado copiado do salvo: duas cargas do mesmo estado são dois ramos que não se misturam."""
        with open(os.path.join(pasta, "estado.pickle"), "rb") as f:
            m = pickle.load(f)
        cons = {}
        for nome in BANCOS:
            mem = _banco_em_memoria(nome)
            origem = sqlite3.connect(os.path.join(pasta, nome + ".sqlite"))
            origem.backup(mem)
            origem.close()
            cons[nome] = mem
        m._ligar_bancos(cons)
        nova = historia or tempfile.mkdtemp(prefix="mundo_v2_historia_")
        _copiar_historia(os.path.join(pasta, "historia"), nova, m.registro.dias_gravados)
        m.registro.pasta = nova
        return m

    def _ligar_bancos(self, cons):
        self.produto.ligar(cons["produto"])
        self.fluxo.ligar_banco(cons["fluxo"])
        self.repo.db = cons["repositorio"]
        self.crm.ligar_banco(cons["crm"])
        self.agenda.db = cons["agenda"]
        self.quadro.db = cons["quadro"]

    def __getstate__(self):
        return dict(self.__dict__)

    def __setstate__(self, d):
        self.__dict__.update(d)
        for k, v in (("campanhas_injetadas", []), ("ramos", []), ("com_ramos", True),     # um estado salvo antes da v2.2
                     ("opcoes", {"porta": False, "relogio": False, "agenda_calada": None})):   # ou antes da v2.3
            self.__dict__.setdefault(k, v)
        self.registro.__dict__.setdefault("ramos_a_calcular", [])
        self.registro.__dict__.setdefault("com_ramo", set())
        if "painel" not in self.__dict__:
            self.painel = Painel(self._processos)
            self.sis["painel"] = self.painel
        self.porta.__dict__.setdefault("textos_do_minuto", {})
        if getattr(self.porta, "ouvinte", None) is None:
            self.porta.ouvinte = Ouvinte(self._processos)

    # ======================================================================================================== (v2.2) os ramos sem ato
    def _guardar_ramo(self):
        """Há um ato chegando ou ainda aberto com um defeito no ar. Para cada defeito no ar que ainda não tem ramo, o estado de agora
        (o fim do minuto anterior: até aqui nenhum ato agiu desde que ele entrou no ar) é guardado: dele sai o ramo sem ato."""
        com = self.registro.com_ramo
        novos = [ep for (f, v), ep in self.registro.no_ar.items() if (f, v, ep["liberado_em"]) not in com]
        if not novos:
            return
        ramos, self.ramos = self.ramos, []
        try:
            estado = pickle.dumps(self, protocol=pickle.HIGHEST_PROTOCOL)
        finally:
            self.ramos = ramos
        bancos = {nome: con.serialize() for nome, con in self._bancos().items()}
        self.ramos.append({"t": self.t, "estado": estado, "bancos": bancos, "eps": novos})
        for ep in novos:
            com.add((ep["funcao"], ep["implementacao"], ep["liberado_em"]))

    def _calcular_ramos(self):
        """Anda cada ramo sem ato até o defeito sair (ou até o horizonte) e escreve o resultado no episódio."""
        pendentes, self.registro.ramos_a_calcular = self.registro.ramos_a_calcular, []
        for ep in pendentes:
            ramo = next((r for r in self.ramos if any(e is ep for e in r["eps"])), None)
            if ramo is None:                                   # sem estado guardado (um estado salvo antes da v2.2)
                continue
            saida, ate = self._rodar_ramo(ramo, ep)
            self.registro.ramo_calculado(ep, ramo["t"], ate, saida)
        self.ramos = [r for r in self.ramos if any(e["persistente"] is None for e in r["eps"])]

    def _rodar_ramo(self, ramo, ep):
        m = pickle.loads(ramo["estado"])
        cons = {}
        for nome, dados in ramo["bancos"].items():
            con = _banco_em_memoria(nome)
            con.deserialize(dados)
            cons[nome] = con
        m._ligar_bancos(cons)
        pasta = tempfile.mkdtemp(prefix="mundo_v2_ramo_")
        try:
            _copiar_historia(self.registro.pasta, pasta, m.registro.dias_gravados)
            m.registro.pasta = pasta
            m.relogio.tempo_real = False
            m.com_ramos = False
            m.ramos = []
            m.registro.ramos_a_calcular = []
            m.porta.surdo = True                                  # daqui em diante nenhum ato chega ao mundo
            m.porta.chegando = []
            m.porta.descartar_abertos(m.t, m.sis)                 # e os que já tinham chegado não são tratados
            for injetada, inicio, duracao, forca in self.campanhas_injetadas:
                if ramo["t"] < injetada <= ep["saiu_do_ar"] and inicio > m.t:
                    m.injetar_campanha(inicio, duracao, forca)
            chave, desde = (ep["funcao"], ep["implementacao"]), ep["liberado_em"]
            ate = desde + HORIZONTE_RAMO
            while m.t < ate:
                m.passo()
                e = m.registro.no_ar.get(chave)
                if e is None or e["liberado_em"] != desde:
                    e = next(x for x in reversed(m.registro.mem["episodios_de_defeito_no_ar"])
                             if (x["funcao"], x["implementacao"]) == chave and x["liberado_em"] == desde)
                    return (e["saiu_do_ar"], e["saiu_por"]), m.t
            return None, ate
        finally:
            for con in cons.values():
                con.close()
            shutil.rmtree(pasta, ignore_errors=True)

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
        """Uma vez por dia vivido: o que tem taxa por dia (doença, demissão, cancelamento, indicação) e o teto do mercado."""
        self.empresa.dia_vivido(t, cal)
        self.clientes.dia_vivido(t, cal, self.produto, self.registro)
        self.registro.dia_vivido(t, self.clientes.ativos())
        self._deriva(t)
        # as indicações do dia: clientes satisfeitos indicam a plataforma a conhecidos
        self.indicacoes = []
        if cal.util:
            n = self.clientes.ativos()
            media = self.clientes.satisfacao_media()
            esperado = 0.6 * n / 400.0 * (media / 0.8) ** 2 * self.saturacao
            k = int(esperado) + (1 if self.mercado.random() < esperado - int(esperado) else 0)
            for _ in range(k):
                self.indicacoes.append(t + self.mercado.randint(8 * 60, 18 * 60) - cal.minuto)
            self.indicacoes.sort()

    def _mercado(self, t, cal):
        """Os leads que chegam pelo site (mais no horário comercial, proporcionais ao tamanho da carteira) e as indicações."""
        s = self.mercado
        n = self.clientes.ativos() if t % 60 == 0 or not hasattr(self, "_n_cache") else self._n_cache
        self._n_cache = n
        lam = (0.0016 if (cal.util and 8 * 60 <= cal.minuto < 20 * 60) else 0.00025) * n / 400.0 * self.saturacao
        if self.campanha_forca:
            lam *= 1.0 + 3.0 * self.campanha_forca              # (v2) a campanha traz gente nova pelo site
        if s.random() < lam:
            plano = _plano(s)
            self.crm.novo(t, "site", plano, VALOR_PLANO[plano], proxima=t + s.randint(10, 180))
        while self.indicacoes and self.indicacoes[0] <= t:
            self.indicacoes.pop(0)
            plano = _plano(s)
            self.crm.novo(t, "indicação", plano, VALOR_PLANO[plano], proxima=t + s.randint(10, 120))

    # ======================================================================================================== (v2) a deriva que assenta
    def _saturacao(self, n):
        if not self.teto:
            return 1.0
        return float(min(1.0, max(0.05, (self.teto - n) / (LARGURA_SATURACAO * self.teto))))

    def _deriva(self, t):
        """O teto do mercado. Perto dele a chegada de leads seca e a carteira assenta num platô; parada por semanas, o dono decide
        abrir mercado novo (o teto sobe depois de duas a quatro semanas) e a carteira volta a crescer, até o limite do mercado."""
        if self.nulo == "sem_deriva":
            return
        s = self.sorte_teto
        n = self.clientes.ativos()
        if self.expansao is not None and t >= self.expansao[0]:
            antes = self.teto
            self.teto = self.expansao[1]
            self.expansao = None
            self.fase = "crescendo"
            self.registro.plato_fim(t, n, f"o teto do mercado subiu de {antes} para {self.teto} clientes (expansão decidida antes)")
        if self.fase == "crescendo" and n >= LIMIAR_PLATO * self.teto:
            self.fase = "platô"
            self.decidir_em = t + s.randint(25, 70) * MINUTOS_DIA
            self.registro.plato_inicio(t, self.teto, n)
        elif self.fase == "platô" and t >= self.decidir_em:
            limite = int(TETO_MAXIMO * self.teto_inicial)
            if self.teto < limite and s.random() < 0.7:
                novo = min(limite, int(round(self.teto * s.uniform(1.15, 1.35))))
                vale = t + s.randint(14, 28) * MINUTOS_DIA
                self.expansao = (vale, novo)
                self.fase = "expansão decidida"
                self.registro.expansao(t, vale, self.teto, novo, n)
            else:
                self.decidir_em = t + s.randint(25, 70) * MINUTOS_DIA
        self.saturacao = self._saturacao(n)

    # ======================================================================================================== (v2) a campanha
    def _campanha(self, t):
        forca = 0.0
        for c in self.campanhas:
            if c["inicio"] <= t < c["fim"]:
                forca = max(forca, c["forca"])
                if not c["anotada"]:
                    c["anotada"] = True
                    self.registro.campanha(c["inicio"], c["fim"], c["forca"], ONDE_CAMPANHA)
                    self.eventos.append((t, "dia de campanha: as ofertas foram anunciadas aos clientes"))
        self.campanhas = [c for c in self.campanhas if c["fim"] > t]
        self.campanha_forca = forca
        self.clientes.campanha = forca

    # ======================================================================================================== (v2) a memória longa
    def _arquivar(self, t):
        """Uma vez por semana: os sistemas apagam o que passou da janela de retenção e a empresa esquece o que já não serve."""
        self.fluxo.arquivar(t)
        self.repo.arquivar(t)
        self.crm.arquivar(t)
        self.agenda.arquivar(t)
        self.quadro.arquivar(t)
        self.empresa.podar(t)
        self.porta.podar(t)

    def _linha_da_verdade(self, t, cal, contas):
        v = np.full(len(COLUNAS), np.nan, dtype=np.float32)
        v[COL["t"]] = t
        v[COL["data_do_calendario"]] = cal.data
        v[COL["minuto_do_calendario"]] = cal.minuto
        v[COL["dia_util"]] = 1.0 if cal.util else 0.0
        reg = self.registro
        por_comp = dict.fromkeys(COMPONENTES_COM_CODIGO, 0)
        for (f, _) in reg.no_ar:
            por_comp[codigo.COMPONENTE_FUNCAO[f]] += 1
        v[COL["defeitos_no_ar"]] = len(reg.no_ar)
        for c, k in por_comp.items():
            v[COL[f"defeitos_no_ar.{c}"]] = k
        aberto = reg.incidente_aberto
        v[COL["produto_parado"]] = 1.0 if aberto is not None else 0.0
        v[COL["incidente_de_volume"]] = 1.0 if aberto is not None and aberto["causa"] == "volume do banco cheio" else 0.0
        v[COL["volume_paginas"]] = self.produto.volume_paginas
        v[COL["volume_paginas_livres"]] = contas["livre_paginas"]          # lido das contas do minuto, sem tocar no banco
        n = self.clientes.ativos()
        v[COL["carteira"]] = n
        v[COL["teto_do_mercado"]] = self.teto
        v[COL["fase_da_deriva"]] = FASES_DERIVA[self.fase] if self.nulo != "sem_deriva" else 0
        v[COL["saturacao"]] = self.saturacao
        v[COL["campanha"]] = self.campanha_forca
        emp = self.empresa
        v[COL["pressa.PROD"]] = emp.pressa["PROD"]
        v[COL["pressa.PLAT"]] = emp.pressa["PLAT"]
        presentes = 0
        tratando = dict.fromkeys(EQUIPES, 0)
        for p in emp.pessoas:
            if p.ativo and p.presente:
                presentes += 1
                if p.tarefa is not None and p.tarefa["tipo"] == "ato":
                    tratando[p.equipe] += 1
        v[COL["pessoas_presentes"]] = presentes
        for e, eq in emp.equipes.items():
            v[COL[f"{e}.atos_na_fila"]] = len(self.porta.fila[e])
            v[COL[f"{e}.atos_em_tratamento"]] = tratando[e]
            v[COL[f"{e}.cansaco"]] = eq.cansaco
            v[COL[f"{e}.atencao"]] = eq.atencao
            v[COL[f"{e}.confianca"]] = eq.confianca
            v[COL[f"{e}.ocupacao"]] = eq.ocupacao
            v[COL[f"{e}.demora_de_pedido"]] = eq.atraso("pedido")
        return v

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


def _banco_em_memoria(nome):
    return sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False, cached_statements=0 if nome == "produto" else 128)


def _plano(s):
    r = s.random()
    return "básico" if r < 0.55 else ("pro" if r < 0.87 else "empresarial")



def _copiar_historia(origem, destino, dias):
    """Copia os arquivos dos dias já fechados (com ligação física quando o disco deixa: eles nunca mudam)."""
    os.makedirs(destino, exist_ok=True)
    for d in range(dias):
        for ext in (".npz", ".json"):
            nome = f"dia_{d:05d}{ext}"
            a, b = os.path.join(origem, nome), os.path.join(destino, nome)
            if os.path.exists(b):
                os.remove(b)
            try:
                os.link(a, b)
            except OSError:
                shutil.copy2(a, b)
