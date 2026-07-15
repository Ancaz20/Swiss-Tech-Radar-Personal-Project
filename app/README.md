# Swiss Tech Radar

Aplicacion Flask para agregar y visualizar ofertas junior de tecnologia, con buscador, filtros, multiidioma y refresh de datos desde varias fuentes.

## Caracteristicas

- Agregacion de ofertas desde Adzuna, SwissDevJobs, jobs.ch, JobScout24 y EURES.
- Integracion de EURES por API JSON (no scraping HTML), con resultados para Suiza, Alemania y Paises Bajos.
- Vista principal con ordenacion, buscador y columnas de ciudad, pais y salario.
- Soporte de idiomas: espanol, ingles, aleman y frances.
- Endpoint JSON para consumo externo.
- Refresh de datos desde la interfaz con limitador de frecuencia.

## Estructura

- `app.py`: factory Flask y registro de blueprints.
- `core.py`: logica de aplicacion, filtros de busqueda y campos de presentacion.
- `ingest.py`: importacion de ofertas y persistencia en base de datos.
- `infrastructure/job_sources.py`: conectores por fuente y normalizacion.
- `routes/`: endpoints web (`/`, `/jobs`, `/refresh`).
- `templates/index.html`: interfaz principal.
- `translations/`: textos por idioma.
- `tests/`: pruebas unitarias y de rutas.

## Requisitos

- Python 3.11 o superior.
- pip.
- Docker y Docker Compose (opcional).

## Inicio rapido local

1. Crear entorno virtual e instalar dependencias:

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

2. Configurar variables de entorno (opcional):

```bash
copy .env.example .env
```

3. Ejecutar la aplicacion:

```bash
python app.py
```

La web queda en `http://127.0.0.1:5000`.

## Uso con Docker

```bash
docker compose up --build
```

Servicios:

- `web` en `http://localhost:5000`
- `db` (PostgreSQL) en `localhost:5432`

## Variables de entorno

Variables principales:

- `FLASK_SECRET_KEY`: obligatoria en produccion.
- `FLASK_ENV`: entorno Flask (`development` o `production`).
- `DATABASE_URL`: URL SQLAlchemy (si no se define, usa SQLite local).
- `ADZUNA_APP_ID` y `ADZUNA_APP_KEY`: credenciales para habilitar Adzuna.
- `EURES_QUERY`: termino base para busqueda en EURES (por defecto `software engineer`).
- `EURES_LANG`: idioma de peticion a EURES (por defecto `en`).
- `EURES_API_URL`: endpoint EURES (por defecto API publica de EURES).

Variables adicionales de scraping:

- `JOBS_CH_QUERY`: termino de busqueda para jobs.ch.
- `JOBSCOUT24_QUERY`: termino de busqueda para JobScout24.
- `ADZUNA_WHAT` y `ADZUNA_WHERE`: parametros de busqueda para Adzuna.

## Ingesta de datos

Para refrescar manualmente desde terminal:

```bash
python ingest.py
```

La ruta `POST /refresh` ejecuta `ingest.py` desde la UI y aplica un minimo entre refreshes para evitar abuso.

## Endpoints

- `GET /`: vista principal HTML.
- `GET /jobs`: devuelve JSON con ofertas (`count`, `sort`, `query`, `jobs`).
- `POST /refresh`: relanza ingesta y vuelve a la home con mensaje flash.

## Tests y calidad

Ejecutar pruebas:

```bash
pytest -q
```

Ejecutar checks de calidad:

```bash
ruff check .
black --check .
```

## Notas de fuentes

- EURES usa API oficial con payload JSON para obtener resultados mas robustos.
- LinkedIn y Glassdoor no se incluyen por restricciones de acceso/autenticacion y estabilidad de scraping.
