# Swiss Tech Radar

Aplicación Flask para recopilar y consultar ofertas junior de tecnología en Suiza mediante la API de Adzuna. Los datos se guardan en PostgreSQL con Docker Compose o en SQLite durante el desarrollo local.

## Requisitos

- Python 3.11 o superior.
- Docker y Docker Compose (para la ejecución contenerizada).
- Credenciales de API de Adzuna: `ADZUNA_APP_ID` y `ADZUNA_APP_KEY`.

## Ejecutar con Docker Compose

1. Copia `app/.env.example` a `app/.env`.
2. Sustituye todos los valores de ejemplo por credenciales y contraseñas reales. Genera una clave Flask aleatoria; no reutilices los valores del ejemplo.
3. Desde la carpeta `app`, ejecuta:

```bash
docker compose up --build
```

4. Abre http://localhost:5000.

Docker Compose construye la imagen usando la raíz del repositorio como contexto para incluir tanto la aplicación como `ingest.py` y `schema.sql`. PostgreSQL no publica su puerto al host; la aplicación accede a él por la red interna de Compose.

## Ejecución local

Desde la raíz del repositorio:

```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app/app.py
```

Sin `DATABASE_URL`, la aplicación y el proceso de ingesta utilizan SQLite en la raíz del repositorio. Define `ADZUNA_APP_ID` y `ADZUNA_APP_KEY` antes de solicitar una actualización. Puedes configurar `STACK_FOCUS` con términos separados por comas.

## Actualizar ofertas

En la interfaz, utiliza el botón **Actualizar ofertas**. La acción usa POST y un token CSRF. También puedes ejecutar la ingesta manualmente desde la raíz:

```bash
python ingest.py
```

La ingesta conserva las ofertas existentes y añade las nuevas; no vacía la base de datos antes de consultar la API.

## Pruebas

```bash
python -m unittest discover -v
```

## Configuración y seguridad

- No subas `app/.env` ni credenciales al repositorio.
- En Docker Compose, las variables críticas no tienen contraseñas ni claves secretas predeterminadas: deben definirse en `app/.env`.
- El servicio PostgreSQL solo es accesible desde la red interna de Docker Compose.
