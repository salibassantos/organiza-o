"""O código do produto. As rotas chamam funções; cada função tem uma ou mais implementações escritas aqui, as que já existiram e as
que ainda vão existir. Uma versão do produto é a escolha de uma implementação para cada função; um commit troca a implementação de
uma função; liberar é pôr outra escolha no servidor.

Algumas implementações têm defeito, e o defeito é código errado de verdade: uma conversão de texto que quebra com acento, um índice
que passa do fim da lista, uma verificação que saiu numa refatoração, uma consulta que traz a tabela inteira. Quando a rota roda com
essa implementação, a exceção acontece (ou a gravação dobra, ou a consulta pesa), e é isso que as métricas medem. Nada aqui sorteia
erro. Outras implementações são funcionalidades novas: fazem mais (ou menos) trabalho e mudam o normal da rota.

Os testes da qualidade também moram aqui: chamam as rotas num ambiente de ensaio e conferem o resultado."""
import re
import unicodedata

from .cadastro import DIGITO_REGIAO


class Recusa(Exception):
    """O pedido do usuário não pode ser atendido pela regra do negócio (sem estoque, cartão recusado, já pago). Não é erro do código."""


LIMITE_LINHAS_PROCESSO = 40000      # o processo da aplicação não aguenta montar uma lista maior que isso numa requisição
TABELA_FRETE = {"0": (1, 18.0), "1": (1, 19.0), "2": (2, 22.0), "3": (1, 16.0), "4": (4, 31.0), "5": (5, 34.0), "6": (6, 39.0),
                "7": (4, 29.0), "8": (3, 24.0), "9": (3, 26.0)}
ALIQUOTA_UF = {"SP": 0.18, "RJ": 0.20, "ES": 0.17, "MG": 0.18, "PR": 0.195, "SC": 0.17, "RS": 0.17, "BA": 0.205, "SE": 0.19,
               "PE": 0.205, "AL": 0.19, "PB": 0.20, "RN": 0.20, "CE": 0.20, "PI": 0.21, "MA": 0.22, "PA": 0.19, "AM": 0.20,
               "AP": 0.18, "RR": 0.20, "AC": 0.19, "DF": 0.20, "GO": 0.19, "TO": 0.20, "MT": 0.17, "MS": 0.17, "RO": 0.195}
# a tabela que entrou numa refatoração do cálculo de imposto: só as unidades do Sul e do Sudeste
ALIQUOTA_SUL_SUDESTE = {uf: ALIQUOTA_UF[uf] for uf in ("SP", "RJ", "ES", "MG", "PR", "SC", "RS")}


def _sem_acento(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


# ======================================================================================================== login e conta
def normalizar_login__correta(login):
    return unicodedata.normalize("NFC", login).strip().lower()


def normalizar_login__ascii(login):
    return login.strip().encode("ascii").decode("ascii").lower()


def verificar_senha__simples(x, usuario):
    x.trabalho(4)


def verificar_senha__reforcada(x, usuario):
    x.trabalho(320)                                      # muito mais rodadas na derivação da senha


def registrar_dispositivo__nada(x, usuario):
    return None


def registrar_dispositivo__grava(x, usuario):
    n = x.db.um("SELECT COUNT(*) FROM dispositivos WHERE usuario=?", (usuario,))[0]
    if not x.simulacao:
        x.db.exe("INSERT INTO dispositivos (usuario, t) VALUES (?,?)", (usuario, x.t))
    x.trabalho(160 + n // 4)                             # calcula a impressão do dispositivo e compara com as anteriores


def guardar_sessao__com_expiracao(cache, token, usuario, t):
    cache[token] = (usuario, t)
    while cache:
        primeiro = next(iter(cache))
        if cache[primeiro][1] >= t - 120:
            break
        del cache[primeiro]


def guardar_sessao__sem_expiracao(cache, token, usuario, t):
    cache[token] = (usuario, t)


def atualizar_conta__correta(x, cliente, dados):
    telefone = (dados.get("telefone") or "").strip()
    nome = (dados.get("nome_fantasia") or "").strip()
    if not x.simulacao:
        x.db.exe("UPDATE clientes SET telefone=?, nome_fantasia=? WHERE id=?", (telefone or None, nome or None, cliente))


def atualizar_conta__telefone(x, cliente, dados):
    telefone = dados["telefone"].strip().replace(" ", "")        # supõe que todo cliente tem telefone
    nome = (dados.get("nome_fantasia") or "").strip()
    if not x.simulacao:
        x.db.exe("UPDATE clientes SET telefone=?, nome_fantasia=? WHERE id=?", (telefone, nome or None, cliente))


# ======================================================================================================== catálogo e busca
def listar_produtos__pagina_20(x, categoria):
    return x.db.todos("SELECT id, nome, preco, estoque FROM produtos WHERE categoria=? ORDER BY nome", (categoria,)), 20


def listar_produtos__pagina_40(x, categoria):
    linhas = x.db.todos("SELECT id, nome, preco, estoque, peso, vendidos FROM produtos WHERE categoria=? ORDER BY nome", (categoria,))
    x.trabalho(len(linhas) // 3)
    return linhas, 40


def paginar__correta(linhas, pagina, tamanho):
    inicio = (pagina - 1) * tamanho
    return linhas[inicio:inicio + tamanho], pagina * tamanho < len(linhas)


def paginar__ultima_pagina(linhas, pagina, tamanho):
    inicio = (pagina - 1) * tamanho
    fatia = linhas[inicio:inicio + tamanho]
    cursor = linhas[pagina * tamanho - 1][0]               # o cursor da próxima página; não existe na última página incompleta
    return fatia, cursor < linhas[-1][0] or pagina * tamanho < len(linhas)


def recomendar__nenhuma(x, cliente):
    return []


def recomendar__historico(x, cliente):
    linhas = x.db.todos("SELECT i.produto, SUM(i.quantidade) AS q FROM pedidos p JOIN itens_pedido i ON i.pedido = p.id "
                        "WHERE p.cliente=? AND p.t>? GROUP BY i.produto ORDER BY q DESC LIMIT 8", (cliente, x.t - 30 * 1440))
    x.trabalho(60)
    return linhas


def recomendar__historico_curto(x, cliente):
    linhas = x.db.todos("SELECT i.produto, SUM(i.quantidade) AS q FROM pedidos p JOIN itens_pedido i ON i.pedido = p.id "
                        "WHERE p.cliente=? AND p.t>? GROUP BY i.produto ORDER BY q DESC LIMIT 4", (cliente, x.t - 7 * 1440))
    x.trabalho(15)
    return linhas


def normalizar_termo__correta(termo):
    return _sem_acento(termo.lower()).strip()


def normalizar_termo__ascii(termo):
    return termo.lower().encode("ascii").decode("ascii").strip()


def buscar_produtos__varredura(x, termo):
    achados = x.db.todos("SELECT id, nome, preco FROM produtos WHERE nome_busca LIKE ? LIMIT 30", ("%" + termo + "%",))
    x.trabalho(140)                                      # ordena por semelhança comparando o termo com o catálogo inteiro
    return achados


def buscar_produtos__indice(x, termo):
    palavra = termo.split()[0]
    achados = x.db.todos("SELECT p.id, p.nome, p.preco FROM palavras w JOIN produtos p ON p.id = w.produto "
                         "WHERE w.palavra >= ? AND w.palavra < ? LIMIT 30", (palavra, palavra + "\uffff"))
    x.trabalho(10)
    return achados


def buscar_produtos__sinonimos(x, termo):
    achados = x.db.todos("SELECT id, nome, preco FROM produtos WHERE nome_busca LIKE ? LIMIT 30", ("%" + termo + "%",))
    for sinonimo in SINONIMOS.get(termo.split()[0], ()):
        achados += x.db.todos("SELECT id, nome, preco FROM produtos WHERE nome_busca LIKE ? LIMIT 10", ("%" + sinonimo + "%",))
    x.trabalho(25)
    return achados


SINONIMOS = {"refrigerante": ("guarana", "cola"), "biscoito": ("bolacha",), "bolacha": ("biscoito",), "sabao": ("detergente",),
             "detergente": ("sabao",), "papel": ("guardanapo",), "cafe": ("capsula",), "arroz": ("graos",)}


def detalhar_produto__simples(x, produto):
    p = x.db.um("SELECT id, nome, preco, estoque, categoria FROM produtos WHERE id=?", (produto,))
    if p is None:
        raise Recusa("produto inexistente")
    return p


def detalhar_produto__relacionados(x, produto):
    p = x.db.um("SELECT id, nome, preco, estoque, categoria FROM produtos WHERE id=?", (produto,))
    if p is None:
        raise Recusa("produto inexistente")
    rel = x.db.todos("SELECT id, nome, preco FROM produtos WHERE categoria=? AND id<>? ORDER BY vendidos DESC LIMIT 6", (p[4], produto))
    x.trabalho(30)
    return p, rel


# ======================================================================================================== pedido e carrinho
def ler_quantidade__correta(texto):
    q = int(texto)
    if q < 1 or q > 999:
        raise Recusa("quantidade fora do limite")
    return q


def ler_quantidade__um_digito(texto):
    return int(re.fullmatch(r"[1-9]", texto.strip()).group(0))   # a máscara nova só aceita um algarismo


def reservar_estoque__correta(x, itens):
    precos = []
    for produto, q in itens:
        p = x.db.um("SELECT preco, estoque FROM produtos WHERE id=?", (produto,))
        if p is None:
            raise Recusa("produto inexistente")
        if p[1] < q:
            raise Recusa("sem estoque")
        precos.append(p[0])
    if not x.simulacao:
        for produto, q in itens:
            x.db.exe("UPDATE produtos SET estoque = estoque - ?, vendidos = vendidos + ? WHERE id=?", (q, q, produto))
    return precos


def verificar_fraude__nada(x, cliente):
    return True


def verificar_fraude__antifraude(x, cliente):
    recentes = x.db.um("SELECT COUNT(*), COALESCE(SUM(valor), 0) FROM pedidos WHERE cliente=? AND t>?", (cliente, x.t - 1440))
    x.externo(x.produto.antifraude.consultar())
    x.trabalho(20)
    return recentes[0] < 200


# ======================================================================================================== frete
def calcular_frete__correta(cep):
    digitos = cep.replace("-", "").strip()
    if len(digitos) != 8 or not digitos.isdigit():
        raise Recusa("CEP inválido")
    return TABELA_FRETE[digitos[0]]


def calcular_frete__numerico(cep):
    numero = int(cep.replace("-", ""))
    texto = str(numero)
    if len(texto) != 8:                                     # o zero da frente some na conversão para número
        raise ValueError("CEP inválido: " + texto)
    return TABELA_FRETE[texto[0]]


def cotar_transportadoras__uma(x, regiao, peso):
    x.externo(x.produto.frete.cotar())
    return regiao[1] + 2.5 * peso


def cotar_transportadoras__duas(x, regiao, peso):
    a = x.produto.frete.cotar()
    b = x.produto.frete.cotar()
    x.externo(max(a, b) + 40.0)
    x.trabalho(10)
    return min(regiao[1] + 2.5 * peso, regiao[1] * 0.92 + 2.8 * peso)


# ======================================================================================================== pagamento
def autenticar_pagamento__direto(x):
    return True


def autenticar_pagamento__tres_ds(x):
    x.externo(x.produto.gateway.autenticar())
    x.trabalho(12)
    return True


def registrar_cobranca__correta(x, pedido, valor):
    if x.db.um("SELECT 1 FROM pagamentos WHERE pedido=? AND estado<>'recusado'", (pedido,)) is not None:
        raise Recusa("pedido já pago")
    return x.db.exe("INSERT INTO pagamentos (pedido, valor, estado, t) VALUES (?,?,?,?)", (pedido, valor, "pendente", x.t)).lastrowid


def registrar_cobranca__sem_verificacao(x, pedido, valor):
    return x.db.exe("INSERT INTO pagamentos (pedido, valor, estado, t) VALUES (?,?,?,?)", (pedido, valor, "pendente", x.t)).lastrowid


# ======================================================================================================== fiscal
def emitir_nota__correta(x, pedido):
    p = x.db.um("SELECT p.cliente, p.valor, c.uf FROM pedidos p JOIN clientes c ON c.id = p.cliente WHERE p.id=?", (pedido,))
    imposto = round(p[1] * ALIQUOTA_UF[p[2]], 2)
    x.db.exe("INSERT INTO notas (pedido, cliente, uf, valor, imposto, estado, t) VALUES (?,?,?,?,?,?,?)",
             (pedido, p[0], p[2], p[1], imposto, "emitida", x.t))


def emitir_nota__aliquota_regional(x, pedido):
    p = x.db.um("SELECT p.cliente, p.valor, c.uf FROM pedidos p JOIN clientes c ON c.id = p.cliente WHERE p.id=?", (pedido,))
    imposto = round(p[1] * ALIQUOTA_SUL_SUDESTE[p[2]], 2)
    x.db.exe("INSERT INTO notas (pedido, cliente, uf, valor, imposto, estado, t) VALUES (?,?,?,?,?,?,?)",
             (pedido, p[0], p[2], p[1], imposto, "emitida", x.t))


def listar_notas__todas(x, cliente):
    notas = x.db.todos("SELECT id, pedido, valor, imposto, estado, t FROM notas WHERE cliente=? ORDER BY t DESC", (cliente,))
    x.trabalho(len(notas) // 2)                          # monta a página com todas as notas do cliente
    return notas


def listar_notas__paginada(x, cliente):
    return x.db.todos("SELECT id, valor, imposto, t FROM notas WHERE cliente=? ORDER BY t DESC LIMIT 20", (cliente,))


# ======================================================================================================== relatórios
def montar_relatorio__filtrado(x, cliente, desde):
    linhas = x.db.todos("SELECT valor, itens, t FROM pedidos WHERE cliente=? AND t>=?", (cliente, desde))
    x.trabalho(5 + len(linhas) // 4)
    return sum(v for v, _, _ in linhas)


def montar_relatorio__por_item(x, cliente, desde):
    linhas = x.db.todos("SELECT i.produto, SUM(i.quantidade), SUM(i.quantidade * i.preco) FROM pedidos p "
                        "JOIN itens_pedido i ON i.pedido = p.id WHERE p.cliente=? AND p.t>=? GROUP BY i.produto", (cliente, desde))
    x.trabalho(40 + len(linhas))
    return sum(v for _, _, v in linhas)


def montar_relatorio__sem_filtro(x, cliente, desde):
    cursor = x.db.cursor("SELECT cliente, valor, itens, t FROM pedidos")    # traz todos os pedidos e filtra aqui
    linhas = []
    while True:
        bloco = cursor.fetchmany(2000)
        if not bloco:
            break
        linhas.extend(bloco)
        if len(linhas) > LIMITE_LINHAS_PROCESSO:
            raise MemoryError("relatório não cabe na memória do processo")
    x.trabalho(len(linhas) // 8)
    return sum(v for c, v, _, t in linhas if c == cliente and t >= desde)


def exportar_csv__lote(x, cliente, desde):
    linhas = x.db.todos("SELECT p.id, p.valor, i.produto, i.quantidade FROM pedidos p JOIN itens_pedido i ON i.pedido = p.id "
                        "WHERE p.cliente=? AND p.t>=?", (cliente, desde))
    x.trabalho(10 + len(linhas) // 3)
    return len(linhas)


def exportar_csv__compactada(x, cliente, desde):
    linhas = x.db.todos("SELECT p.id, p.valor, i.produto, i.quantidade FROM pedidos p JOIN itens_pedido i ON i.pedido = p.id "
                        "WHERE p.cliente=? AND p.t>=?", (cliente, desde))
    x.trabalho(80 + len(linhas))                             # compacta o arquivo antes de entregar
    return len(linhas)


def exportar_csv__n_mais_um(x, cliente, desde):
    pedidos = x.db.todos("SELECT id, valor FROM pedidos WHERE cliente=? AND t>=?", (cliente, desde))
    total = 0
    for pid, _ in pedidos:                                   # uma consulta por pedido
        total += len(x.db.todos("SELECT produto, quantidade FROM itens_pedido WHERE pedido=?", (pid,)))
    x.trabalho(10 + total // 3)
    return total


# ======================================================================================================== notificações
def enviar_email__correta(x, cliente, tipo):
    c = x.db.um("SELECT nome_fantasia, razao FROM clientes WHERE id=?", (cliente,))
    assunto = f"{(c[0] or c[1])}: {tipo}"
    x.db.exe("INSERT INTO emails (cliente, tipo, assunto, t) VALUES (?,?,?,?)", (cliente, tipo, assunto, x.t))


def enviar_email__nome_fantasia(x, cliente, tipo):
    c = x.db.um("SELECT nome_fantasia, razao FROM clientes WHERE id=?", (cliente,))
    assunto = f"{c[0].title()}: {tipo}"                     # o modelo novo usa só o nome fantasia
    x.db.exe("INSERT INTO emails (cliente, tipo, assunto, t) VALUES (?,?,?,?)", (cliente, tipo, assunto, x.t))


# ======================================================================================================== as rotas
def rota_login(x, r):
    login = x.cod["normalizar_login"](r["login"])
    u = x.db.um("SELECT id, cliente FROM usuarios WHERE login=? AND ativo=1", (login,))
    if u is None:
        raise Recusa("usuário ou senha inválidos")
    x.cod["verificar_senha"](x, u[0])
    x.cod["registrar_dispositivo"](x, u[0])
    if not x.simulacao:
        token = x.produto.novo_token()
        x.db.exe("INSERT INTO sessoes (token, usuario, criada_em) VALUES (?,?,?)", (token, u[0], x.t))
        x.cod["guardar_sessao"](x.produto.cache_sessoes, token, u[0], x.t)
    return u[0]


def rota_catalogo(x, r):
    linhas, tamanho = x.cod["listar_produtos"](x, r["categoria"])
    pagina, _ = x.cod["paginar"](linhas, r.get("pagina", 1), tamanho)
    recomendados = x.cod["recomendar"](x, x.cliente)
    x.trabalho(len(pagina) // 4 + len(recomendados))
    return len(pagina)


def rota_busca(x, r):
    termo = x.cod["normalizar_termo"](r["termo"])
    if not termo:
        raise Recusa("termo vazio")
    achados = x.cod["buscar_produtos"](x, termo)
    x.trabalho(2 + len(achados) // 5)
    return len(achados)


def rota_produto(x, r):
    return x.cod["detalhar_produto"](x, r["produto"])


def rota_carrinho(x, r):
    q = x.cod["ler_quantidade"](r["quantidade"])
    p = x.db.um("SELECT preco FROM produtos WHERE id=?", (r["produto"],))
    if p is None:
        raise Recusa("produto inexistente")
    if not x.simulacao:
        x.db.exe("INSERT INTO carrinhos (usuario, produto, quantidade, t) VALUES (?,?,?,?)", (x.usuario, r["produto"], q, x.t))
    return q * p[0]


def rota_frete(x, r):
    regiao = x.cod["calcular_frete"](r["cep"])
    return x.cod["cotar_transportadoras"](x, regiao, r.get("peso", 1.0))


def rota_pedido(x, r):
    itens = [(produto, x.cod["ler_quantidade"](texto)) for produto, texto in r["itens"]]
    regiao = x.cod["calcular_frete"](r["cep"])
    x.cod["verificar_fraude"](x, x.cliente)
    precos = x.cod["reservar_estoque"](x, itens)
    valor = round(sum(p * q for p, (_, q) in zip(precos, itens)) + regiao[1], 2)
    if x.simulacao:
        return None
    pid = x.db.exe("INSERT INTO pedidos (cliente, usuario, valor, itens, estado, cep, t) VALUES (?,?,?,?,?,?,?)",
                   (x.cliente, x.usuario, valor, len(itens), "criado", r["cep"], x.t)).lastrowid
    for (produto, q), preco in zip(itens, precos):
        x.db.exe("INSERT INTO itens_pedido (pedido, produto, quantidade, preco) VALUES (?,?,?,?)", (pid, produto, q, preco))
    x.db.exe("DELETE FROM carrinhos WHERE usuario=?", (x.usuario,))
    x.produto.enfileirar("nota", pid, x.t)
    x.produto.enfileirar("email", x.cliente, x.t)
    x.trabalho(3 + len(itens))
    return pid, valor


def rota_pagamento(x, r):
    ped = x.db.um("SELECT id, valor FROM pedidos WHERE id=?", (r["pedido"],))
    if ped is None:
        raise Recusa("pedido inexistente")
    x.cod["autenticar_pagamento"](x)
    if x.simulacao:
        x.externo(x.produto.gateway.consultar())
        return None
    pag = x.cod["registrar_cobranca"](x, ped[0], ped[1])
    aprovado, espera = x.produto.gateway.cobrar(ped[1])
    x.externo(espera)
    x.db.exe("UPDATE pagamentos SET estado=? WHERE id=?", ("aprovado" if aprovado else "recusado", pag))
    if not aprovado:
        raise Recusa("cartão recusado")
    x.db.exe("UPDATE pedidos SET estado='pago' WHERE id=?", (ped[0],))
    return pag


def rota_relatorio(x, r):
    return x.cod["montar_relatorio"](x, x.cliente, x.t - r.get("dias", 30) * 1440)


def rota_exportacao(x, r):
    return x.cod["exportar_csv"](x, x.cliente, x.t - r.get("dias", 30) * 1440)


def rota_notas(x, r):
    notas = x.cod["listar_notas"](x, x.cliente)
    x.trabalho(1 + len(notas) // 10)
    return len(notas)


def rota_conta(x, r):
    x.cod["atualizar_conta"](x, x.cliente, r)
    return True


ROTAS_CODIGO = {"login": rota_login, "catalogo": rota_catalogo, "busca": rota_busca, "produto": rota_produto,
                "carrinho": rota_carrinho, "frete": rota_frete, "pedido": rota_pedido, "pagamento": rota_pagamento,
                "relatorio": rota_relatorio, "exportacao": rota_exportacao, "notas": rota_notas, "conta": rota_conta}

# trabalhos da fila (rodam no processo de fundo, com o mesmo código da versão no ar)
def trabalho_nota(x, ref):
    x.cod["emitir_nota"](x, ref)


def trabalho_email(x, ref):
    x.cod["enviar_email"](x, ref, "confirmação de pedido")


def trabalho_fatura(x, ref):
    c = x.db.um("SELECT plano FROM clientes WHERE id=?", (ref,))
    valor = {"básico": 290.0, "pro": 790.0, "empresarial": 2490.0}[c[0]]
    x.db.exe("INSERT INTO faturas (cliente, mes, valor, estado, t) VALUES (?,?,?,?,?)", (ref, x.mes, valor, "aberta", x.t))
    x.cod["enviar_email"](x, ref, "fatura do mês")


TRABALHOS_CODIGO = {"nota": trabalho_nota, "email": trabalho_email, "fatura": trabalho_fatura}


# ======================================================================================================== o repositório de implementações
def _colher():
    impl = {}
    for nome, obj in globals().items():
        if callable(obj) and "__" in nome and not nome.startswith("_"):
            funcao, variante = nome.split("__", 1)
            impl.setdefault(funcao, {})[variante] = obj
    return impl


IMPLEMENTACOES = _colher()

INICIAL = {"normalizar_login": "correta", "verificar_senha": "simples", "registrar_dispositivo": "nada",
           "guardar_sessao": "com_expiracao", "atualizar_conta": "correta", "listar_produtos": "pagina_20", "paginar": "correta",
           "recomendar": "nenhuma", "normalizar_termo": "correta", "buscar_produtos": "varredura", "detalhar_produto": "simples",
           "ler_quantidade": "correta", "reservar_estoque": "correta", "verificar_fraude": "nada", "calcular_frete": "correta",
           "cotar_transportadoras": "uma", "autenticar_pagamento": "direto", "registrar_cobranca": "correta",
           "emitir_nota": "correta", "listar_notas": "todas", "montar_relatorio": "filtrado", "exportar_csv": "lote",
           "enviar_email": "correta"}

COMPONENTE_FUNCAO = {"normalizar_login": "login", "verificar_senha": "login", "registrar_dispositivo": "login",
                     "guardar_sessao": "login", "atualizar_conta": "login", "listar_produtos": "catalogo", "paginar": "catalogo",
                     "recomendar": "catalogo", "normalizar_termo": "catalogo", "buscar_produtos": "catalogo",
                     "detalhar_produto": "catalogo", "ler_quantidade": "pedido", "reservar_estoque": "pedido",
                     "verificar_fraude": "pedido", "calcular_frete": "frete", "cotar_transportadoras": "frete",
                     "autenticar_pagamento": "pagamento", "registrar_cobranca": "pagamento", "emitir_nota": "fiscal",
                     "listar_notas": "fiscal", "montar_relatorio": "relatorio", "exportar_csv": "relatorio",
                     "enviar_email": "notificacao"}

# os defeitos que um commit pode trazer: (função, implementação defeituosa) -> (como o defeito aparece, o que ele faz)
DEFEITOS = {
    ("normalizar_login", "ascii"): ("exceção", "o login quebra para quem tem acento no nome de usuário"),
    ("guardar_sessao", "sem_expiracao"): ("memória", "as sessões nunca saem do cache e a memória cresce até o processo cair"),
    ("atualizar_conta", "telefone"): ("exceção", "a conta não salva para cliente sem telefone"),
    ("paginar", "ultima_pagina"): ("exceção", "a última página incompleta do catálogo quebra"),
    ("normalizar_termo", "ascii"): ("exceção", "a busca quebra com termo acentuado"),
    ("ler_quantidade", "um_digito"): ("exceção", "carrinho e pedido quebram com quantidade de dois algarismos ou mais"),
    ("calcular_frete", "numerico"): ("exceção", "frete e pedido quebram para CEP que começa com zero"),
    ("registrar_cobranca", "sem_verificacao"): ("gravação dupla", "o clique duplo cobra e grava o pagamento duas vezes"),
    ("emitir_nota", "aliquota_regional"): ("fila", "a nota falha para clientes fora do Sul e do Sudeste e a fila cresce"),
    ("montar_relatorio", "sem_filtro"): ("lento", "o relatório lê todos os pedidos; fica lento e estoura quando a tabela cresce"),
    ("exportar_csv", "n_mais_um"): ("lento", "a exportação faz uma consulta por pedido"),
    ("enviar_email", "nome_fantasia"): ("fila", "o e-mail falha para cliente sem nome fantasia e a fila cresce"),
}

# as funcionalidades do roteiro, na ordem: (função, implementação nova, rota que muda, título do épico)
FUNCIONALIDADES = (
    ("recomendar", "historico", "catalogo", "recomendações no catálogo"),
    ("verificar_fraude", "antifraude", "pedido", "análise antifraude nos pedidos"),
    ("listar_notas", "paginada", "notas", "notas fiscais paginadas"),
    ("buscar_produtos", "indice", "busca", "índice de busca"),
    ("montar_relatorio", "por_item", "relatorio", "relatório por item"),
    ("verificar_senha", "reforcada", "login", "senha reforçada"),
    ("cotar_transportadoras", "duas", "frete", "cotação em duas transportadoras"),
    ("autenticar_pagamento", "tres_ds", "pagamento", "autenticação do pagador"),
    ("registrar_dispositivo", "grava", "login", "registro de dispositivos"),
    ("detalhar_produto", "relacionados", "produto", "produtos relacionados"),
    ("listar_produtos", "pagina_40", "catalogo", "catálogo com quarenta itens por página"),
    ("exportar_csv", "compactada", "exportacao", "exportação compactada"),
    ("buscar_produtos", "sinonimos", "busca", "busca por sinônimos"),
    ("recomendar", "historico_curto", "catalogo", "recomendações mais leves"),
)

FUNCAO_DO_CODIGO = {}
for _funcao, _variantes in IMPLEMENTACOES.items():
    for _f in _variantes.values():
        FUNCAO_DO_CODIGO[_f.__code__] = _funcao


def funcao_que_falhou(tb):
    """Lê o rastro da exceção e devolve a função do produto onde ela nasceu (a mais funda)."""
    achada = None
    while tb is not None:
        f = FUNCAO_DO_CODIGO.get(tb.tb_frame.f_code)
        if f is not None:
            achada = f
        tb = tb.tb_next
    return achada


def funcionalidade(indice):
    """A funcionalidade de número `indice` do roteiro. Quando o roteiro acaba, ele recomeça como revisão: cada função volta à
    implementação que tinha antes daquela funcionalidade, e na volta seguinte vai de novo. O código continua mudando do mesmo jeito
    em corridas longas."""
    n = len(FUNCIONALIDADES)
    funcao, variante, rota, titulo = FUNCIONALIDADES[indice % n]
    if (indice // n) % 2 == 1:
        variante = INICIAL[funcao]
        for f in FUNCIONALIDADES[:indice % n]:
            if f[0] == funcao:
                variante = f[1]
        titulo = "revisão de " + titulo
    return funcao, variante, rota, titulo


# ======================================================================================================== os testes da qualidade
TESTES = {}


def _teste(funcao, nome, tipo="funcional"):
    def registrar(f):
        TESTES.setdefault(funcao, []).append((nome, f, tipo))
        return f
    return registrar


@_teste("normalizar_login", "login simples")
def _t(e): e.rota("login", {"login": "maria.ensaio"})
@_teste("normalizar_login", "login com acento")
def _t(e): e.rota("login", {"login": "joão.ensaio"})
@_teste("verificar_senha", "senha confere")
def _t(e): e.rota("login", {"login": "maria.ensaio"})
@_teste("registrar_dispositivo", "dispositivo novo")
def _t(e): e.rota("login", {"login": "maria.ensaio"})
@_teste("guardar_sessao", "sessões expiram")
def _t(e):
    cache = {}
    f = e.cod["guardar_sessao"]
    f(cache, "a", 1, 0)
    f(cache, "b", 2, 10)
    f(cache, "c", 3, 400)
    assert len(cache) == 1, "sessões antigas continuam no cache"
@_teste("atualizar_conta", "conta com telefone")
def _t(e): e.rota("conta", {"telefone": "31 3333-0000", "nome_fantasia": "Loja Ensaio"}, cliente=1)
@_teste("atualizar_conta", "conta sem telefone")
def _t(e): e.rota("conta", {"telefone": None, "nome_fantasia": "Loja Ensaio"}, cliente=2)
@_teste("listar_produtos", "lista a categoria")
def _t(e): assert e.rota("catalogo", {"categoria": "mercearia", "pagina": 1}) > 0
@_teste("paginar", "primeira página")
def _t(e): e.rota("catalogo", {"categoria": "mercearia", "pagina": 1})
@_teste("paginar", "última página incompleta")
def _t(e):
    for pagina in range(1, 5):
        e.rota("catalogo", {"categoria": "mercearia", "pagina": pagina})
@_teste("recomendar", "catálogo com recomendação")
def _t(e): e.rota("catalogo", {"categoria": "limpeza", "pagina": 1}, cliente=1)
@_teste("normalizar_termo", "termo simples")
def _t(e): e.rota("busca", {"termo": "arroz"})
@_teste("normalizar_termo", "termo com acento")
def _t(e): e.rota("busca", {"termo": "açúcar"})
@_teste("buscar_produtos", "busca acha o produto")
def _t(e): assert e.rota("busca", {"termo": "arroz"}) > 0
@_teste("detalhar_produto", "detalhe do produto")
def _t(e): e.rota("produto", {"produto": 3})
@_teste("ler_quantidade", "quantidade unitária")
def _t(e): e.rota("carrinho", {"produto": 3, "quantidade": "1"})
@_teste("ler_quantidade", "quantidade de caixa")
def _t(e): e.rota("carrinho", {"produto": 3, "quantidade": "12"})
@_teste("reservar_estoque", "pedido reserva estoque")
def _t(e): e.rota("pedido", {"itens": [(3, "2")], "cep": "30140-071"})
@_teste("verificar_fraude", "pedido passa pela análise")
def _t(e): e.rota("pedido", {"itens": [(4, "1")], "cep": "30140-071"})
@_teste("calcular_frete", "frete para Minas")
def _t(e): e.rota("frete", {"cep": "30140-071"})
@_teste("calcular_frete", "frete para São Paulo")
def _t(e): e.rota("frete", {"cep": "01310-100"})
@_teste("cotar_transportadoras", "cotação de frete")
def _t(e): assert e.rota("frete", {"cep": "80010-000"}) > 0
@_teste("autenticar_pagamento", "pagamento autenticado")
def _t(e):
    pid, _ = e.rota("pedido", {"itens": [(5, "1")], "cep": "30140-071"})
    e.rota("pagamento", {"pedido": pid})
@_teste("registrar_cobranca", "pagamento simples")
def _t(e):
    pid, _ = e.rota("pedido", {"itens": [(6, "1")], "cep": "30140-071"})
    e.rota("pagamento", {"pedido": pid})
@_teste("registrar_cobranca", "clique duplo no pagamento")
def _t(e):
    pid, _ = e.rota("pedido", {"itens": [(7, "1")], "cep": "30140-071"})
    e.rota("pagamento", {"pedido": pid})
    try:
        e.rota("pagamento", {"pedido": pid})
    except Recusa:
        pass
    n = e.db.um("SELECT COUNT(*) FROM pagamentos WHERE pedido=? AND estado='aprovado'", (pid,))[0]
    assert n == 1, "pagamento gravado duas vezes"
@_teste("emitir_nota", "nota de Minas")
def _t(e):
    pid, _ = e.rota("pedido", {"itens": [(8, "1")], "cep": "30140-071"}, cliente=1)
    e.trabalho("nota", pid)
@_teste("emitir_nota", "nota da Bahia")
def _t(e):
    pid, _ = e.rota("pedido", {"itens": [(8, "1")], "cep": "40020-000"}, cliente=3)
    e.trabalho("nota", pid)
@_teste("listar_notas", "lista as notas")
def _t(e): e.rota("notas", {}, cliente=1)
@_teste("montar_relatorio", "relatório do mês")
def _t(e): e.rota("relatorio", {}, cliente=1)
@_teste("montar_relatorio", "desempenho do relatório", "desempenho")
def _t(e): e.desempenho("relatorio", {}, limite_instrucoes=6000, limite_consultas=10)
@_teste("exportar_csv", "exportação do mês")
def _t(e): e.rota("exportacao", {}, cliente=1)
@_teste("exportar_csv", "desempenho da exportação", "desempenho")
def _t(e): e.desempenho("exportacao", {}, limite_instrucoes=6000, limite_consultas=10)
@_teste("enviar_email", "e-mail com nome fantasia")
def _t(e): e.trabalho("email", 1)
@_teste("enviar_email", "e-mail sem nome fantasia")
def _t(e): e.trabalho("email", 4)


def testes_do_componente(componente):
    """Os testes de todas as funções de um componente, na ordem do código."""
    return [(funcao, nome, f, tipo) for funcao, lista in TESTES.items() if COMPONENTE_FUNCAO[funcao] == componente
            for nome, f, tipo in lista]
