"""Confere as famílias das escolas contra a verdade delas (contrato das famílias, seção 3), sem observador.

    python -m organizacao.escolas.familias.conferir [sementes] [dias]       (padrão: 1,2,3 e os dias de cada família)

Para cada família e cada semente: a mesma vida duas vezes e depois de salvar e carregar (os mesmos minutos); duas sementes dão
estruturas diferentes; o custo de um dia; e o que cada família declara:
- escola 1: cada incidente e cada mudança de regime aparecem no campo, no sentido declarado e com ao menos metade do tamanho em
  desvios; a deriva tem a taxa por semana declarada; cada nulo tira só a sua lei (as outras nos mesmos instantes);
- escola 2: o disparo de origem é seguido do de efeito dentro da folga do atraso típico; a ligação que morre deixa de agir; o
  embaralhado e o sem ligação perdem isso; o disparo aparece no campo;
- escola 4: a amplitude medida no período declarado (por mínimos quadrados) é a declarada; depois da mudança, no período novo; no
  embaralhado some; no período fixo o período velho continua;
- escola 3: os textos chegados no minuto são as respostas daquele minuto; os itens abertos são os atos sem resposta; as horas extras
  nascem dos pedidos no normal e não no paciente; a equipe só responde com gente presente; no surdo nada chega; em ninguém resolve
  nenhum pedido é útil; o defeito aparece nas falhas da máquina; os episódios do defeito começam nos mesmos instantes em todos os nulos;
- presença: as linhas só chegam com ela presente; no normal elas se concentram nas horas do costume, no sorteado não; no surdo ninguém
  responde a ele; a calada não fala;
- corpo: o campo que volta sozinho volta no instante que a verdade prevê; o que só volta com ato não volta sem ato (a surda) e volta
  com ele; os desvios estão nas rajadas, e no nulo calma não há rajada, com os mesmos desvios;
- voz: cada linha chega de 0 a 2 minutos depois do acontecimento a que se refere; no nulo de hora sorteada isso some; com o
  vocabulário permutado as palavras não ficam presas a um sentido; a voz surda não fala.
Grava registros/conferencia.json e registros/hashes.json (o hash dos minutos de cada semente, sem atos)."""
import collections
import math
import json
import os
import sys
import tempfile
import time

from .base import MINUTOS_DIA, hash_dos_minutos
from . import escola1, escola2, escola3, escola4, presenca, corpo, voz

D = MINUTOS_DIA
AQUI = os.path.dirname(os.path.abspath(__file__))
FAMILIAS = {"escola1": escola1, "escola2": escola2, "escola3": escola3, "escola4": escola4, "presenca": presenca, "corpo": corpo, "voz": voz}


def viver(m, dias, atos=None):
    saidas, resp, vozes = [], [], []
    for _ in range(dias * D):
        for a in (atos or {}).get(m.t + 1, ()):
            m.receber(*a)
        saidas.append(m.passo())
        resp += m.respostas()
        vozes += m.vozes()
    return saidas, resp, vozes


def comuns(mod, semente, dias):
    out = {}
    t0 = time.process_time()
    h1 = hash_dos_minutos(mod.Mundo(semente), dias)
    out["segundos_por_dia"] = round((time.process_time() - t0) / dias, 4)
    out["hash"] = h1
    out["mesma_vida"] = h1 == hash_dos_minutos(mod.Mundo(semente), dias)
    m = mod.Mundo(semente)
    a = hash_dos_minutos(m, 1)
    with tempfile.TemporaryDirectory() as p:
        m.salvar(p)
        m2 = mod.Mundo.carregar(p)
    import hashlib
    h = hashlib.sha256()
    ref = mod.Mundo(semente)
    for _ in range(D):
        h.update(json.dumps(ref.passo(), sort_keys=True, ensure_ascii=False).encode())
    hb = hashlib.sha256()
    for _ in range(D):
        hb.update(json.dumps(m2.passo(), sort_keys=True, ensure_ascii=False).encode())
    hr = hashlib.sha256()
    for _ in range(D):
        hr.update(json.dumps(ref.passo(), sort_keys=True, ensure_ascii=False).encode())
    out["salvar_e_carregar"] = hb.hexdigest() == hr.hexdigest() and a == h.hexdigest()
    out["relogio"] = mod.Mundo(semente, relogio=True).processos()[-1].nome == "relógio"
    return out


# ---------------------------------------------------------------------------------------------------- escola 3
def atos_escola3(m, dias):
    atos = {}
    for d in range(dias):
        if d % 7 >= 5:
            continue
        for k, h in enumerate((9 * 60 + 10, 11 * 60 + 40, 14 * 60 + 20, 16 * 60 + 5)):
            e = m.equipes()[(d + k) % len(m.equipes())]
            atos.setdefault(d * D + h, []).append((e, "pedido" if k % 2 == 0 else "pergunta", "vejam a máquina"))
    return atos


def conferir_escola3(semente, dias):
    out = {}
    vidas = {}
    for nulo in (None, "paciente", "surdo", "ninguem_resolve"):
        m = escola3.Mundo(semente, nulo)
        s, r, _ = viver(m, dias, atos_escola3(m, dias))
        vidas[nulo] = (m, s, r, m.verdade())
    m, s, r, v = vidas[None]
    eqs = m.equipes()
    por_min = collections.Counter((t, e) for t, _, e, _ in r)
    out["textos_chegados_sao_as_respostas"] = all(s[i][f"porta da {e}"][0] == por_min[(i + 1, e)] for i in range(len(s)) for e in eqs)
    abertos_ok = True
    for a in v["atos"]:
        if a.get("tratado_em") and a["tratado_em"] - a["recebido"] > 2:
            i = a["recebido"]                                         # minuto seguinte ao que ele chegou: aberto
            abertos_ok &= s[i][f"porta da {a['equipe']}"][1] >= 1
    out["itens_abertos_com_os_atos"] = abertos_ok
    out["so_responde_com_gente_presente"] = all(s[t - 1][f"quadro da {e}"][0] > 0 for t, _, e, _ in r)
    extra = {nulo: sum(max(x[f"quadro da {e}"][1] for x in vidas[nulo][1]) for e in eqs) for nulo in vidas}
    atribuidas = sum(len(a["horas_extras_atribuidas"]) for a in v["atos"])
    out["horas_extras"] = {"normal": round(extra[None], 2), "paciente": round(extra["paciente"], 2), "atribuidas_aos_atos": atribuidas,
                           "ok": extra[None] > 0 and extra["paciente"] == 0 and atribuidas > 0}
    out["surdo_nada_chega"] = sum(x[f"porta da {e}"][0] + x[f"porta da {e}"][1] for x in vidas["surdo"][1] for e in eqs) == 0
    out["ninguem_resolve_sem_util"] = not any(a.get("efeito") and a["efeito"]["util"] for a in vidas["ninguem_resolve"][3]["atos"])
    out["algum_pedido_util_no_normal"] = any(a.get("efeito") and a["efeito"]["util"] for a in v["atos"])
    maq = v["estrutura"]["defeito"]["maquina"]
    dentro = [s[t - 1][maq][1] for ep in v["episodios_de_defeito"] for t in range(ep["inicio"], (ep["fim"] or len(s)) + 0) if t <= len(s)]
    fora = [x[maq][1] for x in s]
    out["defeito_nas_falhas"] = {"falhas_por_minuto_com_defeito": round(sum(dentro) / max(1, len(dentro)), 3),
                                 "no_resto": round(sum(fora) / max(1, len(fora)), 3), "ok": bool(dentro) and sum(dentro) / len(dentro) > 3 * sum(fora) / len(fora)}
    out["o_defeito_nos_mesmos_instantes_sem_atos"] = len({tuple(escola3_inicios(semente, nulo, dias)) for nulo in (None, "paciente", "surdo", "ninguem_resolve")}) == 1
    out["quartis_da_resposta"] = v["quartis_da_resposta"]
    out["ok"] = all(x if isinstance(x, bool) else x.get("ok", True) for k, x in out.items() if k not in ("quartis_da_resposta",))
    return out


def escola3_inicios(semente, nulo, dias):
    m = escola3.Mundo(semente, nulo)
    viver(m, dias)
    return [ep["inicio"] for ep in m.verdade()["episodios_de_defeito"]]


# ---------------------------------------------------------------------------------------------------- presença
def conferir_presenca(semente, dias):
    out = {}
    atos = {t: [("", "linha", "olá")] for t in range(97, dias * D, 97)}
    vidas = {}
    for nulo in (None, "sorteado", "surdo", "calada"):
        m = presenca.Mundo(semente, nulo)
        atos_n = {t: [(m.canal, "linha", "olá")] for t in atos}
        s, _, vz = viver(m, dias, atos_n)
        vidas[nulo] = (m, s, vz, m.verdade())
    m, s, vz, v = vidas[None]
    pres = v["presencas"]
    def dentro(t, pres):
        return any(p["inicio"] <= t < p["fim"] for p in pres)
    out["linhas_so_com_ela_presente"] = all(dentro(t, pres) for t, _, _ in vz)
    hora = v["estrutura"]["costume"]["chega_em_min"]
    def perto_do_costume(vz):
        if not vz:
            return 0.0
        return sum(1 for t, _, _ in vz if abs((t % D) - hora) <= 6 * 60) / len(vz)
    out["costume"] = {"normal": round(perto_do_costume(vz), 3), "sorteado": round(perto_do_costume(vidas["sorteado"][2]), 3)}
    out["costume"]["ok"] = out["costume"]["normal"] > 0.9 and out["costume"]["sorteado"] < out["costume"]["normal"] - 0.2
    so = vidas["sorteado"][3]["presencas"]
    out["sorteado_mesmas_sessoes"] = [p["fim"] - p["inicio"] for p in so] == [p["fim"] - p["inicio"] for p in pres]
    out["contingencia"] = {"respostas_a_ele_normal": sum(1 for x in v["linhas_dele"] if x["respondida_em"]),
                           "surdo": sum(1 for x in vidas["surdo"][3]["linhas_dele"] if x["respondida_em"])}
    out["contingencia"]["ok"] = out["contingencia"]["respostas_a_ele_normal"] > 0 and out["contingencia"]["surdo"] == 0
    out["calada_nao_fala"] = len(vidas["calada"][2]) == 0
    out["campo_conta_as_linhas"] = sum(x[m.canal][0] for x in s) == len(vz)
    out["ok"] = all(x if isinstance(x, bool) else x.get("ok", True) for x in out.values())
    return out


# ---------------------------------------------------------------------------------------------------- corpo
def conferir_corpo(semente, dias):
    out = {}
    vidas = {}
    for nulo in (None, "surda", "calma"):
        m = corpo.Mundo(semente, nulo)
        maos = m.equipes()
        atos = {t: [(maos[(t // 45) % len(maos)], "pedido", "desfaçam")] for t in range(45, dias * D, 45)}
        s, _, _ = viver(m, dias, atos)
        vidas[nulo] = (m, s, m.verdade())
    m, s, v = vidas[None]
    sozinhos = [e for e in v["episodios"] if e["saiu_por"] == "sozinho"]
    out["volta_sozinho_no_instante_previsto"] = bool(sozinhos) and all(e["fim"] == e["reverteria_sozinha_em"] for e in sozinhos)
    com_ato = [e for e in vidas[None][2]["episodios"] if e["lei"] == "só volta com ato"]
    out["so_com_ato_volta_com_ato"] = bool(com_ato) and all(e["saiu_por"] in ("ato", None) for e in com_ato) and any(e["saiu_por"] == "ato" for e in com_ato)
    surda = [e for e in vidas["surda"][2]["episodios"] if e["lei"] == "só volta com ato"]
    out["sem_ato_nao_volta"] = bool(surda) and all(e["fim"] is None for e in surda)
    out["desvios_nas_rajadas"] = all(e["na_rajada"] for e in v["episodios"])
    calma = vidas["calma"][2]
    out["calma_sem_rajada_e_os_mesmos_desvios"] = not calma["rajadas"] and len(vidas["calma"][0].desvios) == len(m.desvios)
    desvio = []
    for e in v["episodios"]:
        if e["fim"] and e["fim"] - e["inicio"] > 5:
            p = next(x for x in v["estrutura"]["processos"] if x["nome"] == e["processo"])
            desvio.append(abs(s[e["inicio"]][e["processo"]][0] - p["lugar"]) > 3 * p["ruido"])
    out["o_desvio_aparece_no_nivel"] = bool(desvio) and sum(desvio) / len(desvio) > 0.9
    out["ok"] = all(out.values())
    return out


# ---------------------------------------------------------------------------------------------------- voz
def conferir_voz(semente, dias):
    out = {}
    vidas = {}
    for nulo in (None, "hora_sorteada", "vocabulario_permutado", "voz_surda"):
        m = voz.Mundo(semente, nulo)
        s, _, vz = viver(m, dias)
        vidas[nulo] = (m, s, vz, m.verdade())
    def no_instante(v):
        ls = v["linhas"]
        return sum(1 for x in ls if 0 <= x["t"] - x["refere"]["instante"] <= 2) / max(1, len(ls))
    out["fala_no_instante"] = {k or "normal": round(no_instante(vidas[k][3]), 3) for k in (None, "hora_sorteada", "vocabulario_permutado")}
    out["fala_no_instante"]["ok"] = out["fala_no_instante"]["normal"] == 1.0 and out["fala_no_instante"]["hora_sorteada"] < 0.1 \
        and out["fala_no_instante"]["vocabulario_permutado"] == 1.0
    m, s, vz, v = vidas[None]
    nome = {p["palavra"]: p["nome"] for p in v["estrutura"]["processos"]}
    def acerto(v):
        ls = v["linhas"]
        ok = sum(1 for x in ls if any(nome.get(w) == x["refere"]["processo"] for w in x["texto"].split()))
        return ok / max(1, len(ls))
    out["a_palavra_do_processo"] = {"normal": round(acerto(v), 3), "permutado": round(acerto(vidas["vocabulario_permutado"][3]), 3)}
    out["a_palavra_do_processo"]["ok"] = out["a_palavra_do_processo"]["normal"] == 1.0 and out["a_palavra_do_processo"]["permutado"] < 0.9
    out["voz_surda_nao_fala"] = len(vidas["voz_surda"][2]) == 0
    out["campo_conta_as_linhas"] = sum(x[m.canal][0] for x in s) == len(vz)
    mud = []
    for a in v["acontecimentos"]:
        t = a["t"]
        if 2 <= t < len(s) - 2 and a["acontecimento"] in ("subir", "descer", "parar"):
            antes, depois = s[t - 2][a["processo"]][0], s[t][a["processo"]][0]
            mud.append(abs(depois - antes) > 5)
    out["o_acontecimento_aparece_no_campo"] = bool(mud) and sum(mud) / len(mud) > 0.85
    out["ok"] = all(x if isinstance(x, bool) else x.get("ok", True) for x in out.values())
    return out


# ---------------------------------------------------------------------------------------------------- escola 1
def _col(m, s, proc, campo):
    procs = m.processos()
    k = [p.nome for p in procs].index(proc)
    j = procs[k].campos.index(campo)
    return [x[proc][j] for x in s]


def conferir_escola1(semente, dias):
    import statistics as st
    out = {}
    vidas = {nulo: None for nulo in (None,) + escola1.NULOS}
    for nulo in vidas:
        m = escola1.Mundo(semente, nulo)
        s, _, _ = viver(m, dias)
        vidas[nulo] = (m, s, m.verdade())
    m, s, v = vidas[None]
    def medido(serie, ini, fim, antes=120):
        a = serie[max(0, ini - 1 - antes):ini - 1]
        b = serie[ini + 1:min(fim - 1, len(serie))]
        if len(a) < 10 or len(b) < 5:
            return None
        return (st.mean(b) - st.mean(a)) / (st.pstdev(a) or 1.0)
    inc = []
    for i in v["incidentes"]:
        x = medido(_col(m, s, *i["onde"][0]), i["inicio"], i["fim"])
        if x is not None:
            inc.append(x * (1 if i["sentido"] == "subiu" else -1) >= 0.5 * i["tamanho_em_desvios"])
    out["incidentes_no_campo"] = {"conferidos": len(inc), "certos": sum(inc), "ok": bool(inc) and all(inc)}
    reg = []
    for r in v["mudancas_de_regime"]:
        serie = _col(m, s, *r["onde"][0])
        fora = lambda t: not any(i["onde"] == r["onde"] and i["inicio"] - 5 <= t <= i["fim"] + 5 for i in v["incidentes"])
        a = [serie[t - 1] for t in range(max(1, r["t"] - 720), r["t"]) if fora(t)]
        b = [serie[t - 1] for t in range(r["t"] + 1, min(len(serie), r["t"] + 720)) if fora(t)]
        if len(a) > 30 and len(b) > 30:
            x = (st.mean(b) - st.mean(a)) / (st.pstdev(a) or 1.0)
            reg.append(x * (1 if r["sentido"] == "subiu" else -1) >= 0.5 * r["tamanho_em_desvios"])
    out["regimes_no_campo"] = {"conferidos": len(reg), "certos": sum(reg), "ok": all(reg)}
    d = v["deriva"]
    if d is not None:
        serie = _col(m, s, *d["onde"][0])
        mexe = lambda t: any(i["onde"] == d["onde"] and i["inicio"] - 5 <= t <= i["fim"] + 5 for i in v["incidentes"]) or \
            any(r["onde"] == d["onde"] and abs(t - r["t"]) < 5 for r in v["mudancas_de_regime"])
        dias_ok = [(t // D, serie[t - 1]) for t in range(d["inicio"] + 1, len(serie) + 1) if not mexe(t)]
        por_dia = collections.defaultdict(list)
        for dd, x in dias_ok:
            por_dia[dd].append(x)
        regs = sorted(r["t"] for r in v["mudancas_de_regime"] if r["onde"] == d["onde"])
        # a taxa medida: a reta do logaritmo das médias diárias, dia inteiro depois do início, em cada trecho entre mudanças de regime
        import numpy as np
        cortes = [d["inicio"]] + regs + [len(serie) + 1]
        inclinacoes, pesos = [], []
        for a, b in zip(cortes[:-1], cortes[1:]):
            xs = [dd for dd in sorted(por_dia) if a // D < dd < b // D and st.mean(por_dia[dd]) > 0]
            if len(xs) >= 4:
                inclinacoes.append(np.polyfit(xs, [math.log(st.mean(por_dia[dd])) for dd in xs], 1)[0])
                pesos.append(len(xs))
        medida = math.expm1(7 * sum(i * w for i, w in zip(inclinacoes, pesos)) / sum(pesos)) if pesos else None
        out["deriva"] = {"declarada_por_semana": d["taxa_por_semana"], "medida_por_semana": round(medida, 4) if medida is not None else None,
                         "ok": medida is not None and medida * d["taxa_por_semana"] > 0 and 0.5 <= medida / d["taxa_por_semana"] <= 2.0}
    instantes = lambda v: ([i["inicio"] for i in v["incidentes"]], [r["t"] for r in v["mudancas_de_regime"]], (v["deriva"] or {}).get("inicio"))
    n = instantes(v)
    out["cada_nulo_tira_so_a_sua"] = all(
        (instantes(vidas[nulo][2])[0] == ([] if nulo == "sem_incidente" else n[0])) and
        (instantes(vidas[nulo][2])[1] == ([] if nulo == "sem_regime" else n[1])) and
        (instantes(vidas[nulo][2])[2] == (None if nulo == "sem_deriva" else n[2])) for nulo in escola1.NULOS)
    out["ok"] = all(x if isinstance(x, bool) else x.get("ok", True) for x in out.values())
    return out


# ---------------------------------------------------------------------------------------------------- escola 2
def conferir_escola2(semente, dias):
    out = {}
    vidas = {}
    for nulo in (None,) + escola2.NULOS:
        m = escola2.Mundo(semente, nulo)
        s, _, _ = viver(m, dias)
        vidas[nulo] = (m, s, m.verdade())
    def acerto(v, L, ini, fim):
        orig = [d["t"] for d in v["disparos"] if d["onde"][0] == L["de"] and ini <= d["t"] < fim]
        dest = [d["t"] for d in v["disparos"] if d["onde"][0] == L["para"]]
        a = L["atraso_tipico_min"]
        return (sum(1 for t in orig if any(0.8 * a - 1 <= u - t <= 1.2 * a + 1 for u in dest)) / len(orig)) if orig else None
    v = vidas[None][2]
    res = []
    for L in v["ligacoes"]:
        fim = L["morre"] if L["morre"] is not None else dias * D
        n, e, sl = acerto(v, L, L["nasce"], fim), acerto(vidas["embaralhado"][2], L, L["nasce"], fim), acerto(vidas["sem_ligacao"][2], L, L["nasce"], fim)
        r = {"de": L["de"][0], "para": L["para"][0], "atraso": L["atraso_tipico_min"], "normal": n, "embaralhado": e, "sem_ligacao": sl}
        if L["intermitente"] and L["morre"] is not None and L["morre"] < dias * D:
            r["depois_de_morrer"] = acerto(v, L, L["morre"], dias * D)
            r["morreu"] = not any(d["ligacao"] == v["ligacoes"].index(L) and d["t"] > L["morre"] + 1.2 * L["atraso_tipico_min"] + 1 for d in v["disparos"])
        r["ok"] = n is not None and n >= 0.6 and (e is None or n - e >= 0.2) and (sl is None or n - sl >= 0.2) and r.get("morreu", True)
        res.append(r)
    out["ligacoes"] = res
    out["ligacoes_ok"] = bool(res) and all(r["ok"] for r in res)
    m, s, _ = vidas[None]
    sobe = []
    for d in v["disparos"]:
        p, c = d["onde"][0]
        t = d["t"]
        if 2 <= t <= len(s) - 2:
            proc = next(x for x in v["estrutura"]["processos"] if x["nome"] == p)
            serie = _col(m, s, p, c)
            sobe.append(serie[t - 1] - proc["base"] > 3 * proc["desvio_do_ruido"])
    out["o_disparo_aparece_no_campo"] = bool(sobe) and sum(sobe) / len(sobe) > 0.8
    esp = lambda v: [(d["t"], tuple(d["onde"][0])) for d in v["disparos"] if d["causa"] == "sozinho"]
    out["os_espontaneos_iguais_nos_nulos"] = esp(v) == esp(vidas["embaralhado"][2]) == esp(vidas["sem_ligacao"][2])
    out["sem_ligacao_sem_efeito"] = all(d["causa"] == "sozinho" for d in vidas["sem_ligacao"][2]["disparos"])
    out["ok"] = out["ligacoes_ok"] and out["o_disparo_aparece_no_campo"] and out["os_espontaneos_iguais_nos_nulos"] and out["sem_ligacao_sem_efeito"]
    return out


# ---------------------------------------------------------------------------------------------------- escola 4
def conferir_escola4(semente, dias):
    import numpy as np
    out = {}
    vidas = {}
    for nulo in (None,) + escola4.NULOS:
        m = escola4.Mundo(semente, nulo)
        s, _, _ = viver(m, dias)
        vidas[nulo] = (m, s, m.verdade())
    def amplitudes(m, s, v, ini, fim, usar_depois):
        """Por mínimos quadrados, a amplitude de cada ciclo no período declarado (o de antes ou o de depois da mudança)."""
        out = []
        por_campo = collections.defaultdict(list)
        for c in v["ciclos"]:
            por_campo[tuple(c["onde"][0])].append(c)
        for (p, campo), cs in por_campo.items():
            y = np.array(_col(m, s, p, campo)[ini:fim], dtype=float)
            t = np.arange(ini + 1, fim + 1, dtype=float)
            cols = [np.ones_like(t)]
            for c in cs:
                P = c["periodo_depois_min"] if (usar_depois and c["muda_em"] is not None) else c["periodo_min"]
                cols += [np.cos(2 * np.pi * t / P), np.sin(2 * np.pi * t / P)]
            coef, *_ = np.linalg.lstsq(np.column_stack(cols), y, rcond=None)
            for i, c in enumerate(cs):
                out.append((c, float(np.hypot(coef[1 + 2 * i], coef[2 + 2 * i]))))
        return out
    m, s, v = vidas[None]
    muda = next((c for c in m.ciclos if c["muda_em"] is not None), None)
    corte = muda["muda_em"] if muda is not None and muda["muda_em"] < len(s) else len(s)
    antes = amplitudes(m, s, v, 0, corte, False)
    out["amplitude_no_periodo_antes_da_mudanca"] = [round(a / c["amplitude"], 3) for c, a in antes]
    ok_antes = all(0.7 <= a / c["amplitude"] <= 1.3 for c, a in antes if c["periodo_min"] * 1.5 <= corte)
    me, se, ve = vidas["embaralhado"]
    emb = amplitudes(me, se, ve, 0, corte, False)
    out["embaralhado"] = [round(a / c["amplitude"], 3) for c, a in emb]
    ok_emb = all(a / c["amplitude"] < 0.5 for c, a in emb if c["periodo_min"] * 1.5 <= corte)
    ok_depois = True
    if muda is not None and corte < len(s):
        depois = amplitudes(m, s, v, corte, len(s), True)
        alvo = next(a / c["amplitude"] for c, a in depois if c["muda_em"] is not None)
        mf, sf, vf = vidas["periodo_fixo"]
        fixo = next(a / c["amplitude"] for c, a in amplitudes(mf, sf, vf, corte, len(sf), False) if c["periodo_min"] == muda["periodo"]
                    and c["onde"] == [[m.proc[muda["k"]]["nome"], m.proc[muda["k"]]["campos"][muda["j"]].nome]])
        out["depois_da_mudanca"] = {"no_periodo_novo": round(alvo, 3), "periodo_fixo_no_velho": round(fixo, 3)}
        longo = (len(s) - corte) >= 1.5 * muda["periodo_depois"]
        ok_depois = (not longo) or (0.7 <= alvo <= 1.3 and 0.7 <= fixo <= 1.3)
    out["ok"] = ok_antes and ok_emb and ok_depois
    return out


ESPECIFICOS = {"escola1": conferir_escola1, "escola2": conferir_escola2, "escola4": conferir_escola4, "escola3": conferir_escola3, "presenca": conferir_presenca, "corpo": conferir_corpo, "voz": conferir_voz}


def main(argv):
    sementes = [int(x) for x in argv[0].split(",")] if argv else [1, 2, 3]
    dias_pedidos = int(argv[1]) if len(argv) > 1 else None
    rel = {"sementes": sementes, "familias": {}}
    hashes = {}
    ok = True
    for nome, mod in FAMILIAS.items():
        dias = dias_pedidos or mod.Mundo.DIAS_PADRAO
        r = {"dias": dias, "sementes": {}}
        estruturas = []
        for s in sementes:
            c = comuns(mod, s, dias)
            e = ESPECIFICOS[nome](s, dias)
            r["sementes"][str(s)] = {"comuns": c, "lei": e}
            estruturas.append(json.dumps([[p.nome, p.campos] for p in mod.Mundo(s).processos()] + [mod.Mundo(s).verdade()["estrutura"]], sort_keys=True,
                                         ensure_ascii=False, default=str))
            hashes.setdefault(nome, {})[str(s)] = c["hash"]
            bom = c["mesma_vida"] and c["salvar_e_carregar"] and c["relogio"] and c["segundos_por_dia"] < 1.0 and e["ok"]
            ok &= bom
            print(f"{nome} semente {s}: {'ok' if bom else 'FALHA'}; {c['segundos_por_dia']} s por dia; {e}", flush=True)
        r["estruturas_diferentes"] = len(set(estruturas)) == len(estruturas)
        ok &= r["estruturas_diferentes"]
        rel["familias"][nome] = r
    rel["tudo_certo"] = bool(ok)
    os.makedirs(os.path.join(AQUI, "registros"), exist_ok=True)
    with open(os.path.join(AQUI, "registros", "conferencia.json"), "w", encoding="utf-8") as f:
        json.dump(rel, f, ensure_ascii=False, indent=1, default=str)
    with open(os.path.join(AQUI, "registros", "hashes.json"), "w", encoding="utf-8") as f:
        json.dump({"como": "sha256 de json.dumps(passo(), sort_keys=True, ensure_ascii=False) de cada minuto, sem atos",
                   "dias": {n: (dias_pedidos or FAMILIAS[n].Mundo.DIAS_PADRAO) for n in FAMILIAS}, "hashes": hashes}, f, ensure_ascii=False, indent=1)
    print("tudo certo" if ok else "há falhas (ver registros/conferencia.json)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
