"""Confere a porta do mundo contra o contrato, sem observador:

- processos(): entre cem e trezentos processos, nomes únicos, de um a oito campos numéricos, sempre a mesma lista;
- passo(): devolve os mesmos processos e campos a cada minuto, na mesma ordem, com números;
- a mesma semente repete a mesma vida (também em outro processo do sistema, com outra semente de hash do Python);
- sementes diferentes dão empresas diferentes;
- salvar e carregar devolvem o mesmo mundo: continuar depois de carregar dá os mesmos minutos que continuar sem parar;
- os nulos rodam e a porta de atos aceita e responde (e, no nulo surdo, aceita e não responde).

    python conferir.py [minutos]
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile

if __package__ in (None, ""):
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
    from organizacao.mundo.v1.mundo import Mundo
else:
    from .mundo import Mundo


def assinatura(m, minutos):
    h = hashlib.sha256()
    nomes = [p.nome for p in m.processos()]
    for _ in range(minutos):
        v = m.passo()
        assert list(v.keys()) == nomes, "a ordem dos processos mudou"
        for p in nomes:
            h.update(json.dumps(v[p]).encode())
    return h.hexdigest()


def conferir(minutos=2500):
    falhas = []

    def checar(cond, texto):
        print(("ok      " if cond else "FALHOU  ") + texto, flush=True)
        if not cond:
            falhas.append(texto)

    m = Mundo(7)
    procs = m.processos()
    nomes = [p.nome for p in procs]
    checar(100 <= len(procs) <= 300, f"{len(procs)} processos (entre cem e trezentos)")
    checar(len(set(nomes)) == len(nomes), "nomes únicos")
    checar(all(1 <= len(p.campos) <= 8 for p in procs), "cada processo com um a oito campos")
    checar(all(len(set(p.campos)) == len(p.campos) for p in procs), "campos únicos dentro de cada processo")
    checar(m.t == 0, "t começa em 0")
    v = m.passo()
    checar(m.t == 1 and m.dia() == 0 and m.minuto_do_dia() == 1 and m.dia_da_semana() == 0, "o primeiro passo faz o minuto 1 da segunda-feira")
    checar(all(len(v[p.nome]) == len(p.campos) for p in procs), "cada processo devolve um valor por campo")
    checar(all(isinstance(x, float) for p in procs for x in v[p.nome]), "os valores são números (float)")
    checar([p.nome for p in m.processos()] == nomes, "processos() não muda depois de andar")

    a = assinatura(Mundo(7), minutos)
    b = assinatura(Mundo(7), minutos)
    checar(a == b, "a mesma semente repete a mesma vida no mesmo processo")
    codigo = ("import sys; sys.path.insert(0, %r); from organizacao.mundo.v1.conferir import assinatura; "
              "from organizacao.mundo.v1.mundo import Mundo; print(assinatura(Mundo(7), %d))"
              % (os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")), minutos))
    outro = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True, env=dict(os.environ, PYTHONHASHSEED="12345"))
    checar(outro.stdout.strip() == a, "a mesma semente repete a mesma vida em outro processo (outra semente de hash)")
    checar(assinatura(Mundo(8), minutos) != a, "sementes diferentes dão empresas diferentes")

    corrido = Mundo(11)
    for _ in range(minutos):
        corrido.passo()
    seguido = assinatura(corrido, minutos)
    parado = Mundo(11)
    for _ in range(minutos):
        parado.passo()
    with tempfile.TemporaryDirectory() as pasta:
        parado.salvar(pasta)
        retomado = Mundo.carregar(pasta)
    checar(retomado.t == minutos, "carregar devolve o relógio")
    checar(assinatura(retomado, minutos) == seguido, "salvar e carregar devolvem o mesmo mundo (os minutos seguintes são iguais)")

    for nulo in ("sem_defeito", "embaralhado", "sem_deriva", "surdo"):
        n = Mundo(7, nulo)
        for _ in range(200):
            n.passo()
        checar(n.t == 200, f"o nulo {nulo} anda")
    m = Mundo(3)
    for _ in range(9 * 60):
        m.passo()
    numero = m.receber("operação", "pergunta", "como está a rota de pedido?")
    checar(isinstance(numero, int), "receber() devolve um número")
    resp = []
    for _ in range(2 * 1440):
        m.passo()
        resp += m.respostas()
    checar(any(r[1] == numero for r in resp), "a pergunta foi respondida dentro do prazo")
    s = Mundo(3, "surdo")
    for _ in range(9 * 60):
        s.passo()
    s.receber("operação", "pergunta", "como está a rota de pedido?")
    resp = []
    for _ in range(1440):
        s.passo()
        resp += s.respostas()
    checar(resp == [], "no nulo surdo nada é respondido")
    print("tudo certo" if not falhas else f"{len(falhas)} falhas")
    return not falhas


if __name__ == "__main__":
    sys.exit(0 if conferir(int(sys.argv[1]) if len(sys.argv) > 1 else 2500) else 1)
