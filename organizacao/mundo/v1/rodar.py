"""Faz o mundo acontecer sem observador e grava tudo, para conferir o mundo sozinho.

    python rodar.py <pasta> <dias> <semente> [nulo] [--atos arquivo.csv]

Grava na pasta:
- minutos.csv.gz: uma linha por minuto (t = 1, 2, ...), na ordem de processos() e de campos; a primeira linha tem os nomes
  "processo.campo";
- processos.json: a lista dos processos e dos campos;
- verdade.json: o que a empresa teve e quando (só para a bancada);
- eventos_humanos.csv: o que uma pessoa da empresa veria acontecer, com o instante;
- respostas.csv e atos.csv: quando há arquivo de atos, os atos entregues e as respostas que voltaram, com instante;
- custo.json: o tempo de máquina e a memória.

O arquivo de atos tem uma linha por ato, com cabeçalho: t,equipe,tipo,texto. O ato da linha t é entregue pela porta logo antes do
passo que faz o minuto t, e acontece nesse minuto."""
import csv
import gzip
import io
import json
import os
import resource
import sys
import time

if __package__ in (None, ""):
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
    from organizacao.mundo.v1.mundo import Mundo
else:
    from .mundo import Mundo


def _fmt(v):
    if v == int(v):
        return str(int(v))
    return f"{v:.2f}".rstrip("0")


def ler_atos(caminho):
    atos = {}
    with open(caminho, encoding="utf-8") as f:
        for linha in csv.DictReader(f):
            atos.setdefault(int(linha["t"]), []).append((linha["equipe"].strip(), linha["tipo"].strip(), linha["texto"].strip()))
    return atos


def rodar(pasta, dias, semente, nulo=None, arquivo_atos=None, avisar=True):
    os.makedirs(pasta, exist_ok=True)
    inicio = time.time()
    m = Mundo(semente, nulo)
    procs = m.processos()
    with open(os.path.join(pasta, "processos.json"), "w", encoding="utf-8") as f:
        json.dump([{"nome": p.nome, "campos": p.campos} for p in procs], f, ensure_ascii=False, indent=1)
    atos = ler_atos(arquivo_atos) if arquivo_atos else {}
    entregues = []
    respostas = []
    total = dias * 1440
    with gzip.open(os.path.join(pasta, "minutos.csv.gz"), "wt", encoding="utf-8", compresslevel=6, newline="") as saida:
        saida.write(",".join('"' + f"{p.nome}.{c}".replace('"', "'") + '"' for p in procs for c in p.campos) + "\n")
        buf = io.StringIO()
        for i in range(total):
            proximo = m.t + 1
            for equipe, tipo, texto in atos.get(proximo, ()):
                numero = m.receber(equipe, tipo, texto)
                entregues.append((proximo, numero, equipe, tipo, texto))
            valores = m.passo()
            buf.write(",".join(_fmt(v) for p in procs for v in valores[p.nome]))
            buf.write("\n")
            for r in m.respostas():
                respostas.append(r)
            if m.t % 1440 == 0:
                saida.write(buf.getvalue())
                buf = io.StringIO()
                if avisar:
                    print(f"dia {m.t // 1440} de {dias}: {time.time() - inicio:.0f} s", flush=True)
        saida.write(buf.getvalue())
    with open(os.path.join(pasta, "verdade.json"), "w", encoding="utf-8") as f:
        json.dump(m.verdade(), f, ensure_ascii=False, indent=1)
    with open(os.path.join(pasta, "eventos_humanos.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t", "acontecimento"])
        w.writerows(m.eventos_humanos())
    if arquivo_atos:
        with open(os.path.join(pasta, "atos.csv"), "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["t", "numero", "equipe", "tipo", "texto"])
            w.writerows(entregues)
        with open(os.path.join(pasta, "respostas.csv"), "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["t", "numero", "equipe", "texto"])
            w.writerows(respostas)
    segundos = time.time() - inicio
    custo = {"dias": dias, "semente": semente, "nulo": nulo, "segundos": round(segundos, 1),
             "segundos_por_dia_simulado": round(segundos / dias, 2),
             "memoria_maxima_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1)}
    with open(os.path.join(pasta, "custo.json"), "w", encoding="utf-8") as f:
        json.dump(custo, f, ensure_ascii=False, indent=1)
    return m, custo


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    arquivo_atos = None
    if "--atos" in argv:
        arquivo_atos = argv[argv.index("--atos") + 1]
        args.remove(arquivo_atos)
    if len(args) < 3:
        print(__doc__)
        return 2
    pasta, dias, semente = args[0], int(args[1]), int(args[2])
    nulo = args[3] if len(args) > 3 and args[3] not in ("", "normal", "nenhum") else None
    _, custo = rodar(pasta, dias, semente, nulo, arquivo_atos)
    print(json.dumps(custo, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
