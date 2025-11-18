"""
Análisis profundo de latencia usando LangSmith traces.
Identifica exactamente dónde se gasta el tiempo.
"""
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from langsmith import Client
from collections import defaultdict
import statistics

load_dotenv()

api_key = os.getenv("LANGCHAIN_API_KEY")
project = os.getenv("LANGCHAIN_PROJECT", "appointment-agent-v2")

if not api_key:
    print("❌ LANGCHAIN_API_KEY no configurada")
    exit(1)

client = Client(api_key=api_key)

print("🔍 ANÁLISIS PROFUNDO DE LATENCIA")
print("=" * 100)

# Obtener runs recientes exitosos (últimas 2 horas)
start_time = datetime.now() - timedelta(hours=2)

runs = list(client.list_runs(
    project_name=project,
    start_time=start_time,
    limit=30,
    is_root=True
))

# Filtrar solo exitosos
successful_runs = [r for r in runs if r.status == "success" and r.end_time]

if not successful_runs:
    print("⚠️  No hay runs exitosos recientes para analizar")
    exit(0)

print(f"📊 Analizando {len(successful_runs)} runs exitosos\n")

# Analizar cada run en detalle
latencies = []
node_times = defaultdict(list)  # {node_name: [latencies]}
llm_times = []
tool_times = []
token_counts = []
iteration_counts = []

for run in successful_runs[:10]:  # Analizar los 10 más recientes en detalle
    run_id = run.id

    # Obtener detalles completos del run
    try:
        detailed_run = client.read_run(run_id)

        # Latencia total
        total_latency = (run.end_time - run.start_time).total_seconds() * 1000
        latencies.append(total_latency)

        # Obtener child runs (nodos del grafo)
        child_runs = list(client.list_runs(
            project_name=project,
            trace_id=run_id,
            is_root=False
        ))

        iteration_counts.append(len(child_runs))

        # Analizar cada nodo
        for child in child_runs:
            if child.end_time and child.start_time:
                node_latency = (child.end_time - child.start_time).total_seconds() * 1000
                node_name = child.name or "unknown"
                node_times[node_name].append(node_latency)

                # Detectar tipo de nodo
                if "llm" in node_name.lower() or "chat" in node_name.lower():
                    llm_times.append(node_latency)
                elif "tool" in node_name.lower():
                    tool_times.append(node_latency)

        # Obtener tokens si están disponibles
        if hasattr(detailed_run, 'outputs') and detailed_run.outputs:
            usage = detailed_run.outputs.get('usage_metadata', {})
            if usage:
                tokens = usage.get('total_tokens', 0)
                if tokens:
                    token_counts.append(tokens)

    except Exception as e:
        print(f"⚠️  Error analizando run {run_id}: {e}")
        continue

# REPORTE DE ANÁLISIS
print("\n" + "=" * 100)
print("📈 MÉTRICAS GLOBALES")
print("=" * 100)

if latencies:
    print(f"\n⏱️  LATENCIA TOTAL:")
    print(f"   Promedio: {statistics.mean(latencies):,.0f}ms")
    print(f"   Mediana: {statistics.median(latencies):,.0f}ms")
    print(f"   Mínima: {min(latencies):,.0f}ms")
    print(f"   Máxima: {max(latencies):,.0f}ms")
    print(f"   Desviación std: {statistics.stdev(latencies):,.0f}ms" if len(latencies) > 1 else "")

if iteration_counts:
    print(f"\n🔄 ITERACIONES DEL GRAFO (pasos de ejecución):")
    print(f"   Promedio de nodos ejecutados: {statistics.mean(iteration_counts):,.1f}")
    print(f"   Mínimo: {min(iteration_counts)}")
    print(f"   Máximo: {max(iteration_counts)}")
    print(f"   ⚠️  Cada iteración = 1 ciclo agent → tools → agent")

if token_counts:
    print(f"\n🎫 TOKENS:")
    print(f"   Promedio por run: {statistics.mean(token_counts):,.0f}")
    print(f"   Total en muestra: {sum(token_counts):,}")

# Análisis por tipo de nodo
print("\n" + "=" * 100)
print("🔍 DESGLOSE POR TIPO DE OPERACIÓN")
print("=" * 100)

if llm_times:
    print(f"\n🤖 LLAMADAS AL LLM (OpenAI):")
    print(f"   Promedio: {statistics.mean(llm_times):,.0f}ms")
    print(f"   Mediana: {statistics.median(llm_times):,.0f}ms")
    print(f"   Mínima: {min(llm_times):,.0f}ms")
    print(f"   Máxima: {max(llm_times):,.0f}ms")
    print(f"   Total de llamadas en muestra: {len(llm_times)}")
    print(f"   ⚠️  HALLAZGO: {(statistics.mean(llm_times) / statistics.mean(latencies) * 100):,.0f}% del tiempo total")

if tool_times:
    print(f"\n🔧 EJECUCIÓN DE TOOLS:")
    print(f"   Promedio: {statistics.mean(tool_times):,.0f}ms")
    print(f"   Mediana: {statistics.median(tool_times):,.0f}ms")
    print(f"   Mínima: {min(tool_times):,.0f}ms")
    print(f"   Máxima: {max(tool_times):,.0f}ms")
    print(f"   Total de llamadas en muestra: {len(tool_times)}")

# Análisis detallado por nodo específico
print("\n" + "=" * 100)
print("📊 DESGLOSE POR NODO DEL GRAFO")
print("=" * 100)

for node_name, times in sorted(node_times.items(), key=lambda x: -statistics.mean(x[1])):
    if times:
        avg = statistics.mean(times)
        print(f"\n📍 {node_name}:")
        print(f"   Promedio: {avg:,.0f}ms")
        print(f"   Mínima: {min(times):,.0f}ms")
        print(f"   Máxima: {max(times):,.0f}ms")
        print(f"   Ejecuciones: {len(times)}")

        # Calcular % del total
        if latencies:
            pct = (avg / statistics.mean(latencies)) * 100
            print(f"   % del tiempo total: {pct:.1f}%")

# Análisis de un run específico en detalle
print("\n" + "=" * 100)
print("🔬 ANÁLISIS DETALLADO DE UN RUN COMPLETO (El más reciente)")
print("=" * 100)

if successful_runs:
    latest_run = successful_runs[0]
    print(f"\nRun ID: {latest_run.id}")
    print(f"Timestamp: {latest_run.start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    total_time = (latest_run.end_time - latest_run.start_time).total_seconds() * 1000
    print(f"Latencia total: {total_time:,.0f}ms")

    # Obtener todos los child runs en orden cronológico
    child_runs = list(client.list_runs(
        project_name=project,
        trace_id=latest_run.id,
        is_root=False
    ))

    # Ordenar por timestamp
    child_runs_sorted = sorted(
        [c for c in child_runs if c.start_time],
        key=lambda x: x.start_time
    )

    print(f"\nSecuencia de ejecución ({len(child_runs_sorted)} pasos):")
    print("-" * 100)

    cumulative_time = 0
    for i, child in enumerate(child_runs_sorted, 1):
        if child.end_time and child.start_time:
            duration = (child.end_time - child.start_time).total_seconds() * 1000
            cumulative_time += duration

            # Calcular % del total
            pct = (duration / total_time) * 100

            # Detectar tipo
            node_type = "🤖 LLM" if any(x in child.name.lower() for x in ["llm", "chat", "openai"]) else \
                       "🔧 Tool" if "tool" in child.name.lower() else \
                       "⚙️  Node"

            print(f"{i}. {node_type} | {child.name:30} | {duration:6,.0f}ms ({pct:4.1f}%)")

    print("-" * 100)
    print(f"Tiempo acumulado de nodos: {cumulative_time:,.0f}ms")
    print(f"Overhead del framework: {total_time - cumulative_time:,.0f}ms ({((total_time - cumulative_time)/total_time*100):.1f}%)")

print("\n" + "=" * 100)
print("🎯 CONCLUSIONES")
print("=" * 100)
print("\nPosibles cuellos de botella identificados:")
print("1. Revisa el % de tiempo en llamadas LLM vs tools")
print("2. Revisa el número de iteraciones - múltiples ciclos = múltiples llamadas LLM")
print("3. Revisa el overhead del framework")
print("4. Revisa si hay tools lentas (>500ms)")
print("\n")
