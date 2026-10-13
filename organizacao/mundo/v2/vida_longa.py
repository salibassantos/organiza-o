"""Vida longa: roda o mundo por muitos dias e mede, a cada janela de dias, o custo por dia simulado, a memória do processo, o tamanho
dos bancos e das estruturas que poderiam crescer, e o tamanho da pasta de história. A vida recebe um ato por dia útil (às 10h, em
rodízio pelas equipes) e uma campanha por mês, para que a porta e a campanha também entrem na conta.

Uso:
    python -m organizacao.mundo.v2.vida_longa --dias 365 --semente 1 --saida pasta
Grava pasta/vida_longa.json (as medidas por janela) e pasta/verdade_resumo.json (incidentes, platôs, expansões, campanhas)."""
import argparse
import json
import os
import resource
import time

from .cadastro import MINUTOS_DIA, EQUIPES
from .mundo import Mundo

ATOS = [("operação", "pedido", "verifiquem a rota pagamento"), ("atendimento", "pergunta", "como estão os chamados de frete?"),
        ("desenvolvimento", "pedido", "olhem o catálogo"), ("qualidade", "pedido", "refaçam os testes do login"),
        ("vendas", "pergunta", "como está o funil?"), ("produto", "pedido", "relatório por fornecedor"),
        ("gestão", "pergunta", "quantos somos?")]


def rss_mb():
    with open("/proc/self/statm") as f:
        return int(f.read().split()[1]) * os.sysconf("SC_PAGE_SIZE") / 1048576


def tamanho_pasta(p):
    return sum(os.path.getsize(os.path.join(p, f)) for f in os.listdir(p)) / 1048576


def medir(m):
    bancos = {}
    for nome, con in m._bancos().items():
        bancos[nome] = round(con.execute("PRAGMA page_count").fetchone()[0] * 4096 / 1048576, 2)
    cli = m.clientes
    emp = m.empresa
    estruturas = {
        "clientes_ativos": cli.ativos(), "clientes_em_memoria": len(cli.info), "vagas_dos_vetores": cli.nvagas,
        "logins_em_memoria": len(cli.usuario_login), "chamados_do_lado_do_cliente": len(cli.chamados),
        "pessoas_em_memoria": len(emp.pessoas), "itens_lembrados_pela_empresa": len(emp.func_historia) + len(emp.autor) + len(emp.restante),
        "historias_lembradas": len(getattr(emp, "historia_de", {})), "versoes_em_memoria": len(m.repo.versoes),
        "atos_em_memoria": len(m.porta.atos), "registros_da_verdade_em_memoria": sum(len(v) for v in m.registro.mem.values()),
        "datas_da_agenda": len(m.agenda.dias), "datas_geradas": len(m.agenda.geradas),
    }
    contar = lambda con, q: con.execute(q).fetchone()[0]
    p, f = m.produto.db.con, m.fluxo.db
    linhas = {"produto.pedidos": contar(p, "SELECT COUNT(*) FROM pedidos"), "produto.notas": contar(p, "SELECT COUNT(*) FROM notas"),
              "produto.auditoria": contar(p, "SELECT COUNT(*) FROM auditoria"), "produto.faturas": contar(p, "SELECT COUNT(*) FROM faturas"),
              "produto.emails": contar(p, "SELECT COUNT(*) FROM emails"), "produto.trabalhos": contar(p, "SELECT COUNT(*) FROM trabalhos"),
              "fluxo.itens": contar(f, "SELECT COUNT(*) FROM itens"),
              "fluxo.itens_abertos": contar(f, "SELECT COUNT(*) FROM itens WHERE estado NOT IN ('liberado', 'concluído', 'fechado', "
                                               "'descartado', 'não reproduzido')"),
              "fluxo.historias_em_backlog_ou_prontas": contar(f, "SELECT COUNT(*) FROM itens WHERE tipo='história' AND estado IN "
                                                                 "('backlog', 'refinamento', 'pronto para desenvolver')"),
              "fluxo.transicoes": contar(f, "SELECT COUNT(*) FROM transicoes"), "fluxo.comentarios": contar(f, "SELECT COUNT(*) FROM comentarios"),
              "crm.negocios": contar(m.crm.db, "SELECT COUNT(*) FROM negocios"), "quadro.ponto": contar(m.quadro.db, "SELECT COUNT(*) FROM ponto")}
    return bancos, estruturas, linhas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int, default=365)
    ap.add_argument("--semente", type=int, default=1)
    ap.add_argument("--janela", type=int, default=30)
    ap.add_argument("--saida", required=True)
    ap.add_argument("--salvar-nos-dias", default="", help="dias (múltiplos da janela) em que o estado é salvo, separados por vírgula")
    a = ap.parse_args()
    salvar_em = {int(x) for x in a.salvar_nos_dias.split(",") if x}
    os.makedirs(a.saida, exist_ok=True)
    m = Mundo(a.semente, historia=os.path.join(a.saida, "historia"))
    janelas = []
    k = 0
    t_ini = time.time()
    t_jan = t_ini
    fim = a.dias * MINUTOS_DIA
    while m.t < fim:
        prox = m.t + 1
        d, mm = divmod(prox, MINUTOS_DIA)
        if mm == 10 * 60 and d % 7 < 5:
            m.receber(*ATOS[k % len(ATOS)])
            k += 1
        if mm == 1 and d % 30 == 12:
            m.injetar_campanha(prox + 8 * 60, 10 * 60, 1.0)
        m.passo()
        m.respostas()
        if m.t % (a.janela * MINUTOS_DIA) == 0:
            agora = time.time()
            bancos, estruturas, linhas = medir(m)
            janelas.append({"ate_o_dia": m.t // MINUTOS_DIA, "segundos_por_dia_na_janela": round((agora - t_jan) / a.janela, 2),
                            "memoria_do_processo_mb": round(rss_mb(), 1), "bancos_mb": bancos,
                            "historia_mb": round(tamanho_pasta(m.registro.pasta), 1), "estruturas": estruturas,
                            "linhas_nos_bancos": linhas})
            if m.t // MINUTOS_DIA in salvar_em:
                m.salvar(os.path.join(a.saida, f"estado_dia_{m.t // MINUTOS_DIA}"))
            t_jan = agora
            print(json.dumps(janelas[-1], ensure_ascii=False), flush=True)
            with open(os.path.join(a.saida, "vida_longa.json"), "w", encoding="utf-8") as f:
                json.dump({"semente": a.semente, "dias": m.t // MINUTOS_DIA, "janelas": janelas}, f, ensure_ascii=False, indent=1)
    total = time.time() - t_ini
    v = m.verdade()
    resumo = {"semente": a.semente, "dias": a.dias, "segundos": round(total, 1), "segundos_por_dia_simulado": round(total / a.dias, 2),
              "memoria_maxima_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1), "janelas": janelas}
    with open(os.path.join(a.saida, "vida_longa.json"), "w", encoding="utf-8") as f:
        json.dump(resumo, f, ensure_ascii=False, indent=1)
    curto = {"incidentes": [{k: i[k] for k in ("inicio", "fim", "duracao_min", "causa", "folga_dada_em_dias", "registros_apagados")}
                            for i in v["incidentes"]],
             "cadastros_adiados": v["cadastros_adiados_por_volume_cheio"], "teto_inicial": v["deriva"]["teto_inicial"],
             "platos": v["deriva"]["platos"], "expansoes": v["deriva"]["expansoes"],
             "carteira_a_cada_30_dias": v["deriva"]["carteira_por_dia"][::30],
             "campanhas": [{k: c[k] for k in ("inicio", "fim", "forca")} for c in v["campanhas"]],
             "liberacoes": len(v["liberacoes"]), "liberacoes_com_defeito": len(v["liberacoes_com_defeito"]),
             "mudancas_de_regime": len(v["mudancas_de_regime"]), "atos": len(v["atos"]),
             "atos_respondidos": sum(1 for x in v["atos"] if x["desfecho"] == "respondido"),
             "pedidos_uteis": sum(1 for x in v["atos"] if x["tipo"] == "pedido" and x["efeito"] and x["efeito"]["util"]),
             "confianca_final": {e: round(m.empresa.equipes[e].confianca, 3) for e in EQUIPES}}
    with open(os.path.join(a.saida, "verdade_resumo.json"), "w", encoding="utf-8") as f:
        json.dump(curto, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: resumo[k] for k in ("dias", "segundos", "segundos_por_dia_simulado", "memoria_maxima_mb")}))


if __name__ == "__main__":
    main()
