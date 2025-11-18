"""
Script para obtener detalles completos de un error específico.
"""
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from langsmith import Client

load_dotenv()

api_key = os.getenv("LANGCHAIN_API_KEY")
project = os.getenv("LANGCHAIN_PROJECT", "appointment-agent-v2")

if not api_key:
    print("❌ LANGCHAIN_API_KEY no configurada")
    exit(1)

client = Client(api_key=api_key)

# Buscar runs con errores en las últimas 24 horas
start_time = datetime.now() - timedelta(hours=24)

runs = list(client.list_runs(
    project_name=project,
    start_time=start_time,
    limit=50,
    is_root=True
))

# Filtrar solo los que tienen errores
error_runs = [r for r in runs if r.error]

print(f"🔍 Encontrados {len(error_runs)} runs con errores\n")
print("=" * 80)

for i, run in enumerate(error_runs[:3], 1):  # Mostrar primeros 3
    print(f"\n{i}. ERROR RUN:")
    print(f"   ID: {run.id}")
    print(f"   Timestamp: {run.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Estado: {run.status}")

    if run.end_time and run.start_time:
        latency = (run.end_time - run.start_time).total_seconds() * 1000
        print(f"   Latencia: {latency:,.0f}ms")

    print(f"\n   ❌ ERROR COMPLETO:")
    print(f"   {run.error}")

    # Intentar obtener más detalles del run
    try:
        detailed_run = client.read_run(run.id)

        # Mostrar inputs si existen
        if hasattr(detailed_run, 'inputs') and detailed_run.inputs:
            print(f"\n   📥 INPUTS (primeros 500 chars):")
            inputs_str = str(detailed_run.inputs)[:500]
            print(f"   {inputs_str}...")

        # Mostrar outputs si existen
        if hasattr(detailed_run, 'outputs') and detailed_run.outputs:
            print(f"\n   📤 OUTPUTS (primeros 500 chars):")
            outputs_str = str(detailed_run.outputs)[:500]
            print(f"   {outputs_str}...")

    except Exception as e:
        print(f"   ⚠️  No se pudieron obtener detalles adicionales: {e}")

    print("\n" + "-" * 80)
