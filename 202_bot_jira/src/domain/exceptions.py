"""Errores de validación a nivel de dominio."""


class DomainError(Exception):
    """Error base para fallos de validación de reglas de negocio."""


class InvalidTicketError(DomainError):
    """El código de ticket no cumple el formato esperado (p.ej. ABC-123)."""


class InvalidTimeFormatError(DomainError):
    """El valor de horas no tiene un formato soportado."""
