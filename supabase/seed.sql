-- ==============================================================================
-- ServiceSync Agent - Datos Semilla (Seed Data) para Hito S2
-- ==============================================================================

INSERT INTO public.servicios (id, nombre, precio_base, tiempo_estimado, descripcion)
VALUES
    (1, 'Mantenimiento Preventivo (Cambio de Aceite y Filtros)', 120.00, '45 min', 'Aceite sintético homologado, filtro de aceite, filtro de aire y revisión de 25 puntos.'),
    (2, 'Servicio y Diagnóstico de Sistema de Frenos', 180.00, '90 min', 'Pastillas cerámicas, rectificado de discos dentro de tolerancia y purga de líquido DOT 4.'),
    (3, 'Alineación y Balanceo Computarizado', 60.00, '40 min', 'Alineación 3D en 4 ruedas, balanceo dinámico y calibración de presión con nitrógeno.'),
    (4, 'Diagnóstico Electrónico Computarizado (Scanner OBD-II)', 50.00, '30 min', 'Escaneo completo de módulos ECU, TCM, ABS, lectura de códigos de falla y borrado de testigos.'),
    (5, 'Mantenimiento del Sistema de Refrigeración', 95.00, '60 min', 'Drenado, limpieza de radiador, presurización contra fugas y refrigerante orgánico 50/50.')
ON CONFLICT (id) DO UPDATE SET
    nombre = EXCLUDED.nombre,
    precio_base = EXCLUDED.precio_base,
    tiempo_estimado = EXCLUDED.tiempo_estimado,
    descripcion = EXCLUDED.descripcion;
