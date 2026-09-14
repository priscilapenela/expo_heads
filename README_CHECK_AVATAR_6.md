# CHECK AVATAR 6 — Constructor modular

Este paquete genera cabezones PNG transparentes sin modificar el launcher, los EXE ni los archivos internos del motor.

## Requisito

```bash
pip install Pillow
```

El `requirements.txt` actual del proyecto ya incluye `Pillow>=10.0.0`.

## Prueba rápida

Copiar esta carpeta al proyecto y ejecutar desde ella:

```bash
python avatar_builder.py --demo demo_avatar
```

Se crearán:

- `avatar_demo_j1.png` y `avatar_demo_j2.png` a 192 × 224 px.
- Las dos orientaciones opuestas.
- `avatar_demo_24.png` con 24 combinaciones.
- Dos configuraciones JSON reproducibles.
- `avatar_catalog.json` con todos los IDs aceptados.

## Crear un avatar desde JSON

```bash
python avatar_builder.py --config avatar_ejemplo.json --output mi_avatar.png
```

Orientación forzada:

```bash
python avatar_builder.py --config avatar_ejemplo.json --output rival.png --facing left
```

## Integración posterior

Desde el launcher se podrá usar:

```python
from avatar_builder import AvatarConfig, save_uuid_avatar

avatar_id, avatar_path = save_uuid_avatar(
    AvatarConfig.from_dict(rasgos_confirmados),
    BASE_DIR / "data" / "avatars",
)
```

El archivo se crea con UUID y nunca reemplaza un PNG anterior. En CHECK AVATAR 7 la cámara producirá los rasgos iniciales; en CHECK AVATAR 9 la persona podrá corregirlos antes de guardar.

## Pruebas automáticas

```bash
python -m unittest -v test_avatar_builder.py
```

Se validan transparencia, tamaño, espejo exacto, IDs inválidos, guardado atómico, UUID sin sobrescritura y 200 combinaciones aleatorias reproducibles.

