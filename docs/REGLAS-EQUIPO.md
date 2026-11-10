# Reglas de trabajo en equipo

## Ramas

- `main` siempre debe arrancar y funcionar. No se sube código a medio hacer.
- No se sube directamente a `main`: todo cambio entra mediante un pull request (PR).
- Una rama por tarjeta de Trello, con el formato `tipo/descripcion-corta`.
  Tipos: `feature` (funcionalidad), `fix` (corrección), `docs` (documentación), `chore` (tareas de base).
  Ejemplos: `feature/api-login`, `docs/der`.

## Commits

- Pequeños y descriptivos, en español, con prefijo: `feat:`, `fix:`, `docs:`, `chore:`.
- Ejemplo: `feat: agrega modelo Lote`.

## Pull requests (livianos)

- Cada PR corresponde a una tarjeta de Trello y la menciona en la descripción.
- No requiere aprobación formal, pero quien lo abre avisa en el grupo.
- Antes de unir: probar que el sistema sigue funcionando.
- Se une con "Squash and merge" y se borra la rama.

## Rutina de trabajo

1. `git switch main` y `git pull` antes de empezar una tarjeta.
2. Crear la rama de la tarjeta.
3. Trabajar, commitear y subir la rama.
4. Abrir el PR, unirlo y pasar la tarjeta en Trello.
5. Anotar el avance en `docs/bitacora/`.

## Base de datos

- Las migraciones de Alembic las crea una sola persona (Lobo). Quien necesite un cambio en el modelo lo pide en el grupo.

## Seguridad y privacidad (el repositorio es público)

- Nunca se sube el archivo `.env`, claves ni contraseñas. Solo `.env.example` con valores ficticios.
- No se suben datos reales del hospital, nombres del personal ni fotos del relevamiento.
- Los datos de prueba son siempre ficticios.
- El material de trabajo que no debe subirse se guarda en la carpeta `privado/`, ignorada por Git.