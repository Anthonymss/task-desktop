# CronVault - Job Scheduler for Windows

Planificador de tareas para Windows con interfaz gráfica y modo servicio.

## 📁 Estructura del Proyecto

\\\
cronvault/
├── src/                      # Código fuente Python
│   ├── main.py              # Interfaz gráfica (GUI)
│   ├── core.py              # Scheduler, BD y servicio
│   └── ui_components.py     # Componentes reutilizables
│
├── config/                   # Configuración e instalación
│   ├── CronVault.xml        # Config WinSW service
│   ├── install_service.bat  # Instalador del servicio
│   └── uninstall_service.bat # Desinstalador
│
├── resources/               # Recursos estáticos
│   └── cronvault.ico        # Icono de aplicación
│
├── BUILD_ME.bat             # Script para compilar .exe
├── CLEAN.bat                # Script para limpiar temporales
├── cronvault.spec           # Configuración PyInstaller
├── requirements.txt         # Dependencias Python
└── README.md               # Este archivo
\\\

## 🚀 Instalación y Uso

### 1️⃣ Instalar Dependencias

\\\powershell
pip install -r requirements.txt
\\\

### 2️⃣ Ejecutar en Modo Desarrollo (GUI)

\\\powershell
python src/main.py
\\\

### 3️⃣ Generar .exe para Windows

#### Opción A: Script automático (RECOMENDADO)
\\\atch
BUILD_ME.bat
\\\
Esto:
- Limpia builds previos
- Verifica PyInstaller (lo instala si falta)
- Compila \cronvault.exe\ en la carpeta \dist/\
- Resultado: \dist\cronvault.exe\

#### Opción B: Manual
\\\powershell
pyinstaller --clean cronvault.spec
\\\

### 4️⃣ Instalar como Servicio Windows

**IMPORTANTE**: Ejecuta como Administrador
\\\atch
config\install_service.bat
\\\

Esto:
- Copia archivos a \C:\Program Files\CronVault\\\
- Descarga WinSW si no existe
- Instala el servicio CronVault
- Inicia automáticamente

### 5️⃣ Desinstalar Servicio

\\\atch
config\uninstall_service.bat
\\\

## 📋 Modos de Ejecución

| Modo | Comando | Descripción |
|------|---------|-------------|
| **GUI** | \python src/main.py\ | Interfaz gráfica interactiva |
| **Servicio** | \python src/main.py --service\ | Ejecuta en background (usado por WinSW) |
| **Compilado** | \dist\cronvault.exe\ | Ejecutable compilado para distribuir |

## ⚙️ Configuración

**Archivos importantes:**
- \src/core.py\, línea 15: Cambiar \DB_PATH\ para ubicación de base de datos
- \config/CronVault.xml\: Opciones adicionales del servicio Windows
- \cronvault.spec\: Configuración de PyInstaller (icono, UAC, etc.)

## 🔧 Troubleshooting

**Error: \"No se encontró cronvault.exe en install_service.bat\"**
- Ejecuta primero \BUILD_ME.bat\ para generar el .exe

**Servicio no inicia**
- Verifica que \config\install_service.bat\ se ejecutó como Admin
- Revisa logs en \C:\Program Files\CronVault\logs\\\

**Cambios en código no se aplican**
- Ejecuta \BUILD_ME.bat\ nuevamente para recompilar

## 📦 Dependencias

Ver \equirements.txt\ para versiones exactas:
- PySide6              # Interfaz gráfica Qt
- APScheduler          # Planificación de tareas
- PyInstaller          # Compilación a .exe

## 📝 License

MIT
