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
        for nulo in ("sem_defeito", "embaralhado", "sem_deriva", "surdo"):
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


if __name__ == "__main__":
    unittest.main()
