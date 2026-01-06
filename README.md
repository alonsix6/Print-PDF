# PDF OCR Enhancement Tool

Una herramienta profesional para mejorar PDFs escaneados con reconocimiento óptico de caracteres (OCR). Convierte documentos de baja calidad en PDFs con texto seleccionable y legible.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## Características

- **Reconocimiento OCR Avanzado**: Utiliza Tesseract 5.x con redes neuronales LSTM
- **Múltiples Idiomas**: Soporte para más de 100 idiomas incluyendo español, inglés, chino, japonés y árabe
- **Mejora de Imagen Automática**:
  - Corrección de rotación (deskew)
  - Eliminación de ruido (denoise)
  - Mejora de contraste (CLAHE)
  - Auto-rotación de páginas
- **Optimización de PDF**: Compresión inteligente con Ghostscript
- **Interfaz Moderna**: Frontend responsive con tema claro/oscuro
- **API REST Completa**: Documentación automática con Swagger

## Arquitectura

```
┌─────────────────────┐     ┌─────────────────────┐
│   Frontend          │     │   Backend           │
│   (Netlify)         │────▶│   (Railway)         │
│                     │     │                     │
│   - HTML/CSS/JS     │     │   - FastAPI         │
│   - Drag & Drop     │     │   - OCRmyPDF        │
│   - Real-time       │     │   - OpenCV          │
│     Progress        │     │   - Ghostscript     │
└─────────────────────┘     └─────────────────────┘
```

## Inicio Rápido

### Requisitos Previos

- Python 3.11+
- Tesseract OCR
- Ghostscript
- Poppler

### Instalación Local

1. **Clonar el repositorio**
```bash
git clone https://github.com/tuusuario/Print-PDF.git
cd Print-PDF
```

2. **Instalar dependencias del sistema (Ubuntu/Debian)**
```bash
sudo apt update
sudo apt install -y \
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-eng \
    poppler-utils \
    ghostscript \
    libmagic1
```

3. **Configurar el backend**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

4. **Ejecutar el backend**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

5. **Abrir el frontend**
```bash
# Abrir frontend/index.html en tu navegador
# O usar un servidor local:
cd ../frontend
python -m http.server 3000
```

6. **Acceder a la aplicación**
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## Despliegue en Producción

### Backend en Railway

1. **Crear cuenta en [Railway](https://railway.app)**

2. **Crear nuevo proyecto**
   - Seleccionar "Deploy from GitHub repo"
   - Autorizar acceso al repositorio

3. **Configurar el servicio**
   - Root Directory: `backend`
   - El Dockerfile será detectado automáticamente

4. **Variables de entorno** (opcional)
```
DEBUG=false
MAX_FILE_SIZE_MB=100
FILE_RETENTION_HOURS=24
```

5. **Obtener la URL del backend**
   - Railway asignará una URL como `https://tu-app.railway.app`

### Frontend en Netlify

1. **Crear cuenta en [Netlify](https://netlify.com)**

2. **Nuevo sitio desde Git**
   - Conectar repositorio GitHub
   - Base directory: `frontend`
   - Build command: (dejar vacío)
   - Publish directory: `frontend`

3. **Actualizar la URL del API**
   - Editar `frontend/js/app.js`
   - Cambiar `API_URL` por la URL de Railway:
```javascript
const CONFIG = {
    API_URL: 'https://tu-backend.railway.app',
    // ...
};
```

4. **Redesplegar**
   - Hacer push de los cambios
   - Netlify desplegará automáticamente

## API Reference

### Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/upload` | Subir PDF para procesar |
| `GET` | `/api/status/{task_id}` | Obtener estado del procesamiento |
| `GET` | `/api/download/{task_id}` | Descargar PDF procesado |
| `GET` | `/api/languages` | Listar idiomas disponibles |
| `GET` | `/api/presets` | Listar presets de calidad |
| `GET` | `/health` | Health check |

### Ejemplo de Uso

```bash
# Subir un PDF
curl -X POST "http://localhost:8000/api/upload?language=spa+eng&quality_preset=ebook" \
  -F "file=@documento.pdf"

# Respuesta
{
  "task_id": "abc123...",
  "status": "pending",
  "message": "File uploaded successfully"
}

# Verificar estado
curl "http://localhost:8000/api/status/abc123..."

# Descargar resultado
curl -O "http://localhost:8000/api/download/abc123..."
```

## Opciones de Procesamiento

| Opción | Tipo | Default | Descripción |
|--------|------|---------|-------------|
| `language` | string | `spa+eng` | Idioma(s) del OCR |
| `deskew` | bool | `true` | Corregir rotación |
| `denoise` | bool | `true` | Eliminar ruido |
| `enhance_contrast` | bool | `true` | Mejorar contraste |
| `remove_background` | bool | `false` | Eliminar fondo |
| `target_dpi` | int | `300` | DPI objetivo (150-600) |
| `quality_preset` | string | `ebook` | Preset de calidad |
| `optimize_size` | bool | `true` | Optimizar tamaño |
| `force_ocr` | bool | `false` | Forzar OCR |
| `rotate_pages` | bool | `true` | Auto-rotar páginas |

### Presets de Calidad

| Preset | DPI | Uso |
|--------|-----|-----|
| `screen` | 72 | Web, menor tamaño |
| `ebook` | 150 | Balance calidad/tamaño |
| `printer` | 300 | Impresión |
| `prepress` | 300 | Máxima calidad |

## Estructura del Proyecto

```
Print-PDF/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py           # FastAPI app
│   │   ├── config.py         # Configuración
│   │   ├── models.py         # Modelos Pydantic
│   │   ├── routers/
│   │   │   └── pdf.py        # Endpoints
│   │   ├── services/
│   │   │   ├── preprocessor.py  # OpenCV
│   │   │   ├── ocr_service.py   # OCRmyPDF
│   │   │   └── optimizer.py     # Ghostscript
│   │   └── utils/
│   │       ├── file_handler.py
│   │       └── task_manager.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── railway.toml
├── frontend/
│   ├── index.html
│   ├── css/
│   │   └── styles.css
│   ├── js/
│   │   └── app.js
│   ├── netlify.toml
│   └── _redirects
├── .gitignore
└── README.md
```

## Tecnologías

### Backend
- **FastAPI** - Framework web async
- **OCRmyPDF** - Motor OCR principal
- **Tesseract 5.x** - Motor de reconocimiento
- **OpenCV** - Procesamiento de imágenes
- **Ghostscript** - Optimización de PDF
- **Pillow** - Manipulación de imágenes

### Frontend
- **HTML5/CSS3** - Estructura y estilos
- **JavaScript (Vanilla)** - Lógica de aplicación
- **CSS Variables** - Temas claro/oscuro
- **Drag & Drop API** - Subida de archivos

### Infraestructura
- **Railway** - Hosting del backend
- **Netlify** - Hosting del frontend
- **Docker** - Containerización

## Rendimiento Esperado

| Escenario | Tiempo por página |
|-----------|-------------------|
| PDF limpio | ~2-3 segundos |
| PDF degradado | ~4-5 segundos |
| PDF muy borroso | ~5-7 segundos |

## Limitaciones

- Tamaño máximo: 100MB por archivo
- Máximo de páginas: 500 por PDF
- No soporta reconocimiento de escritura a mano
- Tiempo de retención de archivos: 24 horas

## Contribuir

1. Fork el repositorio
2. Crear rama de feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo [LICENSE](LICENSE) para más detalles.

## Soporte

Si encuentras un bug o tienes una sugerencia, por favor abre un [issue](https://github.com/tuusuario/Print-PDF/issues).

---

Desarrollado con FastAPI, OCRmyPDF y mucho cafe
