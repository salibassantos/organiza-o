"""A empresa sintética: uma organização de 50 pessoas, com produto, desenvolvimento, qualidade, atendimento (CS), vendas, operação
e o dono, um software próprio no ar, um sistema de fluxo de trabalho (chamados e itens passam por produto, desenvolvimento,
revisão, qualidade, liberação; chamados de cliente passam por atendimento e escalam para desenvolvimento), uma agenda de reuniões e
uma carteira de clientes. O relógio é um instante por minuto. Ninguém é observado como pessoa: o que sai daqui são os fluxos
agregados de cada processo, que viram itens das partes do tecido (ver organismo.py).

O que a empresa tem de verdade (para o núcleo achar sozinho, sem ninguém dizer):
- ciclos: o dia útil (8h às 18h), a semana (segunda com mais chamados; sexta com menos desenvolvimento), o mês (vendas no fim);
- contingências: uma liberação (deploy) às terças e quintas à tarde; uma em cada quatro traz erro: os erros do produto sobem,
  20 a 60 minutos depois os chamados sobem, as escalações sobem, o desenvolvimento larga o que faz e corrige, e os erros caem;
- uma deriva lenta: a carteira de clientes cresce 1% por semana, e com ela os chamados;
- uma mudança de regime no dia 20: uma versão nova do produto muda o normal da latência;
- uma queda (dia 12, 14h, 50 minutos): o produto cai, as requisições somem, os erros explodem, os chamados inundam;
- ausências: férias e faltas mudam quantas pessoas estão presentes, e com isso o ritmo de tudo.
Tudo acima é sorteado com a semente dada: a mesma semente, a mesma empresa."""
import math
import numpy as np

MIN_DIA = 1440
EQUIPES = {"produto": 5, "desenvolvimento": 15, "qualidade": 6, "atendimento": 8, "vendas": 8, "operacao": 4, "administrativo": 3, "dono": 1}   # 50 pessoas


class Empresa:
    def __init__(self, semente=1, clientes=400):
        self.g = np.random.default_rng(semente); self.clientes = float(clientes); self.t = -1
        self.backlog = 40; self.em_dev = 12; self.em_revisao = 4; self.em_qa = 6; self.liberados_dia = 0
        self.chamados_abertos = 6; self.escalados = 1; self.resposta_min = 25.0
        self.erros_base = 0.4; self.latencia_base = 180.0; self.erro_extra = 0.0; self.queda = 0; self.versao_nova = False
        self.propostas = 14; self.leads_dia = 0; self.fechados_dia = 0; self.cancel_dia = 0; self.novos_dia = 0
        self.ausentes = 3; self.horas_extras = 0.0; self.reunioes = 0; self.pessoas_reuniao = 0; self.bugs_reabertos = 2
        self.deploy_em = None; self.corrigindo = 0; self.eventos = []

    # ---------- o relógio da empresa ----------
    def dia(self): return self.t // MIN_DIA
    def minuto(self): return self.t % MIN_DIA
    def hora(self): return self.minuto() / 60.0
    def dia_semana(self): return self.dia() % 7            # 0 = segunda
    def util(self): return self.dia_semana() < 5
    def expediente(self): return self.util() and 8.0 <= self.hora() < 18.0
    def ritmo(self):
        """O ritmo humano do dia: quase zero de madrugada, cheio no expediente, meio no almoço."""
        if not self.util(): return 0.08
        h = self.hora()
        if h < 7 or h >= 19: return 0.05
        if 12 <= h < 13: return 0.5
        return 1.0 if 8 <= h < 18 else 0.3

    # ---------- um minuto ----------
    def passo(self):
        self.t += 1; g = self.g; r = self.ritmo(); d = self.dia(); m = self.minuto(); ds = self.dia_semana()
        if m == 0:                                                               # um dia novo
            self.liberados_dia = 0; self.leads_dia = 0; self.fechados_dia = 0; self.cancel_dia = 0; self.novos_dia = 0; self.horas_extras = 0.0
            self.ausentes = int(g.binomial(50, 0.06)) + (2 if d % 30 in (10, 11, 12) else 0)
            self.clientes *= (1 + 0.01 / 7.0)                                    # a deriva lenta: a carteira cresce 1% por semana
            if d == 20: self.versao_nova = True; self.latencia_base = 240.0; self.eventos.append((self.t, "versão nova do produto no ar"))
        presentes = 50 - self.ausentes if self.util() else 2
        presenca = presentes / 50.0
        # --- o produto no ar ---
        carga = self.clientes * (0.25 + 1.75 * r) / 60.0                        # requisições por minuto
        if d == 12 and 14 * 60 <= m < 14 * 60 + 50:
            if self.queda == 0: self.eventos.append((self.t, "queda do produto"))
            self.queda = 1; requisicoes = g.poisson(carga * 0.05); erros = g.poisson(carga * 0.6); latencia = 2500 + g.normal(0, 200)
        else:
            self.queda = 0; requisicoes = g.poisson(carga); erros = g.poisson(self.erros_base * r + self.erro_extra * r); latencia = self.latencia_base * (1 + 0.3 * r) + g.normal(0, 15) + 2.0 * self.erro_extra
        cpu = min(100.0, 20 + 55 * requisicoes / max(self.clientes * 2.0 / 60.0, 1.0) + g.normal(0, 3))     # relativo à carga máxima que a carteira gera
        # --- liberações (deploy) às terças e quintas à tarde; uma em quatro traz erro ---
        if ds in (1, 3) and m == 15 * 60 and self.util() and presenca > 0.7:
            self.deploy_em = self.t; self.liberados_dia += 1
            if g.random() < 0.25: self.erro_extra = 6.0; self.corrigindo = 0; self.eventos.append((self.t, "liberação com erro"))
            else: self.eventos.append((self.t, "liberação"))
        if self.erro_extra > 0:
            self.corrigindo += 1
            if self.corrigindo > 90 + g.integers(0, 60): self.erro_extra = 0.0; self.eventos.append((self.t, "correção no ar"))  # o desenvolvimento corrige em hora e meia a duas horas e meia
        # --- chamados de atendimento ---
        base_ch = self.clientes / 400.0 * (0.9 if ds == 0 else 0.6) * r / 10.0  # por minuto no expediente
        inundacao = (2.5 if self.queda else 0.0) + (0.8 if self.erro_extra > 0 and self.t - (self.deploy_em or -10 ** 9) > 20 + g.integers(0, 40) else 0.0)
        novos = g.poisson(base_ch + inundacao); self.chamados_abertos += novos
        atendidos = min(self.chamados_abertos, g.poisson(0.12 * presenca * EQUIPES["atendimento"] * r)); self.chamados_abertos -= atendidos
        escalou = g.binomial(atendidos, 0.15 + (0.3 if self.erro_extra > 0 or self.queda else 0.0)); self.escalados += escalou
        self.escalados = max(0, self.escalados - g.poisson(0.05 * presenca * r))
        self.resposta_min = 0.98 * self.resposta_min + 0.02 * (15 + 2.5 * self.chamados_abertos + (40 if self.queda else 0))
        # --- o fluxo de desenvolvimento (produto -> desenvolvimento -> revisão -> qualidade -> liberado) ---
        if self.expediente():
            self.backlog += g.poisson(0.03 * presenca * EQUIPES["produto"] / 5.0 + 0.004 * novos)
            puxou = min(self.backlog, g.poisson(0.02 * presenca * (0.5 if self.erro_extra > 0 else 1.0) * (0.6 if ds == 4 else 1.0))); self.backlog -= puxou; self.em_dev += puxou
            revisou = min(self.em_dev, g.poisson(0.02 * presenca)); self.em_dev -= revisou; self.em_revisao += revisou
            testou = min(self.em_revisao, g.poisson(0.025 * presenca)); self.em_revisao -= testou; self.em_qa += testou
            testes = g.poisson(0.3 * presenca * EQUIPES["qualidade"] / 6.0); falhas = g.binomial(testes, 0.12 + (0.2 if self.erro_extra > 0 else 0.0))
            liberou = min(self.em_qa, g.poisson(0.02 * presenca)); self.em_qa -= liberou
            self.bugs_reabertos = max(0, self.bugs_reabertos + g.binomial(falhas, 0.3) - g.poisson(0.01))
        else: testes = 0; falhas = 0
        # --- vendas (mais no fim do mês) ---
        fim_mes = 1.8 if d % 30 >= 24 else 1.0
        leads = g.poisson(0.04 * r * presenca * fim_mes); self.leads_dia += leads; self.propostas += g.binomial(leads, 0.5)
        fechou = min(self.propostas, g.poisson(0.006 * r * presenca * fim_mes)); self.propostas -= fechou; self.fechados_dia += fechou; self.novos_dia += fechou; self.clientes += fechou
        if self.expediente() and g.random() < 0.0015 * (3 if self.queda else 1): self.cancel_dia += 1; self.clientes -= 1
        # --- a agenda ---
        if self.util() and (9 * 60 <= m < 9 * 60 + 15): self.reunioes = 6; self.pessoas_reuniao = presentes - 4                       # as reuniões diárias de cada equipe
        elif self.util() and ds == 0 and 14 * 60 <= m < 15 * 60 + 30: self.reunioes = 1; self.pessoas_reuniao = 12                   # planejamento da semana
        elif self.util() and d % 30 == 1 and 10 * 60 <= m < 11 * 60 + 30: self.reunioes = 1; self.pessoas_reuniao = 50 - self.ausentes   # a reunião mensal com o dono
        elif self.expediente(): self.reunioes = int(g.random() < 0.3) + int(g.random() < 0.15); self.pessoas_reuniao = self.reunioes * int(g.integers(2, 6))
        else: self.reunioes = 0; self.pessoas_reuniao = 0
        if self.util() and 18 <= self.hora() < 20 and (self.erro_extra > 0 or self.queda): self.horas_extras += 0.1 * presentes
        return {
            "atendimento": [float(novos), float(self.chamados_abertos), float(self.escalados), float(self.resposta_min)],
            "desenvolvimento": [float(self.backlog), float(self.em_dev), float(self.em_revisao), float(self.em_qa)],
            "qualidade": [float(testes), float(falhas), float(self.bugs_reabertos)],
            "produto no ar": [float(requisicoes), float(erros), float(latencia), float(cpu)],
            "vendas": [float(leads), float(self.propostas), float(fechou)],
            "agenda": [float(self.reunioes), float(self.pessoas_reuniao)],
            "pessoas": [float(presentes), float(self.ausentes), float(self.horas_extras)],
            "clientes": [float(self.clientes), float(self.cancel_dia), float(self.novos_dia)],
        }


PARTES = {1: ("atendimento", ["chamados novos por minuto", "chamados abertos", "chamados escalados", "tempo de primeira resposta em minutos"]),
          2: ("desenvolvimento", ["itens no backlog", "itens em desenvolvimento", "itens em revisão", "itens em qualidade"]),
          3: ("qualidade", ["testes por minuto", "testes que falharam por minuto", "bugs reabertos"]),
          4: ("produto no ar", ["requisições por minuto", "erros por minuto", "latência média em milissegundos", "uso de processador"]),
          5: ("vendas", ["leads por minuto", "propostas abertas", "fechamentos por minuto"]),
          6: ("agenda", ["reuniões em curso", "pessoas em reunião"]),
          7: ("pessoas", ["presentes no quadro do dia", "ausentes do dia", "horas extras do dia"]),
          8: ("clientes", ["clientes ativos", "cancelamentos do dia", "clientes novos do dia"])}
