#!/usr/bin/env python3
"""
Script de prueba para verificar LangSmith tracing.

Ejecuta este script para confirmar que el tracing está funcionando correctamente.
"""
import os
from dotenv import load_dotenv
from src.tracing import setup_langsmith_tracing, get_trace_url

# Cargar variables de entorno
load_dotenv()

def test_tracing_config():
    """Verifica la configuración de LangSmith."""
    print("🔍 Verificando configuración de LangSmith...\n")

    # Verificar variables
    tracing_enabled = os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true"
    api_key = os.getenv("LANGCHAIN_API_KEY", "")
    project = os.getenv("LANGCHAIN_PROJECT", "appointment-agent-v1.2")

    print(f"LANGCHAIN_TRACING_V2: {tracing_enabled}")
    print(f"LANGCHAIN_API_KEY: {'✅ Configurado' if api_key else '❌ No configurado'}")
    print(f"LANGCHAIN_PROJECT: {project}\n")

    if not tracing_enabled:
        print("⚠️  Tracing está desactivado. Actívalo en .env:")
        print("   LANGCHAIN_TRACING_V2=true\n")
        return False

    if not api_key:
        print("⚠️  LANGCHAIN_API_KEY no está configurado.")
        print("   1. Ve a https://smith.langchain.com/")
        print("   2. Obtén tu API key")
        print("   3. Agrégala a .env\n")
        return False

    print("✅ Configuración correcta!\n")
    return True


def test_tracing_setup():
    """Prueba la función setup_langsmith_tracing()."""
    print("🚀 Probando setup_langsmith_tracing()...\n")

    try:
        setup_langsmith_tracing()
        print("✅ Función ejecutada correctamente!\n")
        return True
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return False


def test_simple_agent_call():
    """Prueba una llamada simple al agente."""
    print("🤖 Probando llamada al agente con tracing...\n")

    try:
        from src.agent import create_graph
        from langchain_core.messages import HumanMessage

        # Crear grafo
        graph = create_graph()

        # Estado inicial
        initial_state = {
            "messages": [HumanMessage(content="Hola")],
            "current_state": "collect_service",
            "collected_data": {},
            "available_slots": []
        }

        # Configuración para tracing
        config = {
            "configurable": {"thread_id": "test-tracing-001"}
        }

        # Invocar agente
        print("Enviando mensaje de prueba al agente...")
        result = graph.invoke(initial_state, config)

        print("✅ Agente respondió correctamente!")
        print(f"\nRespuesta: {result['messages'][-1].content[:100]}...\n")

        print("📊 Verifica el trace en LangSmith:")
        print(f"   https://smith.langchain.com/o/projects/p/{os.getenv('LANGCHAIN_PROJECT', 'appointment-agent-v1.2')}\n")

        return True

    except Exception as e:
        print(f"❌ Error: {e}\n")
        return False


def main():
    """Ejecuta todas las pruebas."""
    print("=" * 60)
    print("🔬 TEST DE LANGSMITH TRACING")
    print("=" * 60 + "\n")

    # Test 1: Configuración
    if not test_tracing_config():
        print("\n❌ Configura LangSmith antes de continuar.")
        print("   Lee: docs/LANGSMITH_QUICKSTART_ES.md\n")
        return

    # Test 2: Setup function
    if not test_tracing_setup():
        print("\n❌ Error en setup. Verifica tu configuración.\n")
        return

    # Test 3: Agent call
    print("⚠️  El siguiente test hará una llamada real al agente.")
    print("   Esto consumirá tokens de OpenAI.\n")

    response = input("¿Continuar? (s/n): ").lower().strip()
    if response == 's':
        test_simple_agent_call()
    else:
        print("\n⏭️  Test de agente omitido.\n")

    print("=" * 60)
    print("✨ TESTS COMPLETADOS")
    print("=" * 60 + "\n")

    print("📝 Próximos pasos:")
    print("   1. Ve a https://smith.langchain.com/")
    print("   2. Busca tu proyecto 'appointment-agent-v1.2'")
    print("   3. Verás el trace del test si ejecutaste el Test 3")
    print("   4. Ejecuta el agente normalmente: python chat_cli.py\n")


if __name__ == "__main__":
    main()
