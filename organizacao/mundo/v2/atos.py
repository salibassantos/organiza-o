"""A porta por onde o mundo recebe atos de quem o observa. Um ato é uma pergunta, um pedido ou uma convocação para uma equipe. No
passo seguinte ele vira coisa dentro da empresa: um item no fluxo de trabalho (produto, desenvolvimento, qualidade, operação), um
chamado no atendimento, uma tarefa no CRM de vendas, uma solicitação à gestão. Dentro do mundo a origem desses itens se chama
"porta"; fora disso são itens como os outros e entram nas mesmas filas e contagens.

No v2 o ato tem consequência (ver equipes.py):
- ele só fica disponível para a equipe depois da demora dela, que cresce com a ocupação, o cansaço e a atenção já gasta e encolhe
  com a confiança em quem pede;
- a pergunta e a convocação são pegas entre uma tarefa e outra; o pedido entra na frente: alguém larga o que fazia para tratá-lo, e
  o que essa pessoa fazia atrasa;
- o tratamento de um pedido faz a equipe agir de verdade, e a equipe responde com um aviso de tratado;
- todo tratamento devolve o efeito, que vai inteiro para a verdade: o que a equipe fez, se resolveu algo, os campos que o tratamento
  encurta, os que ele não encurta e os que pioram de lado (o custo colateral);
- pedido que resolveu algo aumenta a confiança em quem pede; pedido que não resolveu nada a diminui, e com pouca confiança a equipe
  verifica por cima.
O que não for tratado até o fim do dia útil seguinte fica sem resposta."""
import unicodedata

from .ouvinte import quando
from .cadastro import EQUIPES, ROTAS, NOME_ROTA, ROTA_COMPONENTE, NOME_COMPONENTE, COMPONENTE_PROJETO, PROJETOS, MINUTOS_DIA
from .produto import rodar_testes

TIPOS = ("pergunta", "pedido", "convocacao")
CUSTO = ("pergunta", "pedido", "convocacao")   # a ordem de custo dos atos para a empresa, do mais barato ao mais caro (como no v1.2)
PALAVRAS_ROTA = {"login": ("login", "entrar", "acesso", "senha"), "catalogo": ("catalogo",), "busca": ("busca", "pesquisa"),
                 "produto": ("produto",), "carrinho": ("carrinho",), "frete": ("frete", "cep", "entrega", "transportadora"),
                 "pedido": ("pedido", "compra", "quantidade"), "pagamento": ("pagamento", "cartao", "cobranca"),
                 "relatorio": ("relatorio",), "exportacao": ("exporta",), "notas": ("nota", "fiscal"), "conta": ("conta", "cadastro", "telefone")}
ERRO = "respostas com erro no minuto"
LAT = "latência média em ms"


def _simples(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def rota_do_texto(texto):
    """A rota de que o texto fala: primeiro o nome exato de um processo ("rota frete", "chamados de frete"), depois palavras."""
    t = _simples(texto)
    for rota in ROTAS:
        if "rota " + _simples(NOME_ROTA[rota]) in t:
            return rota
    for rota, comp in ROTA_COMPONENTE.items():
        if _simples(NOME_COMPONENTE[comp]) in t:
            return rota
    for rota in ROTAS:
        for palavra in PALAVRAS_ROTA[rota]:
            if palavra in t:
                return rota
    return None


def _hora(abs_min):
    d, m = divmod(abs_min, MINUTOS_DIA)
    return f"dia {d}, {m // 60:02d}h{m % 60:02d}"


def _ch(comp):
    return f"chamados de {NOME_COMPONENTE[comp]}"


def _efeito(util=None, acoes=(), encurta=(), nao_encurta=(), colateral=()):
    return {"util": util, "acoes": list(acoes), "encurta": [list(x) for x in encurta], "nao_encurta": [list(x) for x in nao_encurta],
            "colateral": [list(x) for x in colateral]}


class Porta:
    def __init__(self, surdo=False):
        self.surdo = surdo
        self.numero = 0
        self.chegando = []
        self.atos = {}
        self.fila = {e: [] for e in EQUIPES}
        self.saida = []
        self.ouvinte = None                     # (v2.2) posto pelo Mundo

    # ---------- o lado de fora ----------
    def receber(self, equipe, tipo, texto):
        if equipe not in EQUIPES:
            raise ValueError(f"equipe desconhecida: {equipe}; as equipes são {', '.join(EQUIPES)}")
        if tipo not in TIPOS:
            raise ValueError(f"tipo desconhecido: {tipo}; os tipos são {', '.join(TIPOS)}")
        self.numero += 1
        if not self.surdo:
            self.chegando.append((self.numero, equipe, tipo, str(texto)))
        return self.numero

    def respostas(self):
        saida, self.saida = self.saida, []
        return saida

    # ---------- o ato vira coisa dentro do mundo ----------
    def materializar(self, t, cal, sis, equipes):
        if not self.chegando:
            return
        chegando, self.chegando = self.chegando, []
        fluxo = sis["fluxo"]
        for numero, equipe, tipo, texto in chegando:
            rota = rota_do_texto(texto)
            comp = ROTA_COMPONENTE[rota] if rota else None
            # (v2.2) o que a equipe entende do texto inteiro; a rota é a de sempre
            ultima = sis["repo"].db.execute("SELECT t FROM implantacoes ORDER BY id DESC LIMIT 1").fetchone()
            entendido = self.ouvinte.entender(texto, equipe, t, rota, comp, ultima[0] if ultima else None)
            comp = entendido["componente"]
            reconhece = entendido.pop("reconhece")
            esclarecer = tipo == "pedido" and not reconhece
            titulo = texto[:120]
            if equipe == "atendimento":
                item = fluxo.criar(t, "SUP", "chamado", titulo, prioridade="média", componente=comp, equipe=equipe, ator="porta",
                                   canal="interno", origem="porta", protocolo=numero)
                sistema = "fluxo"
            elif equipe == "vendas":
                item = sis["crm"].nova_tarefa(t, titulo, numero)
                sistema = "crm"
            elif equipe == "gestão":
                item = sis["quadro"].solicitar(t, "pedido interno", titulo, protocolo=numero)
                sistema = "quadro"
            else:
                projeto = "INFRA" if equipe == "operação" else ("PLAT" if comp and COMPONENTE_PROJETO.get(comp) == "PLAT" else "PROD")
                item = fluxo.criar(t, projeto, "tarefa", titulo, prioridade="média", componente=comp or ("infra" if projeto == "INFRA" else None),
                                   equipe=equipe, ator="porta", origem="porta", protocolo=numero)
                sistema = "fluxo"
            # o prazo: o fim do expediente do dia útil seguinte
            d = cal.data + 1
            while d % 7 >= 5:
                d += 1
            prazo = t + (d * MINUTOS_DIA + 18 * 60 - cal.absoluto)
            eq = equipes[equipe]
            atraso = eq.atraso(tipo)
            self.atos[numero] = {"numero": numero, "equipe": equipe, "tipo": tipo, "texto": texto, "rota": rota, "componente": comp,
                                 "sistema": sistema, "item": item, "criado": t, "disponivel": t + int(round(atraso)), "prazo": prazo,
                                 "estado": "aberto", "entendido": entendido, "esclarecer": esclarecer}
            if tipo == "pedido":
                k = 0
                while k < len(self.fila[equipe]) and self.atos[self.fila[equipe][k]]["tipo"] == "pedido":
                    k += 1
                self.fila[equipe].insert(k, numero)               # o pedido passa à frente das perguntas
            else:
                self.fila[equipe].append(numero)
            sis["verdade"].ato(t, numero, equipe, tipo, texto, rota, comp, sistema, item, int(round(atraso)), eq.estado(), entendido, esclarecer)

    def abertos(self):
        """(v2.2) Se há algum ato que chegou e ainda não foi respondido nem expirou."""
        return any(a["estado"] in ("aberto", "em tratamento") for a in self.atos.values())

    def descartar_abertos(self, t, sis):
        """(v2.2) Só no ramo sem ato: os atos abertos saem sem tratamento (o item que viraram é descartado)."""
        for numero, ato in self.atos.items():
            if ato["estado"] in ("aberto", "em tratamento"):
                ato["estado"] = "sem resposta"
                self._fechar(t, ato, sis, "descartado")
                if numero in self.fila[ato["equipe"]]:
                    self.fila[ato["equipe"]].remove(numero)

    def disponivel(self, equipe, t, tipo=None):
        for numero in self.fila[equipe]:
            ato = self.atos[numero]
            if ato["estado"] == "aberto" and ato["disponivel"] <= t and (tipo is None or ato["tipo"] == tipo):
                return ato
        return None

    def proximo(self, equipe, t, tipo=None):
        ato = self.disponivel(equipe, t, tipo)
        if ato is not None:
            self.fila[equipe].remove(ato["numero"])
            ato["estado"] = "em tratamento"
            ato["pego"] = t
        return ato

    def expirar(self, t, sis):
        for numero, ato in self.atos.items():
            if ato["estado"] in ("aberto", "em tratamento") and t >= ato["prazo"]:
                ato["estado"] = "sem resposta"
                self._fechar(t, ato, sis, "descartado")
                if numero in self.fila[ato["equipe"]]:
                    self.fila[ato["equipe"]].remove(numero)
                sis["verdade"].ato_sem_resposta(t, numero)

    def podar(self, t):
        """Os atos fechados há mais de uma semana saem da memória (já estão na verdade)."""
        for numero in [n for n, a in self.atos.items() if a["estado"] in ("respondido", "sem resposta") and t - a.get("fim", t) > 7 * MINUTOS_DIA]:
            del self.atos[numero]

    def _fechar(self, t, ato, sis, como):
        ato["fim"] = t
        if ato["sistema"] == "fluxo":
            r = sis["fluxo"].item(ato["item"])
            if r is None:
                return
            if r["tipo"] == "chamado":
                if como == "descartado":
                    sis["fluxo"].transitar(t, ato["item"], "descartado", "atendimento")
                else:
                    sis["fluxo"].transitar(t, ato["item"], "resolvido", "atendimento")
                    sis["fluxo"].transitar(t, ato["item"], "fechado", "atendimento")
            else:
                sis["fluxo"].transitar(t, ato["item"], "descartado" if como == "descartado" else "concluído", ato["equipe"])
        elif ato["sistema"] == "crm":
            sis["crm"].fechar_tarefa(t, ato["item"], "descartada" if como == "descartado" else "concluída")
        else:
            sis["quadro"].concluir_solicitacao(t, ato["item"], "descartada" if como == "descartado" else "concluída")

    # ---------- alguém da equipe trata o ato ----------
    def tratar(self, numero, pessoa, t, cal, empresa, minutos, adiada):
        ato = self.atos.get(numero)
        if ato is None or ato["estado"] != "em tratamento":
            return
        sis = empresa.sis
        eq = empresa.equipes[ato["equipe"]]
        if ato["sistema"] == "fluxo":
            r = sis["fluxo"].item(ato["item"])
            if r is not None and r["tipo"] == "chamado":
                sis["fluxo"].transitar(t, ato["item"], "em atendimento", "atendimento")
            elif r is not None:
                sis["fluxo"].transitar(t, ato["item"], "em andamento", ato["equipe"])
            sis["fluxo"].comentar(t, ato["item"], ato["equipe"], "tratado")
        ent = ato.get("entendido") or {}
        da_equipe = getattr(self, "_" + {"produto": "produto", "desenvolvimento": "desenvolvimento", "qualidade": "qualidade",
                                         "atendimento": "atendimento", "vendas": "vendas", "operação": "operacao",
                                         "gestão": "gestao"}[ato["equipe"]])
        olhar = ato["tipo"] == "pergunta" or (ato["tipo"] == "pedido" and ent.get("tipo") == "olhar e dizer")
        if ato["tipo"] == "convocacao":
            texto, efeito = self._convocar(ato, pessoa, t, cal, empresa)
        elif ato["tipo"] == "pedido" and ato.get("esclarecer"):
            # (v2.2) a equipe não reconhece nada no texto: pergunta de volta em vez de ler o painel
            texto, efeito = ("Pedido não entendido: não sabemos de que parte se trata. Qual rota, qual processo, qual campo? Mandem de "
                             "novo com o nome que aparece no painel."), _efeito(None, ["pediu esclarecimento"])
        elif ato["tipo"] == "pedido" and olhar:
            # (v2.2) pedido de olhar e dizer: a equipe olha e conta, sem agir
            texto, efeito = da_equipe(dict(ato, tipo="pergunta"), pessoa, t, cal, empresa, eq)
            efeito["util"] = None
        else:
            texto, efeito = da_equipe(ato, pessoa, t, cal, empresa, eq)
        if olhar and not ato.get("esclarecer"):
            leitura = self._leitura(sis, ent, t)
            if leitura:
                texto += " " + leitura
                efeito["acoes"].append(f"olhou o painel de {ent['processo']}" + (f", {ent['campo']}" if ent.get("campo") else ""))
        if ato["tipo"] == "pedido":
            if not ato.get("esclarecer"):
                texto = "Pedido tratado. " + texto
            efeito["colateral"].append([f"quadro da equipe de {ato['equipe']}", "horas extras no dia"])
        antes, depois = eq.tratado(t, ato["tipo"], efeito["util"] if ato["tipo"] == "pedido" else None)
        ato["estado"] = "respondido"
        self._fechar(t, ato, sis, "concluído")
        self.saida.append((t, numero, ato["equipe"], texto))
        sis["verdade"].ato_tratado(t, numero, ato["pego"], minutos, adiada, efeito, antes, depois, eq.estado(), texto)

    def _leitura(self, sis, ent, t):
        """(v2.2) O que o painel mostrou no processo e no campo entendidos, desde o instante entendido (ou na última hora)."""
        painel = sis.get("painel")
        proc = ent.get("processo")
        if painel is None or proc is None:
            return ""
        campos = [ent["campo"]] if ent.get("campo") else [c for p, cs in painel.nomes if p == proc for c in cs][:6]
        partes = []
        desde_de_fato = None
        for c in campos:
            r = painel.ler(proc, c, ent.get("desde"), t)
            if r is None:
                continue
            media, maximo, agora, n, desde_de_fato = r
            partes.append(f"{c}: média de {_num(media)}, máximo de {_num(maximo)}, agora {_num(agora)}")
        if not partes:
            return ""
        return f"No painel de {proc}, desde {quando(desde_de_fato)}: " + "; ".join(partes) + "."

    # ---------- o que cada equipe olha e faz ----------
    def _rota_agora(self, sis, rota, minutos=30):
        prod = sis["produto"]
        req, err = prod.erros_na_janela(rota, minutos)
        lat = prod.latencia_na_janela(rota, minutos)
        return req, err, lat

    def _versao(self, sis):
        repo = sis["repo"]
        r = repo.db.execute("SELECT t FROM implantacoes ORDER BY id DESC LIMIT 1").fetchone()
        quando = f", no ar há {(sis['relogio'].t - r[0]) // 60} h" if r else ""
        return f"versão {repo.no_ar}{quando}"

    def _operacao(self, ato, pessoa, t, cal, empresa, eq):
        sis = empresa.sis
        prod = sis["produto"]
        livre = 100.0 * max(0, prod.volume_paginas - prod.paginas_ocupadas()) / max(1, prod.volume_paginas)
        base = f"{self._versao(sis)}; volume do banco com {livre:.0f}% livre; fila de trabalhos com {prod.fila_pendentes}."
        rota = ato["rota"]
        infra = [["projeto Infraestrutura: itens", "em andamento"]]
        if rota is None:
            erros = sum(prod.erros_na_janela(r, 30)[1] for r in ROTAS)
            texto = f"Visão geral: {base} {erros} respostas com erro em todas as rotas na última meia hora."
            if ato["tipo"] == "pedido":
                texto += " Sem rota indicada, não rodamos verificação."
            return texto, _efeito(False if ato["tipo"] == "pedido" else None, ["leu o painel"], colateral=infra)
        req, err, lat = self._rota_agora(sis, rota)
        texto = f"Rota {NOME_ROTA[rota]}: {req} requisições, {err} com erro e latência média de {lat:.0f} ms na última meia hora; {base}"
        if ato["tipo"] != "pedido":
            return texto, _efeito(None, ["leu o painel da rota"], colateral=infra)
        repo = sis["repo"]
        comp = ROTA_COMPONENTE[rota]
        cob = eq.cobertura()
        n, falhas = rodar_testes(repo.versoes[repo.no_ar], comp, pessoa.s_porta, cob, todos=cob >= 1.0)
        repo.registrar_testes(t, comp, "no ar", n, len(falhas), "operação")
        acoes = [f"rodou {n} testes de {NOME_COMPONENTE[comp]} na versão no ar (cobertura {cob:.2f})"]
        nao = [[_ch(comp), "abertos"], [_ch(comp), "escalados"]]
        if not falhas:
            return texto + f" Rodamos {n} testes de {NOME_COMPONENTE[comp]} contra a versão no ar: todos passam.", \
                _efeito(False, acoes, nao_encurta=[[f"rota {NOME_ROTA[rota]}", ERRO]] + nao, colateral=infra)
        nomes = "; ".join(sorted({nome for _, nome, _ in falhas}))
        funcoes = sorted({f for f, _, _ in falhas})
        ultima = repo.db.execute("SELECT t, tipo FROM implantacoes ORDER BY id DESC LIMIT 1").fetchone()
        anterior = repo.versoes.get(repo.anterior, {})
        veio_agora = ultima is not None and t - ultima[0] < 2 * MINUTOS_DIA and ultima[1] != "reversão" and \
            any(anterior.get(f) != repo.versoes[repo.no_ar].get(f) for f in funcoes)
        fluxo = sis["fluxo"]
        projeto = COMPONENTE_PROJETO.get(comp, "PROD")
        bug = fluxo.criar(t, "PLAT" if projeto == "INFRA" else projeto, "bug", f"falha verificada em {NOME_ROTA[rota]}",
                          prioridade="crítica", componente=comp, equipe="desenvolvimento", ator="operação", origem="monitoramento")
        fluxo.comentar(t, bug, "operação", "testes que falham: " + nomes)
        acoes.append(f"abriu o bug {fluxo.item(bug)['chave']} como crítico ({', '.join(funcoes)})")
        rotas_afetadas = [[f"rota {NOME_ROTA[r]}", ERRO] for r, c in ROTA_COMPONENTE.items() if c == comp]
        if veio_agora and empresa.reverter is None:
            empresa.reverter = repo.anterior
            empresa.reverter_por_ato = ato["numero"]
            pessoa.tarefa = {"tipo": "reverter", "resta": pessoa.s_porta.randint(8, 15), "urgente": True}
            acoes.append(f"reverteu para a versão {repo.anterior}")
            mudam = sorted({ROTA_COMPONENTE_DE_FUNCAO(f) for f, v in repo.versoes[repo.no_ar].items() if anterior.get(f) != v} - {None})
            colat = infra + [["implantação", "implantações no minuto"]] + [[f"rota {NOME_ROTA[r]}", LAT] for r in mudam]
            return texto + f" Na versão no ar falha: {nomes}. A falha veio com a última liberação; vamos voltar para a versão {repo.anterior} e abrimos a correção.", \
                _efeito(True, acoes, encurta=rotas_afetadas + [["sessões dos clientes", "sessões abandonadas depois de erro no minuto"]],
                        nao_encurta=nao, colateral=colat)
        return texto + f" Na versão no ar falha: {nomes}. Abrimos a correção com prioridade crítica.", \
            _efeito(True, acoes, encurta=rotas_afetadas, nao_encurta=nao,
                    colateral=infra + [[f"projeto {PROJETOS[COMPONENTE_PROJETO.get(comp, 'PROD') if COMPONENTE_PROJETO.get(comp) != 'INFRA' else 'PLAT']}: sprint", "pontos restantes"]])

    def _qualidade(self, ato, pessoa, t, cal, empresa, eq):
        sis = empresa.sis
        fluxo = sis["fluxo"]
        repo = sis["repo"]
        espera = fluxo.contar(tipo=None, estados=("em qualidade",))
        exec24 = repo.db.execute("SELECT COUNT(*), COALESCE(SUM(testes), 0), COALESCE(SUM(falhas), 0) FROM execucoes_teste WHERE t > ?",
                                 (t - MINUTOS_DIA,)).fetchone()
        texto = f"Na qualidade há {espera} itens esperando teste; nas últimas 24 h foram {exec24[0]} execuções, {exec24[1]} testes e {exec24[2]} falhas."
        comp = ato["componente"]
        fila_qa = [[f"projeto {PROJETOS[p]}: desenvolvimento", "em qualidade"] for p in ("PROD", "PLAT")]
        if ato["tipo"] != "pedido":
            return texto, _efeito(None, ["contou a fila de teste"], colateral=fila_qa)
        if comp is None:
            return texto + " Sem componente indicado, não refizemos testes.", _efeito(False, ["leu o painel"], colateral=fila_qa)
        cob = eq.cobertura()
        n, falhas = rodar_testes(repo.versoes[repo.no_ar], comp, pessoa.s_porta, cob, todos=cob >= 1.0)
        repo.registrar_testes(t, comp, "no ar", n, len(falhas), "qualidade")
        acoes = [f"refez {n} testes de {NOME_COMPONENTE[comp]} na versão no ar (cobertura {cob:.2f})"]
        if not falhas:
            return texto + f" Refizemos os {n} testes de {NOME_COMPONENTE[comp]} na versão no ar: passam.", \
                _efeito(False, acoes, nao_encurta=[[_ch(comp), "abertos"]], colateral=fila_qa)
        reabertos = []
        for funcao in sorted({f for f, _, _ in falhas}):
            origem = repo.autoria.get(funcao)
            bug = fluxo.criar(t, COMPONENTE_PROJETO.get(comp, "PROD") if COMPONENTE_PROJETO.get(comp) != "INFRA" else "PLAT", "bug",
                              f"teste refeito falha em {NOME_COMPONENTE[comp]}", prioridade="alta", componente=comp,
                              equipe="desenvolvimento", ator="qualidade", origem="qualidade")
            acoes.append(f"abriu o bug {fluxo.item(bug)['chave']} ({funcao})")
            if origem is not None:
                o = fluxo.item(origem)
                fluxo.ligar(t, bug, origem, "causado por")
                if o is not None and o["estado"] == "liberado" and o["tipo"] in ("história", "tarefa") and \
                        repo.principal.get(funcao) == repo.versoes[repo.no_ar].get(funcao):
                    fluxo.transitar(t, origem, "em desenvolvimento" if o["tipo"] != "tarefa" else "em andamento", "qualidade")
                    reabertos.append(o["chave"])
                    acoes.append(f"reabriu {o['chave']}")
        nomes = "; ".join(sorted({nome for _, nome, _ in falhas}))
        rotas_afetadas = [[f"rota {NOME_ROTA[r]}", ERRO] for r, c in ROTA_COMPONENTE.items() if c == comp]
        return texto + f" Refizemos os testes de {NOME_COMPONENTE[comp]} na versão no ar e falha: {nomes}." + \
            (f" Reabrimos {', '.join(reabertos)}." if reabertos else " Abrimos um bug."), \
            _efeito(True, acoes, encurta=rotas_afetadas, nao_encurta=[[_ch(comp), "abertos"]], colateral=fila_qa)

    def _desenvolvimento(self, ato, pessoa, t, cal, empresa, eq):
        sis = empresa.sis
        fluxo = sis["fluxo"]
        comp = ato["componente"]
        emdev = fluxo.contar(estados=("em desenvolvimento", "em andamento"))
        emrev = fluxo.contar(estados=("em revisão",))
        texto = f"No desenvolvimento há {emdev} itens em andamento e {emrev} em revisão."
        sprint = [[f"projeto {PROJETOS[p]}: sprint", "pontos restantes"] for p in ("PROD", "PLAT")]
        if comp is None:
            return texto, _efeito(False if ato["tipo"] == "pedido" else None, ["contou o trabalho em andamento"], colateral=sprint)
        bugs = fluxo.db.execute("SELECT id, chave, prioridade FROM itens WHERE tipo='bug' AND componente=? AND estado NOT IN "
                                "('liberado', 'não reproduzido') ORDER BY id", (comp,)).fetchall()
        texto += f" Bugs abertos em {NOME_COMPONENTE[comp]}: {len(bugs)}."
        if ato["tipo"] != "pedido":
            return texto, _efeito(None, ["contou os bugs do componente"], colateral=sprint)
        rotas_afetadas = [[f"rota {NOME_ROTA[r]}", ERRO] for r, c in ROTA_COMPONENTE.items() if c == comp]
        if bugs:
            alvo = bugs[-1]
            if alvo["prioridade"] != "crítica":
                fluxo.priorizar(alvo["id"], "crítica")
            return texto + f" Passamos o {alvo['chave']} para prioridade crítica; quem estiver livre pega agora.", \
                _efeito(True, [f"passou {alvo['chave']} para crítico"], encurta=[[f"bugs de {NOME_COMPONENTE[comp]}", "abertos"]] + rotas_afetadas,
                        nao_encurta=[[_ch(comp), "abertos"]], colateral=sprint)
        repo = sis["repo"]
        cob = eq.cobertura()
        n, falhas = rodar_testes(repo.versoes[repo.no_ar], comp, pessoa.s_porta, cob, todos=cob >= 1.0)
        repo.registrar_testes(t, comp, "no ar", n, len(falhas), "desenvolvimento")
        acoes = [f"rodou {n} testes do componente na versão no ar (cobertura {cob:.2f})"]
        if not falhas:
            return texto + f" Rodamos os {n} testes do componente na versão no ar: passam.", \
                _efeito(False, acoes, nao_encurta=rotas_afetadas, colateral=sprint)
        bug = fluxo.criar(t, COMPONENTE_PROJETO.get(comp, "PROD") if COMPONENTE_PROJETO.get(comp) != "INFRA" else "PLAT", "bug",
                          f"falha encontrada em {NOME_COMPONENTE[comp]}", prioridade="crítica", componente=comp,
                          equipe="desenvolvimento", ator="desenvolvimento", origem="monitoramento")
        acoes.append(f"abriu o bug {fluxo.item(bug)['chave']} como crítico")
        return texto + f" Na versão no ar falha: {'; '.join(sorted({nm for _, nm, _ in falhas}))}. Abrimos {fluxo.item(bug)['chave']} como crítico.", \
            _efeito(True, acoes, encurta=rotas_afetadas, nao_encurta=[[_ch(comp), "abertos"]], colateral=sprint)

    def _atendimento(self, ato, pessoa, t, cal, empresa, eq):
        fluxo = empresa.sis["fluxo"]
        abertos = fluxo.contar("SUP", "chamado", ("aberto", "em atendimento", "aguardando cliente", "escalado"))
        sem = fluxo.contar("SUP", "chamado", ("aberto",))
        texto = f"No atendimento há {abertos} chamados abertos, {sem} ainda sem primeira resposta."
        comp = ato["componente"]
        prazos = [["projeto Suporte: prazos", "chamados fora do prazo de primeira resposta"],
                  ["projeto Suporte: prazos", "espera do chamado mais antigo sem resposta em minutos"]]
        if comp is None:
            return texto, _efeito(False if ato["tipo"] == "pedido" else None, ["contou a fila"], colateral=prazos[:1])
        n = fluxo.contar("SUP", "chamado", ("aberto", "em atendimento", "aguardando cliente", "escalado"), componente=comp)
        esc = fluxo.contar("SUP", "chamado", ("escalado",), componente=comp)
        texto += f" De {NOME_COMPONENTE[comp]}: {n} abertos, {esc} escalados."
        if ato["tipo"] != "pedido":
            return texto, _efeito(None, ["contou os chamados do componente"], colateral=prazos[:1])
        empresa.foco_atendimento = (comp, t + 240)
        texto += f" Nas próximas quatro horas respondemos primeiro os de {NOME_COMPONENTE[comp]}."
        util = (n - esc) >= 3
        return texto, _efeito(util, [f"passou os chamados de {NOME_COMPONENTE[comp]} para a frente da fila até {t + 240}"],
                              encurta=[[_ch(comp), "abertos"]] if util else [],
                              nao_encurta=[[_ch(comp), "escalados"], [f"bugs de {NOME_COMPONENTE[comp]}", "abertos"]] + ([] if util else [[_ch(comp), "abertos"]]),
                              colateral=prazos)

    def _vendas(self, ato, pessoa, t, cal, empresa, eq):
        crm = empresa.sis["crm"]
        n = {e: crm.em_estagio(e) for e in ("lead", "qualificação", "proposta", "negociação")}
        ganhos = crm.db.execute("SELECT COUNT(*) FROM negocios WHERE estagio='ganho' AND fechado_em > ?", (t - 7 * MINUTOS_DIA,)).fetchone()[0]
        texto = (f"No funil: {n['lead']} leads, {n['qualificação']} em qualificação, {n['proposta']} propostas e {n['negociação']} em "
                 f"negociação; {ganhos} negócios ganhos nos últimos sete dias.")
        if ato["tipo"] != "pedido":
            return texto, _efeito(None, ["contou o funil"], colateral=[["atividades de vendas", "ligações no minuto"]])
        empresa.foco_vendas = t + 2 * MINUTOS_DIA
        texto += " Nos próximos dois dias a equipe retoma primeiro as propostas e negociações paradas."
        util = n["proposta"] + n["negociação"] >= 4
        return texto, _efeito(util, [f"retomar propostas e negociações até {t + 2 * MINUTOS_DIA}"],
                              encurta=[["funil de vendas", "em negociação"], ["funil de vendas", "propostas"]] if util else [],
                              nao_encurta=[["funil de vendas", "leads"]], colateral=[["leads de prospecção", "novos no minuto"]])

    def _produto(self, ato, pessoa, t, cal, empresa, eq):
        fluxo = empresa.sis["fluxo"]
        backlog = fluxo.contar(tipo="história", estados=("backlog", "refinamento"))
        prontos = fluxo.contar(tipo="história", estados=("pronto para desenvolver",))
        texto = f"No produto há {backlog} histórias no backlog e em refinamento e {prontos} prontas para desenvolver."
        if ato["tipo"] != "pedido":
            return texto, _efeito(None, ["contou o backlog"])
        comp = ato["componente"]
        projeto = COMPONENTE_PROJETO.get(comp, "PROD") if comp else "PROD"
        projeto = "PLAT" if projeto == "INFRA" else projeto
        h = fluxo.criar(t, projeto, "história", ato["texto"][:120], prioridade="alta", componente=comp, equipe="desenvolvimento",
                        ator="produto", pontos=3)
        texto += f" Registramos a história {fluxo.item(h)['chave']} com prioridade alta."
        util = comp is not None and fluxo.contar("SUP", "chamado", ("aberto", "em atendimento", "aguardando cliente", "escalado"), componente=comp) >= 3
        return texto, _efeito(util, [f"registrou a história {fluxo.item(h)['chave']}"],
                              nao_encurta=[[_ch(comp), "abertos"]] if comp else [],
                              colateral=[[f"projeto {PROJETOS[projeto]}: entrada", "histórias no backlog"], [f"projeto {PROJETOS[projeto]}: sprint", "pontos restantes"]])

    def _gestao(self, ato, pessoa, t, cal, empresa, eq):
        sis = empresa.sis
        ativos = [p for p in empresa.pessoas if p.ativo]
        presentes = sum(1 for p in ativos if p.presente)
        ferias = sum(1 for p in ativos if p.ausente == "férias")
        vagas, cand = sis["quadro"].contagem_vagas()
        texto = (f"Somos {len(ativos)} pessoas; {presentes} trabalhando agora, {ferias} de férias hoje; {vagas} vagas abertas com "
                 f"{cand} candidatos; {sis['clientes'].ativos()} clientes ativos.")
        if ato["tipo"] != "pedido":
            return texto, _efeito(None, ["leu o quadro"])
        lideres = [p.id for p in ativos if p.papel in ("dono", "líder técnico", "coordenador de atendimento", "líder de produto",
                                                       "gerente de vendas")]
        ini = sis["agenda"].primeiro_horario_livre(lideres, cal.absoluto, 45)
        acoes = []
        if ini is not None:
            sis["agenda"].marcar(t, "alinhamento", "gestão", ini, 45, lideres, ato["texto"][:80], origem="porta", protocolo=ato["numero"])
            texto += f" A direção marcou um alinhamento com as lideranças para {_hora(ini)}."
            acoes.append(f"marcou alinhamento das lideranças para {_hora(ini)}")
        util = empresa.escalacoes_dia >= 5 or empresa.incidente is not None
        return texto, _efeito(util, acoes, colateral=[["reuniões do tipo alinhamento", "pessoas"], ["agenda da equipe de gestão", "pessoas em reunião"]])

    def _convocar(self, ato, pessoa, t, cal, empresa):
        sis = empresa.sis
        membros = [p.id for p in empresa.pessoas if p.ativo and p.equipe == ato["equipe"]]
        ini = sis["agenda"].primeiro_horario_livre(membros, cal.absoluto, 30)
        if ini is None:
            membros = [p.id for p in empresa.pessoas if p.ativo and p.equipe == ato["equipe"] and p.ausente is None][:6]
            ini = sis["agenda"].primeiro_horario_livre(membros, cal.absoluto, 30)
        if ini is None:
            return "Não achamos horário livre para todos nos próximos dias; tente de novo.", _efeito(None, ["procurou horário e não achou"])
        sis["agenda"].marcar(t, "alinhamento", ato["equipe"], ini, 30, membros, ato["texto"][:80], origem="porta", protocolo=ato["numero"])
        return f"Reunião marcada para {_hora(ini)}, 30 minutos, com {len(membros)} pessoas da equipe de {ato['equipe']}.", \
            _efeito(None, [f"marcou reunião para {_hora(ini)} com {len(membros)} pessoas"],
                    colateral=[[f"agenda da equipe de {ato['equipe']}", "pessoas em reunião"], ["reuniões do tipo alinhamento", "em curso"]])


def _num(x):
    return f"{x:.0f}" if abs(x - round(x)) < 0.05 or abs(x) >= 100 else f"{x:.1f}"


def ROTA_COMPONENTE_DE_FUNCAO(funcao):
    """A rota cuja latência muda quando a implementação de uma função muda (a primeira rota do componente da função)."""
    from .codigo import COMPONENTE_FUNCAO
    from .verdade import ROTAS_FUNCOES
    for rota, fs in ROTAS_FUNCOES.items():
        if funcao in fs and rota in ROTA_COMPONENTE:
            return rota
    return None
