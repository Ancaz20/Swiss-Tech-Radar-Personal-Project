# Swiss Tech Radar — Docker + Postgres

Instrucciones rápidas para ejecutar la app con Docker y PostgreSQL.

Prerequisitos
- Docker y Docker Compose instalados.

Levantar la aplicación (desarrollo local)

```bash
cd app
docker compose up --build
```

Esto levantará dos servicios:
- `web`: la app Flask escuchando en el puerto `5000`.
- `db`: PostgreSQL con usuario `postgres`, contraseña `example`, base `swiss`.

Variables de entorno importantes
- `FLASK_SECRET_KEY`: clave secreta para Flask (por defecto `dev_secret_key` en compose).
- `DATABASE_URL`: si quieres apuntar a otra base de datos, exporta la URL (ej: `postgresql://user:pass@host:5432/dbname`).
- `ADZUNA_APP_ID` y `ADZUNA_APP_KEY`: necesarias para que `ingest.py` funcione y pueda descargar ofertas.

Variables por archivo `.env`

Copiar el archivo de ejemplo y completar valores:

```bash
cd app
cp .env.example .env
```

No subas `.env` a control de versiones — contiene secretos.

Uso de `ingest.py`

El script `ingest.py` detecta `DATABASE_URL` automáticamente y volcará los datos en PostgreSQL cuando esté presente; si no, usará `swiss_tech_radar.db` (SQLite).

Ejecutar ingest manualmente dentro del contenedor web:

```bash
docker compose exec web python /app/ingest.py
```

Notas
- Para producción cambia la contraseña de Postgres y maneja secretos de forma segura.
- Si `ingest.py` necesita ajustes para campos adicionales, puedo adaptarlo más.
# Swiss Tech Radar — Run locally

Instrucciones rápidas para ejecutar la app localmente.

1. Crear un entorno virtual (Windows PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Instalar dependencias:

```powershell
pip install -r requirements.txt
```

3. Ejecutar la app:

```powershell
python app/app.py
```

4. Abrir en el navegador: http://127.0.0.1:5000

Notas:
- Define las variables de entorno `ADZUNA_APP_ID` y `ADZUNA_APP_KEY` antes de refrescar datos.
- Para desarrollo puedes exportar `FLASK_DEBUG=true` para activar modo depuración.
