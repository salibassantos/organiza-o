"""O mundo do serviço de um modelo de linguagem: uma caixa com comportamento sorteado pela semente servindo uma população de clientes
simulados, visto só por medidas. Um minuto por passo(). Nenhum texto sai pela porta: nem pedidos, nem respostas, nem instruções; só
contagens, tempos, tokens e custos.

O que a semente sorteia:
- o modelo: latência fixa e por token, espalhamento da latência, taxas de erro, de recusa e de repetição, uso de ferramentas;
- as classes de pedido (de três a sete no começo, mais uma que aparece depois), com tamanhos de entrada e de saída;
- os segmentos de clientes (de dois a cinco), com quantos clientes (de dezenas a milhares no total), horário, paciência, reenvio;
- as ferramentas (de duas a cinco) e as suas falhas;
- a capacidade do serviço e o limite de chamadas;
- as leis com instante: trocas de versão, mudanças das instruções do sistema, incidentes de carga, degradações lentas, a classe nova.

As leis com instante saem de sortes separadas umas das outras, de modo que um nulo tira só a lei dele e as outras ficam nos mesmos
instantes. Ver VERDADE.md."""
import math
import os
import pickle
import re
import unicodedata
import zlib
from dataclasses import dataclass, field

import numpy as np

FAMILIA = "servico"
DESCRICAO = "um serviço de modelo de linguagem usado por clientes, visto só por medidas"
NULOS = (None, "embaralhado", "sem_troca", "sem_degradacao", "surdo")
MINUTOS_DIA = 1440
HORIZONTE_DIAS = 3650
EQUIPES = ("operação do serviço", "produto", "atendimento")
TIPOS = ("pergunta", "pedido")
DIAS = ("segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo")

# classe: (tokens de entrada, tokens de saída, chamadas de ferramenta por pedido, fator de recusa)
CLASSES = {
    "conversa curta": (300, 150, 0.0, 1.0), "resumo de documentos": (3000, 250, 0.0, 0.6),
    "extração de dados": (1500, 200, 0.1, 0.5), "geração de código": (800, 600, 0.2, 0.8),
    "tradução": (600, 600, 0.0, 0.4), "classificação de textos": (400, 12, 0.0, 0.3),
    "busca com ferramentas": (500, 300, 1.5, 1.0), "redação longa": (400, 1200, 0.0, 1.3),
    "perguntas e respostas": (500, 200, 0.3, 1.2), "análise de planilhas": (2500, 400, 0.8, 0.5),
    "agente com ferramentas": (1200, 500, 3.0, 0.9), "revisão de textos": (1200, 900, 0.0, 0.6),
}
# segmento: (chamadas por cliente por minuto, paciência em segundos, chance de reenvio depois de falha, chance de chamado por falha,
#            parte dos clientes que avalia as respostas)
SEGMENTOS = {
    "empresas": (0.03, 45, 0.6, 0.03, 0.3), "desenvolvedores": (0.06, 90, 0.8, 0.01, 0.1),
    "uso pessoal": (0.008, 30, 0.5, 0.002, 0.5), "integrações automáticas": (0.4, 200, 0.95, 0.004, 0.0),
    "lojas com atendimento automático": (0.05, 20, 0.7, 0.02, 0.1),
}
FERRAMENTAS = ("busca de documentos", "calculadora", "consulta a banco de dados", "agenda", "envio de mensagens", "leitura de planilhas")
VARIAVEIS_VERSAO = ("latencia", "erro", "recusa", "repeticao", "tamanho_saida", "ferramentas")
RUINS_SE_SOBEM = ("latencia", "erro", "recusa", "repeticao")
NOME_VARIAVEL = {"latencia": "latência", "erro": "erros internos", "recusa": "recusas", "repeticao": "repetições",
                 "tamanho_saida": "tamanho da saída", "ferramentas": "uso de ferramentas"}

CAMPOS_PEDIDOS = ["chamadas recebidas", "chamadas atendidas", "tokens de entrada", "tokens de saída", "latência média em ms",
                  "latência do percentil 95 em ms"]
CAMPOS_QUALIDADE = ["recusas", "repetições", "tempo esgotado", "erros internos"]
CAMPOS_CLIENTES = ["clientes distintos no minuto", "chamadas enviadas", "reenvios no minuto", "desistências no minuto"]
CAMPOS_FERRAMENTA = ["chamadas no minuto", "falhas no minuto"]
GLOBAIS = [
    ("porta de entrada", ["chamadas recebidas", "rejeitadas por limite", "fila de espera", "espera na fila em ms"], "operação do serviço"),
    ("serviço do modelo", ["uso de processador em %", "memória em uso em GB", "chamadas atendidas", "capacidade em mil tokens por minuto"],
     "operação do serviço"),
    ("erros do serviço", ["tempo esgotado no minuto", "limite excedido no minuto", "erros internos no minuto"], "operação do serviço"),
    ("tokens do serviço", ["entrada no minuto", "saída no minuto"], "operação do serviço"),
    ("custo do serviço", ["custo de processamento no minuto em reais", "custo de capacidade no minuto em reais"], "operação do serviço"),
    ("implantação", ["implantações no minuto"], "operação do serviço"),
    ("atendimento", ["chamados novos no minuto", "chamados abertos", "chamados resolvidos no minuto"], "atendimento"),
    ("avaliações dos clientes", ["avaliações positivas no minuto", "avaliações negativas no minuto"], "atendimento"),
]


def resolucao_do_campo(campo):
    c = campo.lower()
    if "em %" in c or "em mil" in c:
        return 0.1
    if "em gb" in c or "em reais" in c:
        return 0.01
    return 1.0


@dataclass(frozen=True)
class Processo:
    nome: str
    campos: list = field(default_factory=list)
    equipe: str = "operação do serviço"
    resolucao: list = field(default_factory=list)


def _gerador(semente, nome):
    return np.random.Generator(np.random.PCG64(np.random.SeedSequence([int(semente), zlib.crc32(nome.encode("utf-8"))])))


_A = (0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429)


def _phi(z):
    """A função de distribuição normal (aproximação de Abramowitz e Stegun, erro abaixo de 2e-7)."""
    x = np.abs(z) * 0.7071067811865476
    k = 1.0 / (1.0 + 0.3275911 * x)
    y = 1.0 - ((((_A[4] * k + _A[3]) * k + _A[2]) * k + _A[1]) * k + _A[0]) * k * np.exp(-x * x)
    return 0.5 * (1.0 + np.sign(z) * y)


def _p_atraso_chamado():
    """A chance de cada atraso do chamado, de 1 a 1001 minutos: o arredondamento de uma lognormal de mediana 30, cortado em 1000."""
    cdf = lambda x: 0.5 * (1.0 + math.erf((math.log(x) - math.log(30)) / (0.8 * math.sqrt(2))))
    bordas = [0.0] + [cdf(k + 0.5) for k in range(1000)] + [1.0]
    p = np.diff(np.array(bordas))
    return p / p.sum()


GRANDE = 1_000_000                   # acima disto os atrasos saem por faixa (a mesma lei), e não um por chamado ou por avaliação
P_ATRASO_CHAMADO = _p_atraso_chamado()


def _perfil(tipo, fuso):
    """O perfil de uso de um segmento por dia da semana e hora (7 x 24, média 1)."""
    h = np.arange(24.0)
    sino = lambda c, l: np.exp(-((h - c) ** 2) / (2 * l * l))
    faixa = lambda a, b: ((h >= a) & (h < b)).astype(float)
    P = np.zeros((7, 24))
    if tipo == "empresas":
        u = 0.05 + 1.3 * faixa(8, 18) * (1 - 0.35 * faixa(12, 13)) + 0.3 * sino(10, 1.2) + 0.25 * sino(15, 1.2)
        P[:5] = u
        P[0] *= 1.1
        P[4] *= 0.9
        P[5], P[6] = 0.15 * u, 0.08 * u
    elif tipo == "desenvolvedores":
        u = 0.15 + 1.0 * faixa(9, 23) + 0.3 * sino(21, 1.5) + 0.25 * faixa(0, 2)
        P[:5] = u
        P[5:] = 0.6 * u
    elif tipo == "uso pessoal":
        u = 0.08 + 0.5 * faixa(7, 9) + 0.6 * faixa(12, 14) + 1.4 * faixa(18, 24) + 0.3 * faixa(9, 18)
        P[:5] = u
        P[5:] = 0.1 + 1.1 * faixa(9, 24) + 0.5 * faixa(19, 23)
    elif tipo == "integrações automáticas":
        P[:] = 1.0 + 1.5 * faixa(1, 5)
    else:
        u = 0.05 + 1.2 * faixa(8, 20)
        P[:5] = u
        P[5], P[6] = 0.9 * u, 0.3 * u
    P = np.roll(P.reshape(-1), int(fuso)).reshape(7, 24)
    return P / P.mean()


def _aplicar(atual, mult):
    """A mudança sorteada, aplicada sobre o que está no ar; se ela levaria a variável para além de e^0,9 do valor da criação (de 0,41 a
    2,46 vezes), vai no sentido contrário. Assim, em anos de trocas, nada anda sem limite."""
    nova = {}
    for k, x in atual.items():
        m = mult.get(k, 1.0)
        nova[k] = x * m if abs(math.log(x * m)) <= 0.9 else x / m
    return nova


def _simples(texto):
    return "".join(c for c in unicodedata.normalize("NFD", str(texto).lower()) if unicodedata.category(c) != "Mn")


# ---- a leitura dos pedidos: só o trecho antes do primeiro ";", decidida pelo verbo; nome de parte ou de campo nunca é verbo
TETO_CAPACIDADE = 8.0                # a capacidade não passa de 8 vezes a da criação
PROVISIONAMENTO_MIN = 60             # cada aumento cobra de uma vez 60 minutos da capacidade acrescentada
ESTADO_NORMAL = re.compile(r"\bvolt[a-z]*\s+(?:(?:a|ao|aos|as|para|pro|pra)\s+)?(?:ser\s+)?(?:o\s+|a\s+)?"
                           r"(?:normal|normalidade|nivel normal|patamar normal|de antes|como antes|como era|que era)\b")


def _verbo(palavra):
    """O verbo de ação de uma palavra do pedido: "reverter", "aumentar" ou None."""
    if palavra.startswith(("revert", "desfaz", "desfac", "desfiz", "volt", "retorn")):
        return "reverter"
    if palavra.startswith(("aument", "ampli", "expand", "acrescent", "escalon")) or palavra in (
            "subam", "suba", "subir", "subirem", "dobrem", "dobre", "dobrar", "escalem", "escale", "escalar"):
        return "aumentar"
    return None


def _objeto(palavra):
    if palavra.startswith(("versao", "versoes", "implantac")) or palavra == "modelo":
        return "versão"
    if palavra.startswith(("instruc", "prompt")):
        return "instruções"
    if palavra.startswith(("capacidade", "maquina", "servidor")) or palavra == "escala":
        return "capacidade"
    return None


def ler_pedido(texto, nomes):
    """O que o pedido pede: os verbos de ação e as coisas sobre que eles agem. `nomes` são os nomes das partes e dos campos do mundo
    (já simplificados), com o objeto que cada um nomeia ou "" (o nome some da leitura)."""
    x = " " + _simples(str(texto).split(";", 1)[0]) + " "
    for nome, objeto in nomes:
        x = re.sub(r"(?<![a-z])" + re.escape(nome) + r"(?![a-z])", f" {objeto} ", x)
    x = ESTADO_NORMAL.sub(" ", x)
    palavras = re.findall(r"[a-z]+", x)
    return {v for v in map(_verbo, palavras) if v}, {o for o in map(_objeto, palavras) if o}


class Mundo:
    def __init__(self, semente: int, nulo: str | None = None):
        if nulo not in NULOS:
            raise ValueError(f"nulo desconhecido: {nulo}; os nulos são {', '.join(n for n in NULOS if n)}")
        self.semente, self.nulo = int(semente), nulo
        self.t = 0
        self._estrutura()
        self._agendar()
        self._estado_inicial()

    # ======================================================================================================== a estrutura sorteada
    def _estrutura(self):
        s = _gerador(self.semente, "estrutura")
        nomes = list(CLASSES)
        n_ini = int(s.integers(3, 8))
        escolhidas = [nomes[i] for i in s.permutation(len(nomes))[: n_ini + 1]]
        self.classes = escolhidas                                  # a última é a classe nova
        self.classe_nova = len(escolhidas) - 1
        C = len(self.classes)
        segs = [list(SEGMENTOS)[i] for i in sorted(s.permutation(len(SEGMENTOS))[: int(s.integers(2, 6))])]
        self.segmentos = segs
        S = len(segs)
        self.ferramentas = [FERRAMENTAS[i] for i in sorted(s.permutation(len(FERRAMENTAS))[: int(s.integers(2, 6))])]
        T = len(self.ferramentas)
        total = int(round(math.exp(s.uniform(math.log(30), math.log(4000)))))
        pesos = s.dirichlet([2.0] * S) * np.array([0.15 if g == "integrações automáticas" else 1.0 for g in segs])
        pesos /= pesos.sum()
        self.n_clientes = np.maximum(3, np.round(total * pesos)).astype(np.int64)
        par = np.array([SEGMENTOS[g] for g in segs], dtype=float)
        mult = s.uniform(0.7, 1.4, size=(S, 4))
        self.taxa_cliente = par[:, 0] * mult[:, 0]
        self.paciencia_ms = par[:, 1] * mult[:, 1] * 1000.0
        self.reenvio = np.clip(par[:, 2] * mult[:, 2], 0.05, 0.98)
        self.p_chamado = par[:, 3] * mult[:, 3]
        self.avalia = par[:, 4]
        self.fuso = s.integers(-2, 3, size=S)
        self.perfil = np.stack([_perfil(g, f) for g, f in zip(segs, self.fuso)])          # S x 7 x 24
        mix = np.zeros((S, C))
        for i in range(S):
            mix[i, :-1] = s.dirichlet([1.5] * (C - 1))
        self.mix_nova = s.uniform(0.1, 0.35, size=S)                                        # parte do tráfego da classe nova
        self.mix = mix
        par_c = np.array([CLASSES[c] for c in self.classes], dtype=float)
        mc = s.uniform(0.7, 1.4, size=(C, 2))
        self.tok_in = par_c[:, 0] * mc[:, 0]
        self.tok_out = par_c[:, 1] * mc[:, 1]
        self.ferr_por_pedido = par_c[:, 2]
        self.fator_recusa = par_c[:, 3]
        self.mix_ferr = s.dirichlet([1.0] * T, size=C)                                       # C x T
        self.p_falha_ferr = s.uniform(0.01, 0.06, size=T)
        self.modelo = {"latencia_fixa_ms": float(s.uniform(200, 600)), "ms_por_token_de_saida": float(s.uniform(8, 25)),
                       "ms_por_token_de_entrada": float(s.uniform(0.05, 0.2)), "espalhamento": float(s.uniform(0.35, 0.6)),
                       "erro": float(s.uniform(0.002, 0.01)), "recusa": float(s.uniform(0.005, 0.04)),
                       "repeticao": float(s.uniform(0.005, 0.03))}
        m = self.modelo
        self.svc_tipico_ms = m["latencia_fixa_ms"] + m["ms_por_token_de_saida"] * self.tok_out + m["ms_por_token_de_entrada"] * self.tok_in
        self.escala_paciencia = np.maximum(1.0, self.svc_tipico_ms / 3000.0)
        self.trabalho = self.tok_in * 0.1 + self.tok_out                                     # tokens de trabalho por chamada
        base = (self.n_clientes * self.taxa_cliente)[:, None] * mix
        pico = (base * self.perfil.max(axis=(1, 2))[:, None]).sum(axis=0)
        pico_nova = (self.n_clientes * self.taxa_cliente * self.mix_nova * self.perfil.max(axis=(1, 2))).sum()
        demanda = float((pico * self.trabalho).sum() + pico_nova * self.trabalho[-1])
        self.capacidade_inicial = max(2000.0, demanda * float(s.uniform(1.4, 2.2)))
        self.preco_entrada = float(s.uniform(0.005, 0.02))          # reais por mil tokens
        self.preco_saida = float(s.uniform(0.02, 0.08))
        self.preco_capacidade = float(s.uniform(0.002, 0.006))      # reais por mil tokens de capacidade por minuto
        self.memoria_base = float(s.uniform(20, 60))
        self._processos = []
        for c in self.classes:
            self._processos.append(Processo(f"pedidos de {c}", list(CAMPOS_PEDIDOS), "operação do serviço",
                                            [resolucao_do_campo(x) for x in CAMPOS_PEDIDOS]))
            self._processos.append(Processo(f"qualidade de {c}", list(CAMPOS_QUALIDADE), "produto", [1.0] * 4))
        for g in segs:
            self._processos.append(Processo(f"clientes de {g}", list(CAMPOS_CLIENTES), "produto", [1.0] * 4))
        for f in self.ferramentas:
            self._processos.append(Processo(f"ferramenta {f}", list(CAMPOS_FERRAMENTA), "operação do serviço", [1.0] * 2))
        for nome, campos, eq in GLOBAIS:
            self._processos.append(Processo(nome, list(campos), eq, [resolucao_do_campo(x) for x in campos]))
        assert 20 <= len(self._processos) <= 60

    # ======================================================================================================== as leis com instante
    def _agendar(self):
        """Sorteia, cada lei com a sua sorte, os instantes de tudo o que vai acontecer (dez anos)."""
        fim = HORIZONTE_DIAS * MINUTOS_DIA
        self.agenda = {}

        def por(t, ev):
            self.agenda.setdefault(int(t), []).append(ev)
        s = _gerador(self.semente, "versões")
        d, n = 0, 1
        while True:
            d += int(s.integers(10, 31))
            while d % 7 not in (1, 3):
                d += 1
            t = d * MINUTOS_DIA + 14 * 60 + int(s.integers(0, 180))
            if t >= fim:
                break
            mult = self._sortear_mudanca(s, VARIAVEIS_VERSAO, (0.25, 0.55), 2)
            n += 1
            por(t, ("versão", {"versao": n, "mult": mult}))
        s = _gerador(self.semente, "instruções")
        d, n = 0, 1
        while True:
            d += int(s.integers(5, 21))
            while d % 7 >= 5:
                d += 1
            t = d * MINUTOS_DIA + 10 * 60 + int(s.integers(0, 420))
            if t >= fim:
                break
            mult = self._sortear_mudanca(s, ("recusa", "tamanho_saida"), (0.3, 0.7), 1)
            n += 1
            por(t, ("instrução", {"instrucao": n, "mult": mult}))
        s = _gerador(self.semente, "incidentes")
        d = 0
        while True:
            d += int(s.integers(4, 15))
            t = d * MINUTOS_DIA + int(s.integers(9 * 60, 17 * 60))           # os incidentes de carga vêm no horário de movimento
            dur = int(s.integers(20, 181))
            if t + dur >= fim:
                break
            if s.random() < 0.5:
                # uma integração descontrolada ou um robô: chamadas a mais que somam de 0,8 a 2 vezes a capacidade em trabalho
                ev = {"tipo": "pico de chamadas", "segmento": int(s.integers(0, len(self.segmentos))), "forca": float(s.uniform(0.8, 2.0)),
                      "duracao": dur}
            else:
                ev = {"tipo": "perda de capacidade", "segmento": None, "forca": float(s.uniform(0.15, 0.35)), "duracao": dur}
            por(t, ("incidente", ev))
            por(t + dur, ("fim do incidente", ev))
        s = _gerador(self.semente, "degradações")
        t = int(s.uniform(3, 20) * MINUTOS_DIA)
        while True:
            dur = int(s.uniform(14, 35) * MINUTOS_DIA)
            if t + dur >= fim:
                break
            ev = {"variavel": "latencia" if s.random() < 0.5 else "repeticao", "aumento": float(s.uniform(0.3, 0.8)), "inicio": t,
                  "fim": t + dur}
            por(t, ("degradação", ev))
            por(t + dur, ("fim da degradação", ev))
            t += dur + int(s.uniform(20, 60) * MINUTOS_DIA)
        s = _gerador(self.semente, "classe nova")
        d = int(s.integers(8, 36))
        rampa = int(s.integers(3, 11))
        por(d * MINUTOS_DIA + 10 * 60, ("classe nova", {"rampa_dias": rampa}))

    @staticmethod
    def _sortear_mudanca(s, variaveis, faixa, minimo):
        mult = {}
        while sum(1 for v in mult.values() if v != 1.0) < minimo:
            mult = {}
            for v in variaveis:
                if s.random() < 0.5:
                    mult[v] = float(math.exp((1 if s.random() < 0.5 else -1) * s.uniform(*faixa)))
                else:
                    mult[v] = 1.0
        return mult

    # ======================================================================================================== o estado
    def _estado_inicial(self):
        S, C, T = len(self.segmentos), len(self.classes), len(self.ferramentas)
        self.base = (self.n_clientes * self.taxa_cliente)[:, None] * self.mix                 # S x C, chamadas por minuto
        self.trabalho_medio = float((self.trabalho * self.base.sum(axis=0)).sum() / self.base.sum())
        self.ativo = np.ones(C)
        self.ativo[-1] = 0.0
        self.nova = None                                                                       # (início, fim da rampa)
        self.versoes = [{v: 1.0 for v in VARIAVEIS_VERSAO}]
        self.versao_nome = [1]
        self.no_ar = 0
        self.pilha_versoes = []
        self.instrucoes = [{"recusa": 1.0, "tamanho_saida": 1.0}]
        self.instrucao_nome = [1]
        self.instrucao_no_ar = 0
        self.pilha_instrucoes = []
        self.capacidade = self.capacidade_inicial
        self._provisionamento = 0.0                                  # a taxa dos aumentos de capacidade, cobrada no minuto do aumento
        self.incidentes = []
        self.degradacao = None
        self.queda_ate = -1
        self.fila = np.zeros(C, dtype=np.int64)
        self.espera_ms = 0.0
        self.reenvios = np.zeros((8, S, C), dtype=np.int64)
        self.chamados_futuros = np.zeros(1024, dtype=np.int64)
        self.negativas_futuras = np.zeros(16, dtype=np.int64)
        self.chamados_abertos = 0
        self.ultima_hora = np.zeros((60, 8))                                                  # para responder aos atos
        self.s = {k: _gerador(self.semente, k) for k in ("chegadas", "serviço", "retornos", "atendimento", "atos", "calendário")}
        # o calendário (no nulo embaralhado, sorteado em blocos)
        self.bloco = None
        self.blocos = []
        # a porta dos atos
        self.numero = 0
        self.chegando = []
        self.pendentes = []
        self.saida = []
        # a verdade
        self.r = {"trocas_de_versao": [], "mudancas_de_instrucao": [], "incidentes_de_carga": [], "degradacoes": [], "classes_novas": [],
                  "atos": [], "mudancas_de_capacidade": []}
        self.eventos = []
        self.atividade = {k: [] for k in ("falhas", "recusas_repeticoes", "fila", "falhas_de_ferramenta", "implantacoes")}
        self._hora = np.zeros(5)
        self._implantou = 0

    # ======================================================================================================== a porta
    def processos(self):
        return [Processo(p.nome, list(p.campos), p.equipe, list(p.resolucao)) for p in self._processos]

    def equipes(self):
        return list(EQUIPES)

    def dia(self):
        return self.t // MINUTOS_DIA

    def minuto_do_dia(self):
        return self.t % MINUTOS_DIA

    def dia_da_semana(self):
        return self.dia() % 7

    def receber(self, equipe: str, tipo: str, texto: str) -> int:
        if equipe not in EQUIPES:
            raise ValueError(f"equipe desconhecida: {equipe}; as equipes são {', '.join(EQUIPES)}")
        if tipo not in TIPOS:
            raise ValueError(f"tipo desconhecido: {tipo}; os tipos são {', '.join(TIPOS)}")
        self.numero += 1
        if self.nulo != "surdo":
            self.chegando.append((self.numero, equipe, tipo, str(texto)))
        return self.numero

    def respostas(self):
        saida, self.saida = self.saida, []
        return saida

    def eventos_humanos(self):
        return list(self.eventos)

    def salvar(self, pasta):
        os.makedirs(pasta, exist_ok=True)
        with open(os.path.join(pasta, "estado.pickle"), "wb") as f:
            pickle.dump(self, f, protocol=pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def carregar(pasta):
        with open(os.path.join(pasta, "estado.pickle"), "rb") as f:
            m = pickle.load(f)
        m.__dict__.setdefault("_provisionamento", 0.0)               # um estado salvo antes da taxa de provisionamento
        return m

    # ======================================================================================================== o calendário
    def _calendario(self, t):
        """(dia da semana, minuto do dia) em que os clientes e as pessoas vivem; no nulo embaralhado, sorteado em blocos."""
        if self.nulo != "embaralhado":
            return (t // MINUTOS_DIA) % 7, t % MINUTOS_DIA
        if self.bloco is None or t >= self.bloco[1]:
            s = self.s["calendário"]
            dur = int(s.integers(25, 241))
            ini = int(s.integers(0, 7 * MINUTOS_DIA))
            self.bloco = (t, t + dur, ini)
            self.blocos.append({"inicio": t, "fim": t + dur, "dia_da_semana": DIAS[ini // MINUTOS_DIA],
                                "hora": f"{(ini % MINUTOS_DIA) // 60:02d}:{ini % 60:02d}"})
        c = (self.bloco[2] + t - self.bloco[0]) % (7 * MINUTOS_DIA)
        return c // MINUTOS_DIA, c % MINUTOS_DIA

    # ======================================================================================================== um minuto
    def passo(self):
        self.t += 1
        t = self.t
        dow, mdia = self._calendario(t)
        self._implantou = 0
        for ev in self.agenda.pop(t, ()):
            self._evento(t, *ev)
        if self.chegando:
            self._receber_atos(t)
        if self.pendentes:
            self._executar_atos(t)
        S, C = self.base.shape
        sc, ss, sr = self.s["chegadas"], self.s["serviço"], self.s["retornos"]
        # ---- as chegadas
        if self.nova is not None:
            ini, fim_rampa = self.nova
            self.ativo[-1] = min(1.0, (t - ini) / max(1, fim_rampa - ini))
        h = mdia // 60
        f = (mdia % 60) / 60.0
        h2 = (h + 1) % 24
        d2 = dow if h2 else (dow + 1) % 7
        prof = self.perfil[:, dow, h] * (1 - f) + self.perfil[:, d2, h2] * f
        lam = self.base * prof[:, None]
        if self.ativo[-1] > 0:
            lam[:, -1] = self.n_clientes * self.taxa_cliente * self.mix_nova * prof * self.ativo[-1]
        cap_fator = 1.0
        for inc in self.incidentes:
            if inc["tipo"] == "pico de chamadas":
                lam[inc["segmento"]] += inc["extra"]
            else:
                cap_fator *= inc["forca"]
        pos = t % 8
        chegadas = sc.poisson(lam) + self.reenvios[pos]
        self.reenvios[pos] = 0
        distintos = sc.binomial(self.n_clientes, 1.0 - np.exp(-lam.sum(axis=1) / self.n_clientes))
        # ---- o limite de chamadas
        cap = self.capacidade * cap_fator * (0.6 if t <= self.queda_ate else 1.0)
        A = int(chegadas.sum())
        limite = self.capacidade_inicial / self.trabalho_medio * 1.3      # o limite de chamadas foi configurado na criação
        if A > limite:
            rejeitadas = ss.binomial(chegadas, 1.0 - limite / A)
        else:
            rejeitadas = np.zeros_like(chegadas)
        admitidas = (chegadas - rejeitadas).sum(axis=0)
        # ---- a fila e o atendimento
        v = self.versoes[self.no_ar]
        ins = self.instrucoes[self.instrucao_no_ar]
        deg_lat = deg_rep = 1.0
        if self.degradacao is not None:
            dg = self.degradacao
            prog = (t - dg["inicio"]) / (dg["fim"] - dg["inicio"])
            if dg["variavel"] == "latencia":
                deg_lat = 1.0 + dg["aumento"] * prog
            else:
                deg_rep = 1.0 + dg["aumento"] * prog
        saida_tok = self.tok_out * v["tamanho_saida"] * ins["tamanho_saida"]
        w = self.tok_in * 0.1 + saida_tok
        self.fila += admitidas
        W = float((self.fila * w).sum())
        phi = 1.0 if W <= cap else cap / W
        atendidas = ss.binomial(self.fila, phi) if phi < 1.0 else self.fila.copy()
        self.fila -= atendidas
        u = W / cap
        resto = float((self.fila * w).sum())
        m = self.modelo
        svc = (m["latencia_fixa_ms"] + m["ms_por_token_de_saida"] * saida_tok + m["ms_por_token_de_entrada"] * self.tok_in) \
            * v["latencia"] * deg_lat * (1.0 + 0.35 * min(u, 1.0) ** 2)
        media = svc + self.espera_ms
        self.espera_ms = resto / cap * 60000.0
        sig = m["espalhamento"]
        # ---- o tempo esgotado: a paciência de cada segmento para cada classe
        part = chegadas / np.maximum(1, chegadas.sum(axis=0))                                 # S x C
        pac = self.paciencia_ms[:, None] * self.escala_paciencia[None, :]
        mu = np.log(np.maximum(media, 1.0)) - sig * sig / 2
        frac = 1.0 - _phi((np.log(pac) - mu[None, :]) / sig)
        frac_c = np.clip((part * frac).sum(axis=0), 0.0, 1.0)
        esgot = ss.binomial(atendidas, frac_c)
        servidas = atendidas - esgot
        if self.espera_ms > 0 and self.fila.any():                    # quem ainda está na fila e passou da paciência desiste
            fq = 1.0 - _phi((np.log(pac) - math.log(self.espera_ms + 1.0)) / 0.5)
            desist_fila = ss.binomial(self.fila, np.clip((part * fq).sum(axis=0), 0.0, 1.0))
            self.fila -= desist_fila
            esgot = esgot + desist_fila
        p_err = min(0.5, m["erro"] * v["erro"] * (1.0 + 4.0 * max(0.0, u - 1.0)))
        erros = ss.binomial(servidas, p_err)
        ok = servidas - erros
        # ---- as ferramentas
        uso = ok * self.ferr_por_pedido * v["ferramentas"]                                     # C
        cham_ferr = sr.poisson(uso @ self.mix_ferr)                                            # T
        falhas_ferr = sr.binomial(cham_ferr, self.p_falha_ferr)
        nf = int(falhas_ferr.sum())
        if nf:
            pesos = uso * (self.mix_ferr @ self.p_falha_ferr)
            if pesos.sum() > 0:
                extra = np.minimum(sr.multinomial(int(sr.binomial(nf, 0.3)), pesos / pesos.sum()), ok)
                erros = erros + extra
                ok = ok - extra
        # ---- a qualidade das respostas
        p_ref = np.clip(m["recusa"] * self.fator_recusa * v["recusa"] * ins["recusa"], 0.0, 0.9)
        recusas = sr.binomial(ok, p_ref)
        repet = sr.binomial(ok - recusas, min(0.9, m["repeticao"] * v["repeticao"] * deg_rep))
        ruido = sr.normal(0.0, 1.0, size=(2, C))
        tok_e = np.maximum(0, np.round(atendidas * self.tok_in * (1 + 0.08 * ruido[0] / np.sqrt(np.maximum(atendidas, 1)))))
        tok_s = np.maximum(0, np.round(((ok - recusas) * saida_tok + recusas * 40) * (1 + 0.08 * ruido[1] / np.sqrt(np.maximum(ok, 1)))))
        lat = np.where(atendidas > 0, media * np.exp(sr.normal(0, 0.03, size=C)), 0.0)
        k95 = math.exp(1.645 * sig - sig * sig / 2)
        p95 = np.where(atendidas > 0, media * k95 * np.exp(sr.normal(0, 0.05, size=C)), 0.0)
        # ---- os reenvios dos clientes (a falha volta como chamada de um a cinco minutos depois)
        falha_c = esgot + erros
        falhas = rejeitadas + np.round(part * falha_c[None, :]).astype(np.int64)
        voltam = sr.binomial(falhas, self.reenvio[:, None])
        resto_v = voltam
        for d in range(1, 5):
            x = sr.binomial(resto_v, 0.45) if d < 4 else resto_v
            self.reenvios[(t + d) % 8] += x
            resto_v = resto_v - x
        desist = (falhas - voltam).sum(axis=1)
        # ---- o atendimento e as avaliações
        sa = self.s["atendimento"]
        n_ch = int(sa.poisson(float((falhas.sum(axis=1) * self.p_chamado).sum())))
        if n_ch > GRANDE:                                             # muitos de uma vez: a mesma lei por faixa, sem um sorteio por chamado
            self.chamados_futuros[(t + 1 + np.arange(1001)) % 1024] += sa.multinomial(n_ch, P_ATRASO_CHAMADO)
        elif n_ch:
            atrasos = np.minimum(1000, np.round(sa.lognormal(math.log(30), 0.8, size=n_ch))).astype(int) + 1
            np.add.at(self.chamados_futuros, (t + atrasos) % 1024, 1)
        p = t % 1024
        novos = int(self.chamados_futuros[p])
        self.chamados_futuros[p] = 0
        self.chamados_abertos += novos
        expediente = dow < 5 and 8 * 60 <= mdia < 18 * 60
        resolvidos = int(sa.binomial(self.chamados_abertos, 0.02 if expediente else 0.002))
        self.chamados_abertos -= resolvidos
        fav = float((self.avalia * self.n_clientes).sum() / self.n_clientes.sum())
        neg = int(sa.poisson(fav * (0.15 * float((recusas + repet).sum()) + 0.05 * float(esgot.sum()))))
        if neg > GRANDE:
            self.negativas_futuras[(t + np.arange(1, 11)) % 16] += sa.multinomial(neg, np.full(10, 0.1))
        elif neg:
            np.add.at(self.negativas_futuras, (t + sa.integers(1, 11, size=neg)) % 16, 1)
        negativas = int(self.negativas_futuras[t % 16])
        self.negativas_futuras[t % 16] = 0
        positivas = int(sa.poisson(fav * 0.02 * float(ok.sum())))
        # ---- o servidor e o custo
        cpu = min(100.0, max(0.0, 3.0 + 92.0 * min(u, 1.0) + sa.normal(0, 1.5)))
        memoria = self.memoria_base + 0.8 * min(u, 1.5) + 0.000002 * resto
        te, ts = float(tok_e.sum()), float(tok_s.sum())
        custo_proc = te / 1000 * self.preco_entrada + ts / 1000 * self.preco_saida
        custo_cap = self.capacidade / 1000 * self.preco_capacidade + self._provisionamento
        self._provisionamento = 0.0
        # ---- para os atos e para a verdade
        self.ultima_hora[t % 60] = (A, float(falha_c.sum() + rejeitadas.sum()), float(self.fila.sum()), u, float(recusas.sum()),
                                    float(repet.sum()), float(lat.mean()), float(negativas))
        self._hora += (float(falhas.sum()), float((recusas + repet).sum()), float(self.fila.sum()), float(nf), float(self._implantou))
        if t % 60 == 0:
            for k, x in zip(self.atividade, self._hora):
                self.atividade[k].append(x)
            self._hora = np.zeros(5)
        # ---- a saída
        out = {}
        for c, nome in enumerate(self.classes):
            out[f"pedidos de {nome}"] = [float(chegadas[:, c].sum()), float(atendidas[c]), float(tok_e[c]), float(tok_s[c]),
                                         float(round(lat[c])), float(round(p95[c]))]
            out[f"qualidade de {nome}"] = [float(recusas[c]), float(repet[c]), float(esgot[c]), float(erros[c])]
        cs = chegadas.sum(axis=1)
        rs = (voltam.sum(axis=1))
        for i, g in enumerate(self.segmentos):
            out[f"clientes de {g}"] = [float(distintos[i]), float(cs[i]), float(rs[i]), float(desist[i])]
        for k, nome in enumerate(self.ferramentas):
            out[f"ferramenta {nome}"] = [float(cham_ferr[k]), float(falhas_ferr[k])]
        out["porta de entrada"] = [float(A), float(rejeitadas.sum()), float(self.fila.sum()), float(round(self.espera_ms))]
        out["serviço do modelo"] = [round(cpu, 1), round(memoria, 2), float(atendidas.sum()), round(self.capacidade / 1000, 1)]
        out["erros do serviço"] = [float(esgot.sum()), float(rejeitadas.sum()), float(erros.sum())]
        out["tokens do serviço"] = [te, ts]
        out["custo do serviço"] = [round(custo_proc, 2), round(custo_cap, 2)]
        out["implantação"] = [float(self._implantou)]
        out["atendimento"] = [float(novos), float(self.chamados_abertos), float(resolvidos)]
        out["avaliações dos clientes"] = [float(positivas), float(negativas)]
        return out

    # ======================================================================================================== os acontecimentos
    def _onde(self, variavel):
        cls = [c for i, c in enumerate(self.classes) if self.ativo[i] > 0]
        if variavel == "latencia":
            return [[f"pedidos de {c}", x] for c in cls for x in ("latência média em ms", "latência do percentil 95 em ms")]
        if variavel == "erro":
            return [[f"qualidade de {c}", "erros internos"] for c in cls] + [["erros do serviço", "erros internos no minuto"]]
        if variavel == "recusa":
            return [[f"qualidade de {c}", "recusas"] for c in cls]
        if variavel == "repeticao":
            return [[f"qualidade de {c}", "repetições"] for c in cls]
        if variavel == "tamanho_saida":
            return [[f"pedidos de {c}", "tokens de saída"] for c in cls] + [["tokens do serviço", "saída no minuto"],
                                                                          ["custo do serviço", "custo de processamento no minuto em reais"]]
        return [[f"ferramenta {f}", "chamadas no minuto"] for f in self.ferramentas]

    def _efeito(self, antes, depois):
        mult = {k: round(depois[k] / antes[k], 4) for k in antes}
        sobem = [k for k, x in mult.items() if x > 1.0001]
        descem = [k for k, x in mult.items() if x < 0.9999]
        onde = [par for k in sobem + descem for par in self._onde(k)]
        return mult, sobem, descem, onde

    def _evento(self, t, tipo, ev):
        if tipo == "versão":
            if self.nulo == "sem_troca":
                return
            nova = _aplicar(self.versoes[self.no_ar], ev["mult"])
            self._trocar_versao(t, nova, f"versão {ev['versao']}", "troca programada da versão do modelo")
        elif tipo == "instrução":
            if self.nulo == "sem_troca":
                return
            nova = _aplicar(self.instrucoes[self.instrucao_no_ar], ev["mult"])
            self._trocar_instrucao(t, nova, f"instruções {ev['instrucao']}", "mudança programada das instruções do sistema")
        elif tipo == "incidente":
            ev = dict(ev)
            if ev["tipo"] == "pico de chamadas":
                g = ev["segmento"]
                mix = self.mix[g] * self.ativo
                mix = mix / mix.sum()
                # chamadas a mais por minuto, medidas pela capacidade da criação (a força do pico é da procura dos clientes, que não
                # cresce com a capacidade que o serviço comprou depois)
                ev["extra"] = ev["forca"] * self.capacidade_inicial / float((mix * self.trabalho).sum()) * mix
            self.incidentes.append(ev)
            reg = {"inicio": t, "fim": t + ev["duracao"], "duracao_min": ev["duracao"], "tipo": ev["tipo"],
                   "segmento": self.segmentos[ev["segmento"]] if ev["segmento"] is not None else None,
                   "forca": round(ev["forca"], 3), "onde": self._onde_incidente(ev),
                   "chamadas_a_mais_por_minuto": round(float(ev["extra"].sum()), 1) if ev["tipo"] == "pico de chamadas" else None,
                   "causa": (f"os clientes de {self.segmentos[ev['segmento']]} mandaram chamadas a mais que somam {ev['forca']:.1f} vezes a "
                             f"capacidade do serviço em trabalho" if ev["tipo"] == "pico de chamadas" else
                             f"o serviço perdeu capacidade (ficou com {100 * ev['forca']:.0f}% dela)")}
            self.r["incidentes_de_carga"].append(reg)
            self.eventos.append((t + 3, "a fila de espera do serviço disparou"))
        elif tipo == "fim do incidente":
            for inc in self.incidentes:
                if inc["duracao"] == ev["duracao"] and inc["tipo"] == ev["tipo"] and inc["forca"] == ev["forca"]:
                    self.incidentes.remove(inc)
                    self.eventos.append((t, "a fila de espera do serviço voltou ao normal"))
                    break
        elif tipo == "degradação":
            if self.nulo == "sem_degradacao":
                return
            self.degradacao = ev
            self.r["degradacoes"].append({"inicio": ev["inicio"], "fim": ev["fim"], "duracao_dias": round((ev["fim"] - ev["inicio"]) / MINUTOS_DIA, 1),
                                          "variavel": ev["variavel"], "aumento_no_fim": round(ev["aumento"], 3),
                                          "forma": "cresce em linha reta do início ao fim e volta ao normal no fim",
                                          "onde": self._onde(ev["variavel"]),
                                          "causa": f"desgaste lento do serviço ({NOME_VARIAVEL[ev['variavel']]}), corrigido na manutenção do fim"})
        elif tipo == "fim da degradação":
            if self.degradacao is ev:
                self.degradacao = None
                self.eventos.append((t, "manutenção programada do serviço"))
        elif tipo == "classe nova":
            c = self.classes[-1]
            fim_rampa = t + ev["rampa_dias"] * MINUTOS_DIA
            self.nova = (t, fim_rampa)
            self.ativo[-1] = 1e-9
            self.r["classes_novas"].append({"t": t, "classe": c, "rampa_ate": fim_rampa,
                                            "processos": [f"pedidos de {c}", f"qualidade de {c}"],
                                            "onde": [[f"pedidos de {c}", x] for x in CAMPOS_PEDIDOS] + [[f"qualidade de {c}", x] for x in CAMPOS_QUALIDADE],
                                            "causa": f"os clientes passaram a pedir {c}; o tráfego dela cresce em linha reta por {ev['rampa_dias']} dias"})
            self.eventos.append((t, f"lançamento de {c} para os clientes"))

    def _onde_incidente(self, ev):
        onde = [["porta de entrada", "fila de espera"], ["porta de entrada", "espera na fila em ms"],
                ["erros do serviço", "tempo esgotado no minuto"], ["serviço do modelo", "uso de processador em %"]]
        onde += [[f"pedidos de {c}", x] for c in self.classes for x in ("latência média em ms", "latência do percentil 95 em ms")]
        onde += [[f"qualidade de {c}", "tempo esgotado"] for c in self.classes]
        if ev["tipo"] == "pico de chamadas":
            g = self.segmentos[ev["segmento"]]
            onde += [["porta de entrada", "chamadas recebidas"], ["porta de entrada", "rejeitadas por limite"],
                     ["erros do serviço", "limite excedido no minuto"], [f"clientes de {g}", "chamadas enviadas"]]
        return onde

    def _trocar_versao(self, t, nova, nome, causa, ato=None):
        antes = self.versoes[self.no_ar]
        mult, sobem, descem, onde = self._efeito(antes, nova)
        self.pilha_versoes.append(self.no_ar)
        self.versoes.append(nova)
        self.versao_nome.append(nome)
        de = self.versao_nome[self.no_ar]
        self.no_ar = len(self.versoes) - 1
        self.queda_ate = t + 2
        self._implantou = 1
        self.r["trocas_de_versao"].append({"t": t, "de": de if isinstance(de, str) else f"versão {de}", "para": nome, "efeito": mult,
                                           "sobem": sobem, "descem": descem, "onde": onde, "causa": causa, "pedida_pelo_ato": ato,
                                           "reinicio": {"inicio": t, "fim": t + 2, "onde": [["porta de entrada", "fila de espera"],
                                                                                            ["erros do serviço", "tempo esgotado no minuto"]]}})
        self.eventos.append((t, f"implantação da {nome}"))

    def _trocar_instrucao(self, t, nova, nome, causa, ato=None):
        antes = self.instrucoes[self.instrucao_no_ar]
        mult, sobem, descem, onde = self._efeito(antes, nova)
        self.pilha_instrucoes.append(self.instrucao_no_ar)
        self.instrucoes.append(nova)
        self.instrucao_nome.append(nome)
        de = self.instrucao_nome[self.instrucao_no_ar]
        self.instrucao_no_ar = len(self.instrucoes) - 1
        self.r["mudancas_de_instrucao"].append({"t": t, "de": de if isinstance(de, str) else f"instruções {de}", "para": nome,
                                                "efeito": mult, "sobem": sobem, "descem": descem, "onde": onde, "causa": causa,
                                                "pedida_pelo_ato": ato})
        self.eventos.append((t, "as instruções do sistema foram trocadas"))

    # ======================================================================================================== os atos
    def _receber_atos(self, t):
        sa = self.s["atos"]
        for numero, equipe, tipo, texto in self.chegando:
            acao = "pergunta" if tipo != "pedido" else self.ler(equipe, texto)
            demora = int(sa.integers(5, 26)) if equipe == "operação do serviço" else int(sa.integers(20, 121))
            reg = {"numero": numero, "equipe": equipe, "tipo": tipo, "texto": texto, "recebido": t, "acao": acao,
                   "executado_em": t + demora, "efetivo_em": None, "util": None, "por_que": None, "encurtou": [], "piorou_de_lado": [],
                   "custo": None, "resposta": None, "respondido_em": None}
            self.r["atos"].append(reg)
            self.pendentes.append(reg)
        self.chegando = []

    def _nomes_lidos(self):
        """Os nomes das partes e dos campos, do mais longo ao mais curto, com o que cada um nomeia na leitura de um pedido: a capacidade,
        o modelo e a implantação nomeiam a coisa (são objeto, nunca verbo); os outros somem da leitura."""
        objeto = {"capacidade em mil tokens por minuto": "capacidade", "serviço do modelo": "modelo", "implantação": "implantacao"}
        nomes = {p.nome for p in self._processos} | {c for p in self._processos for c in p.campos}
        return sorted(((_simples(n), objeto.get(n, "")) for n in nomes), key=lambda x: -len(x[0]))

    def ler(self, equipe, texto):
        """A ação que um pedido a uma equipe pede: "reverter versão", "voltar instruções", "aumentar capacidade" ou "sem ação"."""
        verbos, objetos = ler_pedido(texto, self._nomes_lidos())
        if "reverter" in verbos and "instruções" in objetos and equipe in ("operação do serviço", "produto"):
            return "voltar instruções"
        if "reverter" in verbos and "versão" in objetos and equipe == "operação do serviço":
            return "reverter versão"
        if "aumentar" in verbos and "capacidade" in objetos and equipe == "operação do serviço":
            return "aumentar capacidade"
        return "sem ação"

    def _executar_atos(self, t):
        fica = []
        for reg in self.pendentes:
            if reg["executado_em"] > t:
                fica.append(reg)
                continue
            getattr(self, "_ato_" + {"pergunta": "pergunta", "reverter versão": "reverter", "voltar instruções": "instrucoes",
                                     "aumentar capacidade": "capacidade", "sem ação": "nada"}[reg["acao"]])(t, reg)
            reg["respondido_em"] = t + int(self.s["atos"].integers(1, 6))
            self.saida.append((reg["respondido_em"], reg["numero"], reg["equipe"], reg["resposta"]))
        self.pendentes = fica
        self.saida.sort()

    def _hora_passada(self):
        h = self.ultima_hora
        return {"chamadas": int(h[:, 0].sum()), "falhas": int(h[:, 1].sum()), "fila_media": round(float(h[:, 2].mean()), 1),
                "uso_maximo": float(h[:, 3].max()), "recusas": int(h[:, 4].sum()), "repeticoes": int(h[:, 5].sum()),
                "latencia_media_ms": round(float(h[:, 6].mean())), "negativas": int(h[:, 7].sum())}

    def _ato_pergunta(self, t, reg):
        h = self._hora_passada()
        if reg["equipe"] == "operação do serviço":
            reg["resposta"] = (f"Na última hora: {h['chamadas']} chamadas, {h['falhas']} falhas (tempo esgotado, limite ou erro), "
                               f"fila média de {h['fila_media']} chamadas, latência média de {h['latencia_media_ms']} ms; capacidade de "
                               f"{self.capacidade / 1000:.1f} mil tokens por minuto.")
        elif reg["equipe"] == "produto":
            reg["resposta"] = (f"Na última hora: {h['recusas']} recusas, {h['repeticoes']} respostas com trechos repetidos e "
                               f"{h['negativas']} avaliações negativas.")
        else:
            reg["resposta"] = f"Há {self.chamados_abertos} chamados abertos no atendimento."

    def _ato_nada(self, t, reg):
        reg["resposta"] = "Pedido registrado; não há o que esta equipe faça com ele."
        reg["util"] = False
        reg["por_que"] = "o pedido não corresponde a nenhuma ação desta equipe"

    def _ato_reverter(self, t, reg):
        if not self.pilha_versoes:
            reg.update(resposta="Não há versão anterior para voltar.", util=False, por_que="não havia versão anterior")
            return
        atual, anterior = self.versoes[self.no_ar], self.versoes[self.pilha_versoes[-1]]
        piores = [k for k in RUINS_SE_SOBEM if atual[k] > anterior[k] * 1.1]
        melhores = [k for k in RUINS_SE_SOBEM if atual[k] < anterior[k] / 1.1]
        alvo = self.pilha_versoes.pop()
        nome = self.versao_nome[alvo]
        nome = nome if isinstance(nome, str) else f"versão {nome}"
        self._trocar_versao(t, dict(anterior), nome, "reversão pedida pela operação", ato=reg["numero"])
        self.pilha_versoes.pop()                                                            # a reversão não empilha a volta
        reg.update(efetivo_em=t, util=bool(piores), encurtou=[p for k in piores for p in self._onde(k)],
                   piorou_de_lado=[p for k in melhores for p in self._onde(k)] + [["porta de entrada", "fila de espera"],
                                                                                 ["erros do serviço", "tempo esgotado no minuto"]],
                   custo="o reinício da implantação: dois minutos com 60% da capacidade",
                   por_que=("a versão no ar era pior que a anterior em " + ", ".join(NOME_VARIAVEL[k] for k in piores)) if piores
                   else "a versão no ar não era pior que a anterior",
                   resposta=f"Pedido tratado. Voltamos para a {nome}.")

    def _ato_instrucoes(self, t, reg):
        if not self.pilha_instrucoes:
            reg.update(resposta="Não há instruções anteriores para voltar.", util=False, por_que="não havia instruções anteriores")
            return
        atual, anterior = self.instrucoes[self.instrucao_no_ar], self.instrucoes[self.pilha_instrucoes[-1]]
        piores = ["recusa"] if atual["recusa"] > anterior["recusa"] * 1.1 else []
        lado = ["tamanho_saida"] if abs(math.log(atual["tamanho_saida"] / anterior["tamanho_saida"])) > 0.05 else []
        alvo = self.pilha_instrucoes.pop()
        nome = self.instrucao_nome[alvo]
        nome = nome if isinstance(nome, str) else f"instruções {nome}"
        self._trocar_instrucao(t, dict(anterior), nome, "volta pedida por quem observa", ato=reg["numero"])
        self.pilha_instrucoes.pop()
        reg.update(efetivo_em=t, util=bool(piores), encurtou=[p for k in piores for p in self._onde(k)],
                   piorou_de_lado=([p for k in lado for p in self._onde(k)]) + ([] if piores else self._onde("recusa")),
                   custo=None, por_que="as instruções no ar recusavam mais que as anteriores" if piores
                   else "as instruções no ar não recusavam mais que as anteriores",
                   resposta=f"Pedido tratado. Voltamos às {nome}.")

    def _ato_capacidade(self, t, reg):
        h = self._hora_passada()
        antes = self.capacidade
        teto = self.capacidade_inicial * TETO_CAPACIDADE
        if antes >= teto * (1 - 1e-9):
            reg.update(util=False, por_que=f"a capacidade já estava no teto ({TETO_CAPACIDADE:.0f} vezes a da criação)",
                       resposta=f"Pedido recusado. A capacidade já está no teto de {teto / 1000:.1f} mil tokens por minuto "
                                f"({TETO_CAPACIDADE:.0f} vezes a da criação); acima dele o serviço não cresce.")
            return
        self.capacidade = min(antes * 1.5, teto)
        taxa = (self.capacidade - antes) / 1000 * self.preco_capacidade * PROVISIONAMENTO_MIN
        self._provisionamento += taxa
        util = h["uso_maximo"] > 0.9 or h["fila_media"] > 0 or h["falhas"] > 0.02 * max(1, h["chamadas"])
        self.r["mudancas_de_capacidade"].append({"t": t, "de_mil_tokens_por_minuto": round(antes / 1000, 1),
                                                 "para_mil_tokens_por_minuto": round(self.capacidade / 1000, 1),
                                                 "no_teto": self.capacidade >= teto * (1 - 1e-9),
                                                 "taxa_de_provisionamento_em_reais": round(taxa, 2), "pedida_pelo_ato": reg["numero"]})
        self.eventos.append((t, "a capacidade do serviço foi aumentada"))
        no_teto = " e chegou ao teto" if self.capacidade >= teto * (1 - 1e-9) else ""
        reg.update(efetivo_em=t, util=bool(util),
                   encurtou=[["porta de entrada", "fila de espera"], ["porta de entrada", "espera na fila em ms"],
                             ["erros do serviço", "tempo esgotado no minuto"], ["erros do serviço", "limite excedido no minuto"]]
                   + [[f"pedidos de {c}", "latência média em ms"] for c in self.classes] if util else [],
                   piorou_de_lado=[["custo do serviço", "custo de capacidade no minuto em reais"], ["serviço do modelo", "capacidade em mil tokens por minuto"]],
                   custo=f"a taxa de provisionamento de {taxa:.2f} reais, cobrada de uma vez no custo de capacidade do minuto, e o custo "
                         f"de capacidade, que sobe de {antes / 1000 * self.preco_capacidade:.2f} para "
                         f"{self.capacidade / 1000 * self.preco_capacidade:.2f} reais por minuto",
                   por_que="na última hora o serviço passou de 90% de uso, teve fila ou mais de 2% de falhas" if util
                   else "na última hora o serviço não estava apertado",
                   resposta=f"Pedido tratado. A capacidade passou de {antes / 1000:.1f} para {self.capacidade / 1000:.1f} mil tokens por "
                            f"minuto{no_teto} (o teto é {teto / 1000:.1f}); a taxa de provisionamento foi de {taxa:.2f} reais e o custo de "
                            f"capacidade passa a {self.capacidade / 1000 * self.preco_capacidade:.2f} reais por minuto.")

    # ======================================================================================================== a verdade
    def verdade(self) -> dict:
        from .ligacoes import causas
        segs = {}
        for i, g in enumerate(self.segmentos):
            segs[g] = {"clientes": int(self.n_clientes[i]), "chamadas_por_cliente_por_minuto": round(float(self.taxa_cliente[i]), 4),
                       "paciencia_em_segundos": round(float(self.paciencia_ms[i]) / 1000, 1), "chance_de_reenvio": round(float(self.reenvio[i]), 3),
                       "chance_de_chamado_por_falha": round(float(self.p_chamado[i]), 4), "fuso_em_horas": int(self.fuso[i]),
                       "perfil_por_hora": {DIAS[d]: [round(float(x), 3) for x in self.perfil[i, d]] for d in range(7)}}
        estrutura = {
            "modelo": {k: round(v, 4) for k, v in self.modelo.items()},
            "classes": {c: {"tokens_de_entrada": round(float(self.tok_in[i])), "tokens_de_saida": round(float(self.tok_out[i])),
                            "ferramentas_por_pedido": float(self.ferr_por_pedido[i]), "fator_de_recusa": float(self.fator_recusa[i]),
                            "nova": i == self.classe_nova} for i, c in enumerate(self.classes)},
            "segmentos": segs,
            "ferramentas": {f: {"chance_de_falha": round(float(self.p_falha_ferr[k]), 4)} for k, f in enumerate(self.ferramentas)},
            "capacidade_inicial_em_mil_tokens_por_minuto": round(self.capacidade_inicial / 1000, 1),
            "teto_de_capacidade_em_mil_tokens_por_minuto": round(self.capacidade_inicial * TETO_CAPACIDADE / 1000, 1),
            "taxa_de_provisionamento": f"cada aumento cobra de uma vez {PROVISIONAMENTO_MIN} minutos do custo da capacidade acrescentada, no "
                                       f"custo de capacidade do minuto do aumento",
            "precos_em_reais": {"por_mil_tokens_de_entrada": round(self.preco_entrada, 4), "por_mil_tokens_de_saida": round(self.preco_saida, 4),
                                "por_mil_tokens_de_capacidade_por_minuto": round(self.preco_capacidade, 4)},
        }
        if self.nulo == "embaralhado":
            ciclos = {"ausentes": "nulo embaralhado: os clientes e as pessoas vivem num calendário sorteado em blocos de 25 a 240 minutos; "
                                  "nenhum ciclo de hora ou de dia da semana corresponde ao relógio da porta; as leis causais ficam",
                      "blocos_do_calendario": list(self.blocos)}
        else:
            ciclos = {"dia": "cada segmento usa o serviço pelo seu perfil por hora (ver estrutura.segmentos.*.perfil_por_hora: a taxa de "
                             "chamadas daquele segmento naquela hora, média 1 na semana); o atendimento resolve chamados das 8h às 18h nos dias úteis",
                      "semana": "dias úteis, sábado e domingo têm perfis próprios em cada segmento",
                      "leis_com_dia_marcado": "as versões novas sobem às terças e quintas entre 14h e 17h; as instruções mudam em dias úteis "
                                              "entre 10h e 17h"}
        r = self.r
        saida = {
            "familia": FAMILIA, "semente": self.semente, "nulo": self.nulo, "minutos": self.t,
            "convencao_do_tempo": "t = 0 é a criação (segunda-feira, 0h); cada passo avança t e faz acontecer o minuto t",
            "estrutura": estrutura, "ciclos": ciclos,
            "trocas_de_versao": r["trocas_de_versao"], "mudancas_de_instrucao": r["mudancas_de_instrucao"],
            "incidentes_de_carga": [dict(x, fim=x["fim"] if x["fim"] <= self.t else None) for x in r["incidentes_de_carga"]],
            "degradacoes": [dict(x, fim=x["fim"] if x["fim"] <= self.t else None) for x in r["degradacoes"]],
            "classes_novas": r["classes_novas"], "mudancas_de_capacidade": r["mudancas_de_capacidade"],
            "atos": r["atos"],
        }
        saida["causas"] = causas(self, saida)
        if self.nulo == "sem_troca":
            saida["observacao_do_nulo"] = "nenhuma troca programada de versão nem de instruções; as outras leis ficam nos mesmos instantes"
        elif self.nulo == "sem_degradacao":
            saida["observacao_do_nulo"] = "nenhuma degradação lenta; as outras leis ficam nos mesmos instantes"
        elif self.nulo == "surdo":
            saida["observacao_do_nulo"] = "a porta aceita atos e devolve números, mas nenhum ato chega ao mundo e nada é respondido"
        return saida
