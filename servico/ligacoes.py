"""As ligações entre campos no mundo do serviço, em três categorias (como na v2.1 do mundo da empresa):

- causa declarada: uma lei do mundo leva de um campo ao outro, com atraso; ela só conta onde agiu (a fonte teve atividade no
  intervalo olhado);
- causa comum: os dois campos se mexem juntos porque a mesma coisa mexe nos dois, sem que um cause o outro: um incidente de carga,
  uma troca de versão, uma mudança das instruções, uma degradação, a chegada da classe nova, ou o ciclo (a hora e o dia da semana);
- sem relação: nenhuma das anteriores."""

CATEGORIAS = ("causa declarada", "causa comum (incidente de carga)", "causa comum (troca de versão)", "causa comum (mudança de instrução)",
              "causa comum (degradação)", "causa comum (classe nova)", "causa comum (ciclo)", "sem relação")
FORA_DO_CICLO = {("serviço do modelo", "capacidade em mil tokens por minuto"), ("custo do serviço", "custo de capacidade no minuto em reais"),
                 ("implantação", "implantações no minuto")}


def leis(m):
    """As leis declaradas, com os nomes de processo desta semente."""
    cls = m.classes
    clientes = [f"clientes de {g}" for g in m.segmentos]
    falhas_de = lambda c: [[f"qualidade de {c}", "tempo esgotado"], [f"qualidade de {c}", "erros internos"]]
    out = []
    for c in cls:
        out.append({"nome": f"falha de {c} volta como reenvio", "de": falhas_de(c),
                    "para": [[g, "reenvios no minuto"] for g in clientes] + [[f"pedidos de {c}", "chamadas recebidas"],
                                                                             ["porta de entrada", "chamadas recebidas"]],
                    "atraso": "de 1 a 4 minutos (45% no minuto seguinte)", "fonte": "falhas",
                    "mecanismo": "o cliente que recebe tempo esgotado ou erro reenvia a mesma chamada com a chance de reenvio do seu segmento"})
    out.append({"nome": "chamada recusada pelo limite volta como reenvio",
                "de": [["porta de entrada", "rejeitadas por limite"], ["erros do serviço", "limite excedido no minuto"]],
                "para": [[g, "reenvios no minuto"] for g in clientes] + [["porta de entrada", "chamadas recebidas"]]
                + [[f"pedidos de {c}", "chamadas recebidas"] for c in cls],
                "atraso": "de 1 a 4 minutos", "fonte": "falhas", "mecanismo": "o mesmo reenvio, depois de passar do limite de chamadas"})
    todas_falhas = [p for c in cls for p in falhas_de(c)] + [["erros do serviço", "tempo esgotado no minuto"],
                                                             ["erros do serviço", "erros internos no minuto"],
                                                             ["erros do serviço", "limite excedido no minuto"],
                                                             ["porta de entrada", "rejeitadas por limite"]]
    out.append({"nome": "falha vira chamado no atendimento", "de": todas_falhas,
                "para": [["atendimento", "chamados novos no minuto"], ["atendimento", "chamados abertos"]],
                "atraso": "lognormal de mediana 30 minutos (90% em até 85)", "fonte": "falhas",
                "mecanismo": "uma parte das falhas (pela chance de chamado de cada segmento) vira chamado no atendimento"})
    out.append({"nome": "resposta ruim vira avaliação negativa",
                "de": [[f"qualidade de {c}", x] for c in cls for x in ("recusas", "repetições", "tempo esgotado")],
                "para": [["avaliações dos clientes", "avaliações negativas no minuto"]], "atraso": "de 1 a 10 minutos",
                "fonte": "recusas_repeticoes", "mecanismo": "os clientes que avaliam dão nota negativa a 15% das recusas e repetições e a 5% "
                                                           "dos tempos esgotados"})
    out.append({"nome": "a fila atrasa as respostas",
                "de": [["porta de entrada", "fila de espera"], ["porta de entrada", "espera na fila em ms"]],
                "para": [[f"pedidos de {c}", x] for c in cls for x in ("latência média em ms", "latência do percentil 95 em ms")]
                + [[f"qualidade de {c}", "tempo esgotado"] for c in cls] + [["erros do serviço", "tempo esgotado no minuto"]],
                "atraso": "a espera de um minuto entra na latência do minuto seguinte; o tempo esgotado no mesmo minuto da latência",
                "fonte": "fila", "mecanismo": "quem espera na fila soma a espera à latência; acima da paciência do cliente vira tempo esgotado"})
    out.append({"nome": "a carga ocupa o servidor e custa",
                "de": [[f"pedidos de {c}", "chamadas atendidas"] for c in cls] + [["tokens do serviço", "entrada no minuto"],
                                                                                 ["tokens do serviço", "saída no minuto"]],
                "para": [["serviço do modelo", "uso de processador em %"], ["serviço do modelo", "memória em uso em GB"],
                         ["custo do serviço", "custo de processamento no minuto em reais"]],
                "atraso": "no mesmo minuto", "fonte": "sempre", "mecanismo": "o trabalho do minuto ocupa o processador e é cobrado por token"})
    out.append({"nome": "a capacidade custa e encurta a fila",
                "de": [["serviço do modelo", "capacidade em mil tokens por minuto"]],
                "para": [["custo do serviço", "custo de capacidade no minuto em reais"], ["porta de entrada", "fila de espera"],
                         ["serviço do modelo", "uso de processador em %"]],
                "atraso": "no mesmo minuto", "fonte": "sempre", "mecanismo": "mais capacidade, mais custo fixo e menos fila"})
    for k, f in enumerate(m.ferramentas):
        usam = [c for i, c in enumerate(cls) if m.ferr_por_pedido[i] > 0 and m.mix_ferr[i, k] > 0.02]
        if usam:
            out.append({"nome": f"falha da ferramenta {f} vira erro", "de": [[f"ferramenta {f}", "falhas no minuto"]],
                        "para": [[f"qualidade de {c}", "erros internos"] for c in usam] + [["erros do serviço", "erros internos no minuto"]],
                        "atraso": "no mesmo minuto", "fonte": "falhas_de_ferramenta",
                        "mecanismo": "30% das falhas de ferramenta derrubam a chamada que a usava"})
    out.append({"nome": "a implantação reinicia o serviço", "de": [["implantação", "implantações no minuto"]],
                "para": [["porta de entrada", "fila de espera"], ["erros do serviço", "tempo esgotado no minuto"]],
                "atraso": "do minuto da implantação até dois minutos depois", "fonte": "implantacoes",
                "mecanismo": "por dois minutos o serviço tem 60% da capacidade"})
    for g in clientes:
        out.append({"nome": f"as chamadas de {g[12:]} entram pela porta", "de": [[g, "chamadas enviadas"]],
                    "para": [["porta de entrada", "chamadas recebidas"]] + [[f"pedidos de {c}", "chamadas recebidas"] for c in cls],
                    "atraso": "no mesmo minuto", "fonte": "sempre", "mecanismo": "as chamadas do segmento são parte das chamadas da porta"})
    return out


def campos_do_ciclo(m):
    return [[p.nome, c] for p in m._processos for c in p.campos if (p.nome, c) not in FORA_DO_CICLO]


def causas(m, v):
    return {
        "categorias": {
            "causa declarada": "uma lei do mundo leva de um campo ao outro, com o atraso declarado; conta só onde a fonte da lei teve "
                               "atividade no intervalo olhado",
            "causa comum (incidente de carga)": "os dois campos estão no 'onde' de um incidente que encosta no intervalo (até quatro horas "
                                                "depois do fim, enquanto reenvios e chamados chegam)",
            "causa comum (troca de versão)": "os dois campos estão no 'onde' de uma troca de versão no intervalo (do instante até um dia depois)",
            "causa comum (mudança de instrução)": "o mesmo, para uma mudança das instruções do sistema",
            "causa comum (degradação)": "os dois campos estão no 'onde' de uma degradação lenta que cobre o intervalo",
            "causa comum (classe nova)": "os dois campos são da classe nova, na rampa de chegada dela",
            "causa comum (ciclo)": "os dois campos se mexem com a hora e o dia da semana (quase todos: o tráfego segue o horário dos "
                                   "clientes); fora do ciclo só a capacidade, o custo de capacidade e as implantações",
            "sem relação": "nenhuma das anteriores",
        },
        "ordem": list(CATEGORIAS),
        "leis": leis(m),
        "campos_do_ciclo": campos_do_ciclo(m),
        "atividade_por_hora": {k: [round(x, 1) for x in vals] for k, vals in m.atividade.items()},
        "como_classificar": "servico.ligacoes.classificar_par(verdade, [processo, campo], [processo, campo], inicio, fim)",
    }


def _ativa(v, fonte, inicio, fim):
    if fonte == "sempre":
        return True
    horas = v["causas"]["atividade_por_hora"].get(fonte, [])
    a = 0 if inicio is None else max(0, (inicio - 1) // 60)
    b = len(horas) - 1 if fim is None else min(len(horas) - 1, (fim - 1) // 60)
    return any(horas[h] > 0 for h in range(a, b + 1))


def classificar_par(v, de, para, inicio=None, fim=None):
    de, para = list(de), list(para)
    sobrepoe = lambda a, b: inicio is None or ((b is None or b >= inicio) and (fim is None or a <= fim))
    todas, provas = [], []
    for lei in v["causas"]["leis"]:
        if de in lei["de"] and para in lei["para"]:
            if _ativa(v, lei["fonte"], inicio, fim):
                todas.append("causa declarada")
                provas.append({"lei": lei["nome"], "atraso": lei["atraso"]})
            else:
                provas.append({"lei": lei["nome"], "observacao": "a lei existe, mas a fonte dela não teve atividade no intervalo"})
            break
    juntos = lambda onde: de in onde and para in onde
    for inc in v["incidentes_de_carga"]:
        if juntos(inc["onde"]) and sobrepoe(inc["inicio"], (inc["fim"] or inc["inicio"] + inc["duracao_min"]) + 240):
            todas.append("causa comum (incidente de carga)")
            provas.append({"incidente": inc["inicio"]})
            break
    for lista, cat in (("trocas_de_versao", "causa comum (troca de versão)"), ("mudancas_de_instrucao", "causa comum (mudança de instrução)")):
        for tr in v[lista]:
            if juntos(tr["onde"]) and sobrepoe(tr["t"], tr["t"] + 1440):
                todas.append(cat)
                provas.append({lista: tr["t"]})
                break
    for dg in v["degradacoes"]:
        if juntos(dg["onde"]) and sobrepoe(dg["inicio"], dg["fim"] or v["minutos"]):
            todas.append("causa comum (degradação)")
            provas.append({"degradacao": dg["inicio"]})
            break
    for cn in v["classes_novas"]:
        if juntos(cn["onde"]) and sobrepoe(cn["t"], cn["rampa_ate"]):
            todas.append("causa comum (classe nova)")
            provas.append({"classe_nova": cn["t"]})
            break
    ciclo = v["causas"]["campos_do_ciclo"]
    if de in ciclo and para in ciclo:
        todas.append("causa comum (ciclo)")
    if not todas:
        todas.append("sem relação")
    todas = sorted(set(todas), key=CATEGORIAS.index)
    return {"categoria": todas[0], "todas": todas, "provas": provas}
