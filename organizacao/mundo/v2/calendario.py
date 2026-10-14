"""(v2.1) O que o calendário move em cada processo: o gabarito da causa comum pelo calendário.

Duas camadas:
- os motores declarados: as regras do mundo que dependem da hora, do dia da semana, do sprint ou do mês, com os números do código, e,
  para cada campo da porta, quais motores chegam a ele e por qual caminho;
- a força medida: para cada campo, o perfil por hora da semana (168 médias), a fração da variância do campo que a hora da semana
  explica, e o controle: a mesma fração no nulo embaralhado, contada pelo relógio da porta (onde o calendário não corresponde ao
  relógio) e pelo calendário interno (onde ele continua mexendo).

Um campo é "movido pelo calendário" quando tem motor declarado e a fração medida passa de LIMIAR, é ao menos CONTRASTE vezes a do
controle e fica ao menos MARGEM acima dele. Dois campos movidos pelo calendário formam um par de causa comum pelo calendário (o mesmo
relógio move os dois, pelo mesmo motor ou não; a prova diz os motores em comum e a correlação dos perfis). O controle importa nos
campos que se acumulam devagar (chamados abertos, idade, horas extras do dia): neles poucas amostras são independentes e o acaso
sozinho já explica uma fração maior.

    python -m organizacao.mundo.v2.calendario uma <semente> <nulo|normal> <dias> <arquivo.npz>
    python -m organizacao.mundo.v2.calendario juntar <saida.json> <arquivos normais...> -- <arquivos embaralhados...>
"""
import json
import os
import sys
import tempfile

import numpy as np

from .cadastro import MINUTOS_DIA, EQUIPES
from .conectores import lista_de_processos

LIMIAR = 0.05          # fração da variância explicada pela hora da semana
CONTRASTE = 2.0        # quantas vezes acima do controle
MARGEM = 0.05          # e quanto acima dele, em fração da variância
HORAS_SEMANA = 168

MOTORES = {
    "horário das lojas": "as lojas usam o produto no seu horário: cada loja abre entre 7h e 9h30 e fecha entre 17h e 19h30; dentro do "
                         "horário o uso segue um perfil com picos às 10h18 (+28%) e às 15h12 (+22%) e almoço das 12h às 13h30 a 55%; "
                         "fora do horário, 3,5%",
    "semana das lojas": "peso do dia: segunda 1,22, terça 1,04, quarta 1,0, quinta 0,98, sexta 0,82; sábado das 8h às 12h a 60% para 30% "
                        "das lojas (3% para as demais); domingo 2%",
    "fim do mês das lojas": "nos últimos seis dias do mês o uso sobe 12% e as compras e os relatórios pesam mais na jornada",
    "pagamento das faturas": "cada loja paga a fatura num dia entre 3 e 12 do mês, das 8h às 17h; as dúvidas de fatura vêm nos dias 2 a 5, "
                             "das 9h às 16h",
    "expediente das pessoas": "dias úteis; chegada perto das 8h45 (de 7h15 a 10h), almoço perto das 12h05 por 50 a 70 minutos, jornada de "
                              "nove horas, sexta até uma hora mais cedo; hora extra quando há pressa ou urgência; férias e faltas em dias "
                              "úteis",
    "agenda fixa": "diárias das 8h45 às 10h15 (uma por equipe), liderança às segundas 11h, semanais às segundas 14h, refinamento às "
                   "quartas; quem está em reunião não age nos sistemas",
    "sprint": "sprints de duas semanas a partir de segunda: planejamento no primeiro dia, revisão e retrospectiva na sexta da segunda "
              "semana às 15h, pressa no fim quando o sprint está atrasado, contadores do sprint que zeram",
    "liberações": "liberações às terças e quintas a partir das 15h (e sexta de manhã no fim do sprint), regressão antes, das 9h30 às 12h; "
                  "a implantação reinicia o processo e a versão nova pode mudar o trabalho e os erros das rotas",
    "tarefas do servidor": "cópia de segurança às 2h, limpeza de sessões às 3h, expurgo aos domingos 3h30, reposição de estoque às 4h, "
                           "reindexação aos domingos 4h30, resumo às 7h",
    "mês da empresa": "faturamento no dia 1 às 6h (a fila de trabalhos enche), reunião mensal no primeiro dia útil às 16h, vendas fecham "
                      "mais nos últimos seis dias do mês, contadores do quadro que zeram no mês",
    "horário do mercado": "os leads do site chegam mais das 8h às 20h nos dias úteis (seis vezes e meia mais que fora disso)",
}
USO = "as lojas abrem sessões no seu horário e cada passo da jornada é uma chamada ao produto"
LOJAS = (("horário das lojas", USO), ("semana das lojas", USO), ("fim do mês das lojas", USO))


def _m(*pares):
    return [{"motor": m, "caminho": c} for m, c in pares]


def motores_do_campo(proc, campo):
    """Os motores do calendário que chegam a um campo da porta, cada um com o caminho."""
    p, c = proc, campo
    exp = ("expediente das pessoas", "as pessoas só agem nos sistemas no expediente e fora das reuniões")
    agenda = ("agenda fixa", "as reuniões fixas tiram gente dos sistemas e enchem a agenda")
    sprint = ("sprint", "o ciclo do sprint muda o que entra, o que anda e a pressa")
    lib = ("liberações", "a implantação nos dias de liberação reinicia o processo e troca o código no ar")
    tarefas = ("tarefas do servidor", "as tarefas da madrugada ocupam o banco e o processador")
    mes = ("mês da empresa", "o faturamento do dia 1 e o fim do mês das vendas")
    if p.startswith("rota "):
        if c.startswith("latência"):
            return _m(*[(m, "mais requisições, mais carga no processador e mais espera") for m, _ in LOJAS], tarefas,
                      (lib[0], "a versão nova muda o trabalho da rota"))
        if c == "respostas com erro no minuto":
            return _m(*LOJAS, (lib[0], "a versão nova pode trazer defeito à rota"))
        return _m(*LOJAS)
    if p == "servidor da aplicação":
        if c.startswith("uso de processador"):
            return _m(*LOJAS, tarefas)
        if c.startswith("memória"):
            return _m(*[(m, "as sessões em cache crescem com o uso") for m, _ in LOJAS], (lib[0], "a implantação esvazia o cache"))
        return _m(lib)
    if p == "banco do produto":
        if "MB" in c:
            return _m(*[(m, "o banco cresce com o uso") for m, _ in LOJAS], ("tarefas do servidor", "a limpeza e o expurgo liberam espaço"))
        return _m(*LOJAS, tarefas)
    if p == "fila de trabalhos":
        return _m(*[(m, "as notas e os e-mails dos pedidos entram na fila") for m, _ in LOJAS], ("mês da empresa", "o faturamento do dia 1 enche a fila"))
    if p == "e-mails do produto":
        return _m(*LOJAS, ("mês da empresa", "as faturas do dia 1 viram e-mails"))
    if p == "estoque":
        if c == "unidades repostas no minuto":
            return _m(("tarefas do servidor", "os fornecedores repõem às 4h"))
        return _m(*[(m, "as compras gastam o estoque") for m, _ in LOJAS], ("tarefas do servidor", "a reposição às 4h"))
    if p in ("gateway de pagamento", "transportadoras", "pedidos", "pagamentos", "notas fiscais", "sessões dos clientes"):
        return _m(*LOJAS)
    if p == "sonda de disponibilidade":
        return []
    if p == "implantação":
        return _m(lib)
    if p == "tarefas agendadas do servidor":
        return _m(tarefas, ("mês da empresa", "o faturamento do dia 1"))
    if p == "faturamento":
        if c == "faturas emitidas no minuto":
            return _m(("mês da empresa", "o faturamento do dia 1 às 6h"))
        if c == "faturas pagas no minuto":
            return _m(("pagamento das faturas", "as lojas pagam entre os dias 3 e 12, das 8h às 17h"))
        if c == "faturas em aberto":
            return _m(("mês da empresa", "o faturamento do dia 1 abre as faturas"), ("pagamento das faturas", "o pagamento as fecha"))
        return _m(("expediente das pessoas", "o financeiro faz os estornos no expediente"))
    if p.startswith("região ") or p.startswith("clientes do plano "):
        if c == "clientes ativos":
            return []
        return _m(*LOJAS)
    if p == "carteira de clientes":
        if c == "clientes ativos":
            return []
        if c == "entradas no minuto":
            return _m(("expediente das pessoas", "o administrativo cria as contas no expediente"),
                      ("mês da empresa", "vendas fecham mais no fim do mês"))
        return _m(("expediente das pessoas", "o financeiro processa os cancelamentos no expediente"))
    if p == "pesquisa de satisfação":
        return _m(("expediente das pessoas", "o cliente responde quando o chamado fecha"))
    if p.startswith("canal de atendimento "):
        return _m(*[(m, "os contatos nascem do uso") for m, _ in LOJAS],
                  ("expediente das pessoas", "fora do expediente o contato vira e-mail"))
    if p.startswith("chamados de ") or p.startswith("projeto Suporte"):
        out = [(m, "os chamados nascem do uso") for m, _ in LOJAS] + [("expediente das pessoas", "o atendimento responde, escala e resolve no expediente")]
        if p.startswith("projeto Suporte") and ("sprint" in p or "movimento" in p):
            out.append(sprint)
        return _m(*out)
    if p.startswith("bugs de "):
        return _m(exp, (lib[0], "os bugs corrigidos saem nas liberações"))
    if p.startswith("projeto ") or p == "épicos":
        out = [exp, agenda, sprint]
        if "movimento" in p or "desenvolvimento" in p:
            out.append((lib[0], "os itens são liberados nas liberações"))
        return _m(*out)
    if p.startswith("fluxo da equipe de "):
        return _m(exp, agenda)
    if p == "repositório de código" or p.startswith("código de "):
        return _m(exp, sprint, (lib[0], "a regressão roda os testes antes das liberações"))
    if p == "leads de site":
        return _m(("horário do mercado", "os leads do site chegam mais no horário comercial"), exp)
    if p in ("funil de vendas", "atividades de vendas") or p.startswith("leads de "):
        return _m(exp, ("mês da empresa", "vendas fecham mais no fim do mês"))
    if p.startswith("agenda da equipe de ") or p.startswith("reuniões do tipo "):
        out = [agenda, exp]
        if any(x in p for x in ("planejamento", "revisão", "refinamento")):
            out.append(sprint)
        if "mensal" in p:
            out.append(mes)
        return _m(*out)
    if p.startswith("quadro da equipe de "):
        if c == "pessoas no quadro":
            return []
        if c == "horas extras no dia":
            return _m(exp, (sprint[0], "a pressa do fim do sprint faz ficar além da hora"))
        return _m(exp)
    if p == "quadro geral":
        if c == "pessoas no quadro":
            return []
        if c in ("entradas no mês", "saídas no mês"):
            return _m(("mês da empresa", "o contador zera no mês"), exp)
        return _m(exp)
    if p == "ponto":
        return _m(exp)
    return []


# ---------- a medida ----------
def _balde(t):
    return ((t // MINUTOS_DIA) % 7) * 24 + (t % MINUTOS_DIA) // 60


def medir_um(semente, nulo, dias, saida):
    """Anda um mundo e acumula, por campo, a soma, a soma dos quadrados e as somas por hora da semana (pelo relógio da porta e pelo
    calendário interno)."""
    from .mundo import Mundo
    m = Mundo(semente, nulo, historia=tempfile.mkdtemp(prefix="calendario_"))
    procs = m.processos()
    n = sum(len(p.campos) for p in procs)
    soma, quad = np.zeros(n), np.zeros(n)
    porta_s, porta_n = np.zeros((HORAS_SEMANA, n)), np.zeros(HORAS_SEMANA)
    cal_s, cal_n = np.zeros((HORAS_SEMANA, n)), np.zeros(HORAS_SEMANA)
    while m.t < dias * MINUTOS_DIA:
        v = m.passo()
        x = np.array([y for p in procs for y in v[p.nome]], dtype=np.float64)
        soma += x
        quad += x * x
        b = _balde(m.t)
        porta_s[b] += x
        porta_n[b] += 1
        c = m.relogio.cal
        bc = c.dia_semana * 24 + c.minuto // 60
        cal_s[bc] += x
        cal_n[bc] += 1
    np.savez_compressed(saida, soma=soma, quad=quad, porta_s=porta_s, porta_n=porta_n, cal_s=cal_s, cal_n=cal_n,
                        nomes=np.array([f"{p.nome}.{c}" for p in procs for c in p.campos]), semente=semente, dias=dias,
                        nulo=str(nulo))


def _eta(soma, quad, bs, bn):
    n = bn.sum()
    media = soma / n
    total = quad - n * media ** 2
    com = bn > 0
    entre = (bs[com] ** 2 / bn[com, None]).sum(axis=0) - n * media ** 2
    with np.errstate(divide="ignore", invalid="ignore"):
        eta = np.where(total > 1e-9 * np.maximum(1.0, quad), entre / total, np.nan)
    return np.clip(eta, 0.0, 1.0), media


def juntar(saida, normais, embaralhados):
    def somar(arqs):
        acc = None
        for a in arqs:
            z = np.load(a)
            if acc is None:
                acc = {k: z[k].copy() for k in ("soma", "quad", "porta_s", "porta_n", "cal_s", "cal_n")}
                acc["nomes"] = list(z["nomes"])
                acc["dias"] = int(z["dias"])
                acc["sementes"] = [int(z["semente"])]
            else:
                for k in ("soma", "quad", "porta_s", "porta_n", "cal_s", "cal_n"):
                    acc[k] += z[k]
                acc["sementes"].append(int(z["semente"]))
        return acc
    N, E = somar(normais), somar(embaralhados)
    eta_n, media = _eta(N["soma"], N["quad"], N["porta_s"], N["porta_n"])
    eta_porta, _ = _eta(E["soma"], E["quad"], E["porta_s"], E["porta_n"])
    eta_interno, _ = _eta(E["soma"], E["quad"], E["cal_s"], E["cal_n"])
    n_min = N["porta_n"].sum()
    perfis = N["porta_s"] / np.maximum(1, N["porta_n"])[:, None]
    campos = {}
    for i, nome in enumerate(N["nomes"]):
        proc, campo = nome.rsplit(".", 1) if nome.count(".") == 1 else _separar(nome)
        mot = motores_do_campo(proc, campo)
        f, ctl, inte = eta_n[i], eta_porta[i], eta_interno[i]
        piso = 0.0 if np.isnan(ctl) else float(ctl)
        passa = (not np.isnan(f)) and f >= LIMIAR and f >= CONTRASTE * piso and f - piso >= MARGEM
        movido = bool(mot) and passa
        campos[nome] = {
            "processo": proc, "campo": campo,
            "motores": sorted({x["motor"] for x in mot}), "caminhos": mot,
            "fracao_da_variancia": None if np.isnan(f) else round(float(f), 4),
            "controle_embaralhado_pelo_relogio_da_porta": None if np.isnan(ctl) else round(float(ctl), 4),
            "embaralhado_pelo_calendario_interno": None if np.isnan(inte) else round(float(inte), 4),
            "movido_pelo_calendario": bool(movido),
            "medido_sem_motor_declarado": bool((not mot) and passa),
            "media": round(float(media[i]), 4),
            "perfil_por_hora_da_semana": [round(float(x), 4) for x in perfis[:, i]],
        }
    out = {"motores": MOTORES, "limiar": LIMIAR, "contraste": CONTRASTE, "margem": MARGEM,
           "medida": {"normal": {"sementes": N["sementes"], "dias_por_semente": N["dias"]},
                      "embaralhado": {"sementes": E["sementes"], "dias_por_semente": E["dias"]},
                      "vies_do_acaso": round((HORAS_SEMANA - 1) / (n_min - 1), 5),
                      "perfil": "168 médias do campo, uma por hora da semana (0 = segunda 0h a 1h, 167 = domingo 23h a 24h), pelo relógio da porta"},
           "campos": campos}
    with open(saida, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    return out


def _separar(nome):
    for p, campos in lista_de_processos():
        for c in campos:
            if f"{p}.{c}" == nome:
                return p, c
    raise KeyError(nome)


_CACHE = {}


def _medido():
    if "m" not in _CACHE:
        caminho = os.path.join(os.path.dirname(__file__), "registros", "calendario.json")
        _CACHE["m"] = None
        if os.path.exists(caminho):
            with open(caminho, encoding="utf-8") as f:
                _CACHE["m"] = json.load(f)
    return _CACHE["m"]


def correlacao_dos_perfis(a, b):
    """A correlação entre os perfis por hora da semana de dois campos ("processo.campo"): perto de 1, sobem e descem juntos com o
    relógio; perto de -1, um sobe quando o outro desce."""
    m = _medido()
    if m is None or a not in m["campos"] or b not in m["campos"]:
        return None
    x, y = np.array(m["campos"][a]["perfil_por_hora_da_semana"]), np.array(m["campos"][b]["perfil_por_hora_da_semana"])
    if x.std() == 0 or y.std() == 0:
        return None
    return round(float(np.corrcoef(x, y)[0, 1]), 3)


def para_a_verdade():
    """O que entra em verdade()['calendario']: os motores, e por campo os motores, os caminhos, a força medida e a decisão (sem os
    perfis, que ficam em registros/calendario.json)."""
    if "v" not in _CACHE:
        medido = _medido()
        campos = {}
        for p, cs in lista_de_processos():
            for c in cs:
                nome = f"{p}.{c}"
                mot = motores_do_campo(p, c)
                d = {"motores": sorted({x["motor"] for x in mot}), "caminhos": mot}
                if medido and nome in medido["campos"]:
                    m = medido["campos"][nome]
                    d.update({k: m[k] for k in ("fracao_da_variancia", "controle_embaralhado_pelo_relogio_da_porta",
                                                "embaralhado_pelo_calendario_interno", "movido_pelo_calendario")})
                campos[nome] = d
        _CACHE["v"] = {"motores": MOTORES, "limiar": LIMIAR, "contraste": CONTRASTE, "margem": MARGEM,
                       "medida": medido["medida"] if medido else None,
                       "regra": f"um campo é movido pelo calendário quando tem motor declarado e a fração da variância explicada pela "
                                f"hora da semana passa de {LIMIAR}, é ao menos {CONTRASTE:g} vezes a do controle (o nulo embaralhado contado "
                                f"pelo relógio da porta) e fica ao menos {MARGEM} acima dele; dois campos movidos pelo calendário são causa "
                                f"comum (calendário): o mesmo relógio move os dois, pelo mesmo motor ou por motores diferentes; as provas "
                                f"dizem os motores em comum e a correlação dos perfis por hora da semana",
                       "perfis": "registros/calendario.json (168 médias por campo)", "campos": campos}
    return _CACHE["v"]


def main(argv):
    if argv and argv[0] == "uma":
        semente, nulo, dias, saida = int(argv[1]), (None if argv[2] == "normal" else argv[2]), int(argv[3]), argv[4]
        medir_um(semente, nulo, dias, saida)
        return 0
    if argv and argv[0] == "juntar":
        k = argv.index("--")
        out = juntar(argv[1], argv[2:k], argv[k + 1:])
        movidos = sum(1 for c in out["campos"].values() if c["movido_pelo_calendario"])
        sem = [n for n, c in out["campos"].items() if c["medido_sem_motor_declarado"]]
        print(f"{movidos} de {len(out['campos'])} campos movidos pelo calendário; medidos sem motor declarado: {sem}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
