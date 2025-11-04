#!/usr/bin/env python3
"""
Script para atualizar os códigos das operadoras para corresponder aos esperados pela API externa
"""

from apps import create_app, db
from apps.models import Operadora


def atualizar_codigos_operadoras():
    """Atualiza os códigos das operadoras para corresponder aos esperados pela API externa"""

    app = create_app()

    with app.app_context():
        print("🔄 Atualizando códigos das operadoras...")

        # Mapeamento de códigos atuais para códigos esperados pela API
        mapeamento = {
            'EMB': 'EMBRATEL',  # Embratel
            'VIV': 'VIVO',      # Vivo
            'DIG': 'DIGITALNET',  # Digitalnet
            'OI': 'OI'          # Oi (já está correto)
        }

        operadoras = Operadora.query.all()

        for operadora in operadoras:
            codigo_atual = operadora.codigo
            codigo_novo = mapeamento.get(codigo_atual, codigo_atual)

            if codigo_atual != codigo_novo:
                print(
                    f"📝 Atualizando {operadora.nome}: {codigo_atual} -> {codigo_novo}")
                operadora.codigo = codigo_novo
            else:
                print(f"✅ {operadora.nome}: {codigo_atual} (já está correto)")

        # Commit das alterações
        db.session.commit()

        print("\n📊 Operadoras após atualização:")
        operadoras_atualizadas = Operadora.query.all()
        for op in operadoras_atualizadas:
            print(f"  - {op.nome}: {op.codigo}")

        print("\n✅ Atualização concluída!")


def verificar_mapeamento():
    """Verifica o mapeamento atual das operadoras"""

    app = create_app()

    with app.app_context():
        print("🔍 Verificando mapeamento atual das operadoras...")

        operadoras = Operadora.query.all()

        print("\n📋 Operadoras cadastradas:")
        for op in operadoras:
            print(f"  - {op.nome}: {op.codigo}")

        print("\n🎯 Códigos esperados pela API externa:")
        codigos_api = ['OI', 'VIVO', 'EMBRATEL', 'DIGITALNET']
        for codigo in codigos_api:
            print(f"  - {codigo}")

        print("\n📊 Status do mapeamento:")
        for op in operadoras:
            if op.codigo in codigos_api:
                print(f"  ✅ {op.nome}: {op.codigo} (compatível)")
            else:
                print(f"  ❌ {op.nome}: {op.codigo} (incompatível)")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "verificar":
        verificar_mapeamento()
    else:
        atualizar_codigos_operadoras()
