"""
Configuración de Django para agro_config (Sistema de Gestión de Cultivos).
Soporta conexión directa al motor PostgreSQL de Supabase mediante variables de entorno (.env)
con respaldo automático a SQLite local en entornos de desarrollo sin credenciales externas.
"""

import importlib.util
import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

# Directorio raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent

# Cargar variables de entorno desde .env
load_dotenv(BASE_DIR / ".env")

# Seguridad y entorno
SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-agro-proyecto-secreto-2026-dev-key"
)

DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,.onrender.com,.railway.app,.vercel.app,*").split(",")
    if h.strip()
]

HAS_CORSHEADERS = importlib.util.find_spec("corsheaders") is not None
HAS_WHITENOISE = importlib.util.find_spec("whitenoise") is not None

# Definición de aplicaciones
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    *(["corsheaders"] if HAS_CORSHEADERS else []),
    # Aplicación principal de Gestión Agrícola (B1 & B2)
    "cultivos.apps.CultivosConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    *(["whitenoise.middleware.WhiteNoiseMiddleware"] if HAS_WHITENOISE else []),
    *(["corsheaders.middleware.CorsMiddleware"] if HAS_CORSHEADERS else []),
    "agro_config.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Configuración CORS
CORS_ALLOW_ALL_ORIGINS = os.getenv("CORS_ALLOW_ALL_ORIGINS", "True").lower() in ("true", "1", "yes")
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if o.strip()
]

ROOT_URLCONF = "agro_config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "agro_config.wsgi.application"


# ==============================================================================
# Configuración de Base de Datos (Supabase PostgreSQL / Respaldo SQLite)
# ==============================================================================
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DB_HOST = os.getenv("DB_HOST", "").strip()
DB_PASSWORD = os.getenv("DB_PASSWORD", "").strip()

if DATABASE_URL and "tu-proyecto" not in DATABASE_URL:
    # 1. Conexión mediante URI de Supabase (DATABASE_URL)
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=True,
        )
    }
elif DB_HOST and DB_PASSWORD and "tu-password" not in DB_PASSWORD:
    # 2. Conexión por parámetros explícitos de Supabase PostgreSQL
    DATABASES = {
        "default": {
            "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.postgresql"),
            "NAME": os.getenv("DB_NAME", "postgres"),
            "USER": os.getenv("DB_USER", "postgres"),
            "PASSWORD": DB_PASSWORD,
            "HOST": DB_HOST,
            "PORT": os.getenv("DB_PORT", "6543"),
            "OPTIONS": {
                "sslmode": "require",
            },
        }
    }
else:
    # 3. Modo Desarrollo Local (SQLite) cuando aún no se configura .env de Supabase
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# Validadores de contraseñas
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internacionalización (Colombia)
LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

# Archivos estáticos
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
