"""Testes do mundo v2 (sem observador): o contrato da porta, o determinismo e a retomada, os ramos, o nulo surdo, a consequência dos
atos (equipes com fila, cansaço, atenção e confiança), o disco cheio que não derruba o mundo, a deriva que assenta, a campanha e a
verdade por minuto em disco.

    python -m unittest organizacao.mundo.v2.test_mundo_v2        (da raiz do repositório)
    python organizacao/mundo/v2/test_mundo_v2.py
"""
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
import unittest

import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
    from organizacao.mundo.v2.mundo import Mundo
    from organizacao.mundo.v2.equipes import Equipe
    from organizacao.mundo.v2.cadastro import EQUIPES, MINUTOS_DIA
else:
    from .mundo import Mundo
    from .equipes import Equipe
    from .cadastro import EQUIPES, MINUTOS_DIA

D = MINUTOS_DIA
TMP = tempfile.TemporaryDirectory(prefix="teste_mundo_v2_")


def pasta(nome):
    p = os.path.join(TMP.name, nome)
    os.makedirs(p, exist_ok=True)
    return p


def novo(semente, nulo=None, nome=None):
    return Mundo(semente, nulo, historia=pasta(nome or f"h_{semente}_{nulo}_{len(os.listdir(TMP.name))}"))


def viver(m, ate, atos=None, campanhas=None):
    """Anda até o minuto `ate`; devolve (assinatura dos minutos, respostas). atos: {minuto: [(equipe, tipo, texto)]}."""
    h = hashlib.sha256()
    resp = []
    atos = atos or {}
    while m.t < ate:
        for a in atos.get(m.t + 1, ()):
            m.receber(*a)
        v = m.passo()
        h.update(json.dumps(v, sort_keys=True, ensure_ascii=False).encode())
        resp.extend(m.respostas())
    return h.hexdigest(), resp


def ler(caminho):
    with open(caminho, "rb") as f:
        return f.read()


def verdade_sem_pasta(m):
    v = m.verdade()
    v["verdade_por_minuto"].pop("pasta")
    return json.dumps(v, sort_keys=True, ensure_ascii=False)


ATOS = {D + 600: [("operação", "pedido", "verifiquem a rota pagamento"), ("atendimento", "pergunta", "como estão os chamados de frete?")],
        D + 660: [("desenvolvimento", "pedido", "olhem o catálogo"), ("gestão", "convocacao", "alinhamento rápido")]}


class TestePorta(unittest.TestCase):
    def test_contrato(self):
        m = novo(7)
        procs = m.processos()
        nomes = [p.nome for p in procs]
        self.assertEqual(len(procs), 131)
        self.assertEqual(len(set(nomes)), len(nomes))
        for p in procs:
            self.assertIn(p.equipe, EQUIPES)
            self.assertEqual(len(p.resolucao), len(p.campos))
            self.assertTrue(all(r > 0 for r in p.resolucao))
        self.assertEqual(m.equipes(), list(EQUIPES))
        self.assertEqual(m.t, 0)
        v = m.passo()
        self.assertEqual((m.t, m.dia(), m.minuto_do_dia(), m.dia_da_semana()), (1, 0, 1, 0))
        self.assertEqual(list(v), nomes)
        for p in procs:
            self.assertEqual(len(v[p.nome]), len(p.campos))
            for x, r in zip(v[p.nome], p.resolucao):
                self.assertAlmostEqual(round(x / r) * r, x, places=6)       # o valor cai na grade da resolução
        self.assertIsInstance(m.receber("operação", "pergunta", "tudo bem?"), int)
        with self.assertRaises(ValueError):
            m.receber("diretoria", "pergunta", "x")
        with self.assertRaises(ValueError):
            m.receber("operação", "ordem", "x")
        with self.assertRaises(ValueError):
            Mundo(1, "quieto")


class TesteDeterminismo(unittest.TestCase):
    def test_duas_vidas_e_a_retomada(self):
        fim = D + 900
        a = novo(3)
        ha, ra = viver(a, fim, ATOS)
        b = novo(3)
        hb, rb = viver(b, fim, ATOS)
        self.assertEqual(ha, hb)
        self.assertEqual(ra, rb)
        # a terceira vida para no meio (com atos ainda em tratamento), salva, carrega e continua
        c = novo(3)
        h = hashlib.sha256()
        resp = []
        while c.t < fim:
            for x in ATOS.get(c.t + 1, ()):
                c.receber(*x)
            h.update(json.dumps(c.passo(), sort_keys=True, ensure_ascii=False).encode())
            resp.extend(c.respostas())
            if c.t == D + 620:
                salvo = pasta("salvo_retomada")
                c.salvar(salvo)
                c = Mundo.carregar(salvo, historia=pasta("retomada"))
        self.assertEqual(h.hexdigest(), ha)
        self.assertEqual(resp, ra)
        self.assertEqual(verdade_sem_pasta(c), verdade_sem_pasta(a))
        self.assertEqual(c.eventos_humanos(), a.eventos_humanos())
        ta, xa, _ = a.verdade_por_minuto()
        tc, xc, _ = c.verdade_por_minuto()
        self.assertTrue(np.array_equal(ta, tc) and np.array_equal(xa, xc, equal_nan=True))


class TesteRamos(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        m = novo(5)
        viver(m, D + 480)
        cls.salvo = pasta("salvo_ramos")
        m.salvar(cls.salvo)
        cls.fim = D + 1080
        A = {D + 540: [("operação", "pedido", "verifiquem a rota login")], D + 600: [("qualidade", "pedido", "refaçam os testes de frete")]}
        B = {D + 540: [("atendimento", "pedido", "priorizem os chamados de pagamento")]}
        cls.ramos = {}
        for nome, atos in (("A", A), ("A2", A), ("B", B), ("B2", B), ("C", {})):
            r = Mundo.carregar(cls.salvo, historia=pasta(f"ramo_{nome}"))
            cls.ramos[nome] = (r, *viver(r, cls.fim, atos))

    def test_cada_sequencia_e_reproduzivel(self):
        R = self.ramos
        self.assertEqual(R["A"][1], R["A2"][1])
        self.assertEqual(R["B"][1], R["B2"][1])
        self.assertEqual(verdade_sem_pasta(R["A"][0]), verdade_sem_pasta(R["A2"][0]))

    def test_sequencias_diferentes_dao_caminhos_diferentes(self):
        R = self.ramos
        self.assertNotEqual(R["A"][1], R["B"][1])
        self.assertNotEqual(R["A"][1], R["C"][1])
        self.assertNotEqual(R["B"][1], R["C"][1])
        self.assertEqual(len(R["C"][0].verdade()["atos"]), 0)
        self.assertEqual(len(R["A"][0].verdade()["atos"]), 2)

    def test_antes_do_ato_os_ramos_sao_iguais(self):
        """O ramo com ato e o ramo sem ato são o mesmo mundo até o minuto em que o ato vira coisa dentro do mundo."""
        ta, xa, _ = self.ramos["A"][0].verdade_por_minuto(D + 481, D + 539)
        tc, xc, _ = self.ramos["C"][0].verdade_por_minuto(D + 481, D + 539)
        self.assertTrue(np.array_equal(xa, xc, equal_nan=True))

    def test_cada_ramo_tem_a_sua_historia(self):
        pastas = {r[0].pasta_da_historia() for r in self.ramos.values()}
        self.assertEqual(len(pastas), len(self.ramos))

    def test_surdo_e_o_caminho_sem_atos(self):
        s1, s2 = novo(9, "surdo"), novo(9, "surdo")
        h1, r1 = viver(s1, D + 700, ATOS)
        h2, r2 = viver(s2, D + 700)
        self.assertEqual(h1, h2)
        self.assertEqual(r1, [])
        self.assertEqual(s1.verdade()["atos"], [])


class TesteConsequencia(unittest.TestCase):
    def test_equipe_ocupada_cansada_e_desconfiada_demora_mais(self):
        e = Equipe("operação", 1)
        base = e.atraso("pedido")
        self.assertGreater(e.atraso("pedido"), e.atraso("pergunta"))
        e.ocupacao = 1.0
        self.assertGreater(e.atraso("pedido"), base)
        e.ocupacao = 0.0
        e.tratado(0, "pedido", False)
        self.assertLess(e.confianca, 1.0)
        self.assertGreater(e.atraso("pedido") / (1 + 0.6 * e.atencao), base)       # o pedido inútil piora a próxima resposta
        self.assertLess(e.cobertura(), 1.0)                                        # e a equipe passa a verificar por cima
        f = Equipe("operação", 1)
        f.tratado(0, "pedido", True)
        self.assertGreater(f.confianca, 1.0)
        f.atencao = 0.0
        self.assertLess(f.atraso("pedido"), base)                                  # o pedido certo melhora a próxima
        g = Equipe("operação", 1)
        for _ in range(600):
            g.minuto(5, 3, 5, 1, 4, 8)                                             # hora extra cansa
        self.assertGreater(g.cansaco, 0.0)
        self.assertGreater(g.fator_duracao(), 1.0)
        self.assertNotEqual(Equipe("operação", 1).demora_tratamento, Equipe("operação", 2).demora_tratamento)

    def test_o_ato_fica_inteiro_na_verdade(self):
        m = novo(3, nome="consequencia")
        viver(m, D + 1000, ATOS)
        v = m.verdade()
        campos = {(p.nome, c) for p in m.processos() for c in p.campos}
        self.assertEqual(len(v["atos"]), 4)
        for a in v["atos"]:
            self.assertEqual(a["disponivel_em"], a["recebido"] + a["demora_ate_ficar_disponivel_min"])
            self.assertEqual(a["desfecho"], "respondido")
            self.assertGreaterEqual(a["pego_em"], a["disponivel_em"])
            self.assertGreaterEqual(a["tratado_em"], a["pego_em"] + a["minutos_de_trabalho"] - 1)
            ef = a["efeito"]
            for lista in ("encurta", "nao_encurta", "colateral"):
                for par in ef[lista]:
                    self.assertIn(tuple(par), campos, f"{lista}: {par} não é um campo da porta")
            if a["tipo"] == "pedido":
                self.assertIn(["quadro da equipe de " + a["equipe"], "horas extras no dia"], ef["colateral"])
                self.assertIsNotNone(ef["util"])
                self.assertNotEqual(a["confianca_antes"], a["confianca_depois"])
        for lista in (v["incidentes"], v["episodios_de_defeito_no_ar"], v["campanhas"], v["deriva"]["platos"]):
            for r in lista:
                for par in r["onde"]:
                    self.assertIn(tuple(par), campos)


class TesteDisco(unittest.TestCase):
    def test_volume_cheio_e_incidente_tratado_e_nunca_derruba_o_mundo(self):
        m = novo(2, nome="disco")
        viver(m, 600)
        p = m.produto
        p.volume_paginas = p.paginas_ocupadas()
        p._aplicar_volume()
        con = p.db.con
        with self.assertRaises(sqlite3.OperationalError):
            while True:
                con.execute("INSERT INTO auditoria (t, rota, usuario) VALUES (?, ?, 0)", (m.t, "x" * 200))
        for sql in ("INSERT INTO clientes (id, nome_fantasia, razao, plano, cep, uf, regiao, telefone, criado_em, ativo) "
                    "VALUES (?, 'x', 'x', 'pro', 'x', 'x', 0, 'x', 0, 0)", "INSERT INTO usuarios (id, cliente, login, ativo) VALUES (?, 0, 'x' || ?, 0)"):
            k = 10 ** 9
            with self.assertRaises(sqlite3.OperationalError):
                while True:
                    con.execute(sql, (k,) * sql.count("?"))
                    k += 1
        c = m.clientes.entrar(m.t, "pro", p, m.registro)        # o administrativo tenta criar a conta com o volume cheio
        self.assertIn(c, m.clientes.cadastro_pendente)
        viver(m, 600 + D)                                       # não levanta exceção
        v = m.verdade()
        self.assertTrue(any(i["causa"] == "volume do banco cheio" and i["fim"] is not None and i["folga_dada_em_dias"] for i in v["incidentes"]))
        adiado = v["cadastros_adiados_por_volume_cheio"]
        self.assertEqual(len(adiado), 1)
        self.assertIsNotNone(adiado[0]["gravado_em"])
        self.assertIn(c, m.clientes.ativos_ids)


class TesteDerivaECampanha(unittest.TestCase):
    def test_campanha_mexe_em_varios_processos_e_fica_na_verdade(self):
        m = novo(5, nome="campanha_base")
        viver(m, 400)
        salvo = pasta("salvo_campanha")
        m.salvar(salvo)
        com = Mundo.carregar(salvo, historia=pasta("com_campanha"))
        sem = Mundo.carregar(salvo, historia=pasta("sem_campanha"))
        com.injetar_campanha(D + 8 * 60, 10 * 60, 1.0)
        nomes = [p.nome for p in com.processos()]
        soma = {}
        for nome, r in (("com", com), ("sem", sem)):
            s = 0
            while r.t < D + 18 * 60:
                v = r.passo()
                if r.t >= D + 8 * 60:
                    s += v["sessões dos clientes"][0] + v["rota catálogo"][0]
            soma[nome] = s
        self.assertGreater(soma["com"], 1.3 * soma["sem"])
        camp = com.verdade()["campanhas"]
        self.assertEqual(len(camp), 1)
        self.assertEqual((camp[0]["inicio"], camp[0]["fim"]), (D + 8 * 60, D + 18 * 60))
        self.assertEqual(sem.verdade()["campanhas"], [])
        t, x, cols = com.verdade_por_minuto(D + 7 * 60, D + 18 * 60 - 1)
        self.assertEqual(int((x[:, cols.index("campanha")] > 0).sum()), 10 * 60)

    def test_plato_e_expansao(self):
        m = novo(6, nome="plato")
        viver(m, 300)
        n = m.clientes.ativos()
        m.teto = n + 1                                           # um mercado quase cheio
        viver(m, D + 300)
        platos = m.verdade()["deriva"]["platos"]
        self.assertEqual(len(platos), 1)
        self.assertIsNone(platos[0]["fim"])
        t, x, cols = m.verdade_por_minuto(D + 10, D + 20)
        self.assertTrue((x[:, cols.index("fase_da_deriva")] == 1).all())
        self.assertTrue((x[:, cols.index("saturacao")] < 0.5).all())
        m.fase, m.expansao = "expansão decidida", (m.t + 60, m.teto + 80)    # o dono decide abrir mercado
        viver(m, 2 * D + 300)
        p = m.verdade()["deriva"]["platos"][0]
        self.assertIsNotNone(p["fim"])
        self.assertEqual(p["duracao_min"], p["fim"] - p["inicio"])
        self.assertEqual(m.fase, "crescendo")

    def test_sem_deriva_nao_tem_teto_nem_plato(self):
        m = novo(6, "sem_deriva")
        viver(m, D + 60)
        v = m.verdade()
        self.assertIsNone(v["deriva"]["teto_inicial"])
        self.assertEqual(v["deriva"]["platos"], [])
        t, x, cols = m.verdade_por_minuto(10, D)
        self.assertTrue((x[:, cols.index("teto_do_mercado")] == 0).all())


class TesteVerdadeEmDisco(unittest.TestCase):
    def test_um_arquivo_por_dia_que_nao_muda_mais(self):
        m = novo(4, nome="disco_verdade")
        viver(m, 2 * D)
        h = m.pasta_da_historia()
        self.assertTrue(all(os.path.exists(os.path.join(h, f"dia_{d:05d}{e}")) for d in (0, 1) for e in (".npz", ".json")))
        antes = {f: ler(os.path.join(h, f)) for f in os.listdir(h)}
        viver(m, 3 * D)
        for f, conteudo in antes.items():
            self.assertEqual(ler(os.path.join(h, f)), conteudo)
        t, x, cols = m.verdade_por_minuto(D, 2 * D - 1)
        self.assertEqual(x.shape, (D, len(cols)))
        self.assertTrue(np.array_equal(t, np.arange(D, 2 * D)))
        self.assertFalse(np.isnan(x).any())
        v = m.verdade()
        self.assertEqual(v["verdade_por_minuto"]["dias_gravados"], 3)
        self.assertEqual(len(v["deriva"]["carteira_por_dia"]), 4)          # o minuto 3 x 1440 já abriu o dia 3


class TesteNulos(unittest.TestCase):
    def test_os_nulos_andam(self):
        for nulo in ("sem_defeito", "embaralhado", "sem_deriva", "surdo", "paciente"):
            m = novo(8, nulo)
            viver(m, 600)
            self.assertEqual(m.t, 600)
            v = m.verdade()
            self.assertEqual(v["nulo"], nulo)
            if nulo == "embaralhado":
                self.assertGreater(len(v["ciclos"]["blocos_do_calendario"]), 2)


class TesteCausas(unittest.TestCase):
    """(v2.1) A causa dos chamados: num incidente, o par da lei é causa declarada e os outros pares são causa comum."""

    @classmethod
    def setUpClass(cls):
        m = novo(2, "sem_defeito", nome="causas")
        viver(m, 600)
        p = m.produto
        p.volume_paginas = p.paginas_ocupadas() + 5
        p._aplicar_volume()
        viver(m, D + 600)
        cls.m, cls.v = m, m.verdade()

    def test_cada_chamado_tem_origem_e_causa(self):
        v = self.v
        self.assertEqual(sum(v["chamados_por_causa"].values()), len(v["chamados"]))
        for c in v["chamados"]:
            self.assertIn(c["causa"], v["chamados_por_causa"])
            if c["motivo"] in ("erro", "lentidão"):
                self.assertIsNotNone(c["origem"])
        inc = v["incidentes"][0]
        self.assertEqual(sum(inc["chamados_por_rota_de_origem"].values()), inc["chamados"])

    def test_as_categorias_do_incidente(self):
        from organizacao.mundo.v2.causas import classificar_par
        v = self.v
        inc = v["incidentes"][0]
        erro = lambda r: [f"rota {r}", "respostas com erro no minuto"]
        esc = ["chamados de login e conta", "escalados"]
        self.assertEqual(classificar_par(v, erro("login"), esc, inc["inicio"], inc["fim"])["categoria"], "causa declarada")
        self.assertEqual(classificar_par(v, erro("catálogo"), esc, inc["inicio"], inc["fim"])["categoria"], "causa comum (incidente)")
        self.assertEqual(classificar_par(v, erro("login"), ["funil de vendas", "leads"], inc["inicio"], inc["fim"])["categoria"], "sem relação")

    def test_as_leis_falam_de_campos_da_porta(self):
        campos = {(p.nome, c) for p in self.m.processos() for c in p.campos}
        for lei in self.v["causas"]["leis"]:
            for par in lei["de"] + lei["para"]:
                self.assertIn(tuple(par), campos)
        for par in self.v["causas"]["campos_quando_o_produto_para"]:
            self.assertIn(tuple(par), campos)
        self.assertTrue(any(j["chamados_gerados"] for j in self.v["causas"]["janelas_de_rota"]))


class TesteCalendario(unittest.TestCase):
    """(v2.1) Os motores do calendário declarados por campo, e a força medida quando registros/calendario.json existe."""

    def test_motores_e_medida(self):
        from organizacao.mundo.v2 import calendario
        from organizacao.mundo.v2.causas import classificar_par
        cal = calendario.para_a_verdade()
        m = novo(1, nome="calendario")
        nomes = {f"{p.nome}.{c}" for p in m.processos() for c in p.campos}
        self.assertEqual(set(cal["campos"]), nomes)
        sem_motor = {n for n, c in cal["campos"].items() if not c["motores"]}
        self.assertTrue(all(n.endswith(("clientes ativos", "pessoas no quadro")) or n.startswith("sonda") for n in sem_motor))
        if cal["medida"] is None:
            self.skipTest("registros/calendario.json ainda não foi medido")
        c = cal["campos"]
        self.assertTrue(c["rota catálogo.requisições no minuto"]["movido_pelo_calendario"])
        self.assertFalse(c["carteira de clientes.clientes ativos"]["movido_pelo_calendario"])
        self.assertGreater(c["rota catálogo.requisições no minuto"]["fracao_da_variancia"],
                           10 * c["rota catálogo.requisições no minuto"]["controle_embaralhado_pelo_relogio_da_porta"])
        v = {"incidentes": [], "causas": {}, "calendario": cal}
        r = classificar_par(v, ["rota catálogo", "requisições no minuto"], ["sessões dos clientes", "sessões iniciadas no minuto"])
        self.assertEqual(r["categoria"], "causa comum (calendário)")



class TesteReversaoPropria(unittest.TestCase):
    """(v2.2) Na semente 2, a busca quebra com a liberação do dia 3 (t = 5253) e a operação a reverte sozinha em uma hora. Um pedido
    certo à operação logo depois da liberação: o ramo sem ato diz quando a empresa a tiraria sozinha, e os minutos e a verdade de
    antes do ato não mudam."""

    @classmethod
    def setUpClass(cls):
        cls.sem = novo(2, nome="propria_sem")
        cls.h_sem, _ = viver(cls.sem, 5253 + 3 * 60)
        cls.com = novo(2, nome="propria_com")
        cls.h_com, _ = viver(cls.com, 5253 + 3 * 60, {5260: [("operação", "pedido", "Verifiquem a rota busca")]})

    @staticmethod
    def episodio(m):
        return next(e for e in m.verdade()["episodios_de_defeito_no_ar"] if e["funcao"] == "normalizar_termo" and e["liberado_em"] == 5253)

    def test_sem_ato_o_vivido_e_o_ramo(self):
        e = self.episodio(self.sem)
        self.assertEqual(e["saiu_por"], "reversão")
        self.assertIsNone(e["ramo_sem_ato"])
        self.assertEqual(e["reverteria_sozinha_em"], e["saiu_do_ar"])
        self.assertEqual((e["sairia_sozinha_por"], e["persistente"], e["antecipou_min"]), ("reversão", False, 0))

    def test_com_ato_o_ramo_repete_a_vida_sem_ato(self):
        sem, com = self.episodio(self.sem), self.episodio(self.com)
        self.assertEqual(com["ramo_sem_ato"]["desde"], 5259)
        self.assertEqual(com["atos_recebidos_no_ar"], 1)
        self.assertEqual(com["reverteria_sozinha_em"], sem["saiu_do_ar"])
        self.assertEqual(com["sairia_sozinha_por"], sem["saiu_por"])
        self.assertEqual(com["antecipou_min"], com["reverteria_sozinha_em"] - com["saiu_do_ar"])
        if com["saiu_pelo_ato"] is not None:
            ato = next(a for a in self.com.verdade()["atos"] if a["numero"] == com["saiu_pelo_ato"])
            self.assertEqual(ato["efeito"]["antecipou_min"], com["antecipou_min"])

    def test_o_ramo_nao_muda_o_vivido(self):
        m = novo(2, nome="propria_sem_ramos")
        m.com_ramos = False
        h, _ = viver(m, 5253 + 3 * 60, {5260: [("operação", "pedido", "Verifiquem a rota busca")]})
        self.assertEqual(h, self.h_com)
        tira = ("ramo_sem_ato", "reverteria_sozinha_em", "sairia_sozinha_por", "persistente", "antecipou_min")
        limpa = lambda v: json.dumps([{k: x for k, x in e.items() if k not in tira} for e in v["episodios_de_defeito_no_ar"]]
                                     + [{k: x for k, x in a.items() if k != "efeito"} for a in v["atos"]], sort_keys=True)
        self.assertEqual(limpa(m.verdade()), limpa(self.com.verdade()))


class TestePaciente(unittest.TestCase):
    """(v2.2) O nulo paciente: sem atos, a vida normal; com atos, a equipe não se cansa, não gasta atenção nem muda de confiança."""

    def test_sem_atos_e_a_vida_normal(self):
        a, b = novo(3, nome="pac_normal"), novo(3, "paciente", nome="pac_pac")
        self.assertEqual(viver(a, 2 * D)[0], viver(b, 2 * D)[0])

    def test_com_atos_nada_de_atencao_cansaco_confianca_nem_hora_extra(self):
        m = novo(1, "paciente", nome="pac_atos")
        atos = {D + 540 + 20 * k: [("operação", "pedido", "verifiquem a rota login"), ("atendimento", "pergunta", "como está o frete?")]
                for k in range(12)}
        viver(m, 2 * D + 600, atos)
        for e in m.empresa.equipes.values():
            self.assertEqual((e.cansaco, e.atencao, e.confianca), (0.0, 0.0, 1.0))
            self.assertAlmostEqual(e.atraso("pedido"), e.demora_tratamento * (1 + 1.5 * e.ocupacao))
        v = m.verdade()
        self.assertEqual(v["nulo"], "paciente")
        tratados = [a for a in v["atos"] if a["desfecho"] == "respondido"]
        self.assertGreater(len(tratados), 10)
        self.assertTrue(all(a["confianca_antes"] == a["confianca_depois"] == 1.0 for a in tratados))
        self.assertTrue(all(a["horas_extras_atribuidas"] == [] for a in v["atos"]))



class TesteOuvinte(unittest.TestCase):
    """(v2.2) O ouvinte: processo, campo, tempo e tipo do pedido pelo texto inteiro; a rota de sempre; a pergunta de volta."""

    @classmethod
    def setUpClass(cls):
        cls.m = novo(1, nome="ouvinte")
        cls.o = cls.m.porta.ouvinte

    def entender(self, equipe, texto, t=20 * D + 15 * 60):
        from .atos import rota_do_texto
        from .cadastro import ROTA_COMPONENTE
        r = rota_do_texto(texto)
        return self.o.entender(texto, equipe, t, r, ROTA_COMPONENTE[r] if r else None, 19 * D + 900)

    def test_dez_frases_com_campo_e_tempo(self):
        t = 20 * D + 15 * 60
        casos = [
            ("operação", "Olhem a rota busca, latência média, desde o dia 12, 10h, e digam como está",
             ("rota busca", "latência média em ms", "olhar e dizer", 12 * D + 600)),
            ("atendimento", "Quantos chamados de frete escalados há duas horas?", ("chamados de frete", "escalados", "olhar e dizer", t - 120)),
            ("desenvolvimento", "Corrijam os erros da rota pagamento desde ontem",
             ("rota pagamento", "respostas com erro no minuto", "corrigir ou reverter", 19 * D)),
            ("atendimento", "Priorizem os chamados de login e conta abertos nas últimas 3 horas",
             ("chamados de login e conta", "abertos", "pôr à frente da fila", t - 180)),
            ("operação", "Digam como está a fila de trabalhos, trabalhos pendentes, desde as 9h",
             ("fila de trabalhos", "trabalhos pendentes", "olhar e dizer", 20 * D + 540)),
            ("operação", "Revertam a versão: respostas com erro na rota catálogo depois da última liberação",
             ("rota catálogo", "respostas com erro no minuto", "corrigir ou reverter", 19 * D + 900)),
            ("operação", "Mostrem o servidor da aplicação, memória em uso, na última hora",
             ("servidor da aplicação", "memória em uso em MB", "olhar e dizer", t - 60)),
            ("operação", "Como está o banco do produto, espaço livre no volume, desde o dia 20?",
             ("banco do produto", "espaço livre no volume em MB", "olhar e dizer", 20 * D)),
            ("desenvolvimento", "Ponham na frente os bugs de notificações abertos", ("bugs de notificações", "abertos", "pôr à frente da fila", None)),
            ("operação", "Vejam e digam o percentil 95 da rota frete há 30 minutos",
             ("rota frete", "latência do percentil 95 em ms", "olhar e dizer", t - 30)),
        ]
        for equipe, texto, (proc, campo, tipo, desde) in casos:
            e = self.entender(equipe, texto)
            self.assertEqual((e["processo"], e["campo"], e["tipo"], e["desde"]), (proc, campo, tipo, desde), texto)
            self.assertTrue(e["reconhece"])

    def test_sem_nada_reconhecivel(self):
        for equipe, texto in (("operação", "vejam isso agora"), ("operação", "por favor resolvam"), ("produto", "melhorem isso"),
                              ("qualidade", "está tudo estranho desde ontem")):
            self.assertFalse(self.entender(equipe, texto)["reconhece"], texto)
        for equipe, texto in (("vendas", "Retomem as propostas paradas"), ("gestão", "Precisamos alinhar as prioridades do mês"),
                              ("operação", "Como está o volume do banco?")):
            self.assertTrue(self.entender(equipe, texto)["reconhece"], texto)

    def test_a_rota_de_sempre(self):
        from .atos import rota_do_texto
        with open(os.path.join(os.path.dirname(__file__), "atos_exemplo.csv"), encoding="utf-8") as f:
            textos = [linha.split(",", 3)[3].strip().strip('"') for linha in f.readlines()[1:]]
        for texto in textos + ["que rota frete: latência média em ms volte ao normal", "Quantos chamados de pagamento estão abertos?"]:
            self.assertEqual(self.entender("operação", texto)["rota"], rota_do_texto(texto), texto)

    def test_a_pergunta_de_volta_e_o_painel(self):
        m = novo(1, nome="ouvinte_vida")
        atos = {D + 600: [("operação", "pedido", "vejam isso agora")],
                D + 610: [("operação", "pedido", "Digam como está a fila de trabalhos, trabalhos pendentes, desde as 9h")]}
        _, resp = viver(m, D + 900, atos)
        r = {n: x for _, n, _, x in resp}
        self.assertTrue(r[1].startswith("Pedido não entendido"))
        self.assertIn("No painel de fila de trabalhos, desde dia 1, 09h00: trabalhos pendentes", r[2])
        a = {x["numero"]: x for x in m.verdade()["atos"]}
        self.assertTrue(a[1]["pediu_esclarecimento"])
        self.assertIsNone(a[1]["efeito"]["util"])
        self.assertEqual(a[1]["confianca_antes"], a[1]["confianca_depois"])
        self.assertFalse(a[2]["pediu_esclarecimento"])
        self.assertEqual(a[2]["entendido"]["campo"], "trabalhos pendentes")
        self.assertIsNone(a[2]["efeito"]["util"])



class TesteOpcoesV23(unittest.TestCase):
    """(v2.3) A porta da equipe e o relógio como processos, e a agenda calada (o feriado coletivo); desligadas, nada muda."""

    def test_desligadas_nada_muda(self):
        a, b = novo(5, nome="v23_a"), Mundo(5, historia=pasta("v23_b"), porta=False, relogio=False, agenda_calada=None)
        self.assertEqual([p.nome for p in a.processos()], [p.nome for p in b.processos()])
        self.assertEqual(len(a.processos()), 131)
        atos = {D + 600: [("operação", "pedido", "verifiquem a rota login")]}
        self.assertEqual(viver(a, D + 900, atos), viver(b, D + 900, atos))
        self.assertNotIn("opcoes", a.verdade())

    def test_porta_e_relogio(self):
        m = Mundo(1, historia=pasta("v23_porta"), porta=True, relogio=True)
        nomes = [p.nome for p in m.processos()]
        self.assertEqual(nomes[-8:], [f"porta da equipe de {e}" for e in EQUIPES] + ["relógio"])
        atos = {D + 600: [("operação", "pedido", "verifiquem a rota login"), ("atendimento", "pergunta", "como está o frete?")]}
        chegou, abertos, relogio = {}, [], None
        while m.t < D + 900:
            for x in atos.get(m.t + 1, ()):
                m.receber(*x)
            v = m.passo()
            for e in EQUIPES:
                chegou[e] = chegou.get(e, 0) + v[f"porta da equipe de {e}"][0]
            abertos.append(v["porta da equipe de operação"][1])
            if m.t == D + 601:
                relogio = v["relógio"]
        self.assertEqual(relogio, [10.0, 1.0, float(D + 601)])
        resp = m.respostas()
        self.assertEqual(chegou["operação"], sum(1 for x in resp if x[2] == "operação"))
        self.assertEqual(chegou["atendimento"], sum(1 for x in resp if x[2] == "atendimento"))
        self.assertEqual(chegou["vendas"], 0)
        self.assertEqual(abertos[D + 600 - 1], 1.0)                 # o pedido aberto desde o minuto em que chegou
        self.assertEqual(abertos[-1], 0.0)                          # e fechado depois da resposta
        self.assertEqual(m.verdade()["opcoes"], {"porta": True, "relogio": True, "agenda_calada": None})

    def test_surdo_nenhuma_chegada(self):
        m = Mundo(1, "surdo", historia=pasta("v23_surdo"), porta=True)
        atos = {D + 600: [("operação", "pedido", "verifiquem a rota login")]}
        tot = 0
        while m.t < D + 900:
            for x in atos.get(m.t + 1, ()):
                m.receber(*x)
            v = m.passo()
            tot += sum(v[f"porta da equipe de {e}"][0] + v[f"porta da equipe de {e}"][1] for e in EQUIPES)
        self.assertEqual(tot, 0)

    def test_agenda_calada_e_um_feriado(self):
        m = Mundo(1, historia=pasta("v23_feriado"), agenda_calada=(2 * D, 3 * D))
        dia = {}
        while m.t < 4 * D:
            v = m.passo()
            d = dia.setdefault(m.t // D, [0, 0, 0])
            d[0] += v["sessões dos clientes"][0]
            d[1] += sum(v[f"agenda da equipe de {e}"][1] for e in EQUIPES)
            d[2] = max(d[2], sum(v[f"quadro da equipe de {e}"][1] for e in EQUIPES))
        self.assertEqual(dia[2][1:], [0, 0])                        # nenhuma reunião, ninguém presente
        self.assertLess(dia[2][0], 0.1 * dia[1][0])                 # os clientes quase param
        self.assertGreater(dia[3][2], 30)                           # e no dia seguinte tudo volta
        v = m.verdade()
        self.assertEqual((v["agenda_calada"]["datas"], v["agenda_calada"]["inicio"], v["agenda_calada"]["fim"]), ([2], 2 * D, 3 * D))
        _, linhas, colunas = m.verdade_por_minuto(2 * D + 600, 2 * D + 600)
        self.assertEqual(linhas[0][colunas.index("dia_util")], 0.0)

    def test_variavel_de_ambiente(self):
        os.environ["MUNDO_RELOGIO"] = "1"
        try:
            self.assertEqual(Mundo(1, historia=pasta("v23_env")).processos()[-1].nome, "relógio")
        finally:
            del os.environ["MUNDO_RELOGIO"]

    def test_o_relogio_no_v1(self):
        from organizacao.mundo.v1 import Mundo as MundoV1
        m = MundoV1(1, relogio=True)
        self.assertEqual(m.processos()[-1].nome, "relógio")
        for _ in range(61):
            v = m.passo()
        self.assertEqual(v["relógio"], [1.0, 0.0, 61.0])
        self.assertNotEqual(MundoV1(1).processos()[-1].nome, "relógio")


class TesteOuvinteV23(unittest.TestCase):
    """(v2.3) As três lacunas: "verificar", "olhar X ... e dizer", "falhas" da sonda; o que a v2.2 lia continua igual."""

    def entender(self, equipe, texto):
        from .atos import rota_do_texto
        from .cadastro import ROTA_COMPONENTE
        o = novo(1, nome="ouvinte_v23").porta.ouvinte
        r = rota_do_texto(texto)
        return o.entender(texto, equipe, 20 * D + 15 * 60, r, ROTA_COMPONENTE[r] if r else None)

    def test_as_frases(self):
        e = self.entender("operação", "Vocês podem verificar a rota busca?")
        self.assertEqual((e["processo"], e["tipo"]), ("rota busca", "corrigir ou reverter"))
        e = self.entender("operação", "Olhar a fila de trabalhos, trabalhos pendentes, desde as 9h e dizer como está")
        self.assertEqual((e["processo"], e["campo"], e["tipo"]), ("fila de trabalhos", "trabalhos pendentes", "olhar e dizer"))
        e = self.entender("operação", "Olhem a sonda de disponibilidade e me digam as falhas desde ontem")
        self.assertEqual((e["processo"], e["campo"], e["tipo"], e["desde"]),
                         ("sonda de disponibilidade", "verificações com falha no minuto", "olhar e dizer", 19 * D))

    def test_o_pedido_dele_nao_muda(self):
        texto = "que sonda de disponibilidade: verificações com falha no minuto volte ao normal; Sem rota indicada, não rodamos verificação."
        e = self.entender("operação", texto)
        self.assertEqual((e["processo"], e["campo"], e["tipo"]), ("sonda de disponibilidade", "verificações com falha no minuto", None))


if __name__ == "__main__":
    unittest.main()
