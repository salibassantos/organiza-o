"""Confere as famílias das escolas contra a verdade delas (contrato das famílias, seção 3), sem observador.

    python -m organizacao.escolas.familias.conferir [sementes] [dias]       (padrão: 1,2,3 e os dias de cada família)

Para cada família e cada semente: a mesma vida duas vezes e depois de salvar e carregar (os mesmos minutos); duas sementes dão
estruturas diferentes; o custo de um dia; e o que cada família declara:
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
import json
import os
import sys
import tempfile
import time

from .base import MINUTOS_DIA, hash_dos_minutos
from . import escola3, presenca, corpo, voz

D = MINUTOS_DIA
AQUI = os.path.dirname(os.path.abspath(__file__))
FAMILIAS = {"escola3": escola3, "presenca": presenca, "corpo": corpo, "voz": voz}


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


ESPECIFICOS = {"escola3": conferir_escola3, "presenca": conferir_presenca, "corpo": conferir_corpo, "voz": conferir_voz}


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
