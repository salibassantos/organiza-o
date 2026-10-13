"""Olha uma gravação de rodar.py contra a sua verdade, com números simples, para conferir a olho o que o mundo tem:

- o ciclo do dia e da semana (requisições do catálogo por hora do relógio da porta e por dia da semana), e quanto o minuto se
  parece com o mesmo minuto um dia e uma semana antes (correlação);
- a carteira crescendo (clientes ativos no começo, no meio e no fim);
- cada liberação com defeito: erros da rota, chamados e escalações do componente na hora antes e nas horas depois;
- cada incidente: requisições com erro e chamados novos antes, durante e depois;
- cada mudança de regime: a latência da rota nos dias antes e depois.

    python olhar.py <pasta da gravação>
"""
import csv
import gzip
import json
import os
import sys

import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
    from organizacao.mundo.v2.cadastro import NOME_COMPONENTE, NOME_ROTA, ROTA_COMPONENTE
else:
    from .cadastro import NOME_COMPONENTE, NOME_ROTA, ROTA_COMPONENTE

DIAS = ("segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo")


def carregar(pasta):
    with gzip.open(os.path.join(pasta, "minutos.csv.gz"), "rt", encoding="utf-8") as f:
        leitor = csv.reader(f)
        cab = next(leitor)
        dados = np.array([[float(x) for x in linha] for linha in leitor])
    with open(os.path.join(pasta, "verdade.json"), encoding="utf-8") as f:
        verdade = json.load(f)
    return cab, dados, verdade


def serie(cab, dados, nome):
    return dados[:, cab.index(nome)]


def janela(x, t, ini, fim):
    a, b = max(0, t - 1 + ini), min(len(x), t - 1 + fim)
    return float(x[a:b].sum()) if b > a else 0.0


def hm(t):
    d, m = divmod(int(t), 1440)
    return f"dia {d} {m // 60:02d}h{m % 60:02d}"


def olhar(pasta):
    cab, d, v = carregar(pasta)
    n = d.shape[0]
    dias = n // 1440
    print(f"{pasta}: {n} minutos, {d.shape[1]} campos; nulo = {v['nulo']}")
    cat = serie(cab, d, "rota catálogo.requisições no minuto")
    t = np.arange(1, n + 1)
    hora = (t % 1440) // 60
    por_hora = [cat[hora == h].mean() for h in range(24)]
    print("requisições do catálogo por hora (média por minuto):", " ".join(f"{h}h:{x:.1f}" for h, x in enumerate(por_hora)))
    ds = (t // 1440) % 7
    print("requisições do catálogo por dia da semana (média por minuto):", " ".join(f"{DIAS[k]}:{cat[ds == k].mean():.1f}" for k in range(7)))
    for nome, lag in (("um dia", 1440), ("uma semana", 10080)):
        if n > lag + 1440:
            c = np.corrcoef(cat[lag:], cat[:-lag])[0, 1]
            print(f"correlação do catálogo com {nome} antes: {c:.2f}")
    cart = serie(cab, d, "carteira de clientes.clientes ativos")
    print(f"carteira: {cart[0]:.0f} no começo, {cart[n // 2]:.0f} no meio, {cart[-1]:.0f} no fim "
          f"({100.0 * (cart[-1] / cart[0] - 1) / max(1, dias / 7):.2f}% por semana)")
    print("liberações com defeito:")
    for ep in v["episodios_de_defeito_no_ar"]:
        t0 = ep["liberado_em"]
        comp = ep["componente"]
        nome_c = NOME_COMPONENTE[comp]
        ch = serie(cab, d, f"chamados de {nome_c}.novos no minuto")
        rotas = [NOME_ROTA[r] for r, c in ROTA_COMPONENTE.items() if c == comp]
        if ep["como_aparece"] == "fila" or not rotas:
            erros = serie(cab, d, "fila de trabalhos.falhas de trabalho no minuto")
        elif ep["como_aparece"] == "gravação dupla":
            erros = serie(cab, d, "pagamentos.pagamentos aprovados no minuto") - serie(cab, d, "pagamentos.pedidos pagos no minuto")
        elif ep["como_aparece"] == "memória":
            erros = serie(cab, d, "servidor da aplicação.reinícios do processo no minuto")
        else:
            erros = sum(serie(cab, d, f"rota {r}.respostas com erro no minuto") for r in rotas)
        print(f"  {hm(t0)} {ep['funcao']} ({ep['como_aparece']}): sinal {janela(erros, t0, -60, 0):.0f} na hora antes, "
              f"{janela(erros, t0, 0, 60):.0f} na hora depois; chamados de {nome_c} {janela(ch, t0, -240, 0):.0f} nas 4 h antes, "
              f"{janela(ch, t0, 0, 240):.0f} nas 4 h depois; saiu do ar em {hm(ep['saiu_do_ar']) if ep['saiu_do_ar'] else 'não saiu'}")
    novos = serie(cab, d, "projeto Suporte: movimento.chamados novos no minuto")
    sonda = serie(cab, d, "sonda de disponibilidade.verificações com falha no minuto")
    for inc in v["incidentes"]:
        t0 = inc["inicio"]
        print(f"incidente {hm(t0)} ({inc['causa']}, {inc.get('duracao_min')} min): falhas da sonda {janela(sonda, t0, 0, 120):.0f}; "
              f"chamados novos {janela(novos, t0, -120, 0):.0f} nas 2 h antes e {janela(novos, t0, 0, 120):.0f} nas 2 h depois")
    for r in v["mudancas_de_regime"]:
        for rota, a, b in zip(r["rotas"], r["latencia_media_7_dias_antes"], r["latencia_media_7_dias_depois"]):
            print(f"mudança de regime {hm(r['t'])}: {r['funcao']} {r['de']} -> {r['para']}; latência de {rota} {a} ms antes, {b} ms depois")



if __name__ == "__main__":
    olhar(sys.argv[1])
