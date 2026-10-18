"""Confere o mundo do serviço contra a sua verdade, sem observador. Para cada uma de três sementes:

1. os acontecimentos declarados aparecem onde e quando a verdade diz:
   - troca de versão e mudança de instrução: cada variável que a verdade diz que sobe ou desce (de 25% para mais) muda nesse sentido
     nos campos do 'onde', comparando o dia seguinte ao dia anterior (quando nenhum outro acontecimento cai nesses dois dias);
   - incidente de carga: a fila, o tempo esgotado ou o limite excedido sobem durante o incidente, contra a mesma janela do dia anterior;
   - degradação: no fim dela, a variável está (1 + aumento) vezes acima do mesmo mundo sem degradação, e igual antes do início;
   - classe nova: o processo dela fica a zero antes do instante e passa a ter chamadas depois;
   - ciclos: a hora do dia, em dia útil ou fim de semana (pelo relógio da porta), explica a maior parte da variação das chamadas por
     hora no mundo normal e quase nada no embaralhado (fora dos incidentes);
2. cada nulo tira só a lei dele: os instantes das outras leis ficam iguais aos do mundo normal;
3. duas sementes dão estruturas diferentes;
4. a mesma semente repete a mesma vida, também depois de salvar e carregar; no nulo surdo os atos não mudam nada;
5. um ato útil (mais capacidade durante um incidente) é registrado como útil e encurta a fila;
6. a leitura dos pedidos: só o trecho antes do ";", pelo verbo, sem que nome de parte ou de campo conte como verbo;
7. o teto da capacidade: os aumentos param em 8 vezes a capacidade da criação, cada um cobra a taxa de provisionamento, e o pedido
   acima do teto é recusado dizendo por quê;
8. a capacidade absurda não faz tempestade: com 5,5 x 10^13 tokens por minuto, o pico de chamadas é o mesmo da vida sem atos.
Grava registros/conferencia.json e registros/hashes.json (o hash dos minutos de cada semente de exemplo).

    python -m servico.conferir [dias] [sementes]        (padrão: 60 dias, sementes 1,2,3)
"""
import hashlib
import json
import math
import os
import sys
import tempfile
import time

import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from servico.mundo import Mundo, MINUTOS_DIA, TETO_CAPACIDADE, PROVISIONAMENTO_MIN
else:
    from .mundo import Mundo, MINUTOS_DIA, TETO_CAPACIDADE, PROVISIONAMENTO_MIN

D = MINUTOS_DIA
AQUI = os.path.dirname(os.path.abspath(__file__))


def viver(semente, nulo, dias, atos=None):
    m = Mundo(semente, nulo)
    procs = m.processos()
    nomes = [(p.nome, c) for p in procs for c in p.campos]
    X = np.zeros((dias * D, len(nomes)), dtype=np.float64)
    h = hashlib.sha256()
    t0 = time.time()
    for i in range(dias * D):
        for a in (atos or {}).get(m.t + 1, ()):
            m.receber(*a)
        v = m.passo()
        h.update(json.dumps(v, sort_keys=True, ensure_ascii=False).encode())
        X[i] = [x for p in procs for x in v[p.nome]]
    seg = time.time() - t0
    return {"m": m, "X": X, "nomes": nomes, "col": {n: i for i, n in enumerate(nomes)}, "hash": h.hexdigest(), "seg_por_dia": seg / dias,
            "v": m.verdade(), "resp": m.respostas()}


def taxa(r, variavel, a, b):
    """A medida de uma variável do modelo entre os minutos a e b (índices de t - 1)."""
    m, X, col = r["m"], r["X"], r["col"]
    cls = m.classes
    soma = lambda campos: sum(X[a:b, col[c]].sum() for c in campos)
    atend = soma([(f"pedidos de {c}", "chamadas atendidas") for c in cls])
    if atend < 50:
        return None
    if variavel == "recusa":
        return soma([(f"qualidade de {c}", "recusas") for c in cls]) / atend
    if variavel == "repeticao":
        return soma([(f"qualidade de {c}", "repetições") for c in cls]) / atend
    if variavel == "erro":
        return soma([(f"qualidade de {c}", "erros internos") for c in cls]) / atend
    if variavel == "tamanho_saida":                       # por resposta completa e não recusada (a recusa tem saída curta)
        ref = soma([(f"qualidade de {c}", "recusas") for c in cls])
        falhas = soma([(f"qualidade de {c}", x) for c in cls for x in ("tempo esgotado", "erros internos")])
        return (soma([(f"pedidos de {c}", "tokens de saída") for c in cls]) - 40 * ref) / max(1.0, atend - ref - falhas)
    if variavel == "ferramentas":
        return soma([(f"ferramenta {f}", "chamadas no minuto") for f in m.ferramentas]) / atend
    # latência: a média ponderada pelas chamadas atendidas, classe a classe, dividida pelo tempo de serviço que os tokens de saída
    # observados na janela pedem (assim a mudança do tamanho da saída não se confunde com a da latência)
    mo = m.modelo
    num = den = 0.0
    for i, c in enumerate(cls):
        n = X[a:b, col[(f"pedidos de {c}", "chamadas atendidas")]]
        if n.sum() < 5:
            continue
        l = X[a:b, col[(f"pedidos de {c}", "latência média em ms")]]
        saida = X[a:b, col[(f"pedidos de {c}", "tokens de saída")]].sum() / n.sum()
        svc = mo["latencia_fixa_ms"] + mo["ms_por_token_de_saida"] * saida + mo["ms_por_token_de_entrada"] * m.tok_in[i]
        num += (n * l).sum() / svc
        den += n.sum()
    return num / den if den else None


def instantes(v):
    return {"trocas": [x["t"] for x in v["trocas_de_versao"] if x["pedida_pelo_ato"] is None],
            "instrucoes": [x["t"] for x in v["mudancas_de_instrucao"] if x["pedida_pelo_ato"] is None],
            "incidentes": [(x["inicio"], x["duracao_min"], x["tipo"]) for x in v["incidentes_de_carga"]],
            "degradacoes": [(x["inicio"], x["variavel"]) for x in v["degradacoes"]],
            "classes_novas": [x["t"] for x in v["classes_novas"]]}


def perto(t, outros, raio):
    return any(abs(t - o) < raio for o in outros if o != t)


def conferir_semente(semente, dias):
    rel = {"semente": semente}
    N = viver(semente, None, dias)
    rel["processos"] = len(N["nomes"]) and len(N["m"].processos())
    rel["segundos_por_dia"] = round(N["seg_por_dia"], 3)
    v = N["v"]
    ins = instantes(v)
    marcos = ins["trocas"] + ins["instrucoes"] + [i[0] for i in ins["incidentes"]] + ins["classes_novas"] \
        + [d["inicio"] for d in v["degradacoes"]] + [d["fim"] for d in v["degradacoes"] if d["fim"] is not None]
    # ---- trocas de versão e mudanças de instrução
    checks = []
    for lista in ("trocas_de_versao", "mudancas_de_instrucao"):
        for tr in v[lista]:
            t = tr["t"]
            if t < D or t + D > dias * D or perto(t, marcos, 2 * D):
                continue
            for var, mult in tr["efeito"].items():
                if abs(math.log(mult)) < math.log(1.25):
                    continue
                antes, depois = taxa(N, var, t - D - 1, t - 1), taxa(N, var, t + 9, t + D - 1)
                if antes is None or depois is None or antes == 0:
                    continue
                obs = depois / antes
                ok = (obs > 1) == (mult > 1) and abs(math.log(obs)) >= 0.4 * abs(math.log(mult))
                checks.append({"o_que": lista, "t": t, "variavel": var, "declarado": mult, "medido": round(obs, 3), "ok": ok})
    rel["trocas_e_instrucoes"] = {"conferidas": len(checks), "certas": sum(c["ok"] for c in checks), "detalhe": checks}
    # ---- incidentes de carga
    col, X = N["col"], N["X"]
    fila, esg, lim = (X[:, col[("porta de entrada", "fila de espera")]], X[:, col[("erros do serviço", "tempo esgotado no minuto")]],
                      X[:, col[("erros do serviço", "limite excedido no minuto")]])
    inc = []
    for x in v["incidentes_de_carga"]:
        a, b = x["inicio"] - 1, x["inicio"] - 1 + x["duracao_min"]
        if a < D or b > dias * D:
            continue
        durante = fila[a:b].mean() + esg[a:b].sum() + lim[a:b].sum()
        antes = fila[a - D:b - D].mean() + esg[a - D:b - D].sum() + lim[a - D:b - D].sum()
        inc.append({"inicio": x["inicio"], "tipo": x["tipo"], "durante": round(float(durante), 1), "dia_antes": round(float(antes), 1),
                    "ok": durante > 3 * antes + 5})
    rel["incidentes"] = {"conferidos": len(inc), "certos": sum(i["ok"] for i in inc), "detalhe": inc}
    # ---- degradações: contra o mesmo mundo sem degradação
    SD = viver(semente, "sem_degradacao", dias)
    deg = []
    for x in v["degradacoes"]:
        if x["fim"] is None or x["fim"] > dias * D:
            continue
        a, b = x["inicio"] - 1, x["fim"] - 1
        fim_n, fim_s = taxa(N, x["variavel"], b - 2 * D, b), taxa(SD, x["variavel"], b - 2 * D, b)
        ini_n, ini_s = taxa(N, x["variavel"], a - D, a), taxa(SD, x["variavel"], a - D, a)
        if None in (fim_n, fim_s, ini_n, ini_s):
            continue
        esperado = 1 + x["aumento_no_fim"] * (1 - 1 / (b - a) * D)       # a média dos dois últimos dias da rampa
        r_fim, r_ini = fim_n / fim_s, ini_n / ini_s
        deg.append({"inicio": x["inicio"], "variavel": x["variavel"], "esperado_no_fim": round(esperado, 3), "medido_no_fim": round(r_fim, 3),
                    "antes_do_inicio": round(r_ini, 3),
                    "ok": abs(math.log(r_fim) - math.log(esperado)) < 0.35 * math.log(esperado) + 0.03 and abs(math.log(r_ini)) < 0.1})
    rel["degradacoes"] = {"conferidas": len(deg), "certas": sum(d["ok"] for d in deg), "detalhe": deg}
    # ---- a classe nova
    cn = []
    for x in v["classes_novas"]:
        cc = X[:, col[(f"pedidos de {x['classe']}", "chamadas recebidas")]]
        t = x["t"] - 1
        cn.append({"t": x["t"], "classe": x["classe"], "chamadas_antes": float(cc[:t].sum()), "chamadas_no_primeiro_dia_depois": float(cc[t:t + D].sum()),
                   "ok": cc[:t].sum() == 0 and cc[t:t + D].sum() > 0})
    rel["classes_novas"] = {"conferidas": len(cn), "certas": sum(c["ok"] for c in cn), "detalhe": cn}
    # ---- os nulos tiram só a lei deles
    E = viver(semente, "embaralhado", dias)
    ST = viver(semente, "sem_troca", dias)
    iN, iE, iST, iSD = instantes(v), instantes(E["v"]), instantes(ST["v"]), instantes(SD["v"])
    nulos = {
        "sem_troca": {"tira": not iST["trocas"] and not iST["instrucoes"],
                      "o_resto_igual": all(iST[k] == iN[k] for k in ("incidentes", "degradacoes", "classes_novas"))},
        "sem_degradacao": {"tira": not iSD["degradacoes"],
                           "o_resto_igual": all(iSD[k] == iN[k] for k in ("trocas", "instrucoes", "incidentes", "classes_novas"))},
        "embaralhado": {"o_resto_igual": all(iE[k] == iN[k] for k in iN)},
    }

    def eta(r):
        """A fração da variância das chamadas por hora que a hora do dia, separada em dia útil e fim de semana (48 grupos, pelo
        relógio da porta), explica, fora dos incidentes."""
        y = r["X"][:, r["col"][("porta de entrada", "chamadas recebidas")]]
        fora = np.ones(len(y), dtype=bool)
        for x in r["v"]["incidentes_de_carga"]:
            fora[max(0, x["inicio"] - 1):x["inicio"] - 1 + x["duracao_min"] + 240] = False
        horas = len(y) // 60
        yh = y[:horas * 60].reshape(horas, 60).sum(axis=1)
        ok = fora[:horas * 60].reshape(horas, 60).all(axis=1)
        hh = np.arange(horas)[ok]
        b = (hh % 24) + 24 * (((hh // 24) % 7) >= 5)
        yh = yh[ok]
        n = np.bincount(b, minlength=48)
        mu = np.bincount(b, weights=yh, minlength=48) / np.maximum(n, 1)
        return float((n * (mu - yh.mean()) ** 2).sum() / ((yh - yh.mean()) ** 2).sum())
    nulos["embaralhado"]["fracao_da_hora_e_do_fim_de_semana_normal"] = round(eta(N), 3)
    nulos["embaralhado"]["fracao_da_hora_e_do_fim_de_semana_embaralhado"] = round(eta(E), 3)
    nulos["embaralhado"]["tira"] = eta(N) > 0.3 and eta(E) < 0.1
    rel["nulos"] = nulos
    rel["hash_dos_minutos"] = {"normal": N["hash"], "embaralhado": E["hash"], "sem_troca": ST["hash"], "sem_degradacao": SD["hash"]}
    rel["estrutura"] = {"processos": [p.nome for p in N["m"].processos()], "classes": N["m"].classes, "segmentos": N["m"].segmentos,
                        "clientes": int(N["m"].n_clientes.sum()), "ferramentas": N["m"].ferramentas}
    return rel, N


def conferir_porta(semente):
    """Determinismo, salvar e carregar, o nulo surdo e um ato útil."""
    out = {}
    a = viver(semente, None, 3)
    b = viver(semente, None, 3)
    out["mesma_vida"] = a["hash"] == b["hash"]
    m = Mundo(semente)
    h = hashlib.sha256()
    for i in range(3 * D):
        if i == 2000:
            with tempfile.TemporaryDirectory() as p:
                m.salvar(p)
                m = Mundo.carregar(p)
        h.update(json.dumps(m.passo(), sort_keys=True, ensure_ascii=False).encode())
    out["salvar_e_carregar"] = h.hexdigest() == a["hash"]
    atos = {D + 600: [("operação do serviço", "pedido", "aumentem a capacidade"), ("produto", "pergunta", "como estão as recusas?")]}
    s1 = viver(semente, "surdo", 3, atos)
    s2 = viver(semente, "surdo", 3)
    out["surdo_igual_sem_atos"] = s1["hash"] == s2["hash"] and s1["resp"] == [] and s1["v"]["atos"] == []
    # um ato útil: mais capacidade logo no começo do primeiro incidente
    m = Mundo(semente)
    primeiro = min(t for t, evs in m.agenda.items() for e in evs if e[0] == "incidente")
    com = viver(semente, None, primeiro // D + 2, {primeiro + 1: [("operação do serviço", "pedido", "aumentem a capacidade do serviço")]})
    sem = viver(semente, None, primeiro // D + 2)
    ato = com["v"]["atos"][0]
    fila = lambda r: float(r["X"][primeiro + 40:primeiro + 200, r["col"][("porta de entrada", "fila de espera")]].sum())
    esg = lambda r: float(r["X"][primeiro + 40:primeiro + 200, r["col"][("erros do serviço", "tempo esgotado no minuto")]].sum()
                          + r["X"][primeiro + 40:primeiro + 200, r["col"][("erros do serviço", "limite excedido no minuto")]].sum())
    out["ato_util"] = {"incidente": primeiro, "util_na_verdade": ato["util"], "fila_com": fila(com), "fila_sem": fila(sem),
                       "tempo_esgotado_e_limite_com": esg(com), "tempo_esgotado_e_limite_sem": esg(sem), "piorou_de_lado": ato["piorou_de_lado"][:1],
                       "ok": ato["util"] is True and fila(com) + esg(com) < fila(sem) + esg(sem)}
    return out


OP, PR, AT = "operação do serviço", "produto", "atendimento"
RESPOSTA_OP = ("Na última hora: 812 chamadas, 3 falhas (tempo esgotado, limite ou erro), fila média de 0.0 chamadas, latência média de "
               "2210 ms; capacidade de 13.0 mil tokens por minuto.")
LEITURAS = [
    (OP, "que serviço do modelo: chamadas atendidas volte ao normal; " + RESPOSTA_OP, "sem ação"),
    (OP, "que serviço do modelo: capacidade em mil tokens por minuto volte ao normal; " + RESPOSTA_OP, "sem ação"),
    (OP, "que custo do serviço: custo de capacidade no minuto em reais volte ao normal; Pedido tratado. A capacidade passou de 13.0 "
         "para 19.4 mil tokens por minuto.", "sem ação"),
    (OP, "que porta de entrada: fila de espera volte ao normal; " + RESPOSTA_OP, "sem ação"),
    (OP, "que implantação: implantações no minuto volte ao normal; Pedido tratado. Voltamos para a versão 2.", "sem ação"),
    (PR, "que avaliações dos clientes: avaliações negativas no minuto volte ao normal; Na última hora: 4 recusas.", "sem ação"),
    (OP, "que serviço do modelo: memória em uso em GB volte a ser como antes", "sem ação"),
    (OP, "que a versão anterior volte ao ar", "reverter versão"),
    (OP, "a fila está alta; aumentem a capacidade", "sem ação"),
    (OP, "aumentem a capacidade", "aumentar capacidade"),
    (OP, "aumentem a capacidade do serviço", "aumentar capacidade"),
    (OP, "que serviço do modelo: capacidade em mil tokens por minuto aumente", "aumentar capacidade"),
    (OP, "ampliem os servidores; a fila está alta", "aumentar capacidade"),
    (OP, "revertam a versão do modelo", "reverter versão"),
    (OP, "voltem para a versão anterior", "reverter versão"),
    (OP, "desfaçam a última implantação", "reverter versão"),
    (PR, "voltem às instruções anteriores", "voltar instruções"),
    (OP, "revertam o prompt", "voltar instruções"),
    (PR, "revertam a versão", "sem ação"),
    (AT, "aumentem a capacidade", "sem ação"),
]


def conferir_leitura(semente):
    m = Mundo(semente)
    lidas = [(e, x, m.ler(e, x), certa) for e, x, certa in LEITURAS]
    erradas = [{"equipe": e, "texto": x, "lida": lida, "certa": certa} for e, x, lida, certa in lidas if lida != certa]
    return {"conferidas": len(lidas), "erradas": erradas, "ok": not erradas}


def conferir_teto(semente):
    """Dez pedidos de aumento, um a cada meia hora: seis aumentos (o sexto até o teto) e quatro recusas."""
    m = Mundo(semente)
    atos = {60 + 30 * k: [(OP, "pedido", "aumentem a capacidade")] for k in range(10)}
    r = viver(semente, None, 1, atos)
    v, ini = r["v"], m.capacidade_inicial
    mud = v["mudancas_de_capacidade"]
    recusas = [a for a in v["atos"] if a["efetivo_em"] is None]
    col = r["col"][("custo do serviço", "custo de capacidade no minuto em reais")]
    cobrou = all(abs(r["X"][x["t"] - 1, col] - r["X"][x["t"] - 2, col] * x["para_mil_tokens_por_minuto"] / x["de_mil_tokens_por_minuto"]
                     - x["taxa_de_provisionamento_em_reais"]) < 0.02 + 0.01 * x["para_mil_tokens_por_minuto"] / x["de_mil_tokens_por_minuto"]
                 and x["taxa_de_provisionamento_em_reais"] > 0 for x in mud)
    final = r["m"].capacidade
    out = {"aumentos": len(mud), "recusas": len(recusas), "capacidade_final_em_vezes_a_inicial": round(final / ini, 3),
           "taxa_cobrada_no_minuto": cobrou, "recusa_diz_por_que": all("teto" in a["resposta"] for a in recusas)}
    out["ok"] = (len(mud) == 6 and len(recusas) == 4 and abs(final / ini - TETO_CAPACIDADE) < 1e-9 and mud[-1]["no_teto"] and cobrou
                 and out["recusa_diz_por_que"])
    return out


def conferir_tempestade(semente):
    """A capacidade posta em 5,5 x 10^13 tokens por minuto (sem passar pela porta) um minuto antes do primeiro pico de chamadas."""
    m0 = Mundo(semente)
    pico = min(t for t, evs in m0.agenda.items() for e in evs if e[0] == "incidente" and e[1]["tipo"] == "pico de chamadas")
    fim = pico + next(e[1]["duracao"] for e in m0.agenda[pico] if e[0] == "incidente") + 120
    vidas = {}
    for nome, cap in (("sem atos", None), ("capacidade absurda", 5.5e13)):
        m = Mundo(semente)
        maior = 0.0
        for _ in range(fim):
            if cap is not None and m.t == pico - 1:
                m.capacidade = cap
            maior = max(maior, m.passo()["porta de entrada"][0])
        inc = next(x for x in m.verdade()["incidentes_de_carga"] if x["inicio"] == pico)
        vidas[nome] = {"maior_chegada_no_minuto": maior, "chamadas_a_mais_por_minuto": inc["chamadas_a_mais_por_minuto"],
                       "chamados_abertos_no_fim": m.chamados_abertos}
    a, b = vidas["sem atos"], vidas["capacidade absurda"]
    return {"pico": pico, **vidas, "ok": a["chamadas_a_mais_por_minuto"] == b["chamadas_a_mais_por_minuto"]
            and b["maior_chegada_no_minuto"] <= 2 * a["maior_chegada_no_minuto"]}


def main(argv):
    dias = int(argv[0]) if argv else 60
    sementes = [int(x) for x in argv[1].split(",")] if len(argv) > 1 else [1, 2, 3]
    relatorio = {"dias": dias, "sementes": []}
    estruturas = []
    for s in sementes:
        rel, N = conferir_semente(s, dias)
        relatorio["sementes"].append(rel)
        estruturas.append((tuple(rel["estrutura"]["processos"]), json.dumps(N["v"]["estrutura"], sort_keys=True)))
        print(f"semente {s}: {len(rel['estrutura']['processos'])} processos, {rel['segundos_por_dia']} s por dia; "
              f"trocas {rel['trocas_e_instrucoes']['certas']}/{rel['trocas_e_instrucoes']['conferidas']}, "
              f"incidentes {rel['incidentes']['certos']}/{rel['incidentes']['conferidos']}, "
              f"degradações {rel['degradacoes']['certas']}/{rel['degradacoes']['conferidas']}, "
              f"classe nova {rel['classes_novas']['certas']}/{rel['classes_novas']['conferidas']}, nulos {rel['nulos']}", flush=True)
    relatorio["estruturas_diferentes"] = all(estruturas[i] != estruturas[j] for i in range(len(estruturas)) for j in range(i + 1, len(estruturas)))
    relatorio["porta"] = conferir_porta(sementes[0])
    relatorio["porta"]["leitura"] = conferir_leitura(sementes[0])
    relatorio["porta"]["teto"] = {str(s): conferir_teto(s) for s in sementes}
    relatorio["porta"]["tempestade"] = {str(s): conferir_tempestade(s) for s in sementes}
    print("estruturas diferentes:", relatorio["estruturas_diferentes"], "porta:", relatorio["porta"], flush=True)
    certo = lambda x: (x["ok"] if "ok" in x else all(map(certo, x.values()))) if isinstance(x, dict) else x
    ok = relatorio["estruturas_diferentes"] and all(certo(x) for x in relatorio["porta"].values())
    for rel in relatorio["sementes"]:
        for k in ("trocas_e_instrucoes", "incidentes", "degradacoes", "classes_novas"):
            c = rel[k]
            ok &= c[next(x for x in c if x.startswith("cert"))] == c[next(x for x in c if x.startswith("conf"))]
        ok &= all(x.get("tira", True) and x.get("o_resto_igual", True) for x in rel["nulos"].values())
    relatorio["tudo_certo"] = bool(ok)
    os.makedirs(os.path.join(AQUI, "registros"), exist_ok=True)
    with open(os.path.join(AQUI, "registros", "conferencia.json"), "w", encoding="utf-8") as f:
        json.dump(relatorio, f, ensure_ascii=False, indent=1, default=float)
    with open(os.path.join(AQUI, "registros", "hashes.json"), "w", encoding="utf-8") as f:
        json.dump({"dias": dias, "como": "sha256 de json.dumps(passo(), sort_keys=True, ensure_ascii=False) de cada minuto, em ordem",
                   "sementes": {str(r["semente"]): r["hash_dos_minutos"] for r in relatorio["sementes"]}}, f, ensure_ascii=False, indent=1)
    print("tudo certo" if ok else "há falhas (ver registros/conferencia.json)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
