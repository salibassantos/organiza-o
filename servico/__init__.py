"""O mundo do serviço de um modelo de linguagem (família "servico"): ver LEIA-ME.md, VERDADE.md."""
from .mundo import Mundo, Processo, NULOS, FAMILIA, DESCRICAO, EQUIPES
from .ligacoes import classificar_par

__all__ = ["Mundo", "Processo", "NULOS", "FAMILIA", "DESCRICAO", "EQUIPES", "classificar_par"]
