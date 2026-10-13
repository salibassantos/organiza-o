"""Os conectores: o que sai pela porta do mundo. Cada processo é um agregado lido dos sistemas da empresa (o produto no ar, o banco,
a fila, o repositório, o fluxo de trabalho, o CRM, a agenda, o quadro de pessoal, a carteira), por rota, componente, projeto,
equipe, etapa, fila, plano, região. Nenhum campo diz o que importa, nenhum é rótulo de normal ou anormal, nenhum vem de uma pessoa só:
são medidas do que os sistemas fizeram naquele minuto ou do estado em que estão.

A lista de processos e campos é fixa e sai sempre na mesma ordem."""
from .cadastro import (ROTAS, NOME_ROTA, COMPONENTES, NOME_COMPONENTE, EQUIPES, PLANOS, REGIOES, PROJETOS)
from .agenda import TIPOS as TIPOS_REUNIAO
from .crm import ORIGENS
from .fluxo import FINAIS

ABERTOS_SUP = ("aberto", "em atendimento", "aguardando cliente", "escalado")
NAO_ABERTOS = set(FINAIS) | {"resolvido"}


def lista_de_processos():
    P = []
    for r in ROTAS:
        P.append((f"rota {NOME_ROTA[r]}", ["requisições no minuto", "respostas com erro no minuto", "respostas recusadas no minuto",
                                           "latência média em ms", "latência do percentil 95 em ms", "clientes distintos no minuto"]))
    P += [("servidor da aplicação", ["uso de processador em %", "memória em uso em MB", "reinícios do processo no minuto"]),
          ("banco do produto", ["tamanho ocupado em MB", "espaço livre no volume em MB", "consultas no minuto", "escritas no minuto",
                                "instruções executadas em milhares"]),
          ("fila de trabalhos", ["trabalhos pendentes", "trabalhos concluídos no minuto", "falhas de trabalho no minuto",
                                 "idade do trabalho pendente mais antigo em minutos"]),
          ("gateway de pagamento", ["chamadas no minuto", "recusas no minuto"]),
          ("transportadoras", ["cotações de frete no minuto", "cotações com erro no minuto"]),
          ("sonda de disponibilidade", ["verificações no minuto", "verificações com falha no minuto"]),
          ("implantação", ["implantações no minuto", "commits incluídos no minuto", "itens incluídos no minuto"]),
          ("tarefas agendadas do servidor", ["tarefas em execução", "linhas processadas no minuto"]),
          ("e-mails do produto", ["enviados no minuto", "com falha no minuto"]),
          ("pedidos", ["pedidos criados no minuto", "valor dos pedidos no minuto em reais", "itens nos pedidos do minuto"]),
          ("pagamentos", ["pagamentos aprovados no minuto", "pedidos pagos no minuto", "pagamentos recusados no minuto"]),
          ("notas fiscais", ["notas emitidas no minuto", "emissões com falha no minuto"]),
          ("estoque", ["produtos sem estoque", "unidades repostas no minuto"]),
          ("sessões dos clientes", ["sessões iniciadas no minuto", "sessões abandonadas depois de erro no minuto", "sessões ativas",
                                    "usuários conectados"]),
          ("faturamento", ["faturas emitidas no minuto", "faturas pagas no minuto", "faturas em aberto", "estornos feitos no minuto"])]
    for g in REGIOES:
        P.append((f"região {g}", ["clientes ativos", "pedidos no minuto", "cotações de frete no minuto", "cotações com erro no minuto"]))
    P.append(("carteira de clientes", ["clientes ativos", "entradas no minuto", "cancelamentos no minuto", "pedidos de cancelamento abertos"]))
    for pl in PLANOS:
        P.append((f"clientes do plano {pl}", ["clientes ativos", "sessões ativas", "pedidos no minuto", "chamados abertos no minuto"]))
    P.append(("pesquisa de satisfação", ["respostas no minuto", "soma das notas no minuto"]))
    for canal in ("chat", "e-mail", "telefone"):
        P.append((f"canal de atendimento {canal}", ["contatos recebidos no minuto"]))
    for proj in ("PROD", "PLAT"):
        nome = f"projeto {PROJETOS[proj]}"
        P += [(f"{nome}: entrada", ["histórias no backlog", "histórias em refinamento", "bugs abertos ou em triagem", "épicos em andamento",
                                    "tarefas no backlog"]),
              (f"{nome}: desenvolvimento", ["prontos para desenvolver", "em desenvolvimento", "em revisão", "em qualidade",
                                            "prontos para liberar"]),
              (f"{nome}: movimento", ["itens criados no minuto", "transições no minuto", "itens liberados no minuto",
                                      "reprovações no minuto", "reaberturas no minuto", "comentários no minuto"]),
              (f"{nome}: sprint", ["itens no sprint", "pontos planejados", "pontos do sprint", "pontos concluídos", "pontos restantes",
                                   "itens de prioridade alta ou crítica no sprint"]),
              (f"{nome}: prioridades", ["itens abertos de prioridade baixa", "itens abertos de prioridade média",
                                        "itens abertos de prioridade alta", "itens abertos de prioridade crítica"]),
              (f"{nome}: idade", ["itens abertos", "idade média dos itens abertos em horas"])]
    P += [("projeto Infraestrutura: itens", ["tarefas no backlog", "tarefas prontas", "em andamento", "bugs abertos", "concluídos no minuto"]),
          ("projeto Infraestrutura: movimento", ["itens criados no minuto", "transições no minuto", "comentários no minuto"]),
          ("projeto Infraestrutura: sprint", ["itens no sprint", "pontos planejados", "pontos do sprint", "pontos concluídos", "pontos restantes",
                                              "itens de prioridade alta ou crítica no sprint"]),
          ("projeto Infraestrutura: prioridades", ["itens abertos de prioridade baixa", "itens abertos de prioridade média",
                                                   "itens abertos de prioridade alta", "itens abertos de prioridade crítica"]),
          ("projeto Infraestrutura: idade", ["itens abertos", "idade média dos itens abertos em horas"]),
          ("projeto Suporte: chamados por estado", ["abertos sem primeira resposta", "em atendimento", "aguardando cliente", "escalados",
                                                    "resolvidos aguardando fechamento"]),
          ("projeto Suporte: movimento", ["chamados novos no minuto", "primeiras respostas no minuto", "resolvidos no minuto",
                                          "fechados no minuto", "reabertos no minuto", "comentários no minuto"]),
          ("projeto Suporte: prazos", ["chamados fora do prazo de primeira resposta", "espera do chamado mais antigo sem resposta em minutos"]),
          ("projeto Suporte: prioridades", ["chamados abertos de prioridade baixa", "chamados abertos de prioridade média",
                                            "chamados abertos de prioridade alta", "chamados abertos de prioridade crítica"]),
          ("projeto Suporte: sprint", ["itens no sprint", "pontos planejados", "pontos do sprint", "pontos concluídos", "pontos restantes",
                                       "itens de prioridade alta ou crítica no sprint"]),
          ("projeto Suporte: idade", ["chamados abertos", "idade média dos chamados abertos em horas"])]
    for c in COMPONENTES:
        P.append((f"chamados de {NOME_COMPONENTE[c]}", ["abertos", "novos no minuto", "escalados", "resolvidos no minuto"]))
    for c in COMPONENTES:
        P.append((f"bugs de {NOME_COMPONENTE[c]}", ["abertos", "criados no minuto", "liberados no minuto"]))
    for e in EQUIPES:
        P.append((f"fluxo da equipe de {e}", ["itens abertos sob responsabilidade da equipe", "transições no minuto",
                                              "comentários no minuto", "itens criados no minuto"]))
    P.append(("épicos", ["abertos", "em andamento", "concluídos no minuto"]))
    P.append(("repositório de código", ["commits no minuto", "linhas alteradas no minuto", "revisões aprovadas no minuto",
                                        "revisões que pediram mudança no minuto", "ramos abertos"]))
    for c in COMPONENTES:
        P.append((f"código de {NOME_COMPONENTE[c]}", ["commits no minuto", "testes executados no minuto", "testes com falha no minuto"]))
    P.append(("funil de vendas", ["leads", "em qualificação", "propostas", "em negociação", "ganhos no minuto", "perdidos no minuto",
                                  "valor em aberto em milhares de reais"]))
    P.append(("atividades de vendas", ["ligações no minuto", "e-mails no minuto", "propostas enviadas no minuto", "tarefas internas abertas"]))
    for o in ORIGENS:
        P.append((f"leads de {o}", ["novos no minuto", "em aberto no funil"]))
    for e in EQUIPES:
        P.append((f"agenda da equipe de {e}", ["pessoas em reunião", "reuniões em curso", "minutos de reunião no dia"]))
    for tipo in TIPOS_REUNIAO:
        P.append((f"reuniões do tipo {tipo}", ["em curso", "pessoas"]))
    for e in EQUIPES:
        P.append((f"quadro da equipe de {e}", ["pessoas no quadro", "presentes agora", "em almoço", "ausentes por férias hoje",
                                               "ausentes por falta hoje", "horas extras no dia"]))
    P.append(("quadro geral", ["pessoas no quadro", "entradas no mês", "saídas no mês", "vagas abertas", "candidatos em processo",
                               "solicitações abertas à gestão"]))
    P.append(("ponto", ["entradas registradas no minuto", "saídas registradas no minuto"]))
    return P


class Conectores:
    def __init__(self):
        self.processos = lista_de_processos()
        self.minutos_reuniao = {e: 0 for e in EQUIPES}

    def novo_dia(self):
        self.minutos_reuniao = {e: 0 for e in EQUIPES}

    def ler(self, t, cal, m, pr):
        """m: o mundo; pr: as contas do minuto do produto. Devolve {processo: [valores]} na ordem fixa."""
        sis = m.sis
        out = {}
        # ---------------------------------------------------------------- o produto
        rotas = pr["rotas"]
        for r in ROTAS:
            n, e, rec, med, p95, cli = rotas[r]
            out[f"rota {NOME_ROTA[r]}"] = [n, e, rec, round(med, 1), round(p95, 1), cli]
        out["servidor da aplicação"] = [round(pr["cpu"], 1), round(pr["memoria"], 1), pr["reinicios"]]
        out["banco do produto"] = [round(pr["paginas"] * 4096 / 1e6, 2), round(pr["livre_paginas"] * 4096 / 1e6, 2), pr["consultas"],
                                   pr["escritas"], round(pr["instrucoes"] / 100.0, 1)]
        out["fila de trabalhos"] = list(pr["fila"])
        out["gateway de pagamento"] = list(pr["gateway"])
        fr, fre = pr["frete_reg"]
        out["transportadoras"] = [sum(fr), sum(fre)]
        out["sonda de disponibilidade"] = list(pr["sonda"])
        commits, testes, revisoes, impl = sis["repo"].minuto(t)
        out["implantação"] = list(impl)
        out["tarefas agendadas do servidor"] = list(pr["cron"])
        out["e-mails do produto"] = list(pr["emails"])
        ped = pr["pedidos"]
        out["pedidos"] = [ped[0], round(ped[1], 2), ped[2]]
        out["pagamentos"] = list(pr["pag"])
        out["notas fiscais"] = list(pr["notas"])
        out["estoque"] = [pr["sem_estoque"], pr["repostas"]]
        cli = sis["clientes"]
        cm = cli.min
        por_plano, por_regiao, sess_plano, usuarios, sessoes = cli.contagens()
        out["sessões dos clientes"] = [cm["sessoes_iniciadas"], cm["abandonos"], sessoes, usuarios]
        try:
            abertas = sis["produto"].db.con.execute("SELECT COUNT(*) FROM faturas WHERE estado='aberta'").fetchone()[0]
        except Exception:
            abertas = 0
        out["faturamento"] = [pr["faturas_emitidas"], cm["faturas_pagas"], abertas, sis["estornos"][0]]
        sis["estornos"][0] = 0
        reg_ped = dict(pr["pedidos_reg"])
        for i, g in enumerate(REGIOES):
            out[f"região {g}"] = [por_regiao[i], reg_ped.get(i, 0), fr[i], fre[i]]
        cancel = sis["quadro"].db.execute("SELECT COUNT(*) FROM solicitacoes WHERE tipo='cancelamento' AND estado IN ('aberta', 'em andamento')").fetchone()[0]
        out["carteira de clientes"] = [sum(por_plano.values()), cm["entradas"], cm["cancelamentos"], cancel]
        plano_ped = dict(pr["pedidos_plano"])
        for pl in PLANOS:
            out[f"clientes do plano {pl}"] = [por_plano[pl], sess_plano[pl], plano_ped.get(pl, 0), cm["chamados_plano"][pl]]
        out["pesquisa de satisfação"] = [len(cm["pesquisas"]), sum(cm["pesquisas"])]
        for canal in ("chat", "e-mail", "telefone"):
            out[f"canal de atendimento {canal}"] = [cm["contatos"][canal]]
        # ---------------------------------------------------------------- o fluxo de trabalho
        contagens, transicoes, comentarios, sprints, sem_resposta = sis["fluxo"].minuto(t)
        est = {}
        prio = {p: {"baixa": 0, "média": 0, "alta": 0, "crítica": 0} for p in PROJETOS}
        idade = {p: [0, 0] for p in PROJETOS}
        comp_ch = {c: [0, 0] for c in COMPONENTES}
        comp_bug = {c: 0 for c in COMPONENTES}
        equipe_ab = {e: 0 for e in EQUIPES}
        epicos = [0, 0]
        for proj, tipo, estado, prioridade, comp, equipe, n, soma in contagens:
            chave = (proj, tipo, estado)
            est[chave] = est.get(chave, 0) + n
            aberto = estado not in NAO_ABERTOS
            if tipo == "épico":
                if estado == "aberto":
                    epicos[0] += n
                elif estado == "em andamento":
                    epicos[1] += n
                continue
            if aberto:
                prio[proj][prioridade] += n
                idade[proj][0] += n
                idade[proj][1] += soma
                if equipe in equipe_ab:
                    equipe_ab[equipe] += n
            if tipo == "chamado" and comp in comp_ch and estado in ABERTOS_SUP:
                comp_ch[comp][0] += n
                if estado == "escalado":
                    comp_ch[comp][1] += n
            if tipo == "bug" and comp in comp_bug and aberto:
                comp_bug[comp] += n
        g = lambda p, tp, e: est.get((p, tp, e), 0)
        mov = {p: {"criados": 0, "trans": 0, "lib": 0, "rep": 0, "reab": 0, "concl": 0} for p in PROJETOS}
        sup = {"novos": 0, "prim": 0, "resolv": 0, "fech": 0, "reab": 0}
        comp_novos = {c: [0, 0] for c in COMPONENTES}
        bug_mov = {c: [0, 0] for c in COMPONENTES}
        eq_mov = {e: [0, 0] for e in EQUIPES}
        epicos_concl = 0
        for proj, tipo, comp, canal, de, para, ator, reab in transicoes:
            mv = mov[proj]
            mv["trans"] += 1
            if de is None:
                mv["criados"] += 1
            if para == "liberado":
                mv["lib"] += 1
            if para in ("liberado", "concluído"):
                mv["concl"] += 1
            if (de == "em qualidade" or de == "em revisão") and para in ("em desenvolvimento", "em andamento"):
                mv["rep"] += 1
            if reab:
                mv["reab"] += 1
            if ator in eq_mov:
                eq_mov[ator][0] += 1
                if de is None:
                    eq_mov[ator][1] += 1
            if tipo == "épico" and para == "concluído":
                epicos_concl += 1
            if tipo == "chamado":
                if de is None:
                    sup["novos"] += 1
                    if comp in comp_novos:
                        comp_novos[comp][0] += 1
                if de == "aberto" and para not in ("descartado",):
                    sup["prim"] += 1
                if para == "resolvido":
                    sup["resolv"] += 1
                    if comp in comp_novos:
                        comp_novos[comp][1] += 1
                if para == "fechado":
                    sup["fech"] += 1
                if reab:
                    sup["reab"] += 1
            if tipo == "bug" and comp in bug_mov:
                if de is None:
                    bug_mov[comp][0] += 1
                if para == "liberado":
                    bug_mov[comp][1] += 1
        com_proj = {p: 0 for p in PROJETOS}
        com_eq = {e: 0 for e in EQUIPES}
        for proj, equipe, n in comentarios:
            com_proj[proj] += n
            if equipe in com_eq:
                com_eq[equipe] += n
        sp = {p: [0, 0, 0, 0, 0, 0] for p in PROJETOS}
        for proj, meta, total, feitos, n, alta in sprints:
            sp[proj] = [n, meta or 0, total, feitos, max(0, total - feitos), alta]
        idade_h = lambda p: (round((t * idade[p][0] - idade[p][1]) / idade[p][0] / 60.0, 1) if idade[p][0] else 0.0)
        for proj in ("PROD", "PLAT"):
            nome = f"projeto {PROJETOS[proj]}"
            out[f"{nome}: entrada"] = [g(proj, "história", "backlog"), g(proj, "história", "refinamento"),
                                       g(proj, "bug", "aberto") + g(proj, "bug", "triagem"), g(proj, "épico", "em andamento"),
                                       g(proj, "tarefa", "backlog")]
            soma = lambda e: g(proj, "história", e) + g(proj, "tarefa", e) + g(proj, "bug", e)
            out[f"{nome}: desenvolvimento"] = [soma("pronto para desenvolver"), soma("em desenvolvimento") + g(proj, "tarefa", "em andamento"),
                                               soma("em revisão"), soma("em qualidade"), soma("pronto para liberar")]
            mv = mov[proj]
            out[f"{nome}: movimento"] = [mv["criados"], mv["trans"], mv["lib"], mv["rep"], mv["reab"], com_proj[proj]]
            out[f"{nome}: sprint"] = sp[proj]
            out[f"{nome}: prioridades"] = [prio[proj][x] for x in ("baixa", "média", "alta", "crítica")]
            out[f"{nome}: idade"] = [idade[proj][0], idade_h(proj)]
        mv = mov["INFRA"]
        out["projeto Infraestrutura: itens"] = [g("INFRA", "tarefa", "backlog"), g("INFRA", "tarefa", "pronto para desenvolver"),
                                                g("INFRA", "tarefa", "em andamento") + g("INFRA", "bug", "em desenvolvimento"),
                                                sum(est.get(("INFRA", "bug", e), 0) for e in ("aberto", "triagem", "pronto para desenvolver",
                                                                                               "em desenvolvimento", "em qualidade")),
                                                mv["concl"]]
        out["projeto Infraestrutura: movimento"] = [mv["criados"], mv["trans"], com_proj["INFRA"]]
        out["projeto Infraestrutura: sprint"] = sp["INFRA"]
        out["projeto Infraestrutura: prioridades"] = [prio["INFRA"][x] for x in ("baixa", "média", "alta", "crítica")]
        out["projeto Infraestrutura: idade"] = [idade["INFRA"][0], idade_h("INFRA")]
        out["projeto Suporte: chamados por estado"] = [g("SUP", "chamado", e) for e in ("aberto", "em atendimento", "aguardando cliente",
                                                                                         "escalado", "resolvido")]
        out["projeto Suporte: movimento"] = [sup["novos"], sup["prim"], sup["resolv"], sup["fech"], sup["reab"], com_proj["SUP"]]
        fora = 0
        mais_velho = None
        for prioridade, criado in sem_resposta:
            if t - criado > {"crítica": 60, "alta": 240, "média": 1440, "baixa": 4320}[prioridade]:
                fora += 1
            if mais_velho is None or criado < mais_velho:
                mais_velho = criado
        out["projeto Suporte: prazos"] = [fora, (t - mais_velho) if mais_velho is not None else 0]
        out["projeto Suporte: prioridades"] = [prio["SUP"][x] for x in ("baixa", "média", "alta", "crítica")]
        out["projeto Suporte: sprint"] = sp["SUP"]
        out["projeto Suporte: idade"] = [idade["SUP"][0], idade_h("SUP")]
        for c in COMPONENTES:
            out[f"chamados de {NOME_COMPONENTE[c]}"] = [comp_ch[c][0], comp_novos[c][0], comp_ch[c][1], comp_novos[c][1]]
        for c in COMPONENTES:
            out[f"bugs de {NOME_COMPONENTE[c]}"] = [comp_bug[c], bug_mov[c][0], bug_mov[c][1]]
        for e in EQUIPES:
            out[f"fluxo da equipe de {e}"] = [equipe_ab[e], eq_mov[e][0], com_eq[e], eq_mov[e][1]]
        out["épicos"] = [epicos[0], epicos[1], epicos_concl]
        # ---------------------------------------------------------------- o repositório
        rev = dict(revisoes)
        n_commits = sum(x[1] for x in commits)
        out["repositório de código"] = [n_commits, sum(x[2] for x in commits), rev.get("aprovou", 0), rev.get("pediu mudanças", 0),
                                        len(sis["repo"].ramos)]
        cpc = {x[0]: x[1] for x in commits}
        tpc = {x[0]: (x[2], x[3]) for x in testes}
        for c in COMPONENTES:
            tt = tpc.get(c, (0, 0))
            out[f"código de {NOME_COMPONENTE[c]}"] = [cpc.get(c, 0), tt[0] or 0, tt[1] or 0]
        # ---------------------------------------------------------------- o CRM
        cont, trans, ativ, tarefas = sis["crm"].minuto(t)
        por_est = {}
        por_origem = {o: 0 for o in ORIGENS}
        valor = 0.0
        for estagio, origem, n, v in cont:
            por_est[estagio] = por_est.get(estagio, 0) + n
            if estagio in ("lead", "qualificação", "proposta", "negociação"):
                por_origem[origem] = por_origem.get(origem, 0) + n
                valor += v
        ganhos = sum(1 for _, de, para in trans if para == "ganho")
        perdidos = sum(1 for _, de, para in trans if para == "perdido")
        novos_origem = {o: 0 for o in ORIGENS}
        for origem, de, para in trans:
            if de is None and origem in novos_origem:
                novos_origem[origem] += 1
        out["funil de vendas"] = [por_est.get("lead", 0), por_est.get("qualificação", 0), por_est.get("proposta", 0),
                                  por_est.get("negociação", 0), ganhos, perdidos, round(valor / 1000.0, 1)]
        at = dict(ativ)
        out["atividades de vendas"] = [at.get("ligação", 0), at.get("e-mail", 0), at.get("proposta", 0), tarefas]
        for o in ORIGENS:
            out[f"leads de {o}"] = [novos_origem[o], por_origem[o]]
        # ---------------------------------------------------------------- a agenda e o quadro
        emp = m.empresa
        equipe_de = {}
        pres_ids = set()
        presentes = {e: 0 for e in EQUIPES}
        almoco = {e: 0 for e in EQUIPES}
        quadro_n = {e: 0 for e in EQUIPES}
        a = cal.absoluto
        for p in emp.pessoas:
            if not p.ativo:
                continue
            equipe_de[p.id] = p.equipe
            quadro_n[p.equipe] += 1
            if p.presente:
                pres_ids.add(p.id)
                presentes[p.equipe] += 1
                if p.almoco_ini <= a < p.almoco_fim:
                    almoco[p.equipe] += 1
        agenda = sis["agenda"]
        em_reuniao = {e: 0 for e in EQUIPES}
        reun_equipe = {e: 0 for e in EQUIPES}
        por_tipo = {tp: [0, 0] for tp in TIPOS_REUNIAO}
        contados = set()
        for ini, fim, rid, tipo, equipe, pessoas in agenda.agora:
            presentes_r = [x for x in pessoas if x in pres_ids]
            if not presentes_r:
                continue
            if equipe in reun_equipe:
                reun_equipe[equipe] += 1
            por_tipo[tipo][0] += 1
            por_tipo[tipo][1] += len(presentes_r)
            for x in presentes_r:
                if x not in contados:
                    contados.add(x)
                    em_reuniao[equipe_de[x]] += 1
        for e in EQUIPES:
            self.minutos_reuniao[e] += em_reuniao[e]
            out[f"agenda da equipe de {e}"] = [em_reuniao[e], reun_equipe[e], self.minutos_reuniao[e]]
        for tp in TIPOS_REUNIAO:
            out[f"reuniões do tipo {tp}"] = por_tipo[tp]
        q = sis["quadro"]
        for e in EQUIPES:
            d = q.dia[e]
            out[f"quadro da equipe de {e}"] = [quadro_n[e], presentes[e], almoco[e], d["férias"], d["falta"], round(d["extras"], 2)]
        vagas, cand = q.contagem_vagas()
        out["quadro geral"] = [sum(quadro_n.values()), q.mes["entradas"], q.mes["saídas"], vagas, cand, q.solicitacoes_abertas()]
        out["ponto"] = list(q.ponto_min)
        q.ponto_min = [0, 0]
        return {nome: [float(v) for v in out[nome]] for nome, _ in self.processos}

