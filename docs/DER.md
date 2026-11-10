# Modelo entidad-relación de CICLO

Estado: coincide con las migraciones `9afab0f20aec` (esquema inicial) y `0002` (datos fijos).

Reglas que no se pueden dibujar en el diagrama:

- `item`: si tiene `lote_id`, debe tener `metodo_id`. Si tiene `entrega_id`, debe tener `lote_id` (restricciones CHECK).
- `lote`: `fin` es nulo o mayor o igual que `inicio` (CHECK).
- `servicio_incompatible`: `servicio_a_id < servicio_b_id` (CHECK), para que un par no se cargue dos veces en orden inverso.
- `evento_item`: único por (`item_id`, `etapa_id`). Historial de solo agregado.
- La etapa actual de un ítem no se guarda: se deduce de su último evento.
- El método de un lote se obtiene de su equipo.
- Reglas validadas en el backend: el método del ítem coincide con el del equipo del lote, no se mezclan servicios incompatibles en un lote y no se saltean etapas.
- Provisorios, pendientes de validar con el servicio: `programa.metodo_id` y la numeración de `lote.numero`.

```mermaid
erDiagram
    ROL ||--o{ OPERADOR : tiene
    SERVICIO ||--o{ RECEPCION : origen
    SERVICIO ||--o{ ENTREGA : destino
    SERVICIO ||--o{ SERVICIO_INCOMPATIBLE : par_a
    SERVICIO ||--o{ SERVICIO_INCOMPATIBLE : par_b
    RECEPCION ||--o{ ITEM : contiene
    MATERIAL ||--o{ ITEM : es
    METODO_ESTERILIZACION |o--o{ ITEM : se_esteriliza_por
    METODO_ESTERILIZACION ||--o{ EQUIPO : usa
    METODO_ESTERILIZACION ||--o{ PROGRAMA : ofrece
    EQUIPO ||--o{ LOTE : procesa
    PROGRAMA ||--o{ LOTE : aplica
    OPERADOR ||--o{ LOTE : carga
    LOTE |o--o{ ITEM : agrupa
    ENTREGA |o--o{ ITEM : entrega
    ITEM ||--o{ EVENTO_ITEM : historial
    ETAPA ||--o{ EVENTO_ITEM : registra
    OPERADOR ||--o{ EVENTO_ITEM : firma

    ROL {
        int id PK
        string nombre UK
    }
    OPERADOR {
        int id PK
        string numero_operador UK
        string contrasena_hash
        int rol_id FK
        bool activo
    }
    SERVICIO {
        int id PK
        string nombre UK
        bool activo
    }
    SERVICIO_INCOMPATIBLE {
        int servicio_a_id PK
        int servicio_b_id PK
    }
    MATERIAL {
        int id PK
        string nombre UK
        bool activo
    }
    ETAPA {
        int id PK
        int orden UK
        string nombre
        string area
        string color
    }
    METODO_ESTERILIZACION {
        int id PK
        string nombre UK
    }
    EQUIPO {
        int id PK
        string nombre UK
        int metodo_id FK
        bool activo
    }
    PROGRAMA {
        int id PK
        string nombre
        int metodo_id FK
    }
    RECEPCION {
        int id PK
        int servicio_id FK
        datetime fecha_hora
    }
    ENTREGA {
        int id PK
        int servicio_id FK
        datetime fecha_hora
    }
    LOTE {
        int id PK
        int numero UK
        int equipo_id FK
        int programa_id FK
        int operador_id FK
        datetime inicio
        datetime fin
    }
    ITEM {
        int id PK
        int recepcion_id FK
        int material_id FK
        int metodo_id FK
        int lote_id FK
        int entrega_id FK
    }
    EVENTO_ITEM {
        int id PK
        int item_id FK
        int etapa_id FK
        int operador_id FK
        datetime fecha_hora
    }
```
## Reglas del backend (adicionales)

- El programa de un lote debe pertenecer al mismo método que el equipo del lote.

## Pendientes de validación con el servicio

| Tema | Efecto posible en el modelo |
|---|---|
| Numeración de lotes: reinicio por día, mes, año o equipo | Cambiar la unicidad de `lote.numero` |
| Reprocesamiento de un material | Agregar un número de intento a `evento_item` o reemplazar su restricción única |
| Datos del ciclo (temperatura, tiempo, resultado) | Nuevas columnas o tabla en `lote` |
| Urgencia de un material y quién la marca | Nueva columna en `item` |
| Materiales cargados por cantidad (por ejemplo, gasas) | Posible campo de cantidad en `item` |
| Observaciones en la entrega | Nueva columna en `entrega` |
| Programas propios de cada método | Mantener o quitar `programa.metodo_id` |