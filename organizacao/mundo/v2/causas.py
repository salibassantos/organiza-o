"""A causa dos chamados na verdade (v1.4 e v2.1): a lei que liga o erro e a lentidão sentidos pelo cliente numa rota aos chamados do
componente da rota, as janelas em que essa lei esteve ativa e a classificação de um par de campos em três categorias:

- causa declarada: há um mecanismo do mundo que leva de um campo ao outro (a lei abaixo, ou o "onde" de um registro);
- causa comum: os dois campos se mexem juntos porque a mesma coisa mexe nos dois (um incidente, uma queda do processo, o calendário),
  sem que um cause o outro;
- sem relação: nenhuma das duas.

Nada aqui é lido pelas pessoas nem pelos sistemas; é só anotação. O mundo anda igual com ou sem este módulo."""
from .cadastro import ROTAS, NOME_ROTA, ROTA_COMPONENTE, NOME_COMPONENTE
from .conectores import lista_de_processos

LIMIAR_LENTIDAO_MS = 4000.0       # a resposta acima disso é sentida como lenta pelo cliente (clientes.py)
JUNTA_MIN = 60                    # dois eventos da mesma rota a menos de uma hora ficam na mesma janela
CAMPOS_CHAMADOS = ("novos no minuto", "abertos", "escalados", "resolvidos no minuto")
ORIGEM = {"erro": ("respostas com erro no minuto",), "lentidão": ("latência média em ms", "latência do percentil 95 em ms")}
ABANDONO = ["sessões dos clientes", "sessões abandonadas depois de erro no minuto"]
CATEGORIAS = ("causa declarada", "causa comum (incidente)", "causa comum (queda do processo)", "causa comum (calendário)", "sem relação")

MECANISMO = {
    "erro": "o cliente que recebe erro numa rota tenta mais duas vezes; se continua errando, abandona a sessão (no mesmo minuto) e se "
            "frustra; a frustração abre um chamado do componente da rota com chance de 5% (básico), 8% (pro) ou 14% (empresarial), "
            "que cresce 50% a cada frustração anterior do mesmo dia, até 70%; se o cliente já tem chamado aberto daquele componente, ele "
            "só comenta nele",
    "lentidão": "a primeira resposta acima de 4 segundos numa sessão frustra o cliente em 35% das vezes; a chance de chamado é a do erro "
                "vezes 0,6",
}
ATRASO = {"novos no minuto": "o chamado chega depois de um atraso humano lognormal de mediana 12 minutos (sigma 0,75) mais 1 minuto: "
                             "metade em até 13 minutos, 90% em até 32, 99% em até 70",
          "abertos": "o chamado conta como aberto desde que chega até ser resolvido",
          "escalados": "o atendimento escala quando pega o chamado (minutos a horas depois): no incidente, ao item do incidente; com "
                       "defeito, ao bug do componente",
          "resolvidos no minuto": "horas depois, quando o atendimento ou o desenvolvimento resolve",
          "sessões abandonadas depois de erro no minuto": "no mesmo minuto do erro"}

# os processos cujos campos todos mudam juntos quando o produto inteiro para (incidente ou queda do processo)
PREFIXOS_PRODUTO_PARADO = ("rota ", "sonda de disponibilidade", "servidor da aplicação", "banco do produto", "fila de trabalhos",
                           "gateway de pagamento", "transportadoras", "pedidos", "pagamentos", "notas fiscais", "e-mails do produto",
                           "sessões dos clientes", "região ", "clientes do plano ", "canal de atendimento ", "chamados de ",
                           "projeto Suporte", "fluxo da equipe de atendimento", "fluxo da equipe de operação",
                           "projeto Infraestrutura", "bugs de infraestrutura")


def rota_proc(rota):
    return f"rota {NOME_ROTA[rota]}"


def chamados_proc(comp):
    return f"chamados de {NOME_COMPONENTE[comp]}"


def pares_da_lei(rota, tipo):
    """Os pares (de, para) que a lei liga para uma rota e um tipo de evento."""
    de = [[rota_proc(rota), c] for c in ORIGEM[tipo]]
    para = [[chamados_proc(ROTA_COMPONENTE[rota]), c] for c in CAMPOS_CHAMADOS] + ([list(ABANDONO)] if tipo == "erro" else [])
    return de, para


def leis():
    """As leis declaradas que ligam rota a chamados, uma por rota e por tipo de evento."""
    out = []
    for rota in ROTAS:
        for tipo in ("erro", "lentidão"):
            de, para = pares_da_lei(rota, tipo)
            out.append({"de": de, "para": para, "tipo": tipo, "componente": NOME_COMPONENTE[ROTA_COMPONENTE[rota]],
                        "categoria": "causa declarada", "mecanismo": MECANISMO[tipo],
                        "atraso": {c: ATRASO[c] for c in [p[1] for p in para]}})
    return out


def campos_produto_parado():
    return [[nome, c] for nome, campos in lista_de_processos() if nome.startswith(PREFIXOS_PRODUTO_PARADO) for c in campos]


class Janelas:
    """As janelas de rota: os trechos em que clientes sentiram erro ou lentidão numa rota (eventos a menos de uma hora um do outro)."""

    def __init__(self):
        self.abertas = {}

    def evento(self, t, rota, tipo, contexto, guardar):
        j = self.abertas.get((rota, tipo))
        if j is not None and t - j["fim"] <= JUNTA_MIN:
            j["fim"] = t
            j["sessoes_afetadas"] += 1
            if contexto not in j["contextos"]:
                j["contextos"].append(contexto)
            return j
        if j is not None:
            self._fechar(j)
        de, para = pares_da_lei(rota, tipo)
        j = {"rota": rota, "tipo": tipo, "inicio": t, "fim": t, "duracao_min": None, "aberta": True, "sessoes_afetadas": 1,
             "contextos": [contexto], "de": de, "para": para, "categoria": "causa declarada", "chamados_gerados": 0,
             "chamados_escalados": 0, "chamados": []}
        self.abertas[(rota, tipo)] = j
        guardar(j)
        return j

    def _fechar(self, j):
        j["aberta"] = False
        j["duracao_min"] = j["fim"] - j["inicio"] + 1
        del self.abertas[(j["rota"], j["tipo"])]

    def fechar_velhas(self, t, fechou=None):
        for j in [j for j in self.abertas.values() if t - j["fim"] > JUNTA_MIN]:
            self._fechar(j)
            if fechou:
                fechou(j)


def achar_janela(lista, rota, tipo, quando):
    for j in reversed(lista):
        if j["rota"] == rota and j["tipo"] == tipo and j["inicio"] <= quando <= j["fim"]:
            return j
    return None


def classificar_par(verdade, de, para, inicio=None, fim=None):
    """Classifica o par (de, para), cada um [processo, campo], numa das categorias, olhando o intervalo [inicio, fim] quando dado.
    Devolve {"categoria": a primeira que vale na ordem de CATEGORIAS, "todas": todas as que valem, "provas": os registros}."""
    de, para = list(de), list(para)
    causas = verdade.get("causas", {})
    sobrepoe = lambda a, b: inicio is None or (a is not None and (b is None or b >= inicio) and (fim is None or a <= fim))
    todas, provas = [], []
    for lei in causas.get("leis", []):
        if de in lei["de"] and para in lei["para"]:
            ativas = [j for j in causas.get("janelas_de_rota", []) if j["de"] == lei["de"] and sobrepoe(j["inicio"], j["fim"])]
            prova = {"lei": lei["de"][0][0] + " -> " + lei["para"][0][0], "tipo": lei["tipo"], "janelas_no_intervalo": len(ativas),
                     "chamados_gerados_no_intervalo": sum(j["chamados_gerados"] for j in ativas)}
            if ativas:                      # a lei só conta como causa onde agiu: alguém sentiu o erro ou a lentidão na rota
                todas.append("causa declarada")
            else:
                prova["observacao"] = "a lei existe, mas não agiu no intervalo olhado (nenhum cliente sentiu o evento na rota)"
            provas.append(prova)
            break
    for ep in verdade.get("episodios_de_defeito_no_ar", []):
        onde = ep.get("onde", [])
        if de in onde and para in onde and de[0].startswith("rota ") and sobrepoe(ep["liberado_em"], ep["saiu_do_ar"]) \
                and "causa declarada" not in todas:
            todas.append("causa declarada")
            provas.append({"episodio_de_defeito": ep["funcao"], "liberado_em": ep["liberado_em"]})
    for nome, chave in (("incidentes", "causa comum (incidente)"), ("quedas", "causa comum (queda do processo)")):
        lista = verdade["incidentes"] if nome == "incidentes" else verdade.get("quedas_do_processo_por_memoria", {}).get("sonda_parada", [])
        comuns = causas.get("campos_quando_o_produto_para", [])
        for inc in lista:
            if de in comuns and para in comuns and sobrepoe(inc["inicio"], (inc.get("fim") or inc["inicio"]) + 360):
                todas.append(chave)
                provas.append({nome: inc["inicio"]})
                break
    cal = verdade.get("calendario")
    if cal:
        a, b = cal["campos"].get(f"{de[0]}.{de[1]}"), cal["campos"].get(f"{para[0]}.{para[1]}")
        if a and b and a.get("movido_pelo_calendario") and b.get("movido_pelo_calendario"):
            todas.append("causa comum (calendário)")
            prova = {"motores_em_comum": sorted(set(a["motores"]) & set(b["motores"])),
                     "motores_de_cada_um": [a["motores"], b["motores"]],
                     "fracao_da_variancia": [a.get("fracao_da_variancia"), b.get("fracao_da_variancia")]}
            try:
                from .calendario import correlacao_dos_perfis
                prova["correlacao_dos_perfis_por_hora_da_semana"] = correlacao_dos_perfis(f"{de[0]}.{de[1]}", f"{para[0]}.{para[1]}")
            except ImportError:
                pass
            provas.append(prova)
    if not todas:
        todas.append("sem relação")
    todas = sorted(set(todas), key=CATEGORIAS.index)
    return {"categoria": todas[0], "todas": todas, "provas": provas}
