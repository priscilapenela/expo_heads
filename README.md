# ⚽ Expo Heads UNO

Juego de fútbol 2D estilo **Sports Heads** desarrollado para la Expo de la **Universidad Nacional del Oeste (UNO)**, carrera de Informática.

## 🎮 ¿De qué se trata?

Dos jugadores se enfrentan en una cancha de fútbol 2D. Cada jugador es una cabezota gigante con un piecito, y la gracia es que **tu cara se convierte en el personaje**: te sacás una foto con la webcam y el sistema la transforma en pixel art al estilo del juego.

## 🛠️ Tecnologías

- **Python 3.10+**
- **pygame-ce** — motor del juego
- **OpenCV** — captura de webcam
- **MediaPipe** — detección facial
- **Pillow** — procesamiento de imagen

## 📦 Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/TU_USUARIO/expo-heads-uno.git
cd expo-heads-uno

# 2. Crear entorno virtual
python -m venv venv
venv\Scripts\activate    # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar el juego
python main.py
```

## 🎮 Controles

| Acción       | Jugador 1 (teclado) | Jugador 2 (teclado) | Joystick       |
|-------------|---------------------|---------------------|----------------|
| Mover       | A / D               | ← / →               | Stick / D-pad  |
| Saltar      | W                   | ↑                    | Botón A        |
| Patear      | S                   | ↓                    | Botón B        |

## 📁 Estructura del proyecto

```
expo-heads-uno/
├── main.py           # Punto de entrada
├── config.py         # Constantes del juego
├── pitch.py          # Renderizado de la cancha
├── hud.py            # Marcador y timer
├── requirements.txt  # Dependencias
├── .gitignore
├── README.md
└── assets/
    ├── sprites/      # Sprites de personajes
    ├── sounds/       # Efectos de sonido
    └── fonts/        # Fuentes
```

## 👥 Equipo

Desarrollado para la Expo UNO — Carrera de Informática.
