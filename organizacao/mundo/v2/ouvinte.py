"""(v2.2) O ouvinte da porta: o que a equipe entende de um texto, além da rota.

A porta lê o texto inteiro e guarda na verdade o que entendeu:
- a rota e o componente, como antes (o nome exato do processo, o componente ou as palavras de sempre): os textos que já caíam numa
  rota continuam caindo na mesma;
- o processo e o campo pelo nome que aparece nos painéis, de qualquer processo (não só das rotas): "fila de trabalhos, trabalhos
  pendentes", "chamados de frete: escalados", "rota busca, latência média"; o campo também pelo nome curto ("latência média",
  "respostas com erro") e por alguns nomes de uso ("erros", "latência", "percentil 95", "requisições");
- o tempo: "desde o dia 12, 10h", "desde o dia 12", "há duas horas", "há 30 minutos", "nas últimas 3 horas", "na última hora",
  "desde ontem", "desde hoje", "desde as 10h", "depois da liberação" (a última implantação);
- o tipo do pedido: "olhar e dizer" (digam, informem, mostrem, quanto, como está), "corrigir ou reverter" (corrijam, consertem,
  revertam, desfaçam, resolvam, verifiquem, refaçam os testes) ou "pôr à frente da fila" (priorizem, ponham na frente, passem à
  frente, primeiro os); sem nenhum desses, `null`, e a equipe faz o que sempre fez com um pedido;
- se a equipe reconhece alguma coisa no texto: uma rota, um componente, um processo, um campo, ou as palavras do trabalho dela. Um
  pedido em que a equipe não reconhece nada volta com uma pergunta ("qual rota, qual campo?") em vez de virar leitura do painel.

O tempo é contado no relógio da porta: o dia N começa em t = N x 1440 (o dia 0 é o da criação).

Para conferir os atos de uma vida já gravada (a rota de cada um tem de ser a mesma):
    python -m organizacao.mundo.v2.ouvinte <verdade.json>"""
import re
import unicodedata

from .cadastro import NOME_COMPONENTE, ROTA_COMPONENTE, MINUTOS_DIA

TIPOS_DE_PEDIDO = ("olhar e dizer", "corrigir ou reverter", "pôr à frente da fila")
SUFIXOS = (" no minuto", " em ms", " em %", " em mb", " em gb", " em minutos", " em horas", " em reais", " em milhares",
           " em milhares de reais", " no dia", " no mes", " hoje", " agora")
APELIDOS_DE_CAMPO = {"erros": "respostas com erro no minuto", "erro": "respostas com erro no minuto",
                     "latencia": "latência média em ms", "lentidao": "latência média em ms", "percentil 95": "latência do percentil 95 em ms",
                     "p95": "latência do percentil 95 em ms", "requisicoes": "requisições no minuto", "acessos": "requisições no minuto",
                     "recusadas": "respostas recusadas no minuto"}
NUMEROS = {"um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9,
           "dez": 10, "onze": 11, "doze": 12, "quinze": 15, "vinte": 20, "trinta": 30, "quarenta": 40, "meia": 0.5}
UNIDADE = {"minuto": 1, "minutos": 1, "hora": 60, "horas": 60, "dia": MINUTOS_DIA, "dias": MINUTOS_DIA}
_N = r"(\d+|" + "|".join(NUMEROS) + r")"
# as palavras do trabalho de cada equipe: com uma delas a equipe sabe do que se trata, mesmo sem rota nem processo
VOCABULARIO = {
    "operação": ("volume", "banco", "disco", "servidor", "memoria", "fila de trabalho", "versao", "liberacao", "implantacao", "sonda",
                 "fora do ar", "processador", "infra", "alerta", "reiniciar", "reinicio"),
    "desenvolvimento": ("bug", "codigo", "commit", "revisao", "teste", "sprint", "correcao", "versao", "liberacao", "funcao"),
    "qualidade": ("teste", "bug", "regressao", "versao", "liberacao", "qualidade", "reprova"),
    "atendimento": ("chamado", "cliente", "fila de atendimento", "prazo", "reclama", "atendimento", "escalad"),
    "vendas": ("funil", "proposta", "negociac", "lead", "venda", "negocio", "prospec", "ligac", "cliente", "contrato", "meta"),
    "produto": ("historia", "backlog", "funcionalidade", "epico", "refinamento", "roteiro", "melhoria", "cliente", "recurso", "produto"),
    "gestão": ("pessoa", "ferias", "vaga", "candidat", "quadro", "reuni", "alinha", "priorid", "contrat", "equipe", "lideranc",
               "direcao", "mes", "semana", "hora extra", "cansac"),
}
_TIPO = (
    ("corrigir ou reverter", r"\b(corrij|corrig|consert|revert|desfac|desfaz|arrum|resolv|verifiqu|refac|refaz|testem|rodem os testes|"
                             r"voltem? (a|para a|pra) versao)"),
    ("pôr à frente da fila", r"\b(prioriz|a frente|na frente|furar a fila|primeiro os|primeiro as|antes dos outros|antes das outras|"
                             r"adiantem|passem .{0,40}frente|ponham .{0,40}frente)"),
    ("olhar e dizer", r"\b(digam|diga|informem|informe|me contem|contem|mostrem|mostre|quanto|quantos|quantas|como esta|como estao|"
                      r"qual e|qual o|qual a|deem uma olhada|olhem e digam|vejam e digam|olhar e dizer)"),
)


# (v2.3) os tipos que a v2.2 não lia: o infinitivo e o presente de "verificar"; "olhar ... e dizer" com o campo no meio
_TIPO_V23 = (
    ("corrigir ou reverter", r"\bverific(ar|a|ou|ando|arem)\b"),
    ("olhar e dizer", r"\b(olhar|olhem|olhe|ver|vejam|veja|conferir|confiram)\b.{0,120}\b(dizer|digam|diga|contar|contem|informar|informem)\b"),
)


def simples(texto):
    return "".join(c for c in unicodedata.normalize("NFD", str(texto).lower()) if unicodedata.category(c) != "Mn")


def _contem(texto, nome):
    return re.search(r"(?<![a-z0-9])" + re.escape(nome) + r"(?![a-z0-9])", texto) is not None


def _numero(x):
    return float(x) if x.isdigit() else NUMEROS[x]


class Ouvinte:
    """Os nomes do mundo, simplificados, para achar processo e campo num texto."""

    def __init__(self, processos):
        self.processos = [(p.nome, simples(p.nome), list(p.campos)) for p in processos]
        self.processos.sort(key=lambda x: -len(x[1]))
        por_campo = {}
        for nome, _, campos in self.processos:
            for c in campos:
                por_campo.setdefault(c, []).append(nome)
        self.donos = por_campo
        self.campos = {nome: self._formas(campos) for nome, _, campos in self.processos}
        self.todos_campos = self._formas(sorted(por_campo))
        self.componentes = {simples(n): c for c, n in NOME_COMPONENTE.items()}
        # "chamados de busca" é o processo "chamados de catálogo e busca": o nome de uma rota vale pelo do seu componente
        from .cadastro import NOME_ROTA
        nomes = {nome for nome, _, _ in self.processos}
        self.apelidos = []
        for r, c in ROTA_COMPONENTE.items():
            for prefixo in ("chamados de ", "bugs de ", "código de "):
                alvo = prefixo + NOME_COMPONENTE[c]
                apelido = simples(prefixo + NOME_ROTA[r])
                if alvo in nomes and apelido != simples(alvo):
                    self.apelidos.append((apelido, alvo))
        self.apelidos.sort(key=lambda x: -len(x[0]))

    @staticmethod
    def _formas(campos):
        """Cada campo pelo nome inteiro, pelo nome sem o sufixo de unidade e pelos apelidos de uso, da forma mais longa à mais curta."""
        formas = []
        for c in campos:
            s = simples(c)
            formas.append((s, c))
            for suf in SUFIXOS:
                if s.endswith(suf) and len(s) - len(suf) >= 4:
                    formas.append((s[: -len(suf)], c))
        for apelido, c in APELIDOS_DE_CAMPO.items():
            if c in campos:
                formas.append((apelido, c))
        formas.sort(key=lambda x: -len(x[0]))
        return formas

    def apelidos_do_processo(self, processo):
        """(v2.3) Os campos de um processo pela palavra que os distingue: "falhas" para "verificações com falha no minuto", "erros"
        para "cotações com erro no minuto", "falhas" para "falhas de trabalho no minuto"; no plural e no singular."""
        cache = self.__dict__.setdefault("_apelidos", {})
        if processo not in cache:
            formas = []
            for _, s, campos in self.processos:
                if _ != processo:
                    continue
                for c in campos:
                    sc = simples(c)
                    m = re.search(r"\bcom (\w+)", sc) or re.match(r"(\w+)", sc)
                    if m:
                        w = m.group(1)
                        for forma in {w, w[:-1] if w.endswith("s") else w + "s"}:
                            if len(forma) >= 4:
                                formas.append((forma, c))
            nomes = {}
            for forma, c in formas:
                nomes.setdefault(forma, set()).add(c)
            cache[processo] = sorted(((f, next(iter(cs))) for f, cs in nomes.items() if len(cs) == 1), key=lambda x: -len(x[0]))
        return cache[processo]

    # ---------- o processo e o campo ----------
    def processo_e_campo(self, x, rota):
        processo = None
        for nome, s, _ in self.processos:
            if _contem(x, s) or (s.startswith("rota ") and re.search(r"\brota (de |do |da |das |dos )?" + re.escape(s[5:]) + r"\b", x)):
                processo = nome
                break
        if processo is None:
            processo = next((alvo for apelido, alvo in self.apelidos if _contem(x, apelido)), None)
        campo = None
        if processo is not None:
            campo = next((c for forma, c in self.campos[processo] if _contem(x, forma)), None)
        else:
            for forma, c in self.todos_campos:
                if _contem(x, forma):
                    campo = c
                    break
            if campo is not None:
                donos = self.donos[campo]
                if len(donos) == 1:
                    processo = donos[0]
                elif rota is not None and f"rota {_nome_rota(rota)}" in donos:
                    processo = f"rota {_nome_rota(rota)}"
        return processo, campo

    def componente_do_processo(self, processo):
        if processo is None:
            return None
        s = simples(processo)
        if s.startswith("rota "):
            return None
        for prefixo in ("chamados de ", "bugs de ", "codigo de "):
            if s.startswith(prefixo):
                return self.componentes.get(s[len(prefixo):])
        return None

    # ---------- o texto inteiro ----------
    def entender(self, texto, equipe, t, rota, componente, ultima_implantacao=None):
        """O que a equipe entende do texto, dado o minuto `t` e a rota e o componente que a porta já achou (a leitura de sempre)."""
        x = simples(texto)
        processo, campo = self.processo_e_campo(x, rota)
        comp = componente if componente is not None else self.componente_do_processo(processo)
        desde, desde_texto = self.tempo(x, t, ultima_implantacao)
        tipo = next((nome for nome, padrao in _TIPO if re.search(padrao, x)), None)
        # (v2.3) o que a leitura da v2.2 não achava, procurado só nas palavras de quem pede (antes do primeiro ";"): nunca muda o que
        # ela já achou
        proprio = simples(str(texto).split(";", 1)[0])
        if tipo is None:
            tipo = next((nome for nome, padrao in _TIPO_V23 if re.search(padrao, proprio)), None)
        if processo is not None and campo is None:
            campo = next((c for forma, c in self.apelidos_do_processo(processo) if _contem(proprio, forma)), None)
        reconhece = rota is not None or comp is not None or processo is not None or campo is not None or \
            any(re.search(r"(?<![a-z])" + re.escape(p), x) for p in VOCABULARIO.get(equipe, ()))
        return {"processo": processo, "campo": campo, "rota": rota, "componente": comp, "tipo": tipo, "desde": desde,
                "desde_texto": desde_texto, "reconhece": reconhece}

    @staticmethod
    def tempo(x, t, ultima_implantacao=None):
        hoje = t // MINUTOS_DIA
        m = re.search(r"\b(?:desde|a partir|depois|antes)? ?(?:d?o |no )?dia (\d+)(?:[ ,]+(?:as |a |por volta das )?(\d{1,2}) ?(?:h|:|horas)"
                      r" ?(\d{2})?)?", x)
        if m:
            d, h, mi = int(m.group(1)), int(m.group(2) or 0), int(m.group(3) or 0)
            if h < 24 and mi < 60:
                return d * MINUTOS_DIA + h * 60 + mi, m.group(0).strip()
        m = re.search(r"\bha " + _N + r" (minutos?|horas?|dias?)\b", x)
        if m:
            return int(round(t - _numero(m.group(1)) * UNIDADE[m.group(2)])), m.group(0)
        m = re.search(r"\bha (meia hora|uma hora|um dia|pouco)\b", x)
        if m:
            return t - {"meia hora": 30, "uma hora": 60, "um dia": MINUTOS_DIA, "pouco": 30}[m.group(1)], m.group(0)
        m = re.search(r"\bnas? ultimas? (?:" + _N + r" )?(minutos?|horas?|dias?)\b", x)
        if m:
            n = _numero(m.group(1)) if m.group(1) else 1
            return int(round(t - n * UNIDADE[m.group(2)])), m.group(0)
        m = re.search(r"\bdesde (?:as |a )?(\d{1,2}) ?(?:h|:|horas) ?(\d{2})?", x)
        if m and int(m.group(1)) < 24:
            ini = hoje * MINUTOS_DIA + int(m.group(1)) * 60 + int(m.group(2) or 0)
            return (ini if ini <= t else ini - MINUTOS_DIA), m.group(0)
        if re.search(r"\b(desde )?anteontem\b", x):
            return (hoje - 2) * MINUTOS_DIA, "desde anteontem"
        if re.search(r"\b(desde|de|depois de) ontem\b", x):
            return (hoje - 1) * MINUTOS_DIA, "desde ontem"
        if re.search(r"\b(desde hoje|hoje cedo|desde cedo|desde o comeco do dia)\b", x):
            return hoje * MINUTOS_DIA, "desde hoje"
        if ultima_implantacao is not None and re.search(r"\b(depois|desde) (d?a )?(ultima )?(liberacao|implantacao|versao nova)\b", x):
            return ultima_implantacao, "desde a última implantação"
        return None, None


class Painel:
    """O que os painéis mostraram: os valores de cada campo minuto a minuto nas últimas seis horas e, por hora, nos últimos 31 dias
    (soma, máximo e minutos). É o que uma equipe olha quando lhe pedem para olhar um campo desde um instante. Só lê o que já saiu
    pela porta: não muda nada no mundo."""
    MINUTOS = 360
    HORAS = 31 * 24

    def __init__(self, processos):
        import numpy as np
        self.nomes = [(p.nome, list(p.campos)) for p in processos]
        self.indice = {}
        for p in processos:
            for c in p.campos:
                self.indice[(p.nome, c)] = len(self.indice)
        n = len(self.indice)
        self.min = np.full((self.MINUTOS, n), np.nan, dtype=np.float32)
        self.soma = np.zeros((self.HORAS, n), dtype=np.float64)
        self.maximo = np.full((self.HORAS, n), -np.inf, dtype=np.float32)
        self.n = np.zeros(self.HORAS, dtype=np.int32)
        self.hora_de = np.full(self.HORAS, -1, dtype=np.int64)

    def guardar(self, t, saida):
        import numpy as np
        v = np.fromiter((x for nome, _ in self.nomes for x in saida[nome]), dtype=np.float32, count=len(self.indice))
        self.min[t % self.MINUTOS] = v
        h = t // 60
        k = h % self.HORAS
        if self.hora_de[k] != h:
            self.hora_de[k] = h
            self.soma[k] = 0.0
            self.maximo[k] = -np.inf
            self.n[k] = 0
        self.soma[k] += v
        np.maximum(self.maximo[k], v, out=self.maximo[k])
        self.n[k] += 1

    def ler(self, processo, campo, desde, t):
        """(média por minuto, máximo, valor agora, minutos olhados, desde quando de fato) do campo entre `desde` e `t`."""
        import numpy as np
        j = self.indice.get((processo, campo))
        if j is None or t < 1:
            return None
        desde = max(1, t - 60 if desde is None else int(desde))
        agora = float(self.min[t % self.MINUTOS, j])
        if t - desde < self.MINUTOS:
            idx = [u % self.MINUTOS for u in range(desde, t + 1)]
            vals = self.min[idx, j]
            vals = vals[~np.isnan(vals)]
            if len(vals) == 0:
                return None
            return float(vals.mean()), float(vals.max()), agora, len(vals), desde
        h0 = max(desde // 60, t // 60 - self.HORAS + 1)
        ks = [h % self.HORAS for h in range(h0, t // 60 + 1) if self.hora_de[h % self.HORAS] == h]
        n = int(self.n[ks].sum())
        if n == 0:
            return None
        return float(self.soma[ks, j].sum() / n), float(self.maximo[ks, j].max()), agora, n, h0 * 60


def _nome_rota(rota):
    from .cadastro import NOME_ROTA
    return NOME_ROTA[rota]


def quando(t):
    d, m = divmod(int(t), MINUTOS_DIA)
    return f"dia {d}, {m // 60:02d}h{m % 60:02d}"


def conferir_atos(caminho):
    """Relê o texto de cada ato de uma verdade gravada (verdade.json de rodar.py, ou o dict de verdade() salvo em JSON): a rota tem de
    ser a mesma que a porta achou quando o ato chegou; diz também o que o ouvinte entende e quais pedidos voltariam com pergunta."""
    import json
    from collections import Counter
    from .conectores import Conectores
    from .atos import rota_do_texto
    from .mundo import Processo
    with open(caminho, encoding="utf-8") as f:
        v = json.load(f)
    v = v.get("verdade", v)
    o = Ouvinte([Processo(n, list(c)) for n, c in Conectores().processos])
    mesma, outra, tipos, esclarecer = 0, [], Counter(), 0
    for a in v["atos"]:
        r = rota_do_texto(a["texto"])
        e = o.entender(a["texto"], a["equipe"], a["recebido"], r, ROTA_COMPONENTE[r] if r else None)
        if r == a["rota"]:
            mesma += 1
        else:
            outra.append((a["numero"], a["texto"], a["rota"], r))
        tipos[(a["tipo"], e["tipo"], e["processo"] is not None, e["campo"] is not None, e["desde"] is not None)] += 1
        esclarecer += a["tipo"] == "pedido" and not e["reconhece"]
    print(f"{len(v['atos'])} atos; {mesma} na mesma rota; {len(outra)} em outra")
    for x in outra[:20]:
        print("   outra rota:", x)
    print(f"pedidos que voltariam com pergunta (nada reconhecível): {esclarecer}")
    print("(tipo do ato, tipo do pedido entendido, com processo, com campo, com tempo): quantos")
    for k, n in tipos.most_common():
        print("  ", k, n)
    return not outra


__all__ = ["Ouvinte", "Painel", "TIPOS_DE_PEDIDO", "simples", "quando", "conferir_atos"]

if __name__ == "__main__":
    import sys
    sys.exit(0 if conferir_atos(sys.argv[1]) else 1)
