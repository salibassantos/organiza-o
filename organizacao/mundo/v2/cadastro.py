"""O cadastro da empresa: as equipes e os papéis das 50 pessoas, os projetos do fluxo de trabalho, os componentes e as rotas do
produto, as regiões dos clientes. É o que não muda enquanto o mundo anda. Também mora aqui a derivação das sementes: cada parte do
mundo tem a sua sequência de sorteios, tirada da semente da empresa e do nome da parte, para que a mesma semente repita a mesma vida
e para que uma mudança num canto não desloque os sorteios de outro."""
import hashlib
import random

import numpy as np


def semente_de(semente, *nomes):
    """Um inteiro de 63 bits derivado da semente e de nomes; igual em qualquer processo e em qualquer máquina."""
    h = hashlib.blake2b(("|".join([str(semente)] + [str(n) for n in nomes])).encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(h, "big") >> 1


def sorteio(semente, *nomes):
    return random.Random(semente_de(semente, *nomes))


def gerador(semente, *nomes):
    return np.random.default_rng(semente_de(semente, *nomes))


# ---------- as equipes ----------
# O dono e o administrativo formam a equipe "gestão": nenhum agregado sai de uma pessoa só.
EQUIPES = ("produto", "desenvolvimento", "qualidade", "atendimento", "vendas", "operação", "gestão")

# (equipe, papel, quantidade, projeto ou frente de trabalho)
COMPOSICAO = (
    ("produto", "líder de produto", 1, None),
    ("produto", "gerente de produto", 1, "PROD"),
    ("produto", "gerente de produto", 1, "PLAT"),
    ("produto", "designer", 1, "PROD"),
    ("produto", "analista de produto", 1, "PROD"),
    ("desenvolvimento", "líder técnico", 1, "PROD"),
    ("desenvolvimento", "desenvolvedor", 8, "PROD"),
    ("desenvolvimento", "líder técnico", 1, "PLAT"),
    ("desenvolvimento", "desenvolvedor", 5, "PLAT"),
    ("qualidade", "analista de qualidade", 4, "PROD"),
    ("qualidade", "analista de qualidade", 2, "PLAT"),
    ("atendimento", "coordenador de atendimento", 1, "SUP"),
    ("atendimento", "analista de atendimento", 7, "SUP"),
    ("vendas", "gerente de vendas", 1, None),
    ("vendas", "pré-vendas", 2, None),
    ("vendas", "executivo de vendas", 5, None),
    ("operação", "engenheiro de operação", 4, "INFRA"),
    ("gestão", "financeiro", 1, None),
    ("gestão", "pessoas", 1, None),
    ("gestão", "administrativo", 1, None),
    ("gestão", "dono", 1, None),
)

# ---------- o fluxo de trabalho ----------
PROJETOS = {"PROD": "Produto", "PLAT": "Plataforma", "SUP": "Suporte", "INFRA": "Infraestrutura"}

# ---------- o produto ----------
ROTAS = ("login", "catalogo", "busca", "produto", "carrinho", "frete", "pedido", "pagamento", "relatorio", "exportacao", "notas", "conta")
NOME_ROTA = {"login": "login", "catalogo": "catálogo", "busca": "busca", "produto": "produto", "carrinho": "carrinho",
             "frete": "frete", "pedido": "pedido", "pagamento": "pagamento", "relatorio": "relatório", "exportacao": "exportação",
             "notas": "notas fiscais", "conta": "conta"}
COMPONENTES = ("login", "catalogo", "pedido", "frete", "pagamento", "fiscal", "relatorio", "notificacao", "infra")
NOME_COMPONENTE = {"login": "login e conta", "catalogo": "catálogo e busca", "pedido": "pedido e carrinho", "frete": "frete",
                   "pagamento": "pagamento", "fiscal": "fiscal", "relatorio": "relatórios", "notificacao": "notificações",
                   "infra": "infraestrutura"}
ROTA_COMPONENTE = {"login": "login", "conta": "login", "catalogo": "catalogo", "busca": "catalogo", "produto": "catalogo",
                   "carrinho": "pedido", "pedido": "pedido", "frete": "frete", "pagamento": "pagamento", "notas": "fiscal",
                   "relatorio": "relatorio", "exportacao": "relatorio"}
# qual squad cuida de cada componente
COMPONENTE_PROJETO = {"login": "PLAT", "catalogo": "PROD", "pedido": "PROD", "frete": "PROD", "pagamento": "PROD",
                      "fiscal": "PLAT", "relatorio": "PROD", "notificacao": "PLAT", "infra": "INFRA"}

# ---------- os clientes ----------
PLANOS = ("básico", "pro", "empresarial")
# o primeiro dígito do CEP diz a região
REGIOES = ("São Paulo", "Rio de Janeiro e Espírito Santo", "Minas Gerais", "Norte e Nordeste", "Centro-Oeste", "Sul")
DIGITO_REGIAO = {"0": 0, "1": 0, "2": 1, "3": 2, "4": 3, "5": 3, "6": 3, "7": 4, "8": 5, "9": 5}
# unidades da federação por primeiro dígito do CEP (para a nota fiscal)
UF_POR_DIGITO = {"0": ("SP",), "1": ("SP",), "2": ("RJ", "ES"), "3": ("MG",), "4": ("BA", "SE"), "5": ("PE", "AL", "PB", "RN"),
                 "6": ("CE", "PI", "MA", "PA", "AM", "AP", "RR", "AC"), "7": ("DF", "GO", "TO", "MT", "MS", "RO"),
                 "8": ("PR", "SC"), "9": ("RS",)}

MINUTOS_DIA = 1440
