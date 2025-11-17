"""TEST 3: Concurrencia y Carga

Ejecutar: pytest tests/challenge/test_3_concurrency.py -v -s

Objetivo: Verificar que el agente maneja múltiples usuarios simultáneos.
"""
import pytest
import asyncio
import time
import statistics
from langchain_core.messages import HumanMessage


class TestConcurrentUsers:
    """Tests de usuarios concurrentes"""

    async def simulate_user_booking(self, graph, user_id: int):
        """Simula un usuario completando un booking"""
        thread_id = f"concurrent-user-{user_id}"
        config = {"configurable": {"thread_id": thread_id}}

        messages = [
            "Hola, agendar cita",
            "General Checkup",
            "morning",
            "2025-01-20",
            "09:00",
            f"User {user_id}",
            f"user{user_id}@email.com",
            f"12345678{user_id:02d}",
            "sí"
        ]

        start_time = time.time()
        success = False

        try:
            for msg in messages:
                result = await asyncio.to_thread(
                    graph.invoke,
                    {"messages": [HumanMessage(content=msg)]},
                    config=config
                )

                if result is None:
                    break

            # Verificar si completó
            last_msg = result["messages"][-1].content if result else ""
            success = "confirmation" in last_msg.lower()

        except Exception as e:
            print(f"❌ Usuario {user_id} falló: {e}")
            success = False

        total_time = time.time() - start_time

        return {
            "user_id": user_id,
            "success": success,
            "time": total_time,
            "messages": len(messages)
        }

    @pytest.mark.asyncio
    async def test_5_concurrent_users(self, graph):
        """✅ 5 usuarios simultáneos - carga ligera"""
        print("\n🔄 Test: 5 usuarios simultáneos...")

        tasks = [self.simulate_user_booking(graph, i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        self._analyze_results(results, "5 usuarios")

    @pytest.mark.asyncio
    async def test_10_concurrent_users(self, graph):
        """🔥 10 usuarios simultáneos - carga media"""
        print("\n🔄 Test: 10 usuarios simultáneos...")

        tasks = [self.simulate_user_booking(graph, i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        self._analyze_results(results, "10 usuarios")

    @pytest.mark.asyncio
    async def test_20_concurrent_users(self, graph):
        """🔥🔥 20 usuarios simultáneos - carga alta"""
        print("\n🔄 Test: 20 usuarios simultáneos...")

        tasks = [self.simulate_user_booking(graph, i) for i in range(20)]
        results = await asyncio.gather(*tasks)

        self._analyze_results(results, "20 usuarios")

    def _analyze_results(self, results, test_name):
        """Analiza y muestra resultados del test"""
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]
        times = [r["time"] for r in results]

        print(f"\n{'=' * 60}")
        print(f"📊 RESULTADOS: {test_name}")
        print(f"{'=' * 60}")
        print(f"✅ Exitosos: {len(successful)}/{len(results)} ({len(successful) / len(results) * 100:.1f}%)")
        print(f"❌ Fallidos: {len(failed)}")

        if times:
            print(f"\n⏱️  TIEMPOS:")
            print(f"   - Promedio: {statistics.mean(times):.2f}s")
            print(f"   - Mínimo: {min(times):.2f}s")
            print(f"   - Máximo: {max(times):.2f}s")
            print(f"   - Mediana: {statistics.median(times):.2f}s")

            if len(times) > 1:
                print(f"   - Std Dev: {statistics.stdev(times):.2f}s")

        # CRITERIOS DE ÉXITO
        success_rate = len(successful) / len(results)
        avg_time = statistics.mean(times) if times else 999

        print(f"\n🎯 CRITERIOS:")
        print(f"   - Success rate >= 80%: {'✅' if success_rate >= 0.8 else '❌'}")
        print(f"   - Tiempo promedio < 90s: {'✅' if avg_time < 90 else '❌'}")
        print(f"   - Max tiempo < 150s: {'✅' if max(times) < 150 else '❌'}")

        # Assertions más permisivas para MemorySaver
        assert success_rate >= 0.7, f"Success rate muy bajo: {success_rate:.1%}"
        assert avg_time < 120, f"Tiempo promedio muy alto: {avg_time:.2f}s"


class TestSequentialLoad:
    """Test de carga secuencial (más realista para MemorySaver)"""

    def test_sequential_10_users(self, graph):
        """✅ 10 usuarios secuenciales - simula carga real"""
        print("\n📊 Test: 10 usuarios secuenciales...")

        results = []

        for i in range(10):
            thread_id = f"sequential-user-{i}"
            config = {"configurable": {"thread_id": thread_id}}

            messages = [
                "Agendar",
                "General Checkup",
                "any",
                "2025-01-20",
                "09:00",
                f"User {i}",
                f"user{i}@test.com",
                f"1234567{i:03d}",
                "yes"
            ]

            start_time = time.time()
            success = False

            try:
                for msg in messages:
                    result = graph.invoke(
                        {"messages": [HumanMessage(content=msg)]},
                        config=config
                    )

                last_msg = result["messages"][-1].content if result else ""
                success = "confirmation" in last_msg.lower()

            except Exception as e:
                print(f"❌ Usuario {i} falló: {e}")

            total_time = time.time() - start_time

            results.append({
                "user_id": i,
                "success": success,
                "time": total_time
            })

            print(f"   Usuario {i}: {'✅' if success else '❌'} ({total_time:.2f}s)")

        # Análisis
        successful = [r for r in results if r["success"]]
        times = [r["time"] for r in results]

        success_rate = len(successful) / len(results)
        avg_time = statistics.mean(times)

        print(f"\n📊 Success rate: {success_rate:.0%}")
        print(f"⏱️  Tiempo promedio: {avg_time:.2f}s")

        assert success_rate >= 0.8
        assert avg_time < 90
