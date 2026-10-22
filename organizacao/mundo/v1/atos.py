"""A porta por onde o mundo recebe atos de quem o observa (contrato v1.1). Um ato é uma pergunta, um pedido ou uma convocação para
uma equipe. No passo seguinte ele vira coisa dentro da empresa: um item no fluxo de trabalho (produto, desenvolvimento, qualidade,
operação), um chamado no atendimento, uma tarefa no CRM de vendas, uma solicitação à gestão. Dentro do mundo a origem desses itens se
chama "porta"; fora disso são itens como os outros e entram nas mesmas filas e contagens.

Alguém da equipe pega o item na ordem da fila, entre uma tarefa e outra, dentro do horário e fora de reunião, e gasta o seu tempo
nele. A resposta é um texto curto montado com o que os sistemas da equipe mostram naquele momento. O pedido faz a equipe agir: a
operação roda os testes da rota contra a versão no ar e, se algo falha, reverte ou abre a correção; a qualidade reabre o teste; o
atendimento passa os chamados do componente para a frente da fila; e assim por diante. A convocação vira uma reunião no primeiro
horário livre da equipe. O que não for tratado até o fim do dia útil seguinte fica sem resposta."""
import unicodedata

from .cadastro import EQUIPES, ROTAS, NOME_ROTA, ROTA_COMPONENTE, NOME_COMPONENTE, COMPONENTE_PROJETO, MINUTOS_DIA
from .produto import rodar_testes

TIPOS = ("pergunta", "pedido", "convocacao")
CUSTO = ("pergunta", "pedido", "convocacao")   # (contrato v1.2) a ordem de custo dos atos para a empresa, do mais barato ao mais caro: a pergunta só gasta tempo de
                                               # uma pessoa; o pedido faz a equipe agir; a convocação tira várias pessoas para uma reunião. Ordem, não peso; só desempate.
PALAVRAS_ROTA = {"login": ("login", "entrar", "acesso", "senha"), "catalogo": ("catalogo",), "busca": ("busca", "pesquisa"),
                 "produto": ("produto",), "carrinho": ("carrinho",), "frete": ("frete", "cep", "entrega", "transportadora"),
                 "pedido": ("pedido", "compra", "quantidade"), "pagamento": ("pagamento", "cartao", "cobranca"),
                 "relatorio": ("relatorio",), "exportacao": ("exporta",), "notas": ("nota", "fiscal"), "conta": ("conta", "cadastro", "telefone")}


def _simples(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def rota_do_texto(texto):
    t = _simples(texto)
    for rota in ROTAS:
        for palavra in PALAVRAS_ROTA[rota]:
            if palavra in t:
                return rota
    return None


def _hora(abs_min):
    d, m = divmod(abs_min, MINUTOS_DIA)
    return f"dia {d}, {m // 60:02d}h{m % 60:02d}"


class Porta:
    def __init__(self, surdo=False):
        self.surdo = surdo
        self.numero = 0
        self.chegando = []
        self.atos = {}
        self.fila = {e: [] for e in EQUIPES}
        self.saida = []

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
    def materializar(self, t, cal, sis):
        if not self.chegando:
            return
        chegando, self.chegando = self.chegando, []
        fluxo = sis["fluxo"]
        for numero, equipe, tipo, texto in chegando:
            rota = rota_do_texto(texto)
            comp = ROTA_COMPONENTE[rota] if rota else None
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
            self.atos[numero] = {"numero": numero, "equipe": equipe, "tipo": tipo, "texto": texto, "rota": rota, "componente": comp,
                                 "sistema": sistema, "item": item, "criado": t, "prazo": prazo, "estado": "aberto"}
            self.fila[equipe].append(numero)
            sis["verdade"].ato(t, numero, equipe, tipo)

    def proximo(self, equipe, t):
        fila = self.fila[equipe]
        while fila:
            numero = fila.pop(0)
            ato = self.atos[numero]
            if ato["estado"] == "aberto":
                ato["estado"] = "em tratamento"
                return ato
        return None

    def expirar(self, t, sis):
        for numero, ato in self.atos.items():
            if ato["estado"] in ("aberto", "em tratamento") and t >= ato["prazo"]:
                ato["estado"] = "sem resposta"
                self._fechar(t, ato, sis, "descartado")
                if numero in self.fila[ato["equipe"]]:
                    self.fila[ato["equipe"]].remove(numero)

    def _fechar(self, t, ato, sis, como):
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
    def tratar(self, numero, pessoa, t, cal, empresa):
        ato = self.atos.get(numero)
        if ato is None or ato["estado"] != "em tratamento":
            return
        sis = empresa.sis
        if ato["sistema"] == "fluxo":
            r = sis["fluxo"].item(ato["item"])
            if r is not None and r["tipo"] == "chamado":
                sis["fluxo"].transitar(t, ato["item"], "em atendimento", "atendimento")
            elif r is not None:
                sis["fluxo"].transitar(t, ato["item"], "em andamento", ato["equipe"])
            sis["fluxo"].comentar(t, ato["item"], ato["equipe"], "tratado")
        if ato["tipo"] == "convocacao":
            texto = self._convocar(ato, pessoa, t, cal, empresa)
        else:
            texto = getattr(self, "_" + {"produto": "produto", "desenvolvimento": "desenvolvimento", "qualidade": "qualidade",
                                         "atendimento": "atendimento", "vendas": "vendas", "operação": "operacao",
                                         "gestão": "gestao"}[ato["equipe"]])(ato, pessoa, t, cal, empresa)
        ato["estado"] = "respondido"
        self._fechar(t, ato, sis, "concluído")
        self.saida.append((t, numero, ato["equipe"], texto))
        sis["verdade"].ato_respondido(t, numero)

    # ---------- o que cada equipe olha ----------
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

    def _operacao(self, ato, pessoa, t, cal, empresa):
        sis = empresa.sis
        prod = sis["produto"]
        livre = 100.0 * max(0, prod.volume_paginas - prod.paginas_ocupadas()) / max(1, prod.volume_paginas)
        base = f"{self._versao(sis)}; volume do banco com {livre:.0f}% livre; fila de trabalhos com {prod.fila_pendentes}."
        rota = ato["rota"]
        if rota is None:
            erros = sum(prod.erros_na_janela(r, 30)[1] for r in ROTAS)
            texto = f"Visão geral: {base} {erros} respostas com erro em todas as rotas na última meia hora."
            if ato["tipo"] == "pedido":
                texto += " Sem rota indicada, não rodamos verificação."
            return texto
        req, err, lat = self._rota_agora(sis, rota)
        texto = f"Rota {NOME_ROTA[rota]}: {req} requisições, {err} com erro e latência média de {lat:.0f} ms na última meia hora; {base}"
        if ato["tipo"] != "pedido":
            return texto
        repo = sis["repo"]
        comp = ROTA_COMPONENTE[rota]
        n, falhas = rodar_testes(repo.versoes[repo.no_ar], comp, pessoa.s_porta, 1.0, todos=True)
        repo.registrar_testes(t, comp, "no ar", n, len(falhas), "operação")
        if not falhas:
            return texto + f" Rodamos {n} testes de {NOME_COMPONENTE[comp]} contra a versão no ar: todos passam."
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
        if veio_agora and empresa.reverter is None:
            empresa.reverter = repo.anterior
            pessoa.tarefa = {"tipo": "reverter", "resta": pessoa.s_porta.randint(8, 15), "urgente": True}
            return texto + f" Na versão no ar falha: {nomes}. A falha veio com a última liberação; vamos voltar para a versão {repo.anterior} e abrimos a correção."
        return texto + f" Na versão no ar falha: {nomes}. Abrimos a correção com prioridade crítica."

    def _qualidade(self, ato, pessoa, t, cal, empresa):
        sis = empresa.sis
        fluxo = sis["fluxo"]
        repo = sis["repo"]
        espera = fluxo.contar(tipo=None, estados=("em qualidade",))
        exec24 = repo.db.execute("SELECT COUNT(*), COALESCE(SUM(testes), 0), COALESCE(SUM(falhas), 0) FROM execucoes_teste WHERE t > ?",
                                 (t - MINUTOS_DIA,)).fetchone()
        texto = f"Na qualidade há {espera} itens esperando teste; nas últimas 24 h foram {exec24[0]} execuções, {exec24[1]} testes e {exec24[2]} falhas."
        comp = ato["componente"]
        if ato["tipo"] != "pedido" or comp is None:
            return texto
        n, falhas = rodar_testes(repo.versoes[repo.no_ar], comp, pessoa.s_porta, 1.0, todos=True)
        repo.registrar_testes(t, comp, "no ar", n, len(falhas), "qualidade")
        if not falhas:
            return texto + f" Refizemos os {n} testes de {NOME_COMPONENTE[comp]} na versão no ar: passam."
        reabertos = []
        for funcao in sorted({f for f, _, _ in falhas}):
            origem = repo.autoria.get(funcao)
            bug = fluxo.criar(t, COMPONENTE_PROJETO.get(comp, "PROD"), "bug", f"teste refeito falha em {NOME_COMPONENTE[comp]}",
                              prioridade="alta", componente=comp, equipe="desenvolvimento", ator="qualidade", origem="qualidade")
            if origem is not None:
                o = fluxo.item(origem)
                fluxo.ligar(t, bug, origem, "causado por")
                if o is not None and o["estado"] == "liberado" and o["tipo"] in ("história", "tarefa") and \
                        repo.principal.get(funcao) == repo.versoes[repo.no_ar].get(funcao):
                    fluxo.transitar(t, origem, "em desenvolvimento" if o["tipo"] != "tarefa" else "em andamento", "qualidade")
                    reabertos.append(o["chave"])
        nomes = "; ".join(sorted({nome for _, nome, _ in falhas}))
        return texto + f" Refizemos os testes de {NOME_COMPONENTE[comp]} na versão no ar e falha: {nomes}." + \
            (f" Reabrimos {', '.join(reabertos)}." if reabertos else " Abrimos um bug.")

    def _desenvolvimento(self, ato, pessoa, t, cal, empresa):
        sis = empresa.sis
        fluxo = sis["fluxo"]
        comp = ato["componente"]
        emdev = fluxo.contar(estados=("em desenvolvimento", "em andamento"))
        emrev = fluxo.contar(estados=("em revisão",))
        texto = f"No desenvolvimento há {emdev} itens em andamento e {emrev} em revisão."
        if comp is None:
            return texto
        bugs = fluxo.db.execute("SELECT id, chave, prioridade FROM itens WHERE tipo='bug' AND componente=? AND estado NOT IN "
                                "('liberado', 'não reproduzido') ORDER BY id", (comp,)).fetchall()
        texto += f" Bugs abertos em {NOME_COMPONENTE[comp]}: {len(bugs)}."
        if ato["tipo"] != "pedido":
            return texto
        if bugs:
            alvo = bugs[-1]
            if alvo["prioridade"] != "crítica":
                fluxo.priorizar(alvo["id"], "crítica")
            return texto + f" Passamos o {alvo['chave']} para prioridade crítica; quem estiver livre pega agora."
        repo = sis["repo"]
        n, falhas = rodar_testes(repo.versoes[repo.no_ar], comp, pessoa.s_porta, 1.0, todos=True)
        repo.registrar_testes(t, comp, "no ar", n, len(falhas), "desenvolvimento")
        if not falhas:
            return texto + f" Rodamos os {n} testes do componente na versão no ar: passam."
        bug = fluxo.criar(t, COMPONENTE_PROJETO.get(comp, "PROD"), "bug", f"falha encontrada em {NOME_COMPONENTE[comp]}",
                          prioridade="crítica", componente=comp, equipe="desenvolvimento", ator="desenvolvimento", origem="monitoramento")
        return texto + f" Na versão no ar falha: {'; '.join(sorted({nm for _, nm, _ in falhas}))}. Abrimos {fluxo.item(bug)['chave']} como crítico."

    def _atendimento(self, ato, pessoa, t, cal, empresa):
        fluxo = empresa.sis["fluxo"]
        abertos = fluxo.contar("SUP", "chamado", ("aberto", "em atendimento", "aguardando cliente", "escalado"))
        sem = fluxo.contar("SUP", "chamado", ("aberto",))
        texto = f"No atendimento há {abertos} chamados abertos, {sem} ainda sem primeira resposta."
        comp = ato["componente"]
        if comp is not None:
            n = fluxo.contar("SUP", "chamado", ("aberto", "em atendimento", "aguardando cliente", "escalado"), componente=comp)
            esc = fluxo.contar("SUP", "chamado", ("escalado",), componente=comp)
            texto += f" De {NOME_COMPONENTE[comp]}: {n} abertos, {esc} escalados."
            if ato["tipo"] == "pedido":
                empresa.foco_atendimento = (comp, t + 240)
                texto += f" Nas próximas quatro horas respondemos primeiro os de {NOME_COMPONENTE[comp]}."
        return texto

    def _vendas(self, ato, pessoa, t, cal, empresa):
        crm = empresa.sis["crm"]
        n = {e: crm.em_estagio(e) for e in ("lead", "qualificação", "proposta", "negociação")}
        ganhos = crm.db.execute("SELECT COUNT(*) FROM negocios WHERE estagio='ganho' AND fechado_em > ?", (t - 7 * MINUTOS_DIA,)).fetchone()[0]
        texto = (f"No funil: {n['lead']} leads, {n['qualificação']} em qualificação, {n['proposta']} propostas e {n['negociação']} em "
                 f"negociação; {ganhos} negócios ganhos nos últimos sete dias.")
        if ato["tipo"] == "pedido":
            empresa.foco_vendas = t + 2 * MINUTOS_DIA
            texto += " Nos próximos dois dias a equipe retoma primeiro as propostas e negociações paradas."
        return texto

    def _produto(self, ato, pessoa, t, cal, empresa):
        fluxo = empresa.sis["fluxo"]
        backlog = fluxo.contar(tipo="história", estados=("backlog", "refinamento"))
        prontos = fluxo.contar(tipo="história", estados=("pronto para desenvolver",))
        texto = f"No produto há {backlog} histórias no backlog e em refinamento e {prontos} prontas para desenvolver."
        if ato["tipo"] == "pedido":
            comp = ato["componente"]
            projeto = COMPONENTE_PROJETO.get(comp, "PROD") if comp else "PROD"
            projeto = "PLAT" if projeto == "INFRA" else projeto
            h = fluxo.criar(t, projeto, "história", ato["texto"][:120], prioridade="alta", componente=comp, equipe="desenvolvimento",
                            ator="produto", pontos=3)
            texto += f" Registramos a história {fluxo.item(h)['chave']} com prioridade alta."
        return texto

    def _gestao(self, ato, pessoa, t, cal, empresa):
        sis = empresa.sis
        ativos = [p for p in empresa.pessoas if p.ativo]
        presentes = sum(1 for p in ativos if p.presente)
        ferias = sum(1 for p in ativos if p.ausente == "férias")
        vagas, cand = sis["quadro"].contagem_vagas()
        texto = (f"Somos {len(ativos)} pessoas; {presentes} trabalhando agora, {ferias} de férias hoje; {vagas} vagas abertas com "
                 f"{cand} candidatos; {sis['clientes'].ativos()} clientes ativos.")
        if ato["tipo"] == "pedido":
            lideres = [p.id for p in ativos if p.papel in ("dono", "líder técnico", "coordenador de atendimento", "líder de produto",
                                                           "gerente de vendas")]
            ini = sis["agenda"].primeiro_horario_livre(lideres, cal.absoluto, 45)
            if ini is not None:
                sis["agenda"].marcar(t, "alinhamento", "gestão", ini, 45, lideres, ato["texto"][:80], origem="porta", protocolo=ato["numero"])
                texto += f" A direção marcou um alinhamento com as lideranças para {_hora(ini)}."
        return texto

    def _convocar(self, ato, pessoa, t, cal, empresa):
        sis = empresa.sis
        membros = [p.id for p in empresa.pessoas if p.ativo and p.equipe == ato["equipe"]]
        ini = sis["agenda"].primeiro_horario_livre(membros, cal.absoluto, 30)
        if ini is None:
            membros = [p.id for p in empresa.pessoas if p.ativo and p.equipe == ato["equipe"] and p.ausente is None][:6]
            ini = sis["agenda"].primeiro_horario_livre(membros, cal.absoluto, 30)
        if ini is None:
            return "Não achamos horário livre para todos nos próximos dias; tente de novo."
        sis["agenda"].marcar(t, "alinhamento", ato["equipe"], ini, 30, membros, ato["texto"][:80], origem="porta", protocolo=ato["numero"])
        return f"Reunião marcada para {_hora(ini)}, 30 minutos, com {len(membros)} pessoas da equipe de {ato['equipe']}."
