import re
from datetime import datetime

FIELD_NAMES = {
    "rfc": "RFC",
    "razon_social": "Razón social",
    "cp": "Código postal",
    "regimen_fiscal": "Régimen fiscal",
    "uso_cfdi": "Uso de CFDI",
    "correo": "Correo",
    "ticket": "Ticket / Folio",
    "fecha": "Fecha",
    "hora": "Hora",
    "total": "Total",
    "tc": "TC",
    "tr": "TR",
    "itu": "ITU",
    "sucursal": "Sucursal"
}

def validate(data):
    issues = []
    rfc = str(data.get("rfc", "")).strip()
    if rfc and not re.fullmatch(r"[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{2,3}", rfc.upper()):
        issues.append(("RFC_FORMAT", "El RFC no tiene un formato válido.", "Revisa que no tenga espacios, guiones o caracteres copiados de más."))
    cp = str(data.get("cp", "")).strip()
    if cp and not re.fullmatch(r"\d{5}", cp):
        issues.append(("CP_FORMAT", "El código postal fiscal debe tener 5 dígitos.", "Configura el CP fiscal correcto en Configuración."))
    total = str(data.get("total", "")).replace(",", "").replace("$", "").strip()
    if total:
        try:
            if float(total) < 0:
                raise ValueError
        except ValueError:
            issues.append(("TOTAL_FORMAT", "El total del ticket no pudo validarse.", "Revisa la foto o recorta la zona del total y vuelve a leerla."))
    for key in ("tc", "tr", "itu", "ticket"):
        val = str(data.get(key, "")).strip()
        if val and len(re.sub(r"\D", "", val)) < 4:
            issues.append(("CODE_SHORT", f"{FIELD_NAMES[key]} parece incompleto.", "Revisa la foto y confirma todos los dígitos antes de facturar."))
    uso = str(data.get("uso_cfdi", "")).strip().upper()
    if uso and not re.fullmatch(r"[A-Z0-9]{3}", uso):
        issues.append(("CFDI_FORMAT", "El Uso de CFDI parece inválido.", "Usa un código de 3 caracteres configurado en tu perfil fiscal."))
    return issues

def explain_failure(field):
    name = FIELD_NAMES.get(field, field)
    return f"No se pudo completar «{name}» automáticamente.", (
        "Selecciona manualmente el campo correcto en Asistencia y aprendizaje. "
        "La aplicación guardará esta corrección y utilizará el ejemplo en futuros portales."
    )
