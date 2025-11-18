"""
Script para consultar métricas de latencia desde LangSmith.
"""
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from langsmith import Client

# Cargar variables de entorno
load_dotenv()

def get_recent_traces(hours=1, limit=20):
    """
    Obtiene traces recientes de LangSmith con métricas de latencia.

    Args:
        hours: Cuántas horas atrás buscar
        limit: Número máximo de traces a obtener
    """
    # Verificar configuración
    api_key = os.getenv("LANGCHAIN_API_KEY")
    project = os.getenv("LANGCHAIN_PROJECT", "appointment-agent-v2")

    if not api_key:
        print("❌ LANGCHAIN_API_KEY no configurada")
        return

    print(f"🔍 Consultando LangSmith...")
    print(f"   Proyecto: {project}")
    print(f"   Período: últimas {hours} hora(s)")
    print("=" * 80)

    # Crear cliente
    client = Client(api_key=api_key)

    # Calcular timestamp de inicio
    start_time = datetime.now() - timedelta(hours=hours)

    try:
        # Obtener runs del proyecto
        runs = list(client.list_runs(
            project_name=project,
            start_time=start_time,
            limit=limit,
            is_root=True  # Solo runs principales, no sub-runs
        ))

        if not runs:
            print(f"\n⚠️  No se encontraron traces en las últimas {hours} hora(s)")
            print(f"   Proyecto: {project}")
            return

        print(f"\n📊 Se encontraron {len(runs)} traces:\n")

        # Procesar y mostrar métricas
        total_latency = 0
        total_tokens = 0
        run_count = 0

        for i, run in enumerate(runs, 1):
            # Calcular latencia en ms
            if run.end_time and run.start_time:
                latency_ms = (run.end_time - run.start_time).total_seconds() * 1000
                total_latency += latency_ms
                run_count += 1

                # Obtener tokens si están disponibles
                tokens = None
                if hasattr(run, 'outputs') and run.outputs:
                    usage = run.outputs.get('usage_metadata', {})
                    if usage:
                        tokens = usage.get('total_tokens', 0)
                        if tokens:
                            total_tokens += tokens

                # Formatear timestamp
                timestamp = run.start_time.strftime("%H:%M:%S")

                # Mostrar información del run
                status = "✅" if run.status == "success" else "❌"
                print(f"{i}. {status} [{timestamp}] Latencia: {latency_ms:,.0f}ms", end="")

                if tokens:
                    print(f" | Tokens: {tokens}", end="")

                # Mostrar nombre o tipo de run
                if run.name:
                    print(f" | {run.name}", end="")

                # Mostrar error si existe
                if run.error:
                    print(f" | ERROR: {run.error[:50]}...", end="")

                print()  # Nueva línea

        # Mostrar estadísticas agregadas
        if run_count > 0:
            avg_latency = total_latency / run_count
            print("\n" + "=" * 80)
            print(f"📈 ESTADÍSTICAS:")
            print(f"   Total de traces: {run_count}")
            print(f"   Latencia promedio: {avg_latency:,.0f}ms")
            print(f"   Latencia mínima: {min([((r.end_time - r.start_time).total_seconds() * 1000) for r in runs if r.end_time]):,.0f}ms")
            print(f"   Latencia máxima: {max([((r.end_time - r.start_time).total_seconds() * 1000) for r in runs if r.end_time]):,.0f}ms")
            if total_tokens > 0:
                print(f"   Total tokens: {total_tokens:,}")
                print(f"   Promedio tokens/trace: {total_tokens / run_count:,.0f}")

    except Exception as e:
        print(f"\n❌ Error al consultar LangSmith: {e}")
        import traceback
        traceback.print_exc()


def get_detailed_run(run_id=None):
    """
    Obtiene detalles de un run específico o el más reciente.
    """
    api_key = os.getenv("LANGCHAIN_API_KEY")
    project = os.getenv("LANGCHAIN_PROJECT", "appointment-agent-v2")

    if not api_key:
        print("❌ LANGCHAIN_API_KEY no configurada")
        return

    client = Client(api_key=api_key)

    try:
        if run_id:
            run = client.read_run(run_id)
        else:
            # Obtener el run más reciente
            runs = list(client.list_runs(
                project_name=project,
                limit=1,
                is_root=True
            ))
            if not runs:
                print("⚠️  No hay runs disponibles")
                return
            run = runs[0]

        print("\n" + "=" * 80)
        print(f"🔍 DETALLES DEL RUN: {run.id}")
        print("=" * 80)
        print(f"Nombre: {run.name}")
        print(f"Estado: {run.status}")
        print(f"Inicio: {run.start_time}")
        print(f"Fin: {run.end_time}")

        if run.end_time and run.start_time:
            latency = (run.end_time - run.start_time).total_seconds() * 1000
            print(f"Latencia: {latency:,.0f}ms")

        if hasattr(run, 'outputs') and run.outputs:
            print(f"\nOutputs: {run.outputs}")

        if run.error:
            print(f"\n❌ Error: {run.error}")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    import sys

    # Permitir especificar horas como argumento
    hours = 1
    if len(sys.argv) > 1:
        try:
            hours = int(sys.argv[1])
        except ValueError:
            print("Uso: python check_langsmith_metrics.py [horas]")
            sys.exit(1)

    get_recent_traces(hours=hours)
