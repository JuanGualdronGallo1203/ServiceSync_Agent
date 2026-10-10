"""
Contexto base y catálogo oficial de servicios automotrices de ServiceSync.
Este catálogo sirve de anclaje de verdad (ground truth) para evitar alucinaciones.
"""

AUTOMOTIVE_SERVICES_CATALOG = {
    "mantenimiento_preventivo": {
        "nombre": "Mantenimiento Preventivo por Kilometraje",
        "descripcion": "Servicio de rutina para conservar la vida útil y garantía del vehículo (5k, 10k, 20k, 50k km).",
        "actividades": [
            "Cambio de aceite de motor (especificación sintético o mineral según fabricante)",
            "Reemplazo de filtro de aceite de motor",
            "Inspección y/o reemplazo de filtro de aire de motor",
            "Inspección y/o reemplazo de filtro de cabina (aire acondicionado)",
            "Inspección de 25 puntos de seguridad (luces, fluidos, correas, mangueras)",
        ],
        "precio_politica": "El costo final depende de la capacidad de aceite (litros), tipo de viscosidad y motorización del vehículo. Requiere cotización basada en ficha técnica.",
    },
    "sistema_de_frenos": {
        "nombre": "Servicio y Diagnóstico del Sistema de Frenos",
        "descripcion": "Revisión integral de seguridad en el sistema de frenado hidráulico y de fricción.",
        "actividades": [
            "Inspección de desgaste de pastillas/balatas y zapatas",
            "Medición de espesor y tolerancia de discos y tambores",
            "Rectificado de discos de freno (sujeto a tolerancia mínima de seguridad)",
            "Purga y sustitución de líquido de frenos (especificación DOT 3 o DOT 4)",
            "Diagnóstico de sensores ABS y módulos de control de estabilidad",
        ],
        "precio_politica": "Varía por eje (delantero/trasero) y marca de repuesto homologada. No se otorgan precios ciegos sin medir el desgaste de discos.",
    },
    "suspension_y_direccion": {
        "nombre": "Alineación, Balanceo y Tren Delantero",
        "descripcion": "Calibración geométrica computarizada y estabilidad dinámica de rodaje.",
        "actividades": [
            "Alineación 3D computarizada de dirección por eje",
            "Balanceo dinámico computarizado de neumáticos",
            "Rotación de llantas con patrón técnico según tracción (FWD/RWD/AWD)",
            "Inspección de amortiguadores, rótulas, bujes, terminales y terminales de dirección",
        ],
        "precio_politica": "Sujeto a inspección de holguras en terminales y bujes antes de realizar el servicio.",
    },
    "diagnostico_electronico": {
        "nombre": "Escaneo Electrónico y Diagnóstico OBD-II",
        "descripcion": "Lectura avanzada de códigos de avería (DTC) y parámetros en tiempo real.",
        "actividades": [
            "Escaneo de computadora de motor (ECU/ECM), transmisión (TCM) y bolsas de aire (SRS)",
            "Lectura y borrado de códigos de falla Check Engine",
            "Prueba de sensores de oxígeno, flujo de masa de aire (MAF) y cuerpo de aceleración",
            "Prueba del estado del sistema de carga (batería y alternador)",
        ],
        "precio_politica": "El costo del escaneo incluye el reporte de diagnóstico y propuesta técnica de reparación.",
    },
    "sistema_de_enfriamiento": {
        "nombre": "Mantenimiento del Sistema de Refrigeración",
        "descripcion": "Prevención de fallas térmicas y sobrecalentamiento del motor.",
        "actividades": [
            "Prueba de presión y detección de fugas en radiador y mangueras",
            "Comprobación del punto de ebullición del anticongelante/refrigerante",
            "Drenado y relleno con refrigerante orgánico (OAT/HOAT)",
            "Inspección de termostato y motoventilador",
        ],
        "precio_politica": "Cotización según volumen en litros del circuito refrigerante del modelo específico.",
    },
}

SERVICES_NOT_SUPPORTED = [
    "Hojalatería y pintura de carrocería pesada / colisiones mayores",
    "Blindaje automotriz o modificación estructural de chasis",
    "Modificaciones ilegales o reprogramaciones no certificadas (chiptuning / stage racing)",
    "Venta de autopartes sueltas al público sin instalación en taller",
]

POLITICA_ESTRICTA_DE_PRECIOS = """
POLÍTICA DE PRECIOS Y COTIZACIONES:
- Los precios varían según: Marca, Modelo, Año, Cilindrada del motor y condición de desgaste de las piezas.
- El taller NO autoriza precios fijos inventados por el asistente sin una orden de servicio o inspección técnica.
- Instrucción al cliente: "Para darte un presupuesto exacto y transparente, necesitamos registrar tu vehículo (marca, modelo y año) y realizar una inspección técnica o cotización formal con el área de refacciones."
"""


def get_catalog_summary() -> str:
    """Retorna un resumen estructurado del catálogo para inyección de contexto."""
    lines = ["=== CATÁLOGO OFICIAL DE SERVICIOS SERVICESYNC ==="]
    for key, data in AUTOMOTIVE_SERVICES_CATALOG.items():
        lines.append(f"\n* {data['nombre']}:")
        lines.append(f"  - Descripción: {data['descripcion']}")
        lines.append(f"  - Tareas incluidas: {', '.join(data['actividades'])}")
        lines.append(f"  - Consideración: {data['precio_politica']}")

    lines.append("\n=== SERVICIOS NO DISPONIBLES ===")
    for item in SERVICES_NOT_SUPPORTED:
        lines.append(f"- {item}")

    lines.append(f"\n{POLITICA_ESTRICTA_DE_PRECIOS}")
    return "\n".join(lines)
