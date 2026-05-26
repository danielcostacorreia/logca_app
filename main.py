from solver.load_data import load_clientes_csv
from solver.alinea_11 import (
    validar_clientes,
    calcular_solver_por_pais,
    cidade_mais_proxima
)


def main():
    df = load_clientes_csv("data/clientes_logca.csv")
    validar_clientes(df)

    solver = calcular_solver_por_pais(df)
    final = cidade_mais_proxima(df, solver)

    print("\n=== Solver contínuo ===")
    print(solver.to_string(index=False))

    print("\n=== Cidade mais próxima (solução final) ===")
    print(final.to_string(index=False))


if __name__ == "__main__":
    main()