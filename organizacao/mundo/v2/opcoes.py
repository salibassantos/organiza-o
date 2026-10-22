"""(v2.3) As opções do mundo, todas desligadas por padrão: desligadas, o mundo é o da v2.2, byte a byte.

- `porta`: um processo por equipe, "porta da equipe de X", com dois campos de contagem: "textos chegados no minuto" (o que chegou dela
  pela porta naquele minuto: respostas, avisos de tratado, pedidos de esclarecimento) e "itens abertos" (os atos de quem pede que
  chegaram a ela e ainda não foram respondidos nem expiraram, o que um sistema de chamados mostra a quem pediu). Só contagens: o
  campo não diz a que ato uma chegada responde, e o interior da equipe (fila, cansaço, atenção, confiança) continua só na verdade.
- `relogio`: um processo "relógio" com a hora do dia (0 a 23), o dia da semana (0 = segunda) e o minuto do mundo, no relógio da
  porta (no nulo embaralhado também: é o relógio, não o calendário sorteado).
- `agenda_calada`: (início, fim) em minutos do mundo. Um feriado coletivo: as datas que começam dentro do trecho viram dias sem
  expediente para a empresa e para os clientes. Ninguém trabalha, a agenda não marca nem realiza reunião, não há evento de equipe
  (contratação, saída, sprint), os clientes quase não usam o produto (como num domingo). A verdade guarda o trecho pedido e as datas.

Cada opção liga pelo argumento do `Mundo` ou, se o argumento não vier, pela variável de ambiente: MUNDO_PORTA=1, MUNDO_RELOGIO=1,
MUNDO_AGENDA_CALADA=inicio,fim (para a bancada ligar sem tocar no código que monta o mundo)."""
import os

from .cadastro import EQUIPES, MINUTOS_DIA

CAMPOS_PORTA = ["textos chegados no minuto", "itens abertos"]
CAMPOS_RELOGIO = ["hora do dia", "dia da semana", "minuto do mundo"]


def nome_da_porta(equipe):
    return f"porta da equipe de {equipe}"


def _liga(valor, variavel):
    if valor is not None:
        return bool(valor)
    return os.environ.get(variavel, "").strip().lower() in ("1", "sim", "true", "ligado")


def _trecho(valor):
    if valor is None:
        txt = os.environ.get("MUNDO_AGENDA_CALADA", "").strip()
        if not txt:
            return None
        valor = [int(x) for x in txt.replace(";", ",").split(",")]
    if not valor:
        return None
    inicio, fim = int(valor[0]), int(valor[1])
    if fim <= inicio:
        raise ValueError("a agenda calada precisa de fim depois do início")
    return inicio, fim


def ler(porta=None, relogio=None, agenda_calada=None):
    return {"porta": _liga(porta, "MUNDO_PORTA"), "relogio": _liga(relogio, "MUNDO_RELOGIO"), "agenda_calada": _trecho(agenda_calada)}


def datas_do_feriado(trecho):
    """As datas (dias do relógio da porta) cuja meia-noite cai dentro do trecho [início, fim)."""
    if trecho is None:
        return frozenset()
    inicio, fim = trecho
    primeira = -(-inicio // MINUTOS_DIA)
    return frozenset(d for d in range(primeira, fim // MINUTOS_DIA + 1) if inicio <= d * MINUTOS_DIA < fim)


def processos_novos(opcoes):
    """(nome, campos) dos processos que as opções acrescentam, sempre depois dos da v2.2 e nesta ordem."""
    out = []
    if opcoes["porta"]:
        out += [(nome_da_porta(e), list(CAMPOS_PORTA)) for e in EQUIPES]
    if opcoes["relogio"]:
        out.append(("relógio", list(CAMPOS_RELOGIO)))
    return out


def ler_minuto(m, t, saida):
    """Acrescenta à saída do minuto os campos das opções ligadas."""
    op = m.opcoes
    if op["porta"]:
        abertos = dict.fromkeys(EQUIPES, 0)
        for a in m.porta.atos.values():
            if a["estado"] in ("aberto", "em tratamento"):
                abertos[a["equipe"]] += 1
        chegaram = m.porta.textos_do_minuto
        for e in EQUIPES:
            saida[nome_da_porta(e)] = [float(chegaram.get(e, 0)), float(abertos[e])]
    if op["relogio"]:
        saida["relógio"] = [float((t % MINUTOS_DIA) // 60), float((t // MINUTOS_DIA) % 7), float(t)]


def para_a_verdade(m):
    """O que a verdade ganha quando alguma opção está ligada (nada, se todas estão desligadas)."""
    op = m.opcoes
    if not (op["porta"] or op["relogio"] or op["agenda_calada"]):
        return {}
    v = {"opcoes": {"porta": op["porta"], "relogio": op["relogio"], "agenda_calada": list(op["agenda_calada"]) if op["agenda_calada"] else None}}
    if op["agenda_calada"]:
        datas = sorted(datas_do_feriado(op["agenda_calada"]))
        v["agenda_calada"] = {
            "pedido": {"inicio": op["agenda_calada"][0], "fim": op["agenda_calada"][1]},
            "datas": datas,
            "inicio": datas[0] * MINUTOS_DIA if datas else None,
            "fim": (datas[-1] + 1) * MINUTOS_DIA if datas else None,
            "como": "feriado coletivo: cada data do trecho é um dia sem expediente para a empresa e para os clientes; ninguém trabalha, "
                    "a agenda não marca nem realiza reunião, não há evento de equipe (contratação, saída, sprint, reunião de rotina) e os "
                    "clientes usam o produto como num domingo; as tarefas agendadas do servidor continuam",
            "onde": "todos os processos movidos pelo calendário das pessoas e dos clientes (ver calendario.campos)"}
    return v
