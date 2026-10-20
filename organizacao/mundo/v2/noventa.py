"""(v2.2) A prova do efeito real em vidas longas: quantos defeitos cada rota tem, como saem do ar e quanto custa o mundo sozinho.

    python -m organizacao.mundo.v2.noventa vida <semente> <saida.json> [dias]      (padrão: 90 dias, sem atos, nulo normal)
    python -m organizacao.mundo.v2.noventa tabela <pasta com os .json>              (escreve a tabela em Markdown)

Cada vida grava o tempo de processador de cada dia simulado, a memória máxima, a carteira no fim, as liberações e os episódios de
defeito (com a saída e o ramo sem ato da v2.2; sem atos, a saída sozinha é a saída vivida). A tabela conta, por rota e por semente,
os episódios de defeito que chegam à rota (a rota chama a função defeituosa) e como saíram: reversão própria (o alerta da própria
rota levou à volta da versão), reversão de carona (saiu porque a liberação foi revertida por outro defeito), correção no ar e
liberação regular."""
import collections
import json
import os
import resource
import shutil
import statistics as st
import sys
import tempfile
import time

from .cadastro import ROTAS, NOME_ROTA, MINUTOS_DIA

D = MINUTOS_DIA
CAMPOS = ("funcao", "implementacao", "componente", "como_aparece", "onde", "liberado_em", "versao", "primeiro_erro", "erros",
          "primeiro_chamado", "chamados", "primeira_escalacao", "escalacoes", "saiu_do_ar", "duracao_no_ar_min", "saiu_por",
          "reverteria_sozinha_em", "sairia_sozinha_por", "persistente")


def vida(semente, saida, dias=90):
    from .mundo import Mundo
    pasta = tempfile.mkdtemp(prefix="noventa_")
    m = Mundo(semente, historia=pasta)
    por_dia = []
    t0 = time.process_time()
    for _ in range(dias):
        a = time.process_time()
        for _ in range(D):
            m.passo()
        por_dia.append(round(time.process_time() - a, 2))
    v = m.verdade()
    out = {"semente": semente, "dias": dias, "segundos_por_dia": por_dia, "segundos": round(time.process_time() - t0, 1),
           "memoria_maxima_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
           "carteira_no_fim": m.clientes.ativos(),
           "liberacoes": [{k: x[k] for k in ("t", "versao", "tipo", "defeitos_que_entraram", "defeitos_que_sairam")} for x in v["liberacoes"]],
           "episodios": [{k: e[k] for k in CAMPOS} for e in v["episodios_de_defeito_no_ar"]], "incidentes": len(v["incidentes"])}
    with open(saida, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    shutil.rmtree(pasta, ignore_errors=True)
    return out


def saida_de(e, eps_da_vida):
    """Como o episódio saiu do ar: "reversão própria", "reversão de carona", "correção", "regular" ou "no ar"."""
    if e["saiu_por"] is None:
        return "no ar"
    if e["saiu_por"] != "reversão":
        return e["saiu_por"]
    # a reversão vem do alerta de erros de uma rota: é própria do defeito que quebra a rota (exceção, ou lento que estoura) e teve
    # erros; os outros defeitos da mesma liberação vão de carona
    proprio = lambda x: x["como_aparece"] in ("exceção", "lento") and x["erros"] > 0
    juntos = [x for x in eps_da_vida if x["liberado_em"] == e["liberado_em"] and x["saiu_do_ar"] == e["saiu_do_ar"] and x is not e]
    if proprio(e) or not any(proprio(x) for x in juntos):
        return "reversão própria"
    return "reversão de carona"


def _q(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * len(xs)))] if xs else None


def _h(minutos):
    return f"{minutos / 60:.1f} h" if minutos < 2 * D else f"{minutos / D:.1f} dias"


def tabela(pasta):
    vidas = {}
    for nome in sorted(os.listdir(pasta)):
        if nome.endswith(".json") and nome.startswith("s"):
            with open(os.path.join(pasta, nome), encoding="utf-8") as f:
                d = json.load(f)
            vidas[d["semente"]] = d
    sem = sorted(vidas)
    dias = vidas[sem[0]].get("dias", len(vidas[sem[0]]["segundos_por_dia"]))
    for s in sem:
        for e in vidas[s]["episodios"]:
            e["saida"] = saida_de(e, vidas[s]["episodios"])
    L = [f"# Vidas de {dias} dias sem atos, sementes {sem[0]} a {sem[-1]}", ""]
    L.append(f"Cada célula: episódios de defeito que chegam à rota (a rota chama a função com defeito) em {dias} dias; entre parênteses, "
             "reversão própria / reversão de carona / correção no ar / liberação regular, e os que ainda estavam no ar no fim, se houver.")
    L.append("")
    L.append("| rota | " + " | ".join(f"semente {s}" for s in sem) + " | total |")
    L.append("|---|" + "---|" * (len(sem) + 1))
    chaves = ("reversão própria", "reversão de carona", "correção", "regular", "no ar")

    def cel(eps):
        c = collections.Counter(e["saida"] for e in eps)
        txt = f"{len(eps)} ({'/'.join(str(c[k]) for k in chaves[:4])}"
        return txt + (f"; {c['no ar']} no ar)" if c["no ar"] else ")")

    for r in ROTAS:
        nome = f"rota {NOME_ROTA[r]}"
        por = [[e for e in vidas[s]["episodios"] if [nome, "respostas com erro no minuto"] in e["onde"]] for s in sem]
        L.append(f"| {nome} | " + " | ".join(cel(x) for x in por) + f" | {cel([e for x in por for e in x])} |")
    sem_rota = [[e for e in vidas[s]["episodios"] if not any(o[0].startswith("rota ") for o in e["onde"])] for s in sem]
    L.append("| sem rota (fila de trabalhos, memória) | " + " | ".join(cel(x) for x in sem_rota) + f" | {cel([e for x in sem_rota for e in x])} |")
    todos = [[e for e in vidas[s]["episodios"]] for s in sem]
    L.append("| todos os episódios | " + " | ".join(cel(x) for x in todos) + f" | {cel([e for x in todos for e in x])} |")
    L.append("")
    L.append("Um episódio que chega a duas rotas (frete e pedido, por exemplo) conta nas duas; a última linha conta cada um uma vez.")
    L.append("")
    L.append("| semente | liberações | com defeito | reversões | correções no ar | carteira no fim | s por dia (média) | dias 1 a 10 | "
             f"dias {dias - 9} a {dias} | pior dia | memória máxima |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for s in sem:
        d = vidas[s]
        c = collections.Counter(x["tipo"] for x in d["liberacoes"])
        p = d["segundos_por_dia"]
        L.append(f"| {s} | {len(d['liberacoes'])} | {sum(1 for x in d['liberacoes'] if x['defeitos_que_entraram'])} | {c['reversão']} | "
                 f"{c['correção']} | {d['carteira_no_fim']} | {st.mean(p):.2f} | {st.mean(p[:10]):.2f} | {st.mean(p[-10:]):.2f} | "
                 f"{max(p):.2f} | {d['memoria_maxima_mb']:.0f} MB |")
    todos_s = [x for s in sem for x in vidas[s]["segundos_por_dia"]]
    L.append("")
    L.append(f"Custo do mundo sozinho: {st.mean(todos_s):.2f} s de processador por dia simulado em média ({st.mean(todos_s) * dias / 60:.1f} "
             f"minutos por vida de {dias} dias), crescendo com a carteira.")
    L.append("")
    L.append("## A saída sozinha, por classe de defeito")
    L.append("")
    L.append("| classe | episódios | reversão própria | reversão de carona | correção no ar | liberação regular | no ar no fim | "
             "tempo no ar (mediana; 90%) por saída |")
    L.append("|---|---|---|---|---|---|---|---|")
    eps = [e for s in sem for e in vidas[s]["episodios"]]
    for classe in ("exceção", "lento", "fila", "gravação dupla", "memória"):
        g = [e for e in eps if e["como_aparece"] == classe]
        if not g:
            continue
        c = collections.Counter(e["saida"] for e in g)
        tempos = []
        for k in chaves[:4]:
            dur = [e["duracao_no_ar_min"] for e in g if e["saida"] == k]
            if dur:
                tempos.append(f"{k}: {_h(st.median(dur))}; {_h(_q(dur, .9))}")
        L.append(f"| {classe} | {len(g)} | " + " | ".join(str(c[k]) for k in chaves) + " | " + "<br>".join(tempos) + " |")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "vida":
        vida(int(a[1]), a[2], int(a[3]) if len(a) > 3 else 90)
    elif a and a[0] == "tabela":
        print(tabela(a[1]), end="")
    else:
        print(__doc__)
        sys.exit(2)
