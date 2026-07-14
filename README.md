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
