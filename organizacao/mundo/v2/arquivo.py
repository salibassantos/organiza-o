"""(v2) A memória longa dos sistemas: cada banco guarda o que é recente e apaga o que passou da sua janela de retenção, como os
sistemas de uma empresa fazem. Assim o mundo pode viver anos com memória e custo por minuto estáveis.

As tabelas que só recebem linhas (registros, logs) são podadas por marcos: uma vez por semana anota-se o maior rowid de cada tabela;
o que estava abaixo do marco de N dias atrás sai. As tabelas de coisas que mudam de estado (itens, negócios, vagas) saem só quando a
coisa terminou há mais que a janela."""
from .cadastro import MINUTOS_DIA


class Marcos:
    def __init__(self):
        self.lista = []                 # (t, {tabela: maior rowid naquele instante})

    def marcar(self, t, db, tabelas):
        self.lista.append((t, {tb: db.execute(f"SELECT COALESCE(MAX(rowid), 0) FROM {tb}").fetchone()[0] for tb in tabelas}))

    def limite(self, t, dias):
        """O marco mais novo que já tem `dias` dias (ou None)."""
        achado = None
        for tt, m in self.lista:
            if tt <= t - dias * MINUTOS_DIA:
                achado = m
        return achado

    def esquecer(self, t, dias):
        """Tira da lista os marcos que nenhuma janela de até `dias` dias ainda usa."""
        velhos = [i for i, (tt, _) in enumerate(self.lista) if tt <= t - dias * MINUTOS_DIA]
        if len(velhos) > 1:
            del self.lista[:velhos[-1]]


def podar(db, marcos, t, regras):
    """regras: [(tabela, dias, condição extra ou None)]. Devolve quantas linhas saíram."""
    n = 0
    for tabela, dias, extra in regras:
        lim = marcos.limite(t, dias)
        if lim is None or tabela not in lim:
            continue
        q = f"DELETE FROM {tabela} WHERE rowid <= ?" + (f" AND ({extra})" if extra else "")
        n += db.execute(q, (lim[tabela],)).rowcount
    return n
