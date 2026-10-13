"""As equipes como agentes diante de quem observa a empresa (v2). Cada equipe tem uma fila de atos que chegaram pela porta, uma
capacidade (as pessoas presentes e livres), cansaço, atenção gasta e memória de quem lhe pede. Isto é física do mundo, escrita
como regra, e tudo é determinístico pela semente e pelos atos recebidos.

- Cada equipe tem a sua demora própria e estável para responder (pergunta, convocação) e para tratar (pedido), sorteada uma vez da
  semente: é o jeito daquela equipe.
- Um ato só fica disponível para alguém da equipe pegar depois dessa demora, esticada pela ocupação (fila e gente ocupada), pelo
  cansaço e pela atenção que a porta já gastou, e encurtada pela confiança em quem pede.
- A pergunta gasta atenção. O pedido entra na frente da fila: a pessoa que o pega larga o que fazia, e o que ela fazia atrasa.
- Pedido que resolveu algo aumenta a confiança em quem pede; pedido que não resolveu nada a diminui. A confiança também mexe no
  cuidado do tratamento: com pouca confiança a equipe verifica por cima.
- O cansaço sobe com hora extra e com trabalho da porta, e desce com o descanso (noite, fim de semana)."""
from .cadastro import EQUIPES, sorteio

# minutos típicos até alguém da equipe pegar o ato: (responder, tratar)
DEMORA_BASE = {"produto": (55, 120), "desenvolvimento": (70, 90), "qualidade": (45, 70), "atendimento": (12, 25),
               "vendas": (30, 60), "operação": (18, 25), "gestão": (120, 200)}
CONFIANCA_MIN, CONFIANCA_MAX = 0.4, 1.6


class Equipe:
    def __init__(self, nome, semente):
        s = sorteio(semente, "equipe", nome)
        r, p = DEMORA_BASE[nome]
        self.nome = nome
        self.demora_resposta = round(r * s.uniform(0.8, 1.25), 1)
        self.demora_tratamento = round(p * s.uniform(0.8, 1.25), 1)
        self.cansaco = 0.0
        self.atencao = 0.0
        self.confianca = 1.0
        self.ocupacao = 0.0
        self.historico = []                 # (t, tipo, útil) dos últimos atos tratados (no máximo 30)

    def atraso(self, tipo):
        base = self.demora_tratamento if tipo == "pedido" else self.demora_resposta
        return base * (1.0 + 1.5 * self.ocupacao) * (1.0 + 0.8 * self.cansaco) * (1.0 + 0.6 * self.atencao) / self.confianca

    def fator_duracao(self):
        """Uma equipe cansada demora mais em cada coisa que faz para a porta."""
        return 1.0 + 0.5 * self.cansaco

    def cobertura(self):
        """Quanto da verificação a equipe faz num pedido: inteira com confiança, por cima sem ela."""
        return min(1.0, 0.5 + 0.5 * self.confianca)

    def tratado(self, t, tipo, util):
        antes = self.confianca
        if tipo == "pedido" and util is not None:
            self.confianca = min(CONFIANCA_MAX, self.confianca + 0.15) if util else max(CONFIANCA_MIN, self.confianca - 0.2)
        self.atencao += 0.25 if tipo == "pergunta" else (0.5 if tipo == "pedido" else 0.35)
        self.historico.append((t, tipo, util))
        del self.historico[:-30]
        return antes, self.confianca

    def minuto(self, trabalhando, alem_da_hora, presentes, em_reuniao_ou_urgente, fila_regular, membros):
        """Atualiza cansaço, atenção e ocupação a cada minuto."""
        if alem_da_hora:
            self.cansaco += 0.0012 * alem_da_hora / max(1, membros)
        if trabalhando == 0:
            self.cansaco *= 0.9985                       # descanso: meia-vida de umas oito horas
        else:
            self.cansaco *= 0.99995
        self.cansaco = min(self.cansaco, 3.0)
        self.atencao *= 0.995                            # a atenção gasta volta em umas duas horas
        livres = max(0, presentes - em_reuniao_ou_urgente)
        self.ocupacao = min(2.0, (1.0 - livres / presentes if presentes else 1.0) + fila_regular / (4.0 * max(1, membros)))

    def memoria_do_dia(self):
        """A memória de quem pede se apaga devagar: a confiança volta um pouco para o meio a cada dia vivido."""
        self.confianca += 0.05 * (1.0 - self.confianca)

    def estado(self):
        return {"demora_resposta": self.demora_resposta, "demora_tratamento": self.demora_tratamento, "cansaco": round(self.cansaco, 4),
                "atencao": round(self.atencao, 4), "confianca": round(self.confianca, 4), "ocupacao": round(self.ocupacao, 4)}


def criar_equipes(semente):
    return {e: Equipe(e, semente) for e in EQUIPES}
