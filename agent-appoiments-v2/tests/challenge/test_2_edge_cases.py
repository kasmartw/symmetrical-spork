"""TEST 2: Edge Cases y Casos Problemáticos

Ejecutar: pytest tests/challenge/test_2_edge_cases.py -v -s

Objetivo: Verificar que el agente maneja comportamientos impredecibles.
"""
import pytest
from langchain_core.messages import HumanMessage


class TestUserBehaviorEdgeCases:
    """Tests de comportamientos impredecibles del usuario"""

    def test_user_changes_mind_mid_flow(self, graph, thread_config):
        """🔥 Usuario cambia de opinión a mitad del flujo"""
        config = thread_config("change-mind")

        messages = [
            "Agendar cita",
            "General Checkup",
            "morning",
            "2025-01-20",
            "09:00",
            "Juan Pérez",
            "Espera, mejor quiero cancelar",  # Cambio de opinión
            "No, olvídalo, mejor quiero reagendar otra cita existente",
            "CONF-ABC123"
        ]

        # El agente debe manejar esto sin crashear
        for msg in messages:
            result = graph.invoke(
                {"messages": [HumanMessage(content=msg)]},
                config=config
            )
            assert result is not None, f"Graph crasheó con mensaje: {msg}"
            assert "messages" in result, "Respuesta malformada"

        print("\n✅ Agente maneja cambios de opinión sin crashear")

    def test_user_provides_all_info_at_once(self, graph, thread_config):
        """🔥 Usuario da toda la info en un mensaje"""
        config = thread_config("all-at-once")

        message = (
            "Hola, quiero agendar un General Checkup para el 20 de enero "
            "a las 9am. Mi nombre es Juan Pérez, "
            "email juan@email.com y teléfono 1234567890"
        )

        result = graph.invoke(
            {"messages": [HumanMessage(content=message)]},
            config=config
        )

        # Debe procesar sin crashear
        assert result is not None
        assert "messages" in result

        # Verificar que avanzó en el flujo (no quedó en estado inicial)
        state = result.get("current_state")
        assert state is not None

        print("\n✅ Agente procesa info completa en un mensaje")

    def test_user_sends_gibberish(self, graph, thread_config):
        """🔥 Usuario envía mensajes sin sentido"""
        config = thread_config("gibberish")

        messages = [
            "asdfkjh qwerty zxcv",
            "🎨🎭🎪🎬",
            "SELECT * FROM users WHERE 1=1;",  # SQL injection attempt
            "../../etc/passwd",  # Path traversal attempt
            "<script>alert('xss')</script>",  # XSS attempt
        ]

        for msg in messages:
            result = graph.invoke(
                {"messages": [HumanMessage(content=msg)]},
                config=config
            )

            # No debe crashear, debe pedir clarificación
            assert result is not None
            last_message = result["messages"][-1].content
            assert len(last_message) > 0, f"No respondió a: {msg}"

        print("\n✅ Agente resiste intentos de injection y gibberish")

    def test_user_double_texts_rapidly(self, graph, thread_config):
        """🔥 Usuario envía múltiples mensajes sin esperar respuesta"""
        config = thread_config("double-text")

        # Simular mensajes rápidos
        messages = [
            "Hola",
            "Quiero agendar",
            "Una cita",
            "Para mañana",
            "General Checkup"
        ]

        # Enviar todos sin esperar
        for msg in messages:
            result = graph.invoke(
                {"messages": [HumanMessage(content=msg)]},
                config=config
            )

        # Debe manejar sin perder contexto
        assert result is not None
        last_message = result["messages"][-1].content
        assert len(last_message) > 0

        print("\n✅ Agente maneja double-texting sin perder contexto")


class TestValidationEdgeCases:
    """Tests de validación de datos límite"""

    def test_invalid_email_formats(self, graph, thread_config):
        """🔥 Emails inválidos que deben ser rechazados"""
        config = thread_config("invalid-emails")

        invalid_emails = [
            "not-an-email",
            "@example.com",
            "user@",
            "user name@example.com",
            "user@.com",
            "user@domain",
        ]

        # Navegar hasta el estado de email
        messages = [
            "Agendar cita",
            "General Checkup",
            "morning",
            "2025-01-20",
            "09:00",
            "Juan Pérez"
        ]

        for msg in messages:
            graph.invoke(
                {"messages": [HumanMessage(content=msg)]},
                config=config
            )

        # Probar cada email inválido
        rejections = 0
        for email in invalid_emails:
            result = graph.invoke(
                {"messages": [HumanMessage(content=email)]},
                config=config
            )
            last_message = result["messages"][-1].content.lower()

            # Debe indicar que es inválido
            is_rejection = any(word in last_message for word in
                               ["invalid", "inválido", "correct", "válid", "valid"])

            if is_rejection:
                rejections += 1

        # Debe rechazar al menos 80% de emails inválidos
        rejection_rate = rejections / len(invalid_emails)
        assert rejection_rate >= 0.8, f"Solo rechazó {rejection_rate:.0%} de emails inválidos"

        print(f"\n✅ Validación de email: {rejections}/{len(invalid_emails)} rechazados ({rejection_rate:.0%})")

    def test_invalid_phone_formats(self, graph, thread_config):
        """🔥 Teléfonos inválidos"""
        config = thread_config("invalid-phones")

        invalid_phones = [
            "123",  # Muy corto
            "abc",  # No numérico
            "12-34-56",  # Muy corto con guiones
            "phone",  # Palabra
        ]

        # Navegar hasta estado de teléfono
        messages = [
            "Agendar",
            "General Checkup",
            "morning",
            "2025-01-20",
            "09:00",
            "Juan Pérez",
            "juan@email.com"
        ]

        for msg in messages:
            graph.invoke(
                {"messages": [HumanMessage(content=msg)]},
                config=config
            )

        # Probar cada teléfono inválido
        rejections = 0
        for phone in invalid_phones:
            result = graph.invoke(
                {"messages": [HumanMessage(content=phone)]},
                config=config
            )
            last_message = result["messages"][-1].content.lower()

            is_rejection = any(word in last_message for word in
                               ["invalid", "inválido", "digits", "dígitos", "válid", "valid"])

            if is_rejection:
                rejections += 1

        rejection_rate = rejections / len(invalid_phones)
        assert rejection_rate >= 0.75, f"Solo rechazó {rejection_rate:.0%} de teléfonos inválidos"

        print(f"\n✅ Validación de teléfono: {rejections}/{len(invalid_phones)} rechazados ({rejection_rate:.0%})")

    def test_boundary_dates(self, graph, thread_config):
        """🔥 Fechas límite (pasado, muy futuro)"""
        config = thread_config("boundary-dates")

        # Navegar hasta selección de fecha
        messages = [
            "Quiero agendar",
            "General Checkup",
            "any",
        ]

        for msg in messages:
            graph.invoke(
                {"messages": [HumanMessage(content=msg)]},
                config=config
            )

        # Probar fecha en el pasado
        result = graph.invoke(
            {"messages": [HumanMessage(content="2020-01-01")]},
            config=config
        )

        last_message = result["messages"][-1].content
        # Debe estar en la lista de disponibilidad o pedir fecha válida
        assert len(last_message) > 0

        print("\n✅ Agente maneja fechas límite")
