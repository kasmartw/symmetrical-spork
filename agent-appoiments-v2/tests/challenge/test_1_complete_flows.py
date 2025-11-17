"""TEST 1: Flujos Completos End-to-End

Ejecutar: pytest tests/challenge/test_1_complete_flows.py -v -s

Objetivo: Verificar que el agente completa flujos completos sin errores.
"""
import pytest
import time
import re
from datetime import datetime, timedelta
from langchain_core.messages import HumanMessage


def get_future_date(days_ahead=7):
    """Generate a future date string in YYYY-MM-DD format."""
    future_date = datetime.now() + timedelta(days=days_ahead)
    return future_date.strftime("%Y-%m-%d")


class TestCompleteBookingFlows:
    """Test de flujos completos de principio a fin"""

    def test_perfect_booking_flow_spanish(self, graph, thread_config):
        """✅ Usuario perfecto que sigue el flujo feliz en español"""
        config = thread_config("perfect-spanish")

        # Simular conversación completa
        messages = [
            "Hola, quiero agendar una cita",
            "General Consultation",  # Servicio (nombre exacto del config)
            "morning",  # Time preference
            get_future_date(4),  # Fecha (4 días en el futuro)
            "09:00",  # Hora
            "Juan Pérez",  # Nombre
            "juan.perez@email.com",  # Email
            "+1234567890",  # Teléfono
            "sí, confirmar"  # Confirmación
        ]

        start_time = time.time()
        confirmation_number = None

        for msg in messages:
            result = graph.invoke(
                {"messages": [HumanMessage(content=msg)]},
                config=config
            )
            last_message = result["messages"][-1].content

            # Capturar confirmation number del último mensaje
            if "confirmation" in last_message.lower() or "appt-" in last_message.lower():
                match = re.search(r'APPT-\d+', last_message, re.IGNORECASE)
                if match:
                    confirmation_number = match.group()

        total_time = time.time() - start_time

        # Assertions
        assert confirmation_number is not None, "No se generó confirmation number"
        assert total_time < 120, f"Flujo tomó {total_time}s (límite: 120s)"

        print(f"\n✅ Booking completo: {confirmation_number}")
        print(f"⏱️  Tiempo total: {total_time:.2f}s")
        print(f"📊 Mensajes: {len(messages)}")

    def test_perfect_booking_flow_english(self, graph, thread_config):
        """✅ Usuario perfecto en inglés"""
        config = thread_config("perfect-english")

        messages = [
            "Hi, I need to book an appointment",
            "General Consultation",  # Servicio (nombre exacto del config)
            "afternoon",
            get_future_date(5),  # Fecha (5 días en el futuro)
            "14:00",
            "John Smith",
            "john.smith@email.com",
            "+9876543210",
            "yes, confirm"
        ]

        start_time = time.time()
        confirmation_number = None

        for msg in messages:
            result = graph.invoke(
                {"messages": [HumanMessage(content=msg)]},
                config=config
            )
            last_message = result["messages"][-1].content

            if "confirmation" in last_message.lower() or "appt-" in last_message.lower():
                match = re.search(r'APPT-\d+', last_message, re.IGNORECASE)
                if match:
                    confirmation_number = match.group()

        total_time = time.time() - start_time

        assert confirmation_number is not None
        assert total_time < 120

        print(f"\n✅ Booking completo: {confirmation_number}")
        print(f"⏱️  Tiempo total: {total_time:.2f}s")


class TestCancellationFlow:
    """Test flujo de cancelación"""

    def test_cancellation_with_valid_confirmation(self, graph, thread_config, booking_confirmation):
        """✅ Cancelar cita con confirmation number válido"""
        config = thread_config("cancel-valid")

        messages = [
            "Quiero cancelar mi cita",
            booking_confirmation,  # Usar confirmation del fixture
            "sí, cancelar"
        ]

        for msg in messages:
            result = graph.invoke(
                {"messages": [HumanMessage(content=msg)]},
                config=config
            )

        last_message = result["messages"][-1].content
        assert "cancelad" in last_message.lower() or "canceled" in last_message.lower()
        print(f"\n✅ Cita cancelada: {booking_confirmation}")

    def test_cancellation_with_invalid_confirmation(self, graph, thread_config):
        """🔥 Cancelar con confirmation number inválido - debe escalar después de 2 intentos"""
        config = thread_config("cancel-invalid")

        messages = [
            "Cancelar mi cita",
            "CONF-INVALID123",  # Primer intento inválido
            "CONF-WRONG456",  # Segundo intento inválido
        ]

        for msg in messages:
            result = graph.invoke(
                {"messages": [HumanMessage(content=msg)]},
                config=config
            )

        last_message = result["messages"][-1].content

        # Debe escalar después de 2 intentos (transición a POST_ACTION)
        assert any(word in last_message.lower() for word in
                   ["contact", "llamar", "support", "ayuda", "locate", "email"])

        print(f"\n✅ Escalación correcta después de 2 intentos fallidos")


class TestRescheduleFlow:
    """Test flujo de reprogramación"""

    def test_reschedule_complete_flow(self, graph, thread_config, booking_confirmation):
        """✅ Reprogramar cita existente"""
        config = thread_config("reschedule-complete")

        messages = [
            "Necesito reprogramar mi cita",
            booking_confirmation,
            "2025-01-25",  # Nueva fecha
            "15:00",  # Nueva hora
            "sí, confirmar cambio"
        ]

        start_time = time.time()

        for msg in messages:
            result = graph.invoke(
                {"messages": [HumanMessage(content=msg)]},
                config=config
            )

        total_time = time.time() - start_time
        last_message = result["messages"][-1].content

        assert "reprogramad" in last_message.lower() or "rescheduled" in last_message.lower()
        assert total_time < 90  # Reschedule debería ser más rápido

        print(f"\n✅ Cita reprogramada: {booking_confirmation}")
        print(f"⏱️  Tiempo total: {total_time:.2f}s")
