"""
Plantilla para un portal específico.
Copiar a adapters/<sitio>.py cuando un comercio necesite lógica especial.
"""
from pathlib import Path

class SiteAdapter:
    merchant = "Ejemplo"

    def can_handle(self, merchant, portal_url):
        return merchant == self.merchant

    def before_fill(self, page, data):
        """Acciones especiales antes del llenado."""
        return None

    def after_fill(self, page, data):
        """Acciones especiales después del llenado."""
        return None

    def invoice_button(self, page):
        """Selector exacto cuando el portal requiere uno específico."""
        return None
