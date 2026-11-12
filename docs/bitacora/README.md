# Bitácora del proyecto

Índice de las entradas de la bitácora. El detalle completo de cada una
(decisiones, pasos de uso y capturas) está en la pestaña "Bitácora" del
documento de la carpeta del proyecto, de acceso restringido al equipo y a la
tutora. Las capturas no se suben a este repositorio porque es público.

Las entradas más nuevas van arriba. Cada integrante agrega su fila en el mismo
pull request de su tarjeta, y como mínimo una entrada por semana.

## Plantilla de entrada

Cada entrada completa se escribe en la pestaña "Bitácora" del documento, con
estos campos. Si un campo no aplica, se escribe "No aplica".

- **Título:** fecha, quién y tarjeta de Trello.
- **Qué se hizo:** 2 a 4 líneas.
- **Decisiones:** qué se eligió y por qué.
- **Cómo se usa:** pasos para usar esa parte del sistema.
- **Captura:** pantalla funcionando, con epígrafe y sin datos del personal.
- **Qué sigue o problemas:** pendientes o bloqueos.
- **Enlaces:** PR o commits relacionados (opcional).

En este índice solo va una fila por entrada, con un resumen de una línea y el
número del PR.

## Entradas

| Fecha | Quién | Tarjeta de Trello | Resumen |
| --- | --- | --- | --- |
| 12/11/2026 | Lobo | DER y normalización | Migración 0007 (reesterilización, recepción completa, aireación, urgencia y numeración de lote sin UNIQUE), probada con alembic y 25 pruebas de restricciones en PostgreSQL. DER actualizado a las 14 tablas. (#N13 y #N14) | 
| 12/11/2026 | Lobo | Corrige filas de la bitacora | Corrige la última fila del índice de la bitácora, que estaba partida en dos líneas y no se mostraba bien en GitHub (PR #12). | 
| 11/11/2026 | Lobo | Usuarios por N.º de operador | Login con contraseña hasheada y JWT, identificación del operador y pruebas automáticas de autenticación (PR #10 y #11). | 
| 11/11/2026 | Lobo | Bitácora en GitHub | Índice y plantilla de la bitácora en docs/bitacora/ (PR #9). |
| 11/11/2026 | Salica | Historial y detalle del lote | Pantalla Lotes con datos de prueba y contrato de la API de historial (PR #8). |
| 11/11/2026 | Salica | Validar alcance del MVP con la jefa del servicio | Alcance de prioridad alta aprobado; se confirman la numeración de lotes y la reesterilización. |
| 11/11/2026 | Mara | Pantalla Registrar recepción | Pantalla con datos de prueba y validaciones (PR #6). |
| 11/11/2026 | Mara | Catálogos iniciales (materiales) | Migración 0006 con los 15 materiales y sus códigos (PR #7). |
| 11/11/2026 | Lobo | Código opcional y único en material | Migración 0005: columna `codigo` en `material` (PR #5). |
| 11/11/2026 | Mara | Estructura de pantallas y colores por sector | Base del frontend con menú y franjas de color por área (PR #4). |
| 11/11/2026 | Mara | Catálogos iniciales | Migración 0004: servicios, regla NEO–UTI y programas provisorios (PR #3). |
| 10/11/2026 | Lobo | Modelo de datos | Modelo de 14 tablas hasta 3FN, migraciones y DER (PR #2). |
| 10/11/2026 | Lobo | Definir stack y repositorio | Repositorio, reglas de equipo y protección de `main` (PR #1). |
