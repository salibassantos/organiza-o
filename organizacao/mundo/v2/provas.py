"""As provas do relatório, sem observador:

1. determinismo e retomada: duas vidas iguais (semente 1, sete dias, os atos de exemplo da primeira semana e um dia de campanha) e
   uma terceira vida salva e carregada no meio; os minutos, as respostas, a verdade, a verdade por minuto e os eventos humanos têm de
   ser idênticos;
2. ramos: do mesmo estado salvo saem três caminhos (sequência de atos A, sequência B e nenhum ato, que é o caminho surdo daquele
   ponto); A e B correm duas vezes cada. Mede-se onde os caminhos se separam e, para cada pedido, a diferença entre o ramo com o ato
   e o ramo sem ato nos campos que a verdade diz que o tratamento encurta, não encurta ou piora de lado;
3. consequência: com um defeito de verdade no ar, do mesmo estado saem o ramo com o pedido certo (à operação, sobre a rota que
   quebra), o ramo com um pedido inútil (sobre uma rota sã) e o ramo sem ato; mede-se quanto tempo o defeito fica no ar, os erros da
   rota e os chamados do componente em cada um, e a confiança da operação depois.

    python -m organizacao.mundo.v2.provas <pasta>
Grava <pasta>/provas.json."""
import hashlib
import json
import os
import sys
import tempfile
import time

import numpy as np

from .cadastro import MINUTOS_DIA as D
from .mundo import Mundo
from .rodar import ler_atos


def viver(m, ate, atos, guardar=None):
    """Anda até `ate`. Devolve (hash de todos os minutos, hashes por minuto, respostas, matriz dos valores se guardar)."""
    total = hashlib.sha256()
    por_minuto, resp, linhas = [], [], []
    while m.t < ate:
        for a in atos.get(m.t + 1, ()):
            m.receber(*a)
        v = m.passo()
        b = json.dumps(v, sort_keys=True, ensure_ascii=False).encode()
        total.update(b)
        por_minuto.append((m.t, hashlib.sha256(b).hexdigest()[:16]))
        resp.extend(m.respostas())
        if guardar is not None:
            linhas.append([x for p in guardar for x in v[p.nome]])
    return total.hexdigest(), por_minuto, resp, (np.array(linhas) if guardar is not None else None)


def assinatura_da_verdade(m):
    v = m.verdade()
    v["verdade_por_minuto"].pop("pasta")
    h = hashlib.sha256(json.dumps(v, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    t, x, _ = m.verdade_por_minuto()
    hm = hashlib.sha256(t.tobytes() + np.nan_to_num(x, nan=-1.0).tobytes()).hexdigest()
    he = hashlib.sha256(json.dumps(m.eventos_humanos(), ensure_ascii=False).encode()).hexdigest()
    return h, hm, he


def prova_retomada(base, atos):
    fim = 7 * D
    campanha = (3 * D + 8 * 60, 10 * 60, 1.0)
    vidas = {}
    for nome in ("A", "B"):
        m = Mundo(1, historia=os.path.join(base, f"retomada_{nome}"))
        m.injetar_campanha(*campanha)
        h, por_minuto, resp, _ = viver(m, fim, atos)
        vidas[nome] = (h, resp, assinatura_da_verdade(m), por_minuto)
    m = Mundo(1, historia=os.path.join(base, "retomada_C"))
    m.injetar_campanha(*campanha)
    meio = 3 * D + 11 * 60                                   # no meio do dia de campanha, com atos ainda em tratamento
    _, p1, r1, _ = viver(m, meio, atos)
    m.salvar(os.path.join(base, "salvo_no_meio"))
    m = Mundo.carregar(os.path.join(base, "salvo_no_meio"), historia=os.path.join(base, "retomada_C_depois"))
    _, p2, r2, _ = viver(m, fim, atos)
    vidas["C"] = (None, r1 + r2, assinatura_da_verdade(m), p1 + p2)
    iguais_minutos = vidas["C"][3] == vidas["A"][3]
    return {
        "vida": "semente 1, sete dias (t = 1 a 10080), os atos de exemplo da primeira semana e um dia de campanha (dia 3, das 8h às 18h)",
        "salva_e_carregada_em": meio,
        "hash_dos_minutos_A": vidas["A"][0], "hash_dos_minutos_B": vidas["B"][0],
        "A_igual_a_B": vidas["A"][0] == vidas["B"][0] and vidas["A"][1] == vidas["B"][1] and vidas["A"][2] == vidas["B"][2],
        "C_salva_e_carregada_igual_a_A_minuto_a_minuto": iguais_minutos,
        "respostas": len(vidas["A"][1]), "respostas_iguais_em_C": vidas["C"][1] == vidas["A"][1],
        "verdade_igual_em_C": vidas["C"][2][0] == vidas["A"][2][0],
        "verdade_por_minuto_igual_em_C": vidas["C"][2][1] == vidas["A"][2][1],
        "eventos_humanos_iguais_em_C": vidas["C"][2][2] == vidas["A"][2][2],
        "hash_da_verdade": vidas["A"][2][0], "hash_da_verdade_por_minuto": vidas["A"][2][1],
    }


def prova_ramos(base):
    m = Mundo(2, historia=os.path.join(base, "ramos_tronco"))
    t0 = 3 * D + 8 * 60                                      # quinta-feira, 8h
    viver(m, t0, {})
    salvo = os.path.join(base, "salvo_ramos")
    m.salvar(salvo)
    procs = m.processos()
    col = {}
    k = 0
    for p in procs:
        for c in p.campos:
            col[(p.nome, c)] = k
            k += 1
    seqs = {"A": {t0 + 60: [("operação", "pedido", "Verifiquem a rota pagamento")],
                  t0 + 120: [("qualidade", "pedido", "Refaçam os testes do catálogo")]},
            "B": {t0 + 60: [("atendimento", "pedido", "Priorizem os chamados de frete")],
                  t0 + 90: [("gestão", "convocacao", "Alinhamento sobre o mês")]},
            "C": {}}
    fim = t0 + 2 * D
    r = {}
    for nome in ("A", "A", "B", "B", "C"):
        chave = nome if nome not in r else nome + "2"
        w = Mundo.carregar(salvo, historia=os.path.join(base, f"ramo_{chave}"))
        h, por_minuto, resp, mat = viver(w, fim, seqs[nome], guardar=procs)
        r[chave] = {"hash": h, "por_minuto": por_minuto, "respostas": resp, "valores": mat, "verdade": w.verdade(),
                    "pasta": w.pasta_da_historia()}

    def separa(x, y):
        for (t, a), (_, b) in zip(r[x]["por_minuto"], r[y]["por_minuto"]):
            if a != b:
                return t
        return None

    def efeitos(nome):
        out = []
        for a in r[nome]["verdade"]["atos"]:
            item = {k: a[k] for k in ("numero", "equipe", "tipo", "texto", "recebido", "demora_ate_ficar_disponivel_min", "pego_em",
                                      "tratado_em", "minutos_de_trabalho", "trabalho_adiado", "desfecho", "horas_extras_atribuidas")}
            item["efeito"] = {k: a["efeito"][k] for k in ("util", "acoes")} if a["efeito"] else None
            if a["tipo"] == "pedido" and a["tratado_em"]:
                ini = a["tratado_em"] - t0
                medidas = {}
                for lista in ("encurta", "nao_encurta", "colateral"):
                    for proc, campo in a["efeito"][lista]:
                        j = col[(proc, campo)]
                        com = r[nome]["valores"][ini:ini + 8 * 60, j]
                        sem = r["C"]["valores"][ini:ini + 8 * 60, j]
                        medidas.setdefault(lista, []).append({"processo": proc, "campo": campo,
                                                              "media_com_o_ato": round(float(com.mean()), 3),
                                                              "media_sem_o_ato": round(float(sem.mean()), 3)})
                item["oito_horas_depois_do_tratamento_contra_o_ramo_sem_atos"] = medidas
            out.append(item)
        return out

    return {
        "tronco": "semente 2, salva em t = %d (dia 3, quinta-feira, 8h); cada ramo carrega o mesmo estado e anda até t = %d" % (t0, fim),
        "sequencias": {k: {str(t): v for t, v in s.items()} for k, s in seqs.items()},
        "hashes": {k: v["hash"] for k, v in r.items()},
        "A_reproduzivel": r["A"]["hash"] == r["A2"]["hash"] and r["A"]["respostas"] == r["A2"]["respostas"],
        "B_reproduzivel": r["B"]["hash"] == r["B2"]["hash"] and r["B"]["respostas"] == r["B2"]["respostas"],
        "A_diferente_de_B": r["A"]["hash"] != r["B"]["hash"],
        "A_diferente_de_C": r["A"]["hash"] != r["C"]["hash"],
        "B_diferente_de_C": r["B"]["hash"] != r["C"]["hash"],
        "primeiro_minuto_em_que_A_se_separa_de_C": separa("A", "C"),
        "primeiro_minuto_em_que_B_se_separa_de_C": separa("B", "C"),
        "pastas_de_historia_distintas": len({v["pasta"] for v in r.values()}) == len(r),
        "atos_do_ramo_A": efeitos("A"),
        "atos_do_ramo_B": efeitos("B"),
        "atos_do_ramo_C": len(r["C"]["verdade"]["atos"]),
    }


def prova_consequencia(base):
    from .cadastro import ROTAS, NOME_ROTA, ROTA_COMPONENTE, NOME_COMPONENTE
    from .verdade import ROTAS_FUNCOES
    m = Mundo(1, historia=os.path.join(base, "consequencia_tronco"))
    alvo = None
    while alvo is None and m.t < 60 * D:
        m.passo()
        cal = m.relogio.cal
        if cal.util and 9 * 60 <= cal.minuto < 17 * 60:
            ultima = m.repo.db.execute("SELECT t FROM implantacoes ORDER BY id DESC LIMIT 1").fetchone()
            for (f, impl), ep in sorted(m.registro.no_ar.items()):
                rotas = [r for r in ROTAS if f in ROTAS_FUNCOES.get(r, ()) and r in ROTA_COMPONENTE]
                # um defeito que quebra de verdade, no ar há pelo menos uma hora, que veio com a última liberação
                if ep["como_aparece"] == "exceção" and ep["erros"] >= 5 and rotas and 60 <= m.t - ep["liberado_em"] < 2 * D \
                        and ultima is not None and ultima[0] == ep["liberado_em"]:
                    alvo = (f, impl, rotas[0], ep["liberado_em"])
                    break
    if alvo is None:
        return {"achado": False}
    f, impl, rota, liberado = alvo
    t0 = m.t
    salvo = os.path.join(base, "salvo_consequencia")
    m.salvar(salvo)
    no_ar = {g for g, _ in m.registro.no_ar}
    sa = [r for r in ROTAS if ROTA_COMPONENTE.get(r) not in (None, ROTA_COMPONENTE[rota]) and not (ROTAS_FUNCOES.get(r, set()) & no_ar)][0]
    ramos = {"pedido certo": {t0 + 1: [("operação", "pedido", f"Verifiquem a rota {NOME_ROTA[rota]}")]},
             "pedido inútil": {t0 + 1: [("operação", "pedido", f"Verifiquem a rota {NOME_ROTA[sa]}")]},
             "sem ato": {}}
    comp = ROTA_COMPONENTE[rota]
    procs = m.processos()
    nomes = [(p.nome, c) for p in procs for c in p.campos]
    j_err = nomes.index((f"rota {NOME_ROTA[rota]}", "respostas com erro no minuto"))
    j_ch = nomes.index((f"chamados de {NOME_COMPONENTE[comp]}", "novos no minuto"))
    j_ab = nomes.index((f"chamados de {NOME_COMPONENTE[comp]}", "abertos"))
    j_ex = nomes.index(("quadro da equipe de operação", "horas extras no dia"))
    out = {}
    for nome, atos in ramos.items():
        w = Mundo.carregar(salvo, historia=os.path.join(base, "consequencia_" + nome.replace(" ", "_")))
        _, _, resp, mat = viver(w, t0 + 2 * D, atos, guardar=procs)
        v = w.verdade()
        ep = [e for e in v["episodios_de_defeito_no_ar"] if e["funcao"] == f and e["liberado_em"] == liberado]
        ato = v["atos"][0] if v["atos"] else None
        out[nome] = {
            "defeito_saiu_do_ar_em": ep[0]["saiu_do_ar"] if ep else None,
            "minutos_no_ar_depois_do_instante_do_ramo": (ep[0]["saiu_do_ar"] - t0) if ep and ep[0]["saiu_do_ar"] else None,
            "saiu_por": ep[0]["saiu_por"] if ep else None, "saiu_pelo_ato": ep[0]["saiu_pelo_ato"] if ep else None,
            "erros_da_rota_em_dois_dias": int(mat[:, j_err].sum()), "chamados_novos_do_componente_em_dois_dias": int(mat[:, j_ch].sum()),
            "chamados_abertos_do_componente_em_media": round(float(mat[:, j_ab].mean()), 2),
            "horas_extras_da_operacao_somadas_no_fim_de_cada_dia": round(float(mat[D - 1::D, j_ex].sum()), 2),
            "ato": None if ato is None else {k: ato[k] for k in ("demora_ate_ficar_disponivel_min", "pego_em", "tratado_em",
                                                                  "minutos_de_trabalho", "trabalho_adiado", "confianca_antes",
                                                                  "confianca_depois", "resposta")} | {"efeito": ato["efeito"]},
            "confianca_da_operacao_no_fim": round(w.empresa.equipes["operação"].confianca, 3),
            "demora_de_pedido_da_operacao_no_fim": round(w.empresa.equipes["operação"].atraso("pedido"), 1),
        }
    return {"achado": True, "semente": 1, "defeito": {"funcao": f, "implementacao": impl, "rota": rota, "liberado_em": liberado},
            "ramo_em": t0, "rota_sa_do_pedido_inutil": sa, "ramos": out}


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    saida = argv[0]
    os.makedirs(saida, exist_ok=True)
    base = tempfile.mkdtemp(prefix="provas_mundo_v2_")
    atos = {t: v for t, v in ler_atos(os.path.join(os.path.dirname(__file__), "atos_exemplo.csv")).items() if t <= 7 * D}
    t_ini = time.time()
    provas = {"retomada": prova_retomada(base, atos), "ramos": prova_ramos(base), "consequencia": prova_consequencia(base),
              "segundos": None}
    provas["segundos"] = round(time.time() - t_ini, 1)
    with open(os.path.join(saida, "provas.json"), "w", encoding="utf-8") as f:
        json.dump(provas, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in provas["retomada"].items() if not k.startswith("hash")}, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in provas["ramos"].items() if not k.startswith("atos")}, ensure_ascii=False, indent=1))
    print(json.dumps(provas["consequencia"], ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
