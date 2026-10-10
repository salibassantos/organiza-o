"""As 50 pessoas da empresa, como agentes com papel, equipe, horário e um jeito próprio de trabalhar. Cada uma chega, almoça, vai a
reuniões, sai (às vezes fica além da hora), falta, tira férias; e, quando está livre, escolhe o próximo trabalho do seu papel e o faz
nos sistemas:

- produto: mantém o roteiro de épicos, abre e refina histórias, transforma compromissos com clientes em épicos com prazo;
- desenvolvimento: puxa itens do sprint, comenta, comete código (com uma chance de defeito que cresce com a pressa e o tamanho), revisa
  o código dos colegas, investiga e corrige bugs, faz a triagem;
- qualidade: testa (roda os testes de verdade contra o código do ramo), aprova, reprova, faz a regressão antes das liberações;
- atendimento: responde os chamados na ordem do prazo, pergunta ao cliente, escala para o desenvolvimento, resolve, fecha;
- vendas: trabalha o funil no CRM (ligações, demonstrações, propostas, negociação), prospecta, fecha mais no fim do mês;
- operação: libera versões às terças e quintas à tarde, corrige no ar, reverte, atende alertas e o plantão, trata o incidente;
- gestão: o financeiro cria contas, processa cancelamentos e estornos; pessoas contrata; o dono convoca reuniões e assume compromissos.

Nada aqui olha a verdade: as pessoas só sabem o que os sistemas mostram (o fluxo, o CRM, os alertas e o registro de erros do produto,
os testes que rodam)."""
import math

from . import codigo
from .produto import rodar_testes
from .cadastro import (COMPOSICAO, ROTA_COMPONENTE, COMPONENTE_PROJETO, MINUTOS_DIA, sorteio, NOME_COMPONENTE)
from .fluxo import FINAIS
from .crm import ABERTOS

MIN_POR_PONTO = 420.0
GRUPO = {"líder de produto": "produto", "gerente de produto": "produto", "designer": "produto", "analista de produto": "produto",
         "líder técnico": "dev", "desenvolvedor": "dev", "analista de qualidade": "qa", "coordenador de atendimento": "atendimento",
         "analista de atendimento": "atendimento", "gerente de vendas": "vendas", "pré-vendas": "sdr", "executivo de vendas": "vendas",
         "engenheiro de operação": "ops", "financeiro": "financeiro", "pessoas": "rh", "administrativo": "financeiro", "dono": "dono"}
COMPONENTES_SQUAD = {"PROD": ("catalogo", "pedido", "frete", "pagamento", "relatorio"), "PLAT": ("login", "fiscal", "notificacao")}
PRIO_NUM = {"crítica": 0, "alta": 1, "média": 2, "baixa": 3}
PRIO_ORDEM = "CASE prioridade WHEN 'crítica' THEN 0 WHEN 'alta' THEN 1 WHEN 'média' THEN 2 ELSE 3 END"
TEMAS = {"catalogo": ("filtro por marca no catálogo", "ordenação por preço", "fotos maiores no produto", "selo de novidade"),
         "pedido": ("observação no pedido", "pedido mínimo por fornecedor", "repetir pedido anterior", "resumo do carrinho"),
         "frete": ("prazo de entrega na cotação", "frete grátis acima de um valor", "retirada no balcão"),
         "pagamento": ("boleto parcelado", "pagamento por pix", "comprovante no e-mail"),
         "relatorio": ("relatório por fornecedor", "gráfico de compras do mês", "filtro por período"),
         "login": ("lembrar o usuário", "troca de senha pelo celular", "perfis de acesso"),
         "fiscal": ("reenvio da nota", "nota com observação", "cancelamento de nota"),
         "notificacao": ("aviso de entrega", "resumo semanal por e-mail", "alerta de estoque baixo"),
         "infra": ("ajustar alertas do servidor", "atualizar o sistema operacional", "revisar cópias de segurança",
                   "rodar ensaio de recuperação", "atualizar certificados", "limpar imagens antigas")}


class Pessoa:
    def __init__(self, ident, equipe, papel, projeto, semente, admitida_em=0):
        s = sorteio(semente, "pessoa", ident)
        self.id = ident
        self.equipe, self.papel, self.projeto, self.grupo = equipe, papel, projeto, GRUPO[papel]
        self.s = s
        self.inicio = int(max(7 * 60 + 15, min(10 * 60, s.gauss(8 * 60 + 45, 35))))
        self.almoco = int(s.gauss(12 * 60 + 5, 25))
        self.sexta_cedo = s.choice((0, 0, 30, 45, 60))
        self.velocidade = s.lognormvariate(0.0, 0.18)
        self.cuidado = s.lognormvariate(0.0, 0.3)       # quanto maior, mais defeito escapa da mão
        self.cobertura = s.uniform(0.42, 0.62)           # para quem testa: quanto da bateria costuma rodar
        self.ativo = True
        self.admitida_em = admitida_em
        self.sai_em = None                              # aviso prévio: instante da saída
        self.ferias = set()                             # datas do calendário
        self.doente_ate = -1
        self.presente = False
        self.data = None
        self.chega = self.sai = self.almoco_ini = self.almoco_fim = 0
        self.ausente = None
        self.extra_ate = 0
        self.extra_decidida = False
        self.tarefa = None
        self.suspensa = None
        self.ocioso_ate = 0
        self.extras_recentes = []                       # (data, minutos)
        self.remoto_desde = None


class Empresa:
    def __init__(self, semente, nulo, sis):
        self.semente = semente
        self.nulo = nulo
        self.sis = sis                                   # os sistemas e o relógio (um dicionário)
        self.s = sorteio(semente, "decisões da empresa")
        self.pessoas = []
        self.prox_id = 1
        for equipe, papel, n, projeto in COMPOSICAO:
            for _ in range(n):
                self._nova_pessoa(0, equipe, papel, projeto)
        self.pressa = {"PROD": 1.0, "PLAT": 1.0}
        self.velocidade_dev = {"PROD": 0.6, "PLAT": 0.6}     # pontos por pessoa por dia útil, medido nos sprints
        self.epico_ativo = {"PROD": None, "PLAT": None}
        self.prox_funcionalidade = {"PROD": 0, "PLAT": 0}
        self.func_historia = {}                          # item -> (função, implementação, rota, título)
        self.compromissos = []
        self.autor = {}                                  # item -> pessoa que o desenvolveu
        self.reprovacoes = {}                            # item -> funções que falharam
        self.restante = {}                               # item -> minutos de trabalho que ainda faltam
        self.incidente = None
        self.alertas = {}
        self.silencio = {}
        self.runbook = False
        self.foco_atendimento = (None, 0)
        self.foco_vendas = 0
        self.ao_fim = {}                                 # reunião -> ação quando ela acaba
        self.em_curso_antes = ()
        self.sprint_numero = {"PROD": 0, "PLAT": 0, "SUP": 0, "INFRA": 0}
        self.ultimo_planejamento = {}
        self.plantao_dev = None
        self.liberacao_feita = set()
        self.ultima_regressao = {}
        self.ultima_liberacao = -10 ** 9
        self.hotfix = []                                 # bugs aprovados que pedem correção no ar
        self.reverter = None
        self.vaga_crescimento_em = -10 ** 9
        self.fila_alta_dias = 0
        self.mes_compromisso = -1
        self.dia_alinhamento = -1
        self.escalacoes_dia = 0
        self.pressao_planejada = {}
        self._plano_inicial()

    # ======================================================================================================== pessoas
    def _nova_pessoa(self, t, equipe, papel, projeto):
        p = Pessoa(self.prox_id, equipe, papel, projeto, self.semente, t)
        self.prox_id += 1
        self.pessoas.append(p)
        self.sis["quadro"].admitir(t, p.id, equipe, papel, projeto)
        return p

    def ativas(self):
        return [p for p in self.pessoas if p.ativo]

    def da_equipe(self, equipe, papel=None, projeto=None):
        return [p for p in self.pessoas if p.ativo and p.equipe == equipe and (papel is None or p.papel == papel)
                and (projeto is None or p.projeto == projeto)]

    def lider(self, projeto):
        for p in self.pessoas:
            if p.ativo and p.papel == "líder técnico" and p.projeto == projeto:
                return p
        devs = self.da_equipe("desenvolvimento", projeto=projeto)
        return devs[0] if devs else None

    def dono(self):
        for p in self.pessoas:
            if p.papel == "dono":
                return p
        return None

    def _plano_inicial(self):
        """O estado da empresa no dia da criação: férias já marcadas, um aviso prévio, uma vaga em andamento, um compromisso com prazo,
        o primeiro épico de cada squad."""
        s = self.s
        quadro = self.sis["quadro"]
        for p in self.pessoas:
            # cerca de trinta dias de férias por ano, em blocos; sorteados para os próximos quatrocentos dias
            for _ in range(2):
                if s.random() < 0.55:
                    ini = s.randrange(0, 400)
                    ini -= ini % 7
                    for d in range(ini, ini + s.choice((12, 14, 19))):
                        p.ferias.add(d)
        prod_devs = [p for p in self.pessoas if p.papel == "desenvolvedor" and p.projeto == "PROD"]
        for p in s.sample(prod_devs, 2):                 # duas pessoas do squad de Produto saem de férias no segundo sprint
            for d in range(14, 26):
                p.ferias.add(d)
            for d in range(0, 14):
                p.ferias.discard(d)
        candidatos = [p for p in self.pessoas if p.papel in ("desenvolvedor", "analista de atendimento", "executivo de vendas",
                                                             "analista de qualidade")]
        quem = s.choice(candidatos)
        quem.sai_em = s.randint(9, 22) * MINUTOS_DIA + 18 * 60
        vaga = quadro.abrir_vaga(0, "atendimento", "analista de atendimento", "SUP", "crescimento")
        for _ in range(2):
            quadro.candidato(0, vaga, "entrevista", s.uniform(0.4, 1.0))
        quadro.candidato(0, vaga, "triagem", s.uniform(0.3, 1.0))
        self.compromissos.append({"projeto": "PROD", "prazo": s.randint(24, 26) * MINUTOS_DIA + 18 * 60, "pontos": s.randint(46, 58),
                                  "titulo": "integração com o sistema de um cliente grande", "epico": None, "origem": "dono",
                                  "componente": s.choice(COMPONENTES_SQUAD["PROD"])})

    # ======================================================================================================== o dia
    def dia_vivido(self, t, cal):
        """O que acontece uma vez por dia vivido: adoecer, pedir demissão, começar num emprego novo, o dono ler o relatório."""
        for p in self.pessoas:
            if p.ativo and cal.util and p.doente_ate < t:
                chance = 0.011 * (1.5 if cal.dia_semana in (0, 4) else 1.0)
                if p.s.random() < chance:
                    p.doente_ate = t + p.s.choice((0, 0, 0, 1, 2)) * MINUTOS_DIA + MINUTOS_DIA - 1
        if cal.util:
            self._saidas_e_avisos(t, cal)
            self._contratacao(t, cal)
            self._gestao_diaria(t, cal)
            self.escalacoes_dia = 0

    def nova_data(self, t, cal):
        """O que acontece quando a folhinha vira: o plano de presença de cada pessoa, a agenda da data, a pressa dos squads."""
        quadro = self.sis["quadro"]
        for p in self.pessoas:
            if not p.ativo:
                continue
            if p.presente and not (p.tarefa and p.tarefa.get("urgente")):
                self._sair(p, t, cal)
            p.data = cal.data
            p.ausente = None
            p.extra_decidida = False
            p.extra_ate = 0
            if not cal.util:
                continue
            if cal.data in p.ferias:
                p.ausente = "férias"
                quadro.ausencia(p.id, p.equipe, cal.data, "férias")
                continue
            if p.doente_ate >= t:
                p.ausente = "falta"
                quadro.ausencia(p.id, p.equipe, cal.data, "falta")
                continue
            base = cal.data * MINUTOS_DIA
            p.chega = base + p.inicio + p.s.randint(-15, 20)
            jornada = 540 - (p.sexta_cedo if cal.dia_semana == 4 else 0)
            p.sai = p.chega + jornada
            p.almoco_ini = base + p.almoco + p.s.randint(-20, 25)
            p.almoco_fim = p.almoco_ini + p.s.randint(50, 70)
        quadro.novo_dia(cal)
        if cal.util:
            self._agenda_do_dia(t, cal)
            self._pressa(cal)

    def _sair(self, p, t, cal):
        p.presente = False
        self.sis["quadro"].bater_ponto(t, p.id, "saída")
        if p.remoto_desde is not None:
            minutos = max(1, t - p.remoto_desde)
            p.remoto_desde = None
        elif p.extra_ate and p.data == cal.data:
            minutos = max(0, cal.absoluto - p.sai)
        else:
            minutos = 0
        if p.data is not None:
            if minutos > 0:
                self.sis["quadro"].hora_extra(p.id, p.equipe, p.data, minutos)
                p.extras_recentes.append((p.data, minutos))
                del p.extras_recentes[:-15]

    # ======================================================================================================== o minuto
    def minuto(self, t, cal):
        a = cal.absoluto
        agenda = self.sis["agenda"]
        ocupados = agenda.minuto(t, cal)
        antes = self.em_curso_antes
        if antes:
            agora_ids = {r[2] for r in agenda.agora}
            for r in antes:
                if r[2] not in agora_ids:
                    acao = self.ao_fim.pop(r[2], None)
                    if acao:
                        self._ao_fim_da_reuniao(t, cal, acao, r)
        self.em_curso_antes = agenda.agora
        self._operacao(t, cal)
        if cal.minuto % 5 == 0:
            self._urgencias_do_desenvolvimento(t, cal)
        for p in self.pessoas:
            if not p.ativo:
                continue
            urgente = p.tarefa is not None and p.tarefa.get("urgente")
            no_turno = p.ausente is None and cal.util and p.data == cal.data and p.chega <= a
            if not p.presente:
                if no_turno and a < p.sai:
                    p.presente = True
                    p.remoto_desde = None
                    self.sis["quadro"].bater_ponto(t, p.id, "entrada")
                elif urgente:
                    p.presente = True                       # chamada fora de hora: trabalha de casa
                    p.remoto_desde = t
                    self.sis["quadro"].bater_ponto(t, p.id, "entrada")
                else:
                    continue
            elif not urgente:
                if p.remoto_desde is not None or not no_turno:
                    self._sair(p, t, cal)
                    continue
                if a >= max(p.sai, p.extra_ate):
                    if not p.extra_decidida:
                        p.extra_decidida = True
                        extra = self._ficar(p, t, cal)
                        if extra:
                            p.extra_ate = a + extra
                    if a >= max(p.sai, p.extra_ate):
                        self._sair(p, t, cal)
                        continue
            if p.almoco_ini <= a < p.almoco_fim and not urgente:
                continue
            if p.id in ocupados and not urgente:
                continue
            self._trabalhar(p, t, cal, a)

    def _trabalhar(self, p, t, cal, a):
        tar = p.tarefa
        if tar is None:
            if p.ocioso_ate > t:
                return
            tar = self._escolher(p, t, cal)
            if tar is None:
                p.ocioso_ate = t + p.s.randint(15, 40)
                return
            p.tarefa = tar
        tar["resta"] -= 1
        if tar["resta"] <= 0:
            p.tarefa = None
            self._concluir(p, tar, t, cal)
            if p.tarefa is None and p.suspensa is not None:
                p.tarefa, p.suspensa = p.suspensa, None

    def _ficar(self, p, t, cal):
        """Quanto tempo a pessoa fica além da hora hoje (0 se vai embora)."""
        s = p.s
        tar = p.tarefa
        if tar is not None and tar.get("urgente"):
            return 240
        g = p.grupo
        if g in ("dev", "qa") and p.projeto in self.pressa:
            pr = self.pressa[p.projeto]
            if pr > 1.12 and s.random() < min(0.85, 0.4 + (pr - 1.0)):
                return s.randint(45, 150)
            if tar is not None and tar.get("item") and tar.get("prioridade") in ("crítica", "alta") and s.random() < 0.5:
                return s.randint(30, 90)
        if g == "atendimento":
            fila = self.sis["fluxo"].contar("SUP", "chamado", ("aberto",))
            if fila > 25 and s.random() < 0.6:
                return s.randint(30, 100)
        if g == "vendas" and cal.fim_do_mes() and s.random() < 0.35:
            return s.randint(30, 75)
        if g == "ops" and (self.incidente is not None or self.hotfix):
            return s.randint(60, 180)
        if s.random() < 0.04:
            return s.randint(15, 40)
        return 0

    def _escolher(self, p, t, cal):
        porta = self.sis["porta"]
        if p.grupo not in ("dono",):
            ato = porta.proximo(p.equipe, t)
            if ato is not None:
                dur = {"pergunta": p.s.randint(10, 25), "pedido": p.s.randint(30, 80), "convocacao": p.s.randint(5, 12)}[ato["tipo"]]
                return {"tipo": "ato", "resta": dur, "ato": ato["numero"]}
        return getattr(self, "_escolher_" + p.grupo)(p, t, cal)

    def _concluir(self, p, tar, t, cal):
        getattr(self, "_fim_" + tar["tipo"])(p, tar, t, cal)

    def _fim_interno(self, p, tar, t, cal):
        return None

    def _fim_ato(self, p, tar, t, cal):
        self.sis["porta"].tratar(tar["ato"], p, t, cal, self)

    # ======================================================================================================== a agenda
    def _agenda_do_dia(self, t, cal):
        agenda = self.sis["agenda"]
        if cal.data in agenda.geradas:
            return
        agenda.geradas.add(cal.data)
        base = cal.data * MINUTOS_DIA
        ids = lambda lista: [p.id for p in lista]
        eq = {e: self.da_equipe(e) for e in ("produto", "desenvolvimento", "qualidade", "atendimento", "vendas", "operação", "gestão")}
        sq = {pr: [p for p in self.ativas() if p.projeto == pr and p.grupo in ("dev", "qa")] for pr in ("PROD", "PLAT")}
        pm = {pr: [p for p in eq["produto"] if p.projeto == pr] for pr in ("PROD", "PLAT")}
        agenda.marcar(t, "diária", "atendimento", base + 8 * 60 + 45, 15, ids(eq["atendimento"]), "diária do atendimento")
        agenda.marcar(t, "diária", "vendas", base + 9 * 60, 15, ids(eq["vendas"]), "diária de vendas")
        agenda.marcar(t, "diária", "produto", base + 9 * 60 + 15, 15, ids(eq["produto"]), "diária de produto")
        agenda.marcar(t, "diária", "desenvolvimento", base + 9 * 60 + 30, 15, ids(sq["PROD"] + pm["PROD"][:1]), "diária do squad Produto")
        agenda.marcar(t, "diária", "desenvolvimento", base + 9 * 60 + 45, 15, ids(sq["PLAT"] + pm["PLAT"][:1]), "diária do squad Plataforma")
        agenda.marcar(t, "diária", "operação", base + 10 * 60, 15, ids(eq["operação"]), "diária da operação")
        if cal.dia_semana == 0:
            lideres = [p for p in self.ativas() if p.papel in ("dono", "líder de produto", "líder técnico", "coordenador de atendimento",
                                                                 "gerente de vendas", "financeiro")] + eq["operação"][:1]
            agenda.marcar(t, "liderança", "gestão", base + 11 * 60, 60, ids(lideres), "reunião de liderança")
            for e in ("atendimento", "vendas", "operação", "gestão"):
                agenda.marcar(t, "semanal", e, base + 14 * 60 + (30 if e == "gestão" else 0), 60, ids(eq[e]), f"semanal da equipe de {e}")
        if cal.dia_semana == 2:
            for pr, hora in (("PROD", 14 * 60), ("PLAT", 15 * 60 + 30)):
                lider = self.lider(pr)
                devs = [p for p in sq[pr] if p.grupo == "dev" and p is not lider][:2]
                qa = [p for p in sq[pr] if p.grupo == "qa"][:1]
                agenda.marcar(t, "refinamento", "produto", base + hora, 60, ids(pm[pr] + ([lider] if lider else []) + devs + qa),
                              f"refinamento do squad {pr}")
        if cal.dia_sprint == 0:
            for pr, hora, dur in (("PROD", 10 * 60 + 30, 120), ("PLAT", 14 * 60, 120)):
                extra = [p for p in eq["produto"] if p.papel in ("designer", "analista de produto")] if pr == "PROD" else []
                rid = agenda.marcar(t, "planejamento", "desenvolvimento", base + hora, dur, ids(sq[pr] + pm[pr] + extra),
                                    f"planejamento do sprint do squad {pr}")
                self.ao_fim[rid] = ("planejar", pr)
            rid = agenda.marcar(t, "planejamento", "atendimento", base + 10 * 60 + 15, 30, ids(eq["atendimento"]), "planejamento do sprint do suporte")
            self.ao_fim[rid] = ("planejar", "SUP")
            rid = agenda.marcar(t, "planejamento", "operação", base + 10 * 60 + 30, 30, ids(eq["operação"]), "planejamento do sprint de infraestrutura")
            self.ao_fim[rid] = ("planejar", "INFRA")
        if cal.dia_sprint == 11:
            for pr in ("PROD", "PLAT"):
                rid = agenda.marcar(t, "revisão e retrospectiva", "desenvolvimento", base + 15 * 60, 90, ids(sq[pr] + pm[pr]),
                                    f"revisão e retrospectiva do squad {pr}")
                self.ao_fim[rid] = ("retrospectiva", pr)
        primeiro_util = cal.dia_mes == 1 or (cal.dia_semana == 0 and cal.dia_mes <= 3)
        if primeiro_util:
            rid = agenda.marcar(t, "mensal", "gestão", base + 16 * 60, 60, ids(self.ativas()), "reunião mensal com a direção")
            self.ao_fim[rid] = ("mensal", None)

    def _ao_fim_da_reuniao(self, t, cal, acao, r):
        tipo, arg = acao[0], acao[1]
        if tipo == "entrevista":
            self._ao_fim_entrevista(t, acao)
        elif tipo == "planejar":
            self._planejar(t, cal, arg)
        elif tipo == "retrospectiva":
            sp = self.sis["fluxo"].sprint_aberto(arg)
            if sp is not None:
                total, feitos, n = self.sis["fluxo"].pontos_do_sprint(sp["id"])
                texto = (f"entregamos {feitos} de {total} pontos; " + ("faltou gente e sobrou escopo" if feitos < 0.8 * total
                                                                        else "o ritmo ficou bom"))
                self.sis["fluxo"].db.execute("UPDATE sprints SET retrospectiva=? WHERE id=?", (texto, sp["id"]))
        elif tipo == "mensal":
            if self.mes_compromisso != cal.mes and t - getattr(self, "compromisso_t", -10 ** 9) > 20 * MINUTOS_DIA:
                self.mes_compromisso = cal.mes
                self.compromisso_t = t
                if cal.mes > 0 or not self.compromissos:
                    # o dono promete ao mercado um lançamento para o fim do mês, do tamanho do que acha que o squad aguenta
                    s = self.s
                    projeto = "PROD" if s.random() < 0.7 else "PLAT"
                    sp = self.sis["fluxo"].sprint_aberto(projeto)
                    cap = sp["capacidade_pontos"] if sp is not None and sp["capacidade_pontos"] else 40
                    fim_mes = (cal.data + (cal.dias_no_mes - cal.dia_mes)) * MINUTOS_DIA + 18 * 60
                    self.compromissos.append({"projeto": projeto, "prazo": fim_mes + s.randint(0, 10) * MINUTOS_DIA,
                                              "pontos": int(cap * s.uniform(0.6, 1.4)), "titulo": "lançamento prometido no mês",
                                              "epico": None, "origem": "dono", "componente": s.choice(COMPONENTES_SQUAD[projeto])})
        elif tipo == "pós-incidente":
            fluxo = self.sis["fluxo"]
            if not self.runbook:
                fluxo.criar(t, "INFRA", "tarefa", "escrever o procedimento para volume do banco cheio", prioridade="alta",
                            componente="infra", equipe="operação", pontos=2)
            fluxo.criar(t, "PLAT", "história", "limpeza automática da auditoria do produto", prioridade="baixa", componente="infra",
                        equipe="desenvolvimento", pontos=5)

    # ======================================================================================================== sprints
    def _dias_disponiveis(self, projeto, cal, dias=10):
        devs = [p for p in self.ativas() if p.grupo == "dev" and p.projeto == projeto]
        total = 0
        for p in devs:
            for d in range(cal.data, cal.data + 14):
                if d % 7 < 5 and d not in p.ferias:
                    total += 1
        return total, len(devs)

    def _planejar(self, t, cal, projeto):
        fluxo = self.sis["fluxo"]
        if self.ultimo_planejamento.get(projeto, -10 ** 9) > t - 10 * MINUTOS_DIA:
            return
        self.ultimo_planejamento[projeto] = t
        anterior = fluxo.sprint_aberto(projeto)
        carregado = []
        if anterior is not None:
            total, feitos, n = fluxo.pontos_do_sprint(anterior["id"])
            if projeto in self.velocidade_dev:
                dd = max(1, anterior["capacidade_pontos"] / max(0.1, self.velocidade_dev[projeto]))
                medida = feitos / dd if anterior["capacidade_pontos"] else self.velocidade_dev[projeto]
                self.velocidade_dev[projeto] = 0.6 * self.velocidade_dev[projeto] + 0.4 * max(0.25, min(1.2, medida))
            fluxo.fechar_sprint(t, anterior["id"], anterior["retrospectiva"] or "sprint encerrado no planejamento")
            carregado = [r for r in fluxo.itens(sprint=anterior["id"]) if r["estado"] not in FINAIS and r["estado"] != "pronto para liberar"]
            self.sis["verdade"].sprint_fechado(t, projeto, anterior["numero"], total, feitos)
        self.sprint_numero[projeto] += 1
        numero = self.sprint_numero[projeto]
        fim_previsto = (cal.data + 12) * MINUTOS_DIA
        if projeto in ("SUP", "INFRA"):
            sid = fluxo.abrir_sprint(t, projeto, numero, fim_previsto, 0, 0, "manter a casa em ordem")
            equipe = "atendimento" if projeto == "SUP" else "operação"
            pontos = 0
            for r in carregado:
                fluxo.por_no_sprint(r["id"], sid)
                pontos += r["pontos"] or 1
            for _ in range(self.s.randint(3, 6)):
                titulo = (self.s.choice(("artigo na base de conhecimento", "resposta pronta para dúvidas frequentes", "revisão de chamados antigos"))
                          if projeto == "SUP" else self.s.choice(TEMAS["infra"]))
                pts = self.s.choice((1, 2, 2, 3))
                fluxo.criar(t, projeto, "tarefa", titulo, prioridade="média", componente=None if projeto == "SUP" else "infra",
                            equipe=equipe, pontos=pts, sprint=sid, estado="pronto para desenvolver")
                pontos += pts
            fluxo.db.execute("UPDATE sprints SET meta_pontos=?, capacidade_pontos=? WHERE id=?", (pontos, pontos, sid))
            self.sis["eventos"].append((t, f"sprint {numero} do projeto {'Suporte' if projeto == 'SUP' else 'Infraestrutura'} aberto"))
            return
        dias, ndevs = self._dias_disponiveis(projeto, cal)
        capacidade = max(8, int(round(dias * self.velocidade_dev[projeto])))
        fim_sprint = (cal.data + 14) * MINUTOS_DIA
        obrigatorio = []
        for r in carregado:
            obrigatorio.append(r)
        # compromissos que vencem neste sprint entram inteiros
        devidos = [c for c in self.compromissos if c["projeto"] == projeto and c["epico"] is not None and c["prazo"] <= fim_sprint + 3 * MINUTOS_DIA]
        ids_obrig = {r["id"] for r in obrigatorio}
        for c in devidos:
            for r in fluxo.itens(projeto=projeto, tipo="história", extra=f" AND epico={int(c['epico'])} AND estado NOT IN ('liberado', 'pronto para liberar')"):
                if r["id"] not in ids_obrig:
                    obrigatorio.append(r)
                    ids_obrig.add(r["id"])
        for r in fluxo.itens(projeto=projeto, tipo="bug", estados=("pronto para desenvolver", "triagem", "aberto"),
                             extra=" AND prioridade IN ('alta', 'crítica')"):
            if r["id"] not in ids_obrig:
                obrigatorio.append(r)
                ids_obrig.add(r["id"])
        pts_obrig = sum((r["pontos"] or 2) for r in obrigatorio)
        meta = max(capacidade, pts_obrig)
        escolhidos = list(obrigatorio)
        soma = pts_obrig
        if soma < capacidade:
            prontos = fluxo.itens(projeto=projeto, tipo=("história", "tarefa", "bug"), estados=("pronto para desenvolver",),
                                  ordem=PRIO_ORDEM + ", COALESCE(prazo, 1e12), id")
            compromisso_ids = {c["epico"] for c in self.compromissos if c["epico"] is not None}
            for r in prontos:
                if r["id"] in ids_obrig:
                    continue
                if r["epico"] in compromisso_ids:
                    continue                              # o que não vence agora fica para depois
                pts = r["pontos"] or 2
                if soma + pts > capacidade:
                    continue
                escolhidos.append(r)
                soma += pts
        sid = fluxo.abrir_sprint(t, projeto, numero, fim_previsto, meta, capacidade, "entregar os compromissos e o épico em andamento")
        for r in escolhidos:
            fluxo.por_no_sprint(r["id"], sid)
            if r["estado"] in ("backlog", "refinamento", "aberto", "triagem"):
                fluxo.estimar(r["id"], r["pontos"] or 3)
                fluxo.transitar(t, r["id"], "pronto para desenvolver", "produto")
        razao = meta / capacidade
        self.pressao_planejada[projeto] = razao
        self.pressa[projeto] = max(1.0, razao)
        self.sis["verdade"].sprint_planejado(t, projeto, numero, meta, capacidade, razao, cal)
        self.sis["eventos"].append((t, f"sprint {numero} do projeto {'Produto' if projeto == 'PROD' else 'Plataforma'} aberto com meta de {meta} pontos"))

    def _pressa(self, cal):
        """A pressa de cada squad: quanto falta no sprint perto do que ainda dá para fazer até o fim dele."""
        fluxo = self.sis["fluxo"]
        for projeto in ("PROD", "PLAT"):
            sp = fluxo.sprint_aberto(projeto)
            if sp is None:
                self.pressa[projeto] = 1.0
                continue
            total, feitos, n = fluxo.pontos_do_sprint(sp["id"])
            restante = total - feitos
            dias_rest = max(1, 10 - sum(1 for d in range(cal.data - cal.dia_sprint, cal.data) if d % 7 < 5))
            devs = [p for p in self.ativas() if p.grupo == "dev" and p.projeto == projeto]
            pode = max(1.0, dias_rest * len(devs) * self.velocidade_dev[projeto] * 0.9)
            self.pressa[projeto] = max(0.5, min(2.5, restante / pode))

    # ======================================================================================================== produto (a equipe)
    def _escolher_produto(self, p, t, cal):
        fluxo = self.sis["fluxo"]
        s = p.s
        if p.papel == "líder de produto":
            for c in self.compromissos:
                if c["epico"] is None:
                    return {"tipo": "epico_compromisso", "resta": s.randint(60, 120), "compromisso": c}
            for projeto in ("PROD", "PLAT"):
                ep = self.epico_ativo[projeto]
                if ep is None or fluxo.item(ep)["estado"] == "concluído":
                    return {"tipo": "epico_roteiro", "resta": s.randint(60, 120), "projeto": projeto}
        projetos = (p.projeto,) if p.projeto in ("PROD", "PLAT") else ("PROD", "PLAT")
        for projeto in projetos:
            prontos = fluxo.contar(projeto, "história", ("pronto para desenvolver",)) + fluxo.contar(projeto, "tarefa", ("pronto para desenvolver",))
            alvo = 1.4 * self.velocidade_dev[projeto] * 10 * len([x for x in self.ativas() if x.grupo == "dev" and x.projeto == projeto]) / 3.0
            if prontos < alvo:
                r = fluxo.itens(projeto=projeto, tipo="história", estados=("refinamento",), ordem=PRIO_ORDEM + ", id", limite=1)
                if r:
                    return {"tipo": "refinar", "resta": s.randint(30, 70), "item": r[0]["id"]}
                r = fluxo.itens(projeto=projeto, tipo="história", estados=("backlog",), ordem=PRIO_ORDEM + ", id", limite=1)
                if r:
                    return {"tipo": "preparar", "resta": s.randint(20, 45), "item": r[0]["id"]}
                return {"tipo": "historia_avulsa", "resta": s.randint(30, 60), "projeto": projeto}
        if s.random() < 0.25:
            projeto = s.choice(projetos)
            return {"tipo": "historia_avulsa", "resta": s.randint(30, 60), "projeto": projeto}
        return {"tipo": "interno", "resta": s.randint(30, 70)}

    def _criar_epico(self, t, projeto, titulo, n_historias, funcionalidade, prazo, componente, ator):
        fluxo = self.sis["fluxo"]
        s = self.s
        ep = fluxo.criar(t, projeto, "épico", titulo, prioridade="alta" if prazo else "média", componente=componente,
                         equipe="produto", ator=ator, prazo=prazo)
        fluxo.transitar(t, ep, "em andamento", ator)
        comps = COMPONENTES_SQUAD[projeto]
        for i in range(n_historias):
            comp = componente or s.choice(comps)
            tema = s.choice(TEMAS.get(comp, TEMAS["catalogo"]))
            pts = s.choice((2, 3, 3, 5, 5, 8))
            h = fluxo.criar(t, projeto, "história", f"{titulo}: {tema}", prioridade="alta", componente=comp,
                            equipe="desenvolvimento", ator=ator, pontos=pts, epico=ep, prazo=prazo)
        if funcionalidade is not None:
            funcao, impl, rota, tit = funcionalidade
            comp = ROTA_COMPONENTE[rota]
            h = fluxo.criar(t, projeto, "história", f"{titulo}: ligar {tit}", prioridade="alta", componente=comp,
                            equipe="desenvolvimento", ator=ator, pontos=s.choice((3, 5)), epico=ep, prazo=prazo)
            self.func_historia[h] = funcionalidade
        return ep

    def _fim_epico_compromisso(self, p, tar, t, cal):
        c = tar["compromisso"]
        if c["epico"] is not None:
            return
        n = max(3, c["pontos"] // 4)
        c["epico"] = self._criar_epico(t, c["projeto"], c["titulo"], n, None, c["prazo"], c["componente"], "produto")
        self.sis["fluxo"].comentar(t, c["epico"], "produto", "compromisso com prazo; vence no fim do sprint em que cair")

    def _fim_epico_roteiro(self, p, tar, t, cal):
        projeto = tar["projeto"]
        fluxo = self.sis["fluxo"]
        ep = self.epico_ativo[projeto]
        if ep is not None and fluxo.item(ep)["estado"] != "concluído":
            return
        func = None
        i = self.prox_funcionalidade[projeto]
        for k in range(i, i + 60):
            f = codigo.funcionalidade(k)
            comp = ROTA_COMPONENTE[f[2]]
            if COMPONENTE_PROJETO[comp] == projeto:
                func = f
                self.prox_funcionalidade[projeto] = k + 1
                break
        titulo = func[3] if func else "melhorias da plataforma"
        n = self.s.randint(5, 8) if projeto == "PROD" else self.s.randint(4, 6)
        self.epico_ativo[projeto] = self._criar_epico(t, projeto, titulo, n, func, None, None, "produto")

    def _fim_refinar(self, p, tar, t, cal):
        fluxo = self.sis["fluxo"]
        r = fluxo.item(tar["item"])
        if r is None or r["estado"] != "refinamento":
            return
        fluxo.estimar(r["id"], r["pontos"] or p.s.choice((2, 3, 5)))
        fluxo.transitar(t, r["id"], "pronto para desenvolver", "produto")
        if p.s.random() < 0.4:
            fluxo.comentar(t, r["id"], "produto", "critérios de aceite revisados")

    def _fim_preparar(self, p, tar, t, cal):
        fluxo = self.sis["fluxo"]
        r = fluxo.item(tar["item"])
        if r is not None and r["estado"] == "backlog":
            fluxo.transitar(t, r["id"], "refinamento", "produto")

    def _fim_historia_avulsa(self, p, tar, t, cal):
        projeto = tar["projeto"]
        s = p.s
        comp = s.choice(COMPONENTES_SQUAD[projeto])
        tipo = "história" if s.random() < 0.7 else "tarefa"
        self.sis["fluxo"].criar(t, projeto, tipo, s.choice(TEMAS[comp]), prioridade=s.choice(("baixa", "média", "média", "alta")),
                                componente=comp, equipe="desenvolvimento", ator="produto", pontos=s.choice((1, 2, 3, 5)))

    # ======================================================================================================== desenvolvimento
    def _escolher_dev(self, p, t, cal):
        fluxo = self.sis["fluxo"]
        s = p.s
        pr = p.projeto
        # 1. o que voltou para mim (revisão ou qualidade pediu correção)
        for r in fluxo.itens(projeto=pr, estados=("em desenvolvimento", "em andamento"), responsavel=p.id, limite=3):
            if r["id"] in self.reprovacoes:
                return {"tipo": "corrigir", "resta": s.randint(30, 110) / p.velocidade, "item": r["id"], "prioridade": r["prioridade"]}
        # 2. os bugs urgentes não esperam triagem
        r = fluxo.itens(projeto=pr, tipo="bug", estados=("aberto", "triagem", "pronto para desenvolver"), responsavel=None,
                        extra=" AND prioridade IN ('crítica', 'alta')", ordem=PRIO_ORDEM + ", id", limite=1)
        if r:
            return self._pegar(p, t, r[0], "investigar", s.randint(30, 140) / p.velocidade)
        # 3. a triagem (líder)
        if p.papel == "líder técnico":
            r = fluxo.itens(projeto=pr, tipo="bug", estados=("aberto",), ordem="id", limite=1)
            if r:
                return {"tipo": "triagem", "resta": s.randint(10, 25), "item": r[0]["id"]}
        # 3. revisar o código dos colegas
        r = fluxo.itens(projeto=pr, estados=("em revisão",), extra=f" AND (responsavel IS NULL OR responsavel<>{p.id})",
                        ordem="atualizado_em", limite=4)
        for item in r:
            if item["id"] not in self.reprovacoes and self.autor.get(item["id"]) != p.id and not item["id"] in self._revisando():
                return {"tipo": "revisar", "resta": s.randint(15, 45), "item": item["id"]}
        # 5. continuar o que é meu
        for r in fluxo.itens(projeto=pr, estados=("em desenvolvimento", "em andamento"), responsavel=p.id, limite=3):
            if r["id"] in self.restante:
                bloco = min(self.restante[r["id"]], s.randint(120, 300))
                return {"tipo": "desenvolver", "resta": bloco, "bloco": bloco, "item": r["id"], "prioridade": r["prioridade"]}
        # 6. o próximo item do sprint
        sp = fluxo.sprint_aberto(pr)
        if sp is not None:
            cands = fluxo.itens(projeto=pr, estados=("pronto para desenvolver",), sprint=sp["id"], responsavel=None,
                                ordem=PRIO_ORDEM + ", COALESCE(prazo, 1e12), id", limite=8)
            for r in cands:
                if r["id"] in self.func_historia and not self._epico_pronto_para_ligar(r):
                    continue
                if r["tipo"] == "bug":
                    return self._pegar(p, t, r, "investigar", s.randint(30, 140) / p.velocidade)
                return self._pegar(p, t, r, "desenvolver", self._duracao(p, r))
        # 7. fora do planejado: puxa do que está pronto (o compromisso que ainda não vence fica para depois)
        cands = fluxo.itens(projeto=pr, tipo=("história", "tarefa", "bug"), estados=("pronto para desenvolver",), responsavel=None,
                            ordem=PRIO_ORDEM + ", id", limite=12)
        adiados = {c["epico"] for c in self.compromissos if c["epico"] is not None}
        for r in cands:
            if r["id"] in self.func_historia and not self._epico_pronto_para_ligar(r):
                continue
            if r["epico"] in adiados and r["sprint"] is None:
                continue
            if sp is not None:
                fluxo.por_no_sprint(r["id"], sp["id"])
            if r["tipo"] == "bug":
                return self._pegar(p, t, r, "investigar", s.randint(30, 140) / p.velocidade)
            return self._pegar(p, t, r, "desenvolver", self._duracao(p, r))
        return {"tipo": "interno", "resta": s.randint(25, 60)}

    def _revisando(self):
        out = set()
        for q in self.pessoas:
            if q.tarefa is not None and q.tarefa["tipo"] == "revisar":
                out.add(q.tarefa["item"])
        return out

    def _epico_pronto_para_ligar(self, r):
        fluxo = self.sis["fluxo"]
        outros = fluxo.db.execute("SELECT COUNT(*) FROM itens WHERE epico=? AND id<>? AND estado NOT IN ('liberado', 'pronto para liberar')",
                                  (r["epico"], r["id"])).fetchone()[0]
        return outros == 0

    def _duracao(self, p, r):
        pts = r["pontos"] or 2
        rush = max(0.0, min(1.0, self.pressa.get(p.projeto, 1.0) - 1.0))
        return pts * MIN_POR_PONTO / p.velocidade * (1.0 - 0.22 * rush) * p.s.lognormvariate(0.0, 0.3)

    def _pegar(self, p, t, r, tipo, dur):
        fluxo = self.sis["fluxo"]
        para = "em andamento" if r["tipo"] == "tarefa" else "em desenvolvimento"
        if r["tipo"] == "bug" and r["estado"] == "triagem":
            fluxo.transitar(t, r["id"], "pronto para desenvolver", "desenvolvimento")
        fluxo.transitar(t, r["id"], para, "desenvolvimento", equipe="desenvolvimento")
        fluxo.atribuir(r["id"], p.id)
        self.autor[r["id"]] = p.id
        if p.s.random() < 0.3:
            fluxo.comentar(t, r["id"], "desenvolvimento", "comecei; dúvida sobre o comportamento esperado registrada")
        if tipo == "desenvolver":
            self.restante[r["id"]] = dur
            dur = min(dur, p.s.randint(120, 300))
        tar = {"tipo": tipo, "resta": dur, "bloco": dur, "item": r["id"], "prioridade": r["prioridade"]}
        if r["prioridade"] == "crítica":
            tar["urgente"] = True
        return tar

    def _fim_triagem(self, p, tar, t, cal):
        fluxo = self.sis["fluxo"]
        r = fluxo.item(tar["item"])
        if r is None or r["estado"] != "aberto":
            return
        fluxo.transitar(t, r["id"], "triagem", "desenvolvimento")
        chamados = len(fluxo.ligados_a(r["id"], "escalado para"))
        prio = r["prioridade"]
        if chamados >= 6 or r["origem"] == "monitoramento":
            prio = "crítica"
        elif chamados >= 2 and prio in ("baixa", "média"):
            prio = "alta"
        if prio != r["prioridade"]:
            fluxo.priorizar(r["id"], prio)
        fluxo.estimar(r["id"], p.s.choice((1, 2, 2, 3)))
        if prio in ("alta", "crítica"):
            sp = fluxo.sprint_aberto(r["projeto"])
            if sp is not None:
                fluxo.por_no_sprint(r["id"], sp["id"])
        fluxo.transitar(t, r["id"], "pronto para desenvolver", "desenvolvimento")
        fluxo.comentar(t, r["id"], "desenvolvimento", f"triagem: prioridade {prio}")

    def _fim_desenvolver(self, p, tar, t, cal):
        fluxo = self.sis["fluxo"]
        repo = self.sis["repo"]
        r = fluxo.item(tar["item"])
        if r is None or r["estado"] not in ("em desenvolvimento", "em andamento"):
            self.restante.pop(tar["item"], None)
            return
        falta = self.restante.get(r["id"], 0) - tar.get("bloco", 0)
        if falta > 1:
            self.restante[r["id"]] = falta
            if p.s.random() < 0.35:
                repo.commit(t, r["id"], r["componente"], {}, p.s.randint(10, 120), "desenvolvimento", "trabalho em andamento")
            if p.s.random() < 0.12:
                fluxo.comentar(t, r["id"], "desenvolvimento", "andamento registrado")
            return
        self.restante.pop(r["id"], None)
        mudancas = {}
        func = self.func_historia.get(r["id"])
        if func is not None:
            mudancas[func[0]] = func[1]
        comp = r["componente"]
        pts = r["pontos"] or 2
        rush = max(0.0, self.pressa.get(p.projeto, 1.0) - 1.0)
        chance = 1.0 - math.exp(-0.05 * pts * (1.0 + 2.0 * min(1.0, rush)) * p.cuidado)
        if comp in COMPONENTES_SQUAD.get(r["projeto"], ()) or comp == "login":
            if p.s.random() < chance:
                ramo = repo.codigo_do_ramo(r["id"])
                ramo.update(mudancas)
                opcoes = [(f, v) for (f, v) in codigo.DEFEITOS if codigo.COMPONENTE_FUNCAO[f] == comp
                          and ramo[f] == repo.correta[f] and f not in mudancas]
                if opcoes:
                    f, v = p.s.choice(sorted(opcoes))
                    mudancas[f] = v
                    self.sis["verdade"].defeito_escrito(t, r["id"], r["projeto"], f, v, self.pressa.get(p.projeto, 1.0))
        linhas = int(pts * p.s.randint(25, 90))
        repo.commit(t, r["id"], comp, mudancas, linhas, "desenvolvimento", r["titulo"])
        if p.s.random() < 0.5:
            repo.commit(t, r["id"], comp, {}, int(linhas * 0.3), "desenvolvimento", "ajustes")
        fluxo.transitar(t, r["id"], "em revisão", "desenvolvimento")
        fluxo.comentar(t, r["id"], "desenvolvimento", "pronto para revisão")

    def _fim_corrigir(self, p, tar, t, cal):
        fluxo = self.sis["fluxo"]
        repo = self.sis["repo"]
        r = fluxo.item(tar["item"])
        funcoes = self.reprovacoes.pop(tar["item"], [])
        if r is None:
            return
        mudancas = {f: repo.correta[f] for f in funcoes}
        repo.commit(t, r["id"], r["componente"], mudancas, p.s.randint(5, 60), "desenvolvimento", "correção do que voltou")
        destino = "em qualidade" if r["tipo"] in ("história", "bug") else "em revisão"
        fluxo.transitar(t, r["id"], destino, "desenvolvimento", equipe="qualidade" if destino == "em qualidade" else None)
        if destino == "em qualidade":
            fluxo.atribuir(r["id"], None)
        fluxo.comentar(t, r["id"], "desenvolvimento", "corrigido; pode testar de novo")

    def _fim_revisar(self, p, tar, t, cal):
        fluxo = self.sis["fluxo"]
        repo = self.sis["repo"]
        r = fluxo.item(tar["item"])
        if r is None or r["estado"] != "em revisão":
            return
        ramo = repo.ramos.get(r["id"], {})
        defeitos = [f for f, v in ramo.items() if (f, v) in codigo.DEFEITOS]
        rush = max(0.0, min(1.0, self.pressa.get(p.projeto, 1.0) - 1.0))
        if defeitos and p.s.random() < 0.3 * (1.0 - 0.5 * rush):
            repo.registrar_revisao(t, r["id"], "pediu mudanças")
            self.reprovacoes[r["id"]] = defeitos
            fluxo.transitar(t, r["id"], "em andamento" if r["tipo"] == "tarefa" else "em desenvolvimento", "desenvolvimento")
            fluxo.atribuir(r["id"], self.autor.get(r["id"]))
            fluxo.comentar(t, r["id"], "desenvolvimento", "revisão: a mudança quebra um caso; ver comentário no código")
            for f in defeitos:
                self.sis["verdade"].defeito_barrado(t, r["id"], f, "revisão de código")
            return
        if r["tipo"] == "tarefa" and self.nulo == "sem_defeito" and r["componente"]:
            # no nulo sem defeito nada chega ao principal sem a bateria inteira de testes
            n, falhas = rodar_testes(repo.codigo_do_ramo(r["id"]), r["componente"], p.s, 1.0, todos=True)
            repo.registrar_testes(t, r["componente"], "ramo", n, len(falhas), "desenvolvimento")
            if falhas:
                self.reprovacoes[r["id"]] = sorted({f for f, _, _ in falhas})
                fluxo.transitar(t, r["id"], "em andamento", "desenvolvimento")
                fluxo.atribuir(r["id"], self.autor.get(r["id"]))
                return
        repo.registrar_revisao(t, r["id"], "aprovou")
        if r["tipo"] == "tarefa":
            fluxo.transitar(t, r["id"], "pronto para liberar", "desenvolvimento")
            repo.mesclar(r["id"])
        else:
            fluxo.transitar(t, r["id"], "em qualidade", "desenvolvimento", equipe="qualidade")
            fluxo.atribuir(r["id"], None)

    def _fim_investigar(self, p, tar, t, cal):
        """Um bug: reproduzir (rodar a bateria inteira do componente contra o código no ar e o principal), corrigir ou fechar."""
        fluxo = self.sis["fluxo"]
        repo = self.sis["repo"]
        r = fluxo.item(tar["item"])
        if r is None or r["estado"] not in ("em desenvolvimento",):
            return
        comp = r["componente"]
        if comp is None or comp == "infra":
            fluxo.transitar(t, r["id"], "não reproduzido", "desenvolvimento")
            fluxo.comentar(t, r["id"], "desenvolvimento", "não é do código do produto")
            return
        no_ar = repo.versoes[repo.no_ar]
        n1, falhas_ar = rodar_testes(no_ar, comp, p.s, 1.0, todos=True)
        n2, falhas_principal = rodar_testes(repo.principal, comp, p.s, 1.0, todos=True)
        repo.registrar_testes(t, comp, "no ar", n1, len(falhas_ar), "desenvolvimento")
        repo.registrar_testes(t, comp, "principal", n2, len(falhas_principal), "desenvolvimento")
        funcoes = sorted({f for f, _, _ in falhas_ar} | {f for f, _, _ in falhas_principal})
        if not funcoes:
            fluxo.transitar(t, r["id"], "não reproduzido", "desenvolvimento")
            fluxo.comentar(t, r["id"], "desenvolvimento", "não reproduzimos; testes do componente passam")
            return
        mudancas = {f: repo.correta[f] for f in funcoes}
        repo.commit(t, r["id"], comp, mudancas, p.s.randint(5, 40), "desenvolvimento", f"correção em {', '.join(funcoes)}")
        self.hotfix_funcoes = getattr(self, "hotfix_funcoes", {})
        self.hotfix_funcoes[r["id"]] = mudancas
        no_principal = {f for f, _, _ in falhas_principal}
        for f in funcoes:
            origem = repo.autoria.get(f) if f in no_principal else None
            if origem is not None and origem != r["id"]:
                o = fluxo.item(origem)
                if o is not None and o["estado"] == "liberado" and o["tipo"] in ("história", "tarefa"):
                    fluxo.transitar(t, origem, "em desenvolvimento" if o["tipo"] != "tarefa" else "em andamento", "desenvolvimento")
                    fluxo.ligar(t, r["id"], origem, "causado por")
                    fluxo.comentar(t, origem, "desenvolvimento", "reaberto: um bug no ar veio desta mudança")
        fluxo.comentar(t, r["id"], "desenvolvimento", "reproduzido nos testes; correção pronta")
        fluxo.transitar(t, r["id"], "em qualidade", "desenvolvimento", equipe="qualidade")
        fluxo.atribuir(r["id"], None)

    # ======================================================================================================== qualidade
    def _escolher_qa(self, p, t, cal):
        fluxo = self.sis["fluxo"]
        s = p.s
        pr = p.projeto
        r = fluxo.itens(projeto=pr, estados=("em qualidade",), responsavel=None, ordem=PRIO_ORDEM + ", atualizado_em", limite=1)
        if r:
            r = r[0]
            fluxo.atribuir(r["id"], p.id)
            if r["tipo"] == "bug":
                dur = s.randint(20, 45)
            else:
                rush = max(0.0, min(1.0, self.pressa.get(pr, 1.0) - 1.0))
                dur = (r["pontos"] or 2) * s.randint(35, 70) * (1.0 - 0.35 * rush) + 20
            return {"tipo": "testar", "resta": dur, "item": r["id"], "prioridade": r["prioridade"]}
        if cal.dia_semana in (1, 3) and 9 * 60 + 30 <= cal.minuto < 12 * 60 and self.ultima_regressao.get(pr, -10 ** 9) < t - 36 * 60:
            self.ultima_regressao[pr] = t
            return {"tipo": "regressao", "resta": s.randint(40, 90)}
        sp = fluxo.sprint_aberto(pr)
        if s.random() < 0.3:
            return {"tipo": "interno", "resta": s.randint(30, 60)}
        return None

    def _fim_testar(self, p, tar, t, cal):
        fluxo = self.sis["fluxo"]
        repo = self.sis["repo"]
        r = fluxo.item(tar["item"])
        if r is None or r["estado"] != "em qualidade":
            return
        comp = r["componente"]
        rush = max(0.0, min(1.0, self.pressa.get(p.projeto, 1.0) - 1.0))
        todos = r["tipo"] == "bug" or self.nulo == "sem_defeito"
        cobertura = p.cobertura * (1.0 - 0.5 * rush)
        cod = repo.codigo_do_ramo(r["id"])
        n, falhas = rodar_testes(cod, comp, p.s, cobertura, todos=todos) if comp else (0, [])
        repo.registrar_testes(t, comp or "", "ramo", n, len(falhas), "qualidade")
        if falhas:
            funcoes = sorted({f for f, _, _ in falhas})
            self.reprovacoes[r["id"]] = funcoes
            fluxo.transitar(t, r["id"], "em desenvolvimento", "qualidade", equipe="desenvolvimento")
            fluxo.atribuir(r["id"], self.autor.get(r["id"]))
            fluxo.comentar(t, r["id"], "qualidade", "reprovado: " + "; ".join(nome for _, nome, _ in falhas))
            for f in funcoes:
                self.sis["verdade"].defeito_barrado(t, r["id"], f, "qualidade")
            return
        fluxo.transitar(t, r["id"], "pronto para liberar", "qualidade")
        fluxo.comentar(t, r["id"], "qualidade", f"aprovado; {n} testes")
        repo.mesclar(r["id"])
        if r["tipo"] == "bug" and r["prioridade"] in ("crítica", "alta"):
            self.hotfix.append(r["id"])

    def _fim_regressao(self, p, tar, t, cal):
        """Antes da liberação: alguns componentes do principal, com a bateria parcial."""
        repo = self.sis["repo"]
        fluxo = self.sis["fluxo"]
        comps = COMPONENTES_SQUAD[p.projeto]
        for comp in p.s.sample(list(comps), 2):
            n, falhas = rodar_testes(repo.principal, comp, p.s, 0.4)
            repo.registrar_testes(t, comp, "principal", n, len(falhas), "qualidade")
            for funcao in sorted({f for f, _, _ in falhas}):
                origem = repo.autoria.get(funcao)
                bug = fluxo.criar(t, p.projeto, "bug", f"regressão em {NOME_COMPONENTE[comp]}", prioridade="alta", componente=comp,
                                  equipe="desenvolvimento", ator="qualidade", origem="qualidade")
                if origem is not None:
                    fluxo.ligar(t, bug, origem, "causado por")
                    o = fluxo.item(origem)
                    if o is not None and o["estado"] == "liberado" and o["tipo"] in ("história", "tarefa"):
                        fluxo.transitar(t, origem, "em desenvolvimento" if o["tipo"] != "tarefa" else "em andamento", "qualidade")
                self.sis["verdade"].defeito_barrado(t, origem, funcao, "regressão")

    # ======================================================================================================== atendimento
    def _escolher_atendimento(self, p, t, cal):
        fluxo = self.sis["fluxo"]
        s = p.s
        # escalados cujo destino já se resolveu
        r = fluxo.db.execute(
            "SELECT c.id FROM itens c JOIN ligacoes l ON l.de = c.id AND l.tipo='escalado para' JOIN itens b ON b.id = l.para "
            "WHERE c.projeto='SUP' AND c.estado='escalado' AND b.estado IN ('liberado', 'não reproduzido', 'concluído') "
            "ORDER BY c.id LIMIT 1").fetchone()
        if r is not None:
            return {"tipo": "resolver_escalado", "resta": s.randint(4, 10), "item": r[0]}
        foco, ate = self.foco_atendimento
        cond = ""
        if foco and t < ate:
            cond = f"CASE WHEN componente='{foco}' THEN 0 ELSE 1 END, "
        r = fluxo.db.execute(
            "SELECT * FROM itens WHERE projeto='SUP' AND tipo='chamado' AND COALESCE(origem, '') <> 'porta' AND (estado='aberto' OR "
            "(estado='em atendimento' AND responsavel IS NULL)) ORDER BY " + cond + "criado_em + CASE prioridade WHEN 'crítica' THEN 60 WHEN 'alta' THEN 240 "
            "WHEN 'média' THEN 1440 ELSE 4320 END, id LIMIT 1").fetchone()
        if r is not None:
            fluxo.atribuir(r["id"], p.id)
            if r["estado"] == "aberto":
                fluxo.transitar(t, r["id"], "em atendimento", "atendimento")
            massa = self.incidente is not None or (self.sis["clientes"].chamados.get(r["id"], {}).get("motivo") == "erro"
                                                  and fluxo.contar("SUP", "chamado", ("aberto",)) > 30)
            dur = s.randint(5, 12) if massa else s.lognormvariate(math.log(20), 0.45)
            return {"tipo": "chamado", "resta": dur, "item": r["id"]}
        sp = fluxo.sprint_aberto("SUP")
        if sp is not None and s.random() < 0.5:
            r = fluxo.itens(projeto="SUP", tipo="tarefa", estados=("pronto para desenvolver",), sprint=sp["id"], responsavel=None, limite=1)
            if r:
                fluxo.transitar(t, r[0]["id"], "em andamento", "atendimento")
                fluxo.atribuir(r[0]["id"], p.id)
                return {"tipo": "tarefa_simples", "resta": (r[0]["pontos"] or 1) * s.randint(90, 180), "item": r[0]["id"]}
        return {"tipo": "interno", "resta": s.randint(10, 30)}

    def _fim_chamado(self, p, tar, t, cal):
        fluxo = self.sis["fluxo"]
        cli = self.sis["clientes"]
        r = fluxo.item(tar["item"])
        if r is None or r["estado"] != "em atendimento":
            return
        d = cli.chamados.get(r["id"], {})
        motivo = d.get("motivo", "dúvida")
        s = p.s
        comp = r["componente"]
        if motivo == "cancelamento":
            self.sis["quadro"].solicitar(t, "cancelamento", "cliente pediu cancelamento", cliente=r["cliente"])
            fluxo.comentar(t, r["id"], "atendimento", "encaminhado ao financeiro")
            self._resolver(t, r["id"])
            return
        if motivo in ("dúvida", "fatura"):
            if s.random() < 0.8 or "o cliente respondeu" in self._ultimos_comentarios(r["id"]):
                fluxo.comentar(t, r["id"], "atendimento", "orientação enviada")
                self._resolver(t, r["id"])
            else:
                fluxo.comentar(t, r["id"], "atendimento", "pedimos mais detalhes")
                fluxo.transitar(t, r["id"], "aguardando cliente", "atendimento")
                cli.pedir_resposta(t, r["id"], cal)
            return
        # problema técnico: incidente aberto, bug conhecido, ou escalar
        if self.incidente is not None and self.incidente.get("item") is not None:
            self._escalar(t, r, self.incidente["item"], "incidente em andamento")
            return
        if motivo == "cobrança em dobro" and s.random() < 0.7:
            self.sis["quadro"].solicitar(t, "estorno", "estornar cobrança em dobro", cliente=r["cliente"])
        conhecido = fluxo.db.execute(
            "SELECT id FROM itens WHERE tipo='bug' AND componente=? AND estado NOT IN ('liberado', 'não reproduzido') AND criado_em > ? "
            "ORDER BY id DESC LIMIT 1", (comp, t - 5 * MINUTOS_DIA)).fetchone()
        if conhecido is not None:
            self._escalar(t, r, conhecido[0], "mesmo problema de um bug aberto")
            n = len(fluxo.ligados_a(conhecido[0], "escalado para"))
            b = fluxo.item(conhecido[0])
            nova = "crítica" if n >= 6 else ("alta" if n >= 3 else None)
            if nova and b is not None and PRIO_NUM[nova] < PRIO_NUM[b["prioridade"]]:
                fluxo.priorizar(conhecido[0], nova)
                fluxo.comentar(t, conhecido[0], "atendimento", f"já são {n} chamados ligados a este bug")
            return
        if s.random() < 0.25 and "o cliente respondeu" not in self._ultimos_comentarios(r["id"]):
            fluxo.comentar(t, r["id"], "atendimento", "pedimos passos para reproduzir")
            fluxo.transitar(t, r["id"], "aguardando cliente", "atendimento")
            cli.pedir_resposta(t, r["id"], cal)
            return
        recentes = fluxo.db.execute("SELECT COUNT(*) FROM itens WHERE projeto='SUP' AND componente=? AND criado_em > ? AND tipo='chamado'",
                                    (comp, t - 180)).fetchone()[0]
        prio = "crítica" if recentes >= 8 else ("alta" if recentes >= 3 or r["prioridade"] in ("alta", "crítica") else "média")
        projeto = COMPONENTE_PROJETO.get(comp, "PROD")
        if projeto == "INFRA":
            projeto = "PLAT"
        titulo = {"erro": f"erro em {NOME_COMPONENTE.get(comp, comp)} relatado por clientes",
                  "lentidão": f"lentidão em {NOME_COMPONENTE.get(comp, comp)}", "cobrança em dobro": "cliente cobrado duas vezes",
                  "nota não emitida": "nota fiscal não emitida"}.get(motivo, "problema relatado por cliente")
        bug = fluxo.criar(t, projeto, "bug", titulo, prioridade=prio, componente=comp, equipe="desenvolvimento", ator="atendimento",
                          origem="atendimento")
        self._escalar(t, r, bug, "escalado para o desenvolvimento")

    def _ultimos_comentarios(self, item):
        return " ".join(x[0] for x in self.sis["fluxo"].db.execute("SELECT texto FROM comentarios WHERE item=? ORDER BY id DESC LIMIT 3", (item,)).fetchall())

    def _escalar(self, t, r, destino, texto):
        fluxo = self.sis["fluxo"]
        fluxo.ligar(t, r["id"], destino, "escalado para")
        fluxo.comentar(t, r["id"], "atendimento", texto)
        fluxo.transitar(t, r["id"], "escalado", "atendimento")
        self.escalacoes_dia += 1
        self.sis["verdade"].escalado(t, r["id"], destino)

    def _resolver(self, t, item):
        fluxo = self.sis["fluxo"]
        fluxo.transitar(t, item, "resolvido", "atendimento")
        self.sis["clientes"].chamado_resolvido(t, item)

    def _fim_resolver_escalado(self, p, tar, t, cal):
        fluxo = self.sis["fluxo"]
        r = fluxo.item(tar["item"])
        if r is None or r["estado"] != "escalado":
            return
        fluxo.transitar(t, r["id"], "em atendimento", "atendimento")
        fluxo.comentar(t, r["id"], "atendimento", "o problema foi corrigido; avisamos o cliente")
        self._resolver(t, r["id"])

    def _fim_tarefa_simples(self, p, tar, t, cal):
        fluxo = self.sis["fluxo"]
        r = fluxo.item(tar["item"])
        if r is not None and r["estado"] == "em andamento":
            fluxo.transitar(t, r["id"], "concluído", p.equipe)

    # ======================================================================================================== vendas
    def _escolher_sdr(self, p, t, cal):
        crm = self.sis["crm"]
        s = p.s
        n = crm.proximo(t, ("lead",))
        if n is not None:
            crm.assumir(n["id"], p.id)
            return {"tipo": "ligar_lead", "resta": s.randint(12, 30), "negocio": n["id"]}
        if crm.em_estagio("lead") < 3 and s.random() < 0.22:
            return {"tipo": "prospectar", "resta": s.randint(35, 70)}
        return {"tipo": "interno", "resta": s.randint(20, 45)}

    def _fim_ligar_lead(self, p, tar, t, cal):
        crm = self.sis["crm"]
        n = crm.negocio(tar["negocio"])
        if n is None or n[2] != "lead":
            return
        s = p.s
        crm.atividade(t, n[0], "ligação")
        r = s.random()
        if r < 0.35:
            dono = self._executivo_com_menos(crm)
            crm.mover(t, n[0], "qualificação", proxima=t)
            if dono is not None:
                crm.assumir(n[0], dono.id)
        elif r < 0.65:
            crm.mover(t, n[0], "perdido")
        else:
            if n[8] >= 2:
                crm.mover(t, n[0], "perdido")
            else:
                crm.adiar(t, n[0], t + MINUTOS_DIA)

    def _executivo_com_menos(self, crm):
        execs = [p for p in self.ativas() if p.papel == "executivo de vendas"]
        if not execs:
            return None
        carga = []
        for p in execs:
            c = crm.db.execute("SELECT COUNT(*) FROM negocios WHERE responsavel=? AND estagio IN ('qualificação', 'proposta', 'negociação')",
                               (p.id,)).fetchone()[0]
            carga.append((c, p.id, p))
        return min(carga)[2]

    def _fim_prospectar(self, p, tar, t, cal):
        s = p.s
        crm = self.sis["crm"]
        for _ in range(s.choice((0, 1, 1, 2))):
            plano = s.choice(("básico", "básico", "pro", "empresarial"))
            crm.novo(t, "prospecção", plano, VALOR_PLANO[plano], proxima=t + s.randint(30, 240))
        crm.atividade(t, None, "e-mail")

    def _escolher_vendas(self, p, t, cal):
        crm = self.sis["crm"]
        s = p.s
        n = crm.proximo(t, ("qualificação", "proposta", "negociação"), responsavel=p.id)
        if n is not None:
            crm.assumir(n["id"] if hasattr(n, "keys") else n[0], p.id)
            est = n[2]
            dur = {"qualificação": s.randint(15, 30), "proposta": s.randint(15, 30), "negociação": s.randint(20, 40)}[est]
            if est == "qualificação" and n[8] == 1:
                dur = s.randint(40, 80)                      # escrever a proposta depois da demonstração
            return {"tipo": "negocio", "resta": dur, "negocio": n[0]}
        if p.papel == "gerente de vendas" and s.random() < 0.3:
            return {"tipo": "interno", "resta": s.randint(30, 60)}
        if (cal.fim_do_mes() and s.random() < 0.35) or t < self.foco_vendas:
            n = crm.db.execute("SELECT id FROM negocios WHERE estagio IN ('proposta', 'negociação') AND responsavel=? ORDER BY proxima_acao_em LIMIT 1",
                               (p.id,)).fetchone()
            if n is not None:
                crm.db.execute("UPDATE negocios SET proxima_acao_em=? WHERE id=?", (t, n[0]))
                return {"tipo": "negocio", "resta": s.randint(15, 30), "negocio": n[0]}
        if crm.em_estagio("qualificação") + crm.em_estagio("proposta") < 5 and s.random() < 0.15:
            return {"tipo": "prospectar", "resta": s.randint(35, 70)}
        return {"tipo": "interno", "resta": s.randint(20, 50)}

    def _fim_negocio(self, p, tar, t, cal):
        crm = self.sis["crm"]
        n = crm.negocio(tar["negocio"])
        if n is None or n[2] not in ("qualificação", "proposta", "negociação"):
            return
        s = p.s
        a = cal.absoluto
        est = n[2]
        if est == "qualificação":
            if n[8] == 0:                                   # marcar a demonstração
                pessoas = [p.id]
                if n[3] == "empresarial":
                    g = [x for x in self.ativas() if x.papel == "gerente de vendas"]
                    pessoas += [x.id for x in g[:1]]
                ini = self.sis["agenda"].primeiro_horario_livre(pessoas, a + s.randint(1, 3) * MINUTOS_DIA - 6 * 60, 60)
                if ini is None:
                    crm.adiar(t, n[0], t + MINUTOS_DIA)
                    return
                self.sis["agenda"].marcar(t, "com cliente", "vendas", ini, s.choice((45, 60)), pessoas, "demonstração para um lead")
                crm.atividade(t, n[0], "e-mail")
                crm.db.execute("UPDATE negocios SET proxima_acao_em=?, tentativas=1 WHERE id=?", (t + (ini - a) + 60, n[0]))
                return
            crm.atividade(t, n[0], "proposta")
            crm.mover(t, n[0], "proposta", proxima=t + s.randint(2, 4) * MINUTOS_DIA)
            return
        crm.atividade(t, n[0], "ligação")
        fim_mes = cal.fim_do_mes()
        if est == "proposta":
            r = s.random()
            if r < 0.42:
                crm.mover(t, n[0], "negociação", proxima=t + s.randint(1, 3) * MINUTOS_DIA)
            elif r < 0.58:
                crm.mover(t, n[0], "perdido")
            else:
                crm.adiar(t, n[0], t + s.randint(2, 4) * MINUTOS_DIA)
            return
        ganho = 0.135 * (1.6 if fim_mes else 1.0)
        r = s.random()
        if r < ganho:
            crm.mover(t, n[0], "ganho")
            plano = n[3]
            self.sis["quadro"].solicitar(t, "nova conta", f"criar conta do plano {plano}", cliente=n[0])
            if plano == "empresarial" and s.random() < 0.55:
                projeto = "PROD" if s.random() < 0.7 else "PLAT"
                self.compromissos.append({"projeto": projeto, "prazo": t + s.randint(21, 35) * MINUTOS_DIA, "pontos": s.randint(18, 40),
                                          "titulo": "funcionalidade prometida a um cliente empresarial", "epico": None,
                                          "origem": "vendas", "componente": s.choice(COMPONENTES_SQUAD[projeto])})
        elif r < ganho + 0.12:
            crm.mover(t, n[0], "perdido")
        else:
            crm.adiar(t, n[0], t + (MINUTOS_DIA if fim_mes else s.randint(1, 3) * MINUTOS_DIA))

    # ======================================================================================================== gestão
    def _escolher_financeiro(self, p, t, cal):
        q = self.sis["quadro"]
        s = p.s
        r = q.proxima_solicitacao(t, ("nova conta", "cancelamento", "estorno"))
        if r is not None:
            q.db.execute("UPDATE solicitacoes SET estado='em andamento' WHERE id=?", (r[0],))
            return {"tipo": "solicitacao", "resta": s.randint(20, 50), "sid": r[0], "stipo": r[2], "cliente": r[6]}
        return {"tipo": "interno", "resta": s.randint(30, 70)}

    def _fim_solicitacao(self, p, tar, t, cal):
        q = self.sis["quadro"]
        cli = self.sis["clientes"]
        if tar["stipo"] == "nova conta":
            n = self.sis["crm"].negocio(tar["cliente"])
            plano = n[3] if n is not None else "básico"
            c = cli.entrar(t, plano, self.sis["produto"], self.sis["verdade"])
            onboarding = [x.id for x in self.ativas() if x.papel == "analista de atendimento"]
            if onboarding:
                quem = [p.s.choice(onboarding)]
                ini = self.sis["agenda"].primeiro_horario_livre(quem, cal.absoluto, 45)
                if ini is not None:
                    self.sis["agenda"].marcar(t, "com cliente", "atendimento", ini, 45, quem, "boas-vindas a um cliente novo")
        elif tar["stipo"] == "cancelamento":
            cli.sair(t, tar["cliente"], self.sis["produto"], self.sis["verdade"])
        elif tar["stipo"] == "estorno":
            self.sis["estornos"][0] += 1
        q.concluir_solicitacao(t, tar["sid"])

    def _escolher_rh(self, p, t, cal):
        q = self.sis["quadro"]
        s = p.s
        for v in q.vagas_abertas():
            if v[6] != "aberta":
                continue
            if q.candidatos(v[0], "proposta"):
                return {"tipo": "fechar_vaga", "resta": s.randint(20, 40), "vaga": v[0]}
            if q.candidatos(v[0], "entrevista") and not self._entrevista_marcada(v[0]):
                return {"tipo": "marcar_entrevista", "resta": s.randint(10, 20), "vaga": v[0]}
            if q.candidatos(v[0], "triagem"):
                return {"tipo": "triar", "resta": s.randint(20, 40), "vaga": v[0]}
            if s.random() < 0.3:
                return {"tipo": "buscar_candidatos", "resta": s.randint(40, 90), "vaga": v[0]}
        return self._escolher_financeiro(p, t, cal)

    def _entrevista_marcada(self, vaga):
        return any(k[0] == "entrevista" and k[1] == vaga for k in self.ao_fim.values())

    def _fim_buscar_candidatos(self, p, tar, t, cal):
        for _ in range(p.s.randint(1, 3)):
            self.sis["quadro"].candidato(t, tar["vaga"], "triagem", p.s.uniform(0.2, 1.0))

    def _fim_triar(self, p, tar, t, cal):
        q = self.sis["quadro"]
        for c in q.candidatos(tar["vaga"], "triagem"):
            q.mover_candidato(t, c[0], "entrevista" if c[4] > 0.55 else "reprovado")

    def _fim_marcar_entrevista(self, p, tar, t, cal):
        q = self.sis["quadro"]
        v = q.db.execute("SELECT * FROM vagas WHERE id=?", (tar["vaga"],)).fetchone()
        cands = q.candidatos(tar["vaga"], "entrevista")
        if v is None or not cands:
            return
        lider = None
        for x in self.ativas():
            if x.equipe == v[1] and x.papel in ("líder técnico", "coordenador de atendimento", "gerente de vendas", "líder de produto"):
                lider = x
                break
        pessoas = [p.id] + ([lider.id] if lider else [])
        ini = self.sis["agenda"].primeiro_horario_livre(pessoas, cal.absoluto + MINUTOS_DIA, 60)
        if ini is None:
            return
        rid = self.sis["agenda"].marcar(t, "entrevista", "gestão", ini, 60, pessoas, "entrevista com candidato")
        self.ao_fim[rid] = ("entrevista", tar["vaga"], cands[0][0])

    def _fim_fechar_vaga(self, p, tar, t, cal):
        q = self.sis["quadro"]
        v = q.db.execute("SELECT * FROM vagas WHERE id=?", (tar["vaga"],)).fetchone()
        cands = q.candidatos(tar["vaga"], "proposta")
        if v is None or not cands:
            return
        if v[6] != "aberta":
            return
        if p.s.random() < 0.75:
            q.mover_candidato(t, cands[0][0], "contratado")
            for outro in cands[1:] + q.candidatos(v[0], "entrevista") + q.candidatos(v[0], "triagem"):
                q.mover_candidato(t, outro[0], "dispensado")
            q.mudar_vaga(t, v[0], "em contratação")
            inicio = t + p.s.randint(10, 18) * MINUTOS_DIA - cal.minuto
            self.admissoes = getattr(self, "admissoes", [])
            self.admissoes.append((inicio, v[0], v[1], v[2], v[3]))
        else:
            q.mover_candidato(t, cands[0][0], "desistiu")

    def _escolher_dono(self, p, t, cal):
        return {"tipo": "interno", "resta": p.s.randint(30, 90)}

    # ---------- reuniões que terminam em decisão ----------
    def _ao_fim_entrevista(self, t, acao):
        _, vaga, cand = acao
        q = self.sis["quadro"]
        c = q.db.execute("SELECT * FROM candidatos WHERE id=?", (cand,)).fetchone()
        if c is not None and c[2] == "entrevista":
            q.mover_candidato(t, cand, "proposta" if c[4] > 0.7 else "reprovado")

    def _saidas_e_avisos(self, t, cal):
        q = self.sis["quadro"]
        for p in self.pessoas:
            if not p.ativo:
                continue
            if p.sai_em is not None and t >= p.sai_em - 18 * 60:
                p.ativo = False
                p.presente = False
                q.desligar(t, p.id)
                q.mes["saídas"] += 1
                self.sis["agenda"].desmarcar_pessoa(p.id, cal.absoluto)
                fluxo = self.sis["fluxo"]
                for r in fluxo.itens(estados=("em desenvolvimento", "em andamento"), responsavel=p.id):
                    if r["tipo"] in ("história", "tarefa", "bug"):
                        fluxo.transitar(t, r["id"], "pronto para desenvolver", "desenvolvimento")
                    self.restante.pop(r["id"], None)
                fluxo.db.execute("UPDATE itens SET responsavel=NULL WHERE responsavel=? AND estado NOT IN ('liberado', 'concluído', 'fechado')", (p.id,))
                vaga = q.abrir_vaga(t, p.equipe, p.papel, p.projeto, "reposição")
                self.sis["eventos"].append((t, f"saída de uma pessoa da equipe de {p.equipe}"))
                self.sis["verdade"].pessoal_evento(t, "saída", p.equipe)
                continue
            if p.sai_em is None and p.papel not in ("dono",):
                extra = sum(m for d, m in p.extras_recentes if d > cal.data - 14)
                chance = 0.001 * (1.0 + (2.0 if extra > 600 else 0.0))
                if p.s.random() < chance:
                    p.sai_em = t + p.s.randint(15, 30) * MINUTOS_DIA
                    self.sis["eventos"].append((t, f"uma pessoa da equipe de {p.equipe} pediu demissão"))

    def _contratacao(self, t, cal):
        q = self.sis["quadro"]
        for adm in list(getattr(self, "admissoes", [])):
            inicio, vaga, equipe, papel, projeto = adm
            if t >= inicio:
                self.admissoes.remove(adm)
                novo = self._nova_pessoa(t, equipe, papel, projeto)
                novo.velocidade *= 0.7
                novo.data = cal.data
                base = cal.data * MINUTOS_DIA
                novo.chega = base + novo.inicio
                novo.sai = novo.chega + 540
                novo.almoco_ini = base + novo.almoco
                novo.almoco_fim = novo.almoco_ini + 60
                q.mudar_vaga(t, vaga, "preenchida")
                q.mes["entradas"] += 1
                self.sis["eventos"].append((t, f"contratação na equipe de {equipe}"))
                self.sis["verdade"].pessoal_evento(t, "contratação", equipe)
        # o atendimento pede gente quando a fila fica alta por dias seguidos
        fila = self.sis["fluxo"].contar("SUP", "chamado", ("aberto", "em atendimento"))
        n_at = len(self.da_equipe("atendimento"))
        self.fila_alta_dias = self.fila_alta_dias + 1 if fila > 4 * n_at else 0
        if self.fila_alta_dias >= 5 and t - self.vaga_crescimento_em > 30 * MINUTOS_DIA:
            self.vaga_crescimento_em = t
            q.abrir_vaga(t, "atendimento", "analista de atendimento", "SUP", "crescimento")

    def _gestao_diaria(self, t, cal):
        """O dono lê o relatório do dia anterior: se as escalações dispararam, convoca a liderança para alinhar."""
        dono = self.dono()
        if dono is None:
            return
        if getattr(self, "escalacoes_ontem", 0) >= 12 and self.dia_alinhamento != cal.data:
            self.dia_alinhamento = cal.data
            lideres = [p.id for p in self.ativas() if p.papel in ("dono", "líder técnico", "coordenador de atendimento", "líder de produto")]
            ini = self.sis["agenda"].primeiro_horario_livre(lideres, cal.absoluto + 8 * 60, 45)
            if ini is not None:
                self.sis["agenda"].marcar(t, "alinhamento", "gestão", ini, 45, lideres, "alinhamento sobre os chamados de ontem")
        self.escalacoes_ontem = self.escalacoes_dia

    # ======================================================================================================== operação
    def _urgencias_do_desenvolvimento(self, t, cal):
        """Um bug crítico sem ninguém: o plantão do squad (ou quem estiver livre) larga o que faz e pega."""
        fluxo = self.sis["fluxo"]
        ocupados = self.sis["agenda"].ocupados
        for projeto in ("PROD", "PLAT"):
            r = fluxo.itens(projeto=projeto, tipo="bug", estados=("aberto", "triagem", "pronto para desenvolver"), responsavel=None,
                            extra=" AND prioridade='crítica'", ordem="id", limite=1)
            if not r:
                continue
            devs = [p for p in self.ativas() if p.grupo == "dev" and p.projeto == projeto and p.presente and p.id not in ocupados
                    and not (p.tarefa is not None and (p.tarefa.get("urgente") or p.tarefa["tipo"] == "investigar"))]
            if not devs:
                continue
            semana = cal.data // 7
            n = len(devs)
            devs.sort(key=lambda p: (0 if p.id % n == semana % n else 1, p.id))
            p = devs[0]
            if p.tarefa is not None:
                p.suspensa = p.tarefa
            p.tarefa = self._pegar(p, t, r[0], "investigar", p.s.randint(30, 120) / p.velocidade)
            p.tarefa["urgente"] = True

    def _plantonista(self, cal):
        ops = self.da_equipe("operação")
        if not ops:
            return None
        return ops[(cal.data // 7) % len(ops)]

    def _operacao(self, t, cal):
        """O que a operação vê a cada minuto: a sonda, os alertas, as janelas de liberação, os pedidos de correção no ar."""
        produto = self.sis["produto"]
        a = cal.absoluto
        # ---- a sonda: o produto parou de responder ----
        if produto.sonda_falhas_seguidas >= 3 and self.incidente is None:
            expediente = cal.util and 8 * 60 <= cal.minuto < 19 * 60
            espera = (self.s.lognormvariate(math.log(5), 0.5) if expediente else self.s.lognormvariate(math.log(18), 0.45))
            self.incidente = {"inicio": t, "aviso": t + int(espera), "item": None, "quem": None, "resolvido": False}
            self.sis["eventos"].append((t, "o produto parou de responder"))
        inc = self.incidente
        if inc is not None and inc["quem"] is None and t >= inc["aviso"]:
            quem = None
            for p in self.da_equipe("operação"):
                if p.presente and p.id not in self.sis["agenda"].ocupados and not (p.tarefa and p.tarefa.get("urgente")):
                    quem = p
                    break
            if quem is None:
                quem = self._plantonista(cal)
            if quem is not None:
                inc["quem"] = quem.id
                fluxo = self.sis["fluxo"]
                inc["item"] = fluxo.criar(t, "INFRA", "bug", "produto fora do ar", prioridade="crítica", componente="infra",
                                          equipe="operação", ator="operação", origem="monitoramento")
                fluxo.transitar(t, inc["item"], "em desenvolvimento", "operação")
                dur = quem.s.randint(8, 20) if self.runbook else quem.s.randint(22, 50)
                if quem.tarefa is not None and not quem.tarefa.get("urgente"):
                    quem.suspensa = quem.tarefa
                quem.tarefa = {"tipo": "incidente", "resta": dur, "urgente": True}
                quem.ocioso_ate = 0
        if inc is not None and inc["resolvido"] and produto.sonda_falhas_seguidas == 0:
            self.incidente = None
        # ---- alertas de erro, lentidão, memória e fila (vistos por quem está na operação) ----
        if cal.minuto % 5 == 0:
            self._avaliar_alertas(t, cal)
        if self.alertas:
            for p in self.da_equipe("operação"):
                if p.presente and p.tarefa is None or (p.presente and p.tarefa is not None and p.tarefa["tipo"] in ("interno", "tarefa_infra")):
                    if p.id in self.sis["agenda"].ocupados:
                        continue
                    chave = sorted(self.alertas)[0]
                    if p.s.random() < 0.07:
                        al = self.alertas.pop(chave)
                        self.silencio[chave] = t + 6 * 60
                        if p.tarefa is not None:
                            p.suspensa = p.tarefa
                        p.tarefa = {"tipo": "alerta", "resta": p.s.randint(12, 35), "chave": chave, "alerta": al}
                        break
        # ---- liberações: terças e quintas à tarde; fim de sprint na sexta de manhã; correção no ar quando há ----
        if cal.util:
            regular = cal.dia_semana in (1, 3) and 15 * 60 <= cal.minuto < 16 * 60
            fim_sprint = cal.dia_sprint == 11 and 11 * 60 <= cal.minuto < 12 * 60
            if (regular or fim_sprint) and t - self.ultima_liberacao > 12 * 60 and self.incidente is None:
                congelado = self.sis["fluxo"].db.execute(
                    "SELECT COUNT(*) FROM itens WHERE tipo='bug' AND origem='monitoramento' AND prioridade='crítica' AND estado IN "
                    "('aberto', 'triagem', 'pronto para desenvolver', 'em desenvolvimento', 'em qualidade') AND criado_em > ?",
                    (t - 3 * MINUTOS_DIA,)).fetchone()[0]
                if self.sis["repo"].pendentes_implantacao[1] > 0 and not congelado:
                    quem = self._ops_livre()
                    if quem is not None:
                        self.ultima_liberacao = t
                        quem.suspensa = quem.tarefa if quem.tarefa and not quem.tarefa.get("urgente") else quem.suspensa
                        quem.tarefa = {"tipo": "liberar", "resta": quem.s.randint(15, 35), "origem": "regular"}
        if self.hotfix:
            expediente = cal.util and 8 * 60 <= cal.minuto < 19 * 60
            critico = any(self.sis["fluxo"].item(b)["prioridade"] == "crítica" for b in self.hotfix)
            if expediente or critico:
                quem = self._ops_livre() if expediente else self._plantonista(cal)
                if quem is not None and not (quem.tarefa and quem.tarefa["tipo"] in ("liberar", "corrigir_no_ar", "incidente")):
                    bugs, self.hotfix = self.hotfix, []
                    if quem.tarefa and not quem.tarefa.get("urgente"):
                        quem.suspensa = quem.tarefa
                    quem.tarefa = {"tipo": "corrigir_no_ar", "resta": quem.s.randint(10, 25), "bugs": bugs, "urgente": not expediente}

    def _ops_livre(self):
        for p in self.da_equipe("operação"):
            if p.presente and p.id not in self.sis["agenda"].ocupados and not (p.tarefa and p.tarefa.get("urgente")) \
                    and not (p.tarefa and p.tarefa["tipo"] in ("liberar", "corrigir_no_ar", "alerta")):
                return p
        return None

    def _avaliar_alertas(self, t, cal):
        produto = self.sis["produto"]
        for rota in produto.historico_latencia:
            chave = ("erros", rota)
            if self.silencio.get(chave, 0) > t or chave in self.alertas:
                continue
            req, err = produto.erros_na_janela(rota, 10)
            if err >= 20 and err >= 0.10 * max(1, req):
                self.alertas[chave] = {"t": t, "rota": rota, "tipo": "erros"}
        for rota in produto.historico_latencia:
            chave = ("lentidão", rota)
            if self.silencio.get(chave, 0) > t or chave in self.alertas:
                continue
            hab = produto.latencia_habitual(rota)
            agora = produto.latencia_na_janela(rota, 15)
            if hab is not None and agora > 2.5 * hab and agora > 400:
                self.alertas[chave] = {"t": t, "rota": rota, "tipo": "lentidão"}
        chave = ("fila", "fila")
        pend = produto.fila_pendentes
        if pend > 150 and self.silencio.get(chave, 0) <= t and chave not in self.alertas:
            self.alertas[chave] = {"t": t, "rota": "fila", "tipo": "fila"}
        chave = ("memória", "processo")
        quedas = sum(1 for x in produto.erros if x[1] == "processo" and x[0] > t - MINUTOS_DIA)
        if quedas >= 2 and self.silencio.get(chave, 0) <= t and chave not in self.alertas:
            self.alertas[chave] = {"t": t, "rota": "processo", "tipo": "memória"}

    def _escolher_ops(self, p, t, cal):
        fluxo = self.sis["fluxo"]
        s = p.s
        sp = fluxo.sprint_aberto("INFRA")
        r = fluxo.itens(projeto="INFRA", tipo="tarefa", estados=("pronto para desenvolver", "backlog"), responsavel=None,
                        ordem=PRIO_ORDEM + ", id", limite=1, extra=" AND COALESCE(origem, '') <> 'porta'")
        if r and (sp is not None or r[0]["prioridade"] in ("alta", "crítica")):
            fluxo.transitar(t, r[0]["id"], "em andamento", "operação")
            fluxo.atribuir(r[0]["id"], p.id)
            return {"tipo": "tarefa_infra", "resta": (r[0]["pontos"] or 1) * s.randint(100, 220), "item": r[0]["id"]}
        return {"tipo": "interno", "resta": s.randint(20, 50)}

    def _fim_tarefa_infra(self, p, tar, t, cal):
        fluxo = self.sis["fluxo"]
        r = fluxo.item(tar["item"])
        if r is not None and r["estado"] == "em andamento":
            fluxo.transitar(t, r["id"], "concluído", "operação")
            if "procedimento" in r["titulo"]:
                self.runbook = True

    def _fim_incidente(self, p, tar, t, cal):
        """O diagnóstico acabou: o volume do banco está cheio. Apaga a auditoria velha e aumenta o volume, com folga de semanas."""
        produto = self.sis["produto"]
        fluxo = self.sis["fluxo"]
        inc = self.incidente
        s = p.s
        cheio = produto.volume_paginas - produto.paginas_ocupadas() < 200
        if cheio:
            dias = s.randint(2, 6)
            apagados = produto.apagar_auditoria_antiga(t, dias)
            hist = list(produto.paginas_dia)
            if len(hist) >= 2:
                cresc = max(50.0, (hist[-1][1] - hist[0][1]) / max(1.0, (hist[-1][0] - hist[0][0]) / MINUTOS_DIA))
            else:
                cresc = 600.0
            folga = s.randint(21, 35)
            produto.aumentar_volume(produto.paginas_ocupadas() + int(cresc * folga))
            texto = f"volume do banco cheio; apagamos {apagados} registros de auditoria e aumentamos o volume para cerca de {folga} dias de folga"
            self.sis["verdade"].incidente_resolvido(t, "volume do banco cheio", folga, apagados)
        else:
            produto.no_ar_ate = 0
            texto = "processo reiniciado"
            self.sis["verdade"].incidente_resolvido(t, "processo parado", 0, 0)
        if inc is not None:
            inc["resolvido"] = True
            if inc["item"] is not None:
                fluxo.comentar(t, inc["item"], "operação", texto)
                fluxo.transitar(t, inc["item"], "liberado", "operação")
        self.sis["eventos"].append((t, "o produto voltou a responder"))
        # o pós-incidente no próximo dia útil
        envolvidos = [x.id for x in self.da_equipe("operação")] + [x.id for x in self.ativas() if x.papel in ("dono", "líder técnico", "coordenador de atendimento")]
        ini = self.sis["agenda"].primeiro_horario_livre(envolvidos, cal.absoluto + 12 * 60, 60)
        if ini is not None:
            rid = self.sis["agenda"].marcar(t, "alinhamento", "operação", ini, 60, envolvidos, "pós-incidente")
            self.ao_fim[rid] = ("pós-incidente", None)

    def _fim_alerta(self, p, tar, t, cal):
        """Investigar um alerta: ler o registro de erros (o rastro diz a função), ver se começou depois da última liberação."""
        produto = self.sis["produto"]
        repo = self.sis["repo"]
        fluxo = self.sis["fluxo"]
        al = tar["alerta"]
        rota = al["rota"]
        if al["tipo"] == "erros":
            recentes = [e for e in produto.erros if e[1] == rota and e[0] > t - 60]
        elif al["tipo"] == "fila":
            recentes = [e for e in produto.erros if e[1] == "fila" and e[0] > t - 120]
        elif al["tipo"] == "memória":
            recentes = [e for e in produto.erros if e[1] == "processo" and e[0] > t - MINUTOS_DIA]
        else:
            recentes = [e for e in produto.lentas if e[1] == rota and e[0] > t - 60]
        funcoes = sorted({e[2] for e in recentes if e[2] is not None})
        if not recentes:
            return
        ultima = repo.db.execute("SELECT t, versao, tipo FROM implantacoes ORDER BY id DESC LIMIT 1").fetchone()
        comp = codigo.COMPONENTE_FUNCAO[funcoes[0]] if funcoes else ROTA_COMPONENTE.get(rota, "infra")
        projeto = COMPONENTE_PROJETO.get(comp, "PLAT")
        if projeto == "INFRA":
            projeto = "PLAT"
        if al["tipo"] == "erros" and ultima is not None and t - ultima[0] < 36 * 60 and ultima[2] != "reversão":
            antes = [e for e in produto.erros if e[1] == rota and ultima[0] - 600 < e[0] < ultima[0] and e[2] in funcoes]
            req30, err30 = produto.erros_na_janela(rota, 30)
            if funcoes and not antes and repo.anterior != repo.no_ar and err30 >= 0.25 * max(1, req30) and ultima[2] == "regular":
                self.reverter = repo.anterior
                p.suspensa = None
                p.tarefa = {"tipo": "reverter", "resta": p.s.randint(8, 18), "urgente": True}
        titulo = {"erros": f"erros em {rota} no ar", "lentidão": f"{rota} lento no ar", "fila": "fila de trabalhos crescendo",
                  "memória": "processo caindo por falta de memória"}[al["tipo"]]
        aberto = fluxo.db.execute("SELECT id FROM itens WHERE tipo='bug' AND componente=? AND estado NOT IN ('liberado', 'não reproduzido') "
                                  "AND origem='monitoramento' ORDER BY id DESC LIMIT 1", (comp,)).fetchone()
        if aberto is None:
            bug = fluxo.criar(t, projeto, "bug", titulo, prioridade="crítica" if al["tipo"] in ("erros", "memória") else "alta",
                              componente=comp, equipe="desenvolvimento", ator="operação", origem="monitoramento")
            fluxo.comentar(t, bug, "operação", "rastro aponta " + (", ".join(funcoes) if funcoes else "nada no código"))

    def _fim_reverter(self, p, tar, t, cal):
        repo = self.sis["repo"]
        versao = self.reverter
        self.reverter = None
        if versao is None:
            return
        self.sis["produto"].implantar(t, repo.versoes[versao], versao)
        antes = repo.versoes[repo.no_ar]
        repo.registrar_implantacao(t, versao, "reversão", "operação")
        self.sis["verdade"].implantacao(t, versao, "reversão", antes, repo.versoes[versao], [], self.sis["produto"])
        self.sis["eventos"].append((t, f"versão anterior {versao} restaurada"))

    def _fim_liberar(self, p, tar, t, cal):
        repo = self.sis["repo"]
        fluxo = self.sis["fluxo"]
        if repo.pendentes_implantacao[1] == 0:
            return
        antes = repo.versoes[repo.no_ar]
        versao = repo.gerar_versao(t, repo.principal, "regular")
        self.sis["produto"].implantar(t, repo.principal, versao)
        repo.registrar_implantacao(t, versao, "regular", "operação")
        itens = fluxo.itens(estados=("pronto para liberar",), tipo=("história", "tarefa", "bug"))
        funcs = []
        for r in itens:
            fluxo.transitar(t, r["id"], "liberado", "operação")
            fluxo.vincular_versao(t, r["id"], versao)
            if r["id"] in self.func_historia:
                funcs.append(self.func_historia[r["id"]])
            if r["epico"] is not None:
                restantes = fluxo.db.execute("SELECT COUNT(*) FROM itens WHERE epico=? AND estado NOT IN ('liberado')", (r["epico"],)).fetchone()[0]
                if restantes == 0:
                    fluxo.transitar(t, r["epico"], "concluído", "operação")
                    for c in self.compromissos:
                        if c["epico"] == r["epico"]:
                            c["entregue"] = t
            for o in fluxo.ligados(r["id"], "causado por"):
                oi = fluxo.item(o)
                if oi is not None and oi["estado"] in ("em desenvolvimento", "em andamento"):
                    fluxo.transitar(t, o, "liberado", "operação")
        self.compromissos = [c for c in self.compromissos if "entregue" not in c]
        self.sis["verdade"].implantacao(t, versao, "regular", antes, repo.principal, funcs, self.sis["produto"])
        self.sis["eventos"].append((t, f"liberação da versão {versao} com {len(itens)} itens"))

    def _fim_corrigir_no_ar(self, p, tar, t, cal):
        repo = self.sis["repo"]
        fluxo = self.sis["fluxo"]
        antes = repo.versoes[repo.no_ar]
        cod = dict(antes)
        hf = getattr(self, "hotfix_funcoes", {})
        for b in tar["bugs"]:
            cod.update(hf.pop(b, {}))
        if cod == antes:
            for b in tar["bugs"]:
                r = fluxo.item(b)
                if r is not None and r["estado"] == "pronto para liberar":
                    pass
            return
        versao = repo.gerar_versao(t, cod, "correção")
        self.sis["produto"].implantar(t, cod, versao)
        repo.registrar_implantacao(t, versao, "correção", "operação")
        for b in tar["bugs"]:
            r = fluxo.item(b)
            if r is not None and r["estado"] == "pronto para liberar":
                fluxo.transitar(t, b, "liberado", "operação")
                fluxo.vincular_versao(t, b, versao)
                for o in fluxo.ligados(b, "causado por"):
                    oi = fluxo.item(o)
                    if oi is not None and oi["estado"] in ("em desenvolvimento", "em andamento"):
                        fluxo.transitar(t, o, "liberado", "operação")
        self.sis["verdade"].implantacao(t, versao, "correção", antes, cod, [], self.sis["produto"])
        self.sis["eventos"].append((t, f"correção no ar: versão {versao}"))


VALOR_PLANO = {"básico": 290.0 * 12, "pro": 790.0 * 12, "empresarial": 2490.0 * 12}
