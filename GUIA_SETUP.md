# 🚀 Guía de Setup — Expo Heads UNO

## PASO 1: Instalar Git en Windows

1. Andá a **https://git-scm.com/downloads/win**
2. Descargá el instalador (64-bit)
3. Ejecutalo y dale **Next** a todo (las opciones por defecto están bien)
4. Cuando termine, abrí una terminal (CMD o PowerShell) y verificá:

```
git --version
```

Debería mostrar algo como `git version 2.47.0`

5. Configurá tu nombre y email (usá el mismo email de tu cuenta GitHub):

```
git config --global user.name "TU NOMBRE"
git config --global user.email "tu@email.com"
```

---

## PASO 2: Crear el repositorio en GitHub

1. Andá a **https://github.com/new**
2. Completá así:
   - **Repository name:** `expo-heads-uno`
   - **Description:** `Juego de fútbol 2D estilo Sports Heads para la Expo UNO`
   - **Visibilidad:** Public (o Private si preferís)
   - **NO** marques "Add a README" (nosotros ya tenemos uno)
   - **NO** marques "Add .gitignore" (ya tenemos uno)
3. Hacé clic en **Create repository**
4. GitHub te va a mostrar una página con instrucciones. Dejala abierta, la vas a necesitar.

---

## PASO 3: Crear la carpeta del proyecto y el entorno virtual

Abrí una terminal (CMD o PowerShell) y ejecutá:

```
cd Desktop
mkdir expo-heads-uno
cd expo-heads-uno

python -m venv venv
venv\Scripts\activate
```

Vas a ver que el prompt cambia a `(venv)` — eso significa que el entorno virtual está activo.

---

## PASO 4: Copiar los archivos del proyecto

Copiá los 4 archivos .py que descargaste del chat de Claude
(main.py, config.py, pitch.py, hud.py) dentro de la carpeta
`Desktop/expo-heads-uno/`.

También copiá:
- requirements.txt
- .gitignore
- README.md

La estructura debería quedar así:

```
expo-heads-uno/
├── venv/              ← (carpeta del entorno virtual)
├── main.py
├── config.py
├── pitch.py
├── hud.py
├── requirements.txt
├── .gitignore
├── README.md
└── assets/
    ├── sprites/
    ├── sounds/
    └── fonts/
```

Creá la carpeta assets manualmente:
```
mkdir assets
mkdir assets\sprites
mkdir assets\sounds
mkdir assets\fonts
```

---

## PASO 5: Instalar las dependencias

Con el entorno virtual activo `(venv)`, ejecutá:

```
pip install -r requirements.txt
```

Esto instala pygame-ce, OpenCV, MediaPipe y Pillow.

---

## PASO 6: Probar que funcione

```
python main.py
```

Debería abrirse una ventana con la cancha de fútbol, la tribuna con
público, el marcador arriba y el timer corriendo.
Cerrá con ESC o la X de la ventana.

---

## PASO 7: Subir a GitHub

```
git init
git add .
git commit -m "Paso 0: setup del proyecto con cancha y HUD"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/expo-heads-uno.git
git push -u origin main
```

Reemplazá TU_USUARIO por tu usuario real de GitHub.

La primera vez te va a pedir las credenciales de GitHub. Si te pide
token en vez de contraseña, generá uno en:
**GitHub > Settings > Developer Settings > Personal Access Tokens > Tokens (classic)**
y dale permisos de `repo`.

---

## PASO 8: Agregar a tu compañera como colaboradora

1. En GitHub, andá al repo → **Settings** → **Collaborators**
2. Clic en **Add people**
3. Buscá el usuario de GitHub de tu compañera y agregala

Ella después clona el repo en su máquina:
```
git clone https://github.com/TU_USUARIO/expo-heads-uno.git
cd expo-heads-uno
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

---

## 🔄 Flujo de trabajo diario

Cada vez que se sienten a trabajar:

```
cd Desktop\expo-heads-uno
venv\Scripts\activate
git pull
```

Cuando terminen de hacer cambios:

```
git add .
git commit -m "descripción de lo que hicieron"
git push
```

---

¡Listo! Con esto tienen el proyecto andando y el repo compartido.
