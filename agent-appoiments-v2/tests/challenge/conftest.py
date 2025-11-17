"""Configuración compartida para tests de desafío del agente.

Este archivo contiene fixtures de pytest reutilizables.
"""
import pytest
from datetime import datetime, timedelta
from src.agent import create_graph
from langchain_core.messages import HumanMessage


def get_future_date(days_ahead=7):
    """Generate a future date string in YYYY-MM-DD format."""
    future_date = datetime.now() + timedelta(days=days_ahead)
    return future_date.strftime("%Y-%m-%d")


@pytest.fixture(scope="session")
def graph():
    """Graph instance para todos los tests (reutilizable)."""
    return create_graph()


@pytest.fixture
def thread_config():
    """Factory para crear configs de thread únicos con recursion_limit."""
    counter = {"value": 0}

    def _make_config(prefix="test"):
        counter["value"] += 1
        thread_id = f"{prefix}-{counter['value']}"
        return {"configurable": {"thread_id": thread_id, "recursion_limit": 10}}

    return _make_config


@pytest.fixture(scope="session")
def booking_confirmation(graph):
    """
    Crea un booking real y retorna el confirmation number.

    Se ejecuta UNA vez por sesión de pytest y se reutiliza.
    """
    thread_id = "fixture-booking"
    config = {"configurable": {"thread_id": thread_id, "recursion_limit": 10}}

    messages = [
        "Hola, quiero agendar una cita",
        "General Consultation",  # Servicio (nombre exacto del config)
        "morning",
        get_future_date(3),  # Fecha (3 días en el futuro)
        "09:00",
        "Test User",
        "test@example.com",
        "+1234567890",
        "sí, confirmar"
    ]

    confirmation_number = None

    for msg in messages:
        result = graph.invoke(
            {"messages": [HumanMessage(content=msg)]},
            config=config
        )
        last_message = result["messages"][-1].content

        if "confirmation" in last_message.lower() or "appt-" in last_message.lower():
            import re
            match = re.search(r'APPT-\d+', last_message, re.IGNORECASE)
            if match:
                confirmation_number = match.group()

    if not confirmation_number:
        pytest.skip("No se pudo crear booking para fixture")

    return confirmation_number


def extract_confirmation_number(message: str) -> str:
    """Helper para extraer confirmation number de un mensaje."""
    import re
    match = re.search(r'APPT-\d+', message, re.IGNORECASE)
    return match.group() if match else None
