"""O relógio do mundo. Um instante por minuto: t = 0 é a criação da empresa (segunda-feira, 1º de junho de 2026, meia-noite); cada
passo do mundo avança t e faz acontecer o minuto t. O relógio nunca anda sozinho: só avança quando o mundo dá o passo.

Há dois tempos. O tempo real (t) é o do relógio da porta: dia(), minuto_do_dia(), dia_da_semana(). O calendário é o tempo que os
processos da empresa vivem: a hora em que as pessoas chegam, o dia da semana em que se libera versão, o fim do mês das vendas, a hora
das tarefas agendadas do servidor. Na empresa normal os dois coincidem. No nulo "embaralhado" o calendário é sorteado em blocos de
duração variável: cada bloco recebe uma hora, um dia da semana e um dia do mês sorteados, e dentro do bloco o calendário corre minuto a
minuto; as durações e os atrasos de causa e efeito continuam no minuto real. Assim some todo ciclo de hora, de dia e de mês, e o resto
da empresa fica igual."""
import datetime
import time

from .cadastro import sorteio, MINUTOS_DIA

INICIO = datetime.date(2026, 6, 1)       # uma segunda-feira
DIAS_REFERENCIA = 364                    # o ano de onde o calendário embaralhado sorteia as suas datas


class Calendario:
    """O que a folhinha e o relógio de parede dizem a quem trabalha na empresa naquele minuto."""
    __slots__ = ("absoluto", "data", "minuto", "dia_semana", "dia_mes", "dias_no_mes", "mes", "util", "sprint", "dia_sprint", "feriado")

    def ajustar(self, absoluto):
        self.absoluto = absoluto
        data = absoluto // MINUTOS_DIA
        self.minuto = absoluto % MINUTOS_DIA
        if getattr(self, "data", None) != data:
            self.data = data
            d = INICIO + datetime.timedelta(days=data)
            self.dia_semana = data % 7
            self.dia_mes = d.day
            prox = (d.replace(day=28) + datetime.timedelta(days=4))
            self.dias_no_mes = (prox - datetime.timedelta(days=prox.day)).day
            self.mes = (d.year - INICIO.year) * 12 + d.month - INICIO.month
            self.util = self.dia_semana < 5
            self.sprint = data // 14             # os sprints de duas semanas começam às segundas-feiras
            self.dia_sprint = data % 14
            return True
        return False

    def hora(self):
        return self.minuto / 60.0

    def fim_do_mes(self):
        return self.dia_mes > self.dias_no_mes - 6

    def texto(self):
        return f"dia {self.data}, {self.minuto // 60:02d}h{self.minuto % 60:02d}"


class Relogio:
    def __init__(self, semente, embaralhado=False, tempo_real=False):
        self.t = 0
        self.embaralhado = embaralhado
        self.tempo_real = tempo_real
        self.sorte = sorteio(semente, "calendario embaralhado")
        self.cal = Calendario()
        self.cal.ajustar(0)
        self.cal.data = None                  # o primeiro passo entra no dia 0 como numa data nova
        self.bloco = None                     # (início real, fim real, início no calendário)
        self.blocos = []                      # para a verdade: os blocos sorteados
        self._parede = None

    # ---------- o relógio da porta ----------
    def dia(self):
        return self.t // MINUTOS_DIA

    def minuto_do_dia(self):
        return self.t % MINUTOS_DIA

    def dia_da_semana(self):
        return self.dia() % 7

    # ---------- (v2.3) a agenda calada: o feriado coletivo, nas datas do relógio da porta ----------
    def _avancar_com_feriado(self):
        feriados, self.feriados = self.feriados, None
        try:
            self.t -= 1
            novo = self.avancar()
        finally:
            self.feriados = feriados
        cal = self.cal
        cal.feriado = (self.t // MINUTOS_DIA) in feriados
        cal.util = cal.dia_semana < 5 and not cal.feriado
        return novo

    # ---------- um minuto ----------
    def avancar(self):
        """Avança o relógio um minuto e devolve True quando o calendário entra numa data nova."""
        self.t += 1
        if getattr(self, "feriados", None):
            return self._avancar_com_feriado()
        if not self.embaralhado:
            return self.cal.ajustar(self.t)
        if self.bloco is None or self.t >= self.bloco[1]:
            duracao = self.sorte.randint(25, 240)
            inicio_cal = self.sorte.randrange(0, DIAS_REFERENCIA * MINUTOS_DIA)
            self.bloco = (self.t, self.t + duracao, inicio_cal)
            d = inicio_cal // MINUTOS_DIA
            data = INICIO + datetime.timedelta(days=d)
            m = inicio_cal % MINUTOS_DIA
            self.blocos.append({"inicio": self.t, "fim": self.t + duracao, "hora": f"{m // 60:02d}:{m % 60:02d}",
                                "dia_da_semana": d % 7, "dia_do_mes": data.day})
        return self.cal.ajustar(self.bloco[2] + (self.t - self.bloco[0]))

    def esperar(self):
        """No tempo real, o passo só termina quando o minuto de parede correspondente chega. Em simulação não dorme."""
        if not self.tempo_real:
            return
        agora = time.monotonic()
        if self._parede is None:
            self._parede = agora - 60.0 * self.t
        alvo = self._parede + 60.0 * self.t
        if alvo > agora:
            time.sleep(alvo - agora)

    def __getstate__(self):
        d = dict(self.__dict__)
        d["_parede"] = None
        return d
