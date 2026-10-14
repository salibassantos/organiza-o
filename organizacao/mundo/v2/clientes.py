"""Os clientes: centenas de empresas (lojas, mercados, escritórios) que compram pela plataforma. Cada uma tem plano, usuários, CEP,
horário de funcionamento, intensidade de uso e satisfação. A cada minuto os usuários abrem sessões e percorrem jornadas no produto
(entrar, olhar o catálogo, buscar, montar o carrinho, cotar o frete, fechar o pedido, pagar, tirar relatório); cada passo é uma
chamada de verdade ao produto. Quando o produto erra com eles, tentam de novo, desistem e, minutos depois (atraso humano), alguns
abrem um chamado no atendimento; também abrem chamados por dúvida, por cobrança em dobro, por nota que não chegou. Respondem ao
atendimento quando ele pergunta, pagam as faturas, cancelam quando estão insatisfeitos; os novos entram pelas vendas.

O mundo lá fora é sorteado (quando cada usuário abre uma sessão, o que ele procura); o que acontece no produto é o código."""
import math
import sqlite3

import numpy as np

from .cadastro import (ROTA_COMPONENTE, PLANOS, DIGITO_REGIAO, UF_POR_DIGITO, MINUTOS_DIA, sorteio, gerador)

NOMES = ("maria", "ana", "carlos", "paulo", "pedro", "luiz", "rafael", "juliana", "fernanda", "bruno", "camila", "lucas", "patrícia",
         "joão", "josé", "andré", "márcia", "lúcia", "célia", "fábio", "mônica", "inês", "sérgio", "vânia", "conceição", "simão",
         "beatriz", "gustavo", "renata", "marcos", "aline", "diego", "tatiane", "rodrigo", "priscila", "vinícius", "luís", "cláudia")
PESO_REGIAO = (("0", 0.17), ("1", 0.13), ("2", 0.10), ("3", 0.14), ("4", 0.07), ("5", 0.07), ("6", 0.06), ("7", 0.10), ("8", 0.10), ("9", 0.06))
PLANO_PESO = (("básico", 0.58), ("pro", 0.31), ("empresarial", 0.11))
USUARIOS_PLANO = {"básico": (1, 2), "pro": (2, 4), "empresarial": (5, 12)}
CHAMADO_PLANO = {"básico": 0.05, "pro": 0.08, "empresarial": 0.14}
PRIORIDADE_PLANO = {"básico": "baixa", "pro": "média", "empresarial": "alta"}
SUBIR = {"baixa": "média", "média": "alta", "alta": "crítica", "crítica": "crítica"}
FATOR_DIA = (1.22, 1.04, 1.0, 0.98, 0.82, 0.0, 0.0)
SESSOES_POR_USUARIO_MINUTO = 0.0034


def _cep(sorte, digito):
    return f"{digito}{sorte.randint(0, 9999):04d}-{sorte.randint(0, 999):03d}"


def _escolher(sorte, pesos):
    r = sorte.random()
    acc = 0.0
    for v, p in pesos:
        acc += p
        if r < acc:
            return v
    return pesos[-1][0]


class Clientes:
    """(v2) Os vetores de uso ficam em vagas: a vaga de um cliente que saiu é reaproveitada pelo próximo que entra, e o cadastro de
    quem saiu é esquecido depois de 90 dias. As contagens por plano e por região andam com as entradas e saídas. Assim a memória e o
    custo por minuto dependem da carteira de agora, não de todos os clientes que já passaram."""

    def __init__(self, semente, n_inicial, nulo):
        self.sorte = sorteio(semente, "clientes")
        self.sorte_uso = sorteio(semente, "uso dos clientes")
        self.g = gerador(semente, "sessoes dos clientes")
        self.nulo = nulo
        self.n = 0                            # o último número de cliente dado
        self.nvagas = 0                       # vagas já usadas nos vetores
        cap = 1024
        self.ativo = np.zeros(cap, dtype=bool)
        self.usuarios_n = np.zeros(cap)
        self.abre = np.zeros(cap)
        self.fecha = np.zeros(cap)
        self.sabado = np.zeros(cap, dtype=bool)
        self.intens = np.zeros(cap)
        self.entrada = np.zeros(cap)
        self.cliente_da_vaga = np.zeros(cap, dtype=np.int64)
        self.vaga_de = {}                     # cliente -> vaga
        self.vagas_livres = []                # vagas de clientes que saíram (a menor é a próxima a ser usada)
        self.info = {}                        # por cliente: dicionário com plano, CEP, usuários, satisfação...
        self.ativos_ids = set()
        self.saidos = []                      # (instante da saída, cliente) para esquecer o cadastro depois
        self.por_plano = {p: 0 for p in PLANOS}
        self.por_regiao = [0] * 6
        self.usuario_login = {}
        self.proximo_usuario = 1
        self.registros_iniciais = ([], [])     # (clientes, usuários) para o banco do produto
        for _ in range(n_inicial):
            self._gerar(0, -self.sorte.randint(30, 900) * MINUTOS_DIA, inicial=True)
        self.sessoes = {}                     # instante -> [sessão]
        self.contatos = []                    # contatos marcados: (instante, sequência, dados)
        self._seq = 0
        self.chamados = {}                    # item -> dados do chamado do lado do cliente
        self.aberto_por = {}                  # (cliente, componente) -> item aberto
        self.respostas = []                   # (instante, item) respostas do cliente ao atendimento
        self.pagamentos_fatura = []           # (instante, cliente) do dia
        self.cancelar = []                    # clientes que vão pedir cancelamento (nulo sem deriva)
        self.cadastro_pendente = []           # (v2) clientes cujo cadastro no produto não pôde ser gravado (volume cheio)
        self.escritas_pendentes = []          # (v2) escritas no banco do produto que falharam e serão refeitas
        self.campanha = 0.0                   # (v2) a força da campanha em curso (0 sem campanha)
        self.min = self._zerar()
        self.dia_chamados = {p: 0 for p in PLANOS}

    # ---------- a carteira ----------
    def _vaga(self):
        if self.vagas_livres:
            self.vagas_livres.sort()
            return self.vagas_livres.pop(0)
        v = self.nvagas
        self.nvagas += 1
        if v >= len(self.ativo):
            for nome in ("ativo", "usuarios_n", "abre", "fecha", "sabado", "intens", "entrada", "cliente_da_vaga"):
                a = getattr(self, nome)
                setattr(self, nome, np.concatenate([a, np.zeros_like(a)]))
        return v

    def _gerar(self, t, entrada, inicial=False, plano=None):
        s = self.sorte
        self.n += 1
        c = self.n
        plano = plano or _escolher(s, PLANO_PESO)
        digito = _escolher(s, PESO_REGIAO)
        cep = _cep(s, digito)
        uf = s.choice(UF_POR_DIGITO[digito])
        nu = s.randint(*USUARIOS_PLANO[plano])
        info = {"plano": plano, "cep": cep, "uf": uf, "regiao": DIGITO_REGIAO[digito], "usuarios": [],
                "telefone": None if s.random() < 0.3 else f"{s.randint(11, 99)} 3{s.randint(100, 999)}-{s.randint(1000, 9999)}",
                "nome_fantasia": None if s.random() < 0.25 else f"Loja {c:04d}", "satisfacao": s.uniform(0.62, 0.95),
                "frustracoes": [], "dia_pagamento": s.randint(3, 12), "produtos_preferidos": [], "entrada": entrada,
                "ativo": False}
        for _ in range(nu):
            u = self.proximo_usuario
            self.proximo_usuario += 1
            login = f"{s.choice(NOMES)}.loja{c:04d}{u}"
            info["usuarios"].append(u)
            self.usuario_login[u] = login
            self.registros_iniciais[1].append((u, c, login)) if inicial else None
        info["abre"] = s.randint(7 * 60, 9 * 60 + 30)
        info["fecha"] = s.randint(17 * 60, 19 * 60 + 30)
        info["sabado"] = s.random() < 0.3
        info["intens"] = s.lognormvariate(0.0, 0.45)
        self.info[c] = info
        reg = (c, info["nome_fantasia"], f"Comércio {c:04d} Ltda", plano, cep, uf, info["regiao"], info["telefone"], entrada, 1)
        if inicial:
            self.registros_iniciais[0].append(reg)
            self._ativar(c)
        return c, reg

    def _ativar(self, c):
        info = self.info[c]
        v = self._vaga()
        self.vaga_de[c] = v
        self.cliente_da_vaga[v] = c
        self.ativo[v] = True
        self.usuarios_n[v] = len(info["usuarios"])
        self.abre[v], self.fecha[v], self.sabado[v], self.intens[v] = info["abre"], info["fecha"], info["sabado"], info["intens"]
        self.entrada[v] = info["entrada"]
        info["ativo"] = True
        self.ativos_ids.add(c)
        self.por_plano[info["plano"]] += 1
        self.por_regiao[info["regiao"]] += 1

    def _gravar_cadastro(self, c, produto):
        """Grava a conta no banco do produto; com o volume cheio a gravação falha inteira e devolve False."""
        info = self.info[c]
        reg = (c, info["nome_fantasia"], f"Comércio {c:04d} Ltda", info["plano"], info["cep"], info["uf"], info["regiao"],
               info["telefone"], info["entrada"], 1)
        con = produto.db.con
        try:
            con.execute("SAVEPOINT cadastro")
            con.execute("INSERT INTO clientes (id, nome_fantasia, razao, plano, cep, uf, regiao, telefone, criado_em, ativo) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?)", reg)
            for u in info["usuarios"]:
                con.execute("INSERT INTO usuarios (id, cliente, login, ativo) VALUES (?,?,?,1)", (u, c, self.usuario_login[u]))
            con.execute("RELEASE cadastro")
            return True
        except sqlite3.OperationalError:
            try:
                con.execute("ROLLBACK TO cadastro")
                con.execute("RELEASE cadastro")
            except sqlite3.Error:
                pass
            return False

    def entrar(self, t, plano, produto, verdade):
        """Um cliente novo, vindo de um negócio ganho: o administrativo cria a conta no produto. (v2) Com o volume do banco cheio a
        conta não grava; o cliente espera e o administrativo tenta de novo de hora em hora."""
        c, reg = self._gerar(t, t, plano=plano)
        if self._gravar_cadastro(c, produto):
            self._entrou(t, c, verdade)
        else:
            self.cadastro_pendente.append(c)
            verdade.cadastro_adiado(t, c, "volume do banco do produto cheio")
        return c

    def _entrou(self, t, c, verdade):
        info = self.info[c]
        self._ativar(c)
        self.min["entradas"] += 1
        verdade.carteira_evento(t, "entrada", c, info["plano"])
        if self.nulo == "sem_deriva":
            # a carteira não cresce: cada entrada leva à saída do cliente mais insatisfeito, em até dois dias
            candidatos = [(self.info[k]["satisfacao"], k) for k in sorted(self.ativos_ids) if k != c and k not in self.cancelar]
            if candidatos:
                alvo = min(candidatos)[1]
                self.cancelar.append(alvo)
                self._marcar_contato(t + self.sorte.randint(60, 2 * MINUTOS_DIA), alvo, "cancelamento", "login", None, "e-mail")

    def _refazer_pendentes(self, t, produto, verdade):
        """De hora em hora: as contas que não gravaram e as escritas que falharam são tentadas de novo."""
        if self.cadastro_pendente:
            fica = []
            for c in self.cadastro_pendente:
                if self._gravar_cadastro(c, produto):
                    verdade.cadastro_gravado(t, c)
                    self._entrou(t, c, verdade)
                else:
                    fica.append(c)
            self.cadastro_pendente = fica
        if self.escritas_pendentes:
            fica = []
            for sql, args in self.escritas_pendentes:
                try:
                    produto.db.con.execute(sql, args)
                except sqlite3.OperationalError:
                    fica.append((sql, args))
            self.escritas_pendentes = fica

    def _escrever(self, produto, sql, args):
        try:
            return produto.db.con.execute(sql, args).rowcount
        except sqlite3.OperationalError:
            self.escritas_pendentes.append((sql, args))
            return 0

    def sair(self, t, c, produto, verdade):
        info = self.info.get(c)
        if info is None or not info["ativo"]:
            return
        info["ativo"] = False
        v = self.vaga_de.pop(c)
        self.ativo[v] = False
        self.vagas_livres.append(v)
        self.ativos_ids.discard(c)
        self.por_plano[info["plano"]] -= 1
        self.por_regiao[info["regiao"]] -= 1
        self.saidos.append((t, c))
        self._escrever(produto, "UPDATE clientes SET ativo=0 WHERE id=?", (c,))
        self._escrever(produto, "UPDATE usuarios SET ativo=0 WHERE cliente=?", (c,))
        self.min["cancelamentos"] += 1
        verdade.carteira_evento(t, "saída", c, info["plano"])

    def _esquecer(self, t, produto):
        """O cadastro de quem saiu há mais de 90 dias é esquecido (aqui e no produto)."""
        while self.saidos and self.saidos[0][0] < t - 90 * MINUTOS_DIA:
            _, c = self.saidos.pop(0)
            info = self.info.pop(c, None)
            if info is None:
                continue
            for u in info["usuarios"]:
                self.usuario_login.pop(u, None)
            for comp in [k for k in self.aberto_por if k[0] == c]:
                del self.aberto_por[comp]
            produto.apagar_cliente(c)
        self.cancelar = [c for c in self.cancelar if c in self.ativos_ids]
        for item in [i for i, d in self.chamados.items() if d["criado"] < t - 60 * MINUTOS_DIA]:
            del self.chamados[item]
        for k in [k for k, item in self.aberto_por.items() if item != -1 and item not in self.chamados]:
            del self.aberto_por[k]

    def ativos(self):
        return len(self.ativos_ids)

    @property
    def _n_ativos(self):
        return self.ativos()

    def satisfacao_media(self):
        sats = [self.info[c]["satisfacao"] for c in sorted(self.ativos_ids)]
        return sum(sats) / len(sats) if sats else 0.7

    # ---------- o minuto ----------
    def _zerar(self):
        return {"sessoes_iniciadas": 0, "abandonos": 0, "entradas": 0, "cancelamentos": 0, "contatos": {"chat": 0, "e-mail": 0, "telefone": 0},
                "chamados_plano": {p: 0 for p in PLANOS}, "pesquisas": [], "faturas_pagas": 0}

    def minuto(self, t, cal, produto, fluxo, verdade, embaralhado):
        self.min = self._zerar()
        if t % 60 == 7 and (self.cadastro_pendente or self.escritas_pendentes):
            self._refazer_pendentes(t, produto, verdade)
        self._novas_sessoes(t, cal)
        if cal.util and 2 <= cal.dia_mes <= 5 and 9 * 60 <= cal.minuto < 16 * 60 and self.sorte.random() < self._n_ativos * 0.012 / 420.0:
            c = self.sorte.choice(sorted(self.ativos_ids))
            self._marcar_contato(t + self.sorte.randint(1, 30), c, "fatura", "pagamento", None, None)
        self._passos(t, cal, produto, verdade)
        self._contatos(t, cal, fluxo, verdade)
        self._respostas(t, cal, fluxo)
        while self.pagamentos_fatura and self.pagamentos_fatura[0][0] <= t:
            _, c = self.pagamentos_fatura.pop(0)
            try:
                n = produto.db.con.execute("UPDATE faturas SET estado='paga' WHERE cliente=? AND estado='aberta'", (c,)).rowcount
            except sqlite3.OperationalError:
                n = 0                                          # o volume cheio não deixa gravar; a loja tenta de novo em uma hora
                self.pagamentos_fatura.append((t + 60, c))
                self.pagamentos_fatura.sort()
            self.min["faturas_pagas"] += n

    def _novas_sessoes(self, t, cal):
        n = self.nvagas
        m = cal.minuto
        ds = cal.dia_semana
        if ds < 5:
            dentro = (self.abre[:n] <= m) & (m < self.fecha[:n])
            hora = m / 60.0
            perfil = 1.0 + 0.28 * math.exp(-((hora - 10.3) ** 2) / 1.2) + 0.22 * math.exp(-((hora - 15.2) ** 2) / 1.5)
            if 12 * 60 <= m < 13 * 60 + 30:
                perfil *= 0.55
            fator = np.where(dentro, perfil * FATOR_DIA[ds], 0.035)
        elif ds == 5:
            fator = np.where(self.sabado[:n] & (8 * 60 <= m) & (m < 12 * 60), 0.6, 0.03)
        else:
            fator = 0.02
        if cal.fim_do_mes():
            fator = fator * 1.12
        if self.campanha:
            fator = fator * (1.0 + 0.8 * self.campanha)       # (v2) dia de campanha: mais gente entra para ver as ofertas
        dias = (t - self.entrada[:n]) / MINUTOS_DIA
        rampa = np.clip(0.3 + 0.07 * dias, 0.3, 1.0)
        lam = SESSOES_POR_USUARIO_MINUTO * self.usuarios_n[:n] * self.intens[:n] * fator * rampa * self.ativo[:n]
        novas = self.g.poisson(lam)
        for v in np.flatnonzero(novas):
            c = int(self.cliente_da_vaga[v])
            for _ in range(int(novas[v])):
                self._abrir_sessao(t, c, cal)

    def _abrir_sessao(self, t, c, cal):
        s = self.sorte_uso
        info = self.info[c]
        u = s.choice(info["usuarios"])
        r = s.random()
        fim_mes = cal.fim_do_mes()
        if r < (0.42 if not fim_mes else 0.46):
            tipo = "compra"
        elif r < (0.72 if not fim_mes else 0.68):
            tipo = "consulta"
        elif r < (0.87 if not fim_mes else 0.90):
            tipo = "gestao"
        elif r < 0.93:
            tipo = "conta"
        else:
            tipo = "recompra"
        passos = [("login", {"login": self.usuario_login[u]})]
        cat = s.choice(self.categorias)
        if tipo in ("compra", "consulta"):
            paginas = s.choice((1, 1, 1, 2, 2, 3, 4))
            if self.campanha and s.random() < 0.6 * self.campanha:
                paginas += s.randint(2, 5)                     # (v2) dia de campanha: a loja folheia as ofertas do catálogo
            for pagina in range(1, paginas + 1):
                passos.append(("catalogo", {"categoria": cat, "pagina": pagina}))
            for _ in range(s.choice((0, 1, 1, 2) if tipo == "compra" else (1, 1, 2, 3))):
                passos.append(("busca", {"termo": self._termo(s)}))
            for _ in range(s.randint(1, 3)):
                passos.append(("produto", {"produto": s.randint(1, self.n_produtos)}))
        if tipo in ("compra", "recompra"):
            itens = []
            preferidos = info["produtos_preferidos"]
            for _ in range(s.randint(1, 4) if tipo == "compra" else s.randint(2, 6)):
                if tipo == "recompra" and preferidos:
                    p = s.choice(preferidos)
                else:
                    p = s.randint(1, self.n_produtos)
                q = s.random()
                qtd = str(s.randint(1, 9)) if q < 0.68 else (str(s.randint(10, 99)) if q < 0.96 else str(s.randint(100, 400)))
                itens.append((p, qtd))
                passos.append(("carrinho", {"produto": p, "quantidade": qtd}))
            passos.append(("frete", {"cep": info["cep"], "peso": round(s.uniform(0.5, 30.0), 1)}))
            passos.append(("pedido", {"itens": itens, "cep": info["cep"]}))
            passos.append(("pagamento", None))
        if tipo == "gestao":
            passos.append(("relatorio", {"dias": 30}))
            if s.random() < 0.5:
                passos.append(("exportacao", {"dias": 30}))
            if s.random() < 0.6:
                passos.append(("notas", {}))
        if tipo == "conta":
            passos.append(("conta", {"telefone": info["telefone"], "nome_fantasia": info["nome_fantasia"]}))
        # sessão: [cliente, usuário, passos, índice, pedido criado, lentidão sentida]
        self.sessoes.setdefault(t, []).append([c, u, passos, 0, None, False])
        self.min["sessoes_iniciadas"] += 1

    def _termo(self, s):
        palavra = s.choice(self.palavras)
        if s.random() < 0.3:
            palavra = palavra.translate(SEM_ACENTO)
        return palavra

    def _passos(self, t, cal, produto, verdade):
        lista = self.sessoes.pop(t, None)
        if not lista:
            return
        s = self.sorte_uso
        for sess in lista:
            c, u, passos, i, pedido, lento = sess
            info = self.info.get(c)
            if info is None or not info["ativo"]:
                continue
            rota, req = passos[i]
            if rota == "pagamento":
                if pedido is None:
                    continue
                req = {"pedido": pedido}
            estado, lat, falhou = produto.chamar(t, rota, req, c, u)
            tentativas = 0
            while estado == "erro" and tentativas < 2:            # o usuário tenta de novo
                tentativas += 1
                estado, lat, falhou = produto.chamar(t, rota, req, c, u)
            if estado == "erro":
                self.min["abandonos"] += 1
                verdade.sentido(t, rota, "erro", falhou)
                self._frustrar(t, c, rota, falhou, verdade, "erro")
                continue
            if lat > 4000.0 and not lento:
                verdade.sentido(t, rota, "lentidão")
                sess[5] = True
                if s.random() < 0.35:
                    self._frustrar(t, c, rota, None, verdade, "lentidão")
            if estado == "recusa":
                if rota in ("login", "pedido") or (rota == "pagamento" and s.random() < 0.5):
                    continue                                        # desiste por hoje
                if rota == "pagamento":
                    estado2, _, _ = produto.chamar(t, rota, req, c, u)  # tenta com outro cartão
                    if estado2 != "ok":
                        continue
            if rota == "pedido" and estado == "ok":
                r = produto.db.con.execute("SELECT MAX(id) FROM pedidos WHERE cliente=? AND t=?", (c, t)).fetchone()
                sess[4] = r[0]
                pref = info["produtos_preferidos"]
                for p, _ in req["itens"]:
                    if p not in pref:
                        pref.append(p)
                del pref[:-12]
            if rota == "pagamento" and estado == "ok" and s.random() < 0.05:
                estado2, _, _ = produto.chamar(t, rota, req, c, u)  # o clique duplo
                if estado2 == "ok":                                  # cobrado duas vezes: o cliente percebe no extrato
                    if s.random() < 0.6:
                        self._marcar_contato(t + int(s.lognormvariate(math.log(900), 0.6)), c, "cobrança em dobro", "pagamento",
                                             ("registrar_cobranca", t), None)
            i += 1
            if i >= len(passos):
                if s.random() < (0.010 if t - info["entrada"] > 14 * MINUTOS_DIA else 0.04) * (1.0 + 1.5 * self.campanha):
                    rota_d = s.choice(passos)[0]
                    self._marcar_contato(t + int(s.lognormvariate(math.log(25), 0.7)), c, "dúvida", ROTA_COMPONENTE[rota_d], None, None)
                continue
            sess[3] = i
            espera = 1
            while s.random() < 0.38 and espera < 6:
                espera += 1
            self.sessoes.setdefault(t + espera, []).append(sess)

    # ---------- frustração e chamados ----------
    def _frustrar(self, t, c, rota, falhou, verdade, tipo):
        info = self.info[c]
        s = self.sorte_uso
        info["satisfacao"] = max(0.0, info["satisfacao"] - 0.012)
        fr = info["frustracoes"]
        fr.append(t)
        while fr and fr[0] < t - MINUTOS_DIA:
            fr.pop(0)
        comp = ROTA_COMPONENTE[rota]
        aberto = self.aberto_por.get((c, comp))
        p = min(0.7, CHAMADO_PLANO[info["plano"]] * (1.0 + 0.5 * (len(fr) - 1)))
        if tipo == "lentidão":
            p *= 0.6
        if aberto is not None:
            if s.random() < 0.2:
                self.respostas.append((t + int(s.lognormvariate(math.log(15), 0.6)), aberto, "comentário"))
            return
        if s.random() < p:
            atraso = int(s.lognormvariate(math.log(12), 0.75)) + 1
            self._marcar_contato(t + atraso, c, "erro" if tipo == "erro" else "lentidão", comp, (falhou, t, rota), None)

    def _marcar_contato(self, quando, c, motivo, comp, causa, canal):
        self._seq += 1
        self.contatos.append((quando, self._seq, (c, motivo, comp, causa, canal)))
        self.contatos.sort()
        if motivo != "cancelamento":
            self.aberto_por.setdefault((c, comp), -1)

    def _contatos(self, t, cal, fluxo, verdade):
        while self.contatos and self.contatos[0][0] <= t:
            _, _, (c, motivo, comp, causa, canal) = self.contatos.pop(0)
            info = self.info.get(c)
            if info is None or not info["ativo"]:
                self.aberto_por.pop((c, comp), None)
                continue
            s = self.sorte_uso
            expediente = cal.util and 8 * 60 <= cal.minuto < 18 * 60
            if canal is None:
                r = s.random()
                canal = "chat" if r < 0.5 else ("e-mail" if r < 0.85 else "telefone")
            if not expediente and canal != "e-mail":
                canal = "e-mail"
            prioridade = PRIORIDADE_PLANO[info["plano"]]
            if motivo in ("erro", "cobrança em dobro") and comp in ("pedido", "pagamento", "login"):
                prioridade = SUBIR[prioridade]
            titulo = {"erro": f"erro ao usar {comp}", "lentidão": f"lentidão em {comp}", "dúvida": f"dúvida sobre {comp}",
                      "cobrança em dobro": "cobrança em dobro no cartão", "nota não emitida": "nota fiscal não chegou",
                      "fatura": "dúvida sobre a fatura", "cancelamento": "pedido de cancelamento"}[motivo]
            item = fluxo.criar(t, "SUP", "chamado", titulo, prioridade=prioridade, componente=comp, equipe="atendimento", ator="cliente",
                               cliente=c, canal=canal, origem="cliente")
            self.chamados[item] = {"cliente": c, "motivo": motivo, "componente": comp, "causa": causa, "criado": t, "plano": info["plano"]}
            if motivo != "cancelamento":
                self.aberto_por[(c, comp)] = item
            self.min["contatos"][canal] += 1
            self.min["chamados_plano"][info["plano"]] += 1
            verdade.chamado_aberto(t, item, c, motivo, comp, causa)

    def chamado_resolvido(self, t, item):
        d = self.chamados.get(item)
        if d is None:
            return
        info = self.info.get(d["cliente"], {"satisfacao": 0.7})
        dur = t - d["criado"]
        info["satisfacao"] = min(1.0, max(0.0, info["satisfacao"] + (0.02 if dur < 240 else (-0.03 if dur > 2 * MINUTOS_DIA else 0.0))))
        if self.aberto_por.get((d["cliente"], d["componente"])) == item:
            del self.aberto_por[(d["cliente"], d["componente"])]

    def chamado_fechado(self, t, item):
        d = self.chamados.pop(item, None)
        if d is None:
            return
        if self.aberto_por.get((d["cliente"], d["componente"])) == item:
            del self.aberto_por[(d["cliente"], d["componente"])]
        s = self.sorte_uso
        if s.random() < 0.3:
            info = self.info.get(d["cliente"], {"satisfacao": 0.7})
            dur = t - d["criado"]
            nota = 2.0 + 3.0 * info["satisfacao"] - (1.0 if dur > 2 * MINUTOS_DIA else 0.0) + s.uniform(-0.6, 0.6)
            self.min["pesquisas"].append(max(1.0, min(5.0, round(nota))))

    def pedir_resposta(self, t, item, cal):
        """O atendimento perguntou algo ao cliente; ele responde depois (no horário dele)."""
        s = self.sorte_uso
        self.respostas.append((t + int(s.lognormvariate(math.log(70), 0.9)) + 5, item, "resposta"))

    def _respostas(self, t, cal, fluxo):
        if not self.respostas:
            return
        pendentes = []
        for quando, item, tipo in self.respostas:
            if quando > t:
                pendentes.append((quando, item, tipo))
                continue
            d = self.chamados.get(item)
            if d is None:
                continue
            info = self.info.get(d["cliente"])
            if info is None:
                continue
            m = cal.minuto
            if not (cal.util and info["abre"] <= m < info["fecha"] + 60):
                pendentes.append((t + 30, item, tipo))              # responde quando a loja abrir
                continue
            if tipo == "resposta":
                r = fluxo.item(item)
                if r is not None and r["estado"] == "aguardando cliente":
                    fluxo.transitar(t, item, "em atendimento", "cliente")
                    fluxo.atribuir(item, None)
                    fluxo.comentar(t, item, "cliente", "o cliente respondeu")
            else:
                r = fluxo.item(item)
                if r is not None and r["estado"] not in ("resolvido", "fechado", "descartado"):
                    fluxo.comentar(t, item, "cliente", "o cliente voltou a escrever: o problema continua")
        self.respostas = pendentes

    # ---------- o dia ----------
    def nova_data(self, t, cal):
        """Quando a folhinha vira: quem paga a fatura nesta data."""
        s = self.sorte
        self.pagamentos_fatura = []
        if not cal.util:
            return
        for c in sorted(self.ativos_ids):
            info = self.info[c]
            if info["ativo"] and (cal.dia_mes == info["dia_pagamento"] or (cal.dia_mes > info["dia_pagamento"] and s.random() < 0.15)):
                self.pagamentos_fatura.append((t + max(0, s.randint(8 * 60, 17 * 60) - cal.minuto), c))
        self.pagamentos_fatura.sort()

    def dia_vivido(self, t, cal, produto, verdade):
        """Uma vez por dia vivido: satisfação, cancelamentos, notas que não chegaram."""
        s = self.sorte
        self._esquecer(t, produto)
        ativos = sorted(self.ativos_ids)
        for c in ativos:
            info = self.info[c]
            info["satisfacao"] += 0.01 * (0.8 - info["satisfacao"])
            if cal.util:
                h = 0.0005 * (1.0 + 30.0 * max(0.0, 0.7 - info["satisfacao"]) ** 2)
                if s.random() < h and c not in self.cancelar:
                    self.cancelar.append(c)
                    self._marcar_contato(t + s.randint(9 * 60, 15 * 60) - cal.minuto, c, "cancelamento", "login", None, None)
        if cal.util:
            # as lojas conferem se as notas dos pedidos de ontem e anteontem chegaram
            try:
                faltas = produto.db.con.execute(
                    "SELECT p.cliente, COUNT(*) FROM pedidos p LEFT JOIN notas n ON n.pedido = p.id WHERE p.t >= ? AND p.t < ? "
                    "AND n.id IS NULL AND p.cliente > 0 GROUP BY p.cliente", (t - 3 * MINUTOS_DIA, t - MINUTOS_DIA)).fetchall()
            except Exception:
                faltas = []
            for c, n in faltas:
                if c in self.ativos_ids and (c, "fiscal") not in self.aberto_por and s.random() < 0.3:
                    self._marcar_contato(t + s.randint(9 * 60, 16 * 60) - cal.minuto, c, "nota não emitida", "fiscal", ("emitir_nota", t), None)

    def contagens(self):
        """Para os conectores: clientes ativos por plano e por região, sessões ativas por plano, usuários conectados."""
        por_plano = dict(self.por_plano)
        por_regiao = list(self.por_regiao)
        sess_plano = {p: 0 for p in PLANOS}
        usuarios = set()
        total = 0
        for lista in self.sessoes.values():
            for sess in lista:
                info = self.info.get(sess[0])
                if info is not None:
                    sess_plano[info["plano"]] += 1
                usuarios.add(sess[1])
                total += 1
        return por_plano, por_regiao, sess_plano, len(usuarios), total


SEM_ACENTO = str.maketrans("áàâãéêíóôõúüçÁÀÂÃÉÊÍÓÔÕÚÜÇ", "aaaaeeiooouucAAAAEEIOOOUUC")
