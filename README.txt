EXPO HEADS - CHECK 1 - RESET DE TURNO

Reemplazar solamente:
- launcher.py

No reemplazar:
- face_analyzer.py
- avatar_selector.py
- avatars_catalog.json
- PNGs

Cambios:
- Botón RESET TURNO arriba a la izquierda del menú.
- Confirmación obligatoria antes de borrar.
- Borra partidas, ranking, jugadores y registros de avatares del turno.
- Elimina únicamente PNGs archivados con nombre UUID.
- Conserva templates avatar_XXXX.png, catálogo, ejecutables y configuración del juego.
- Limpia el TOP #1 actual y la caché visual del ranking.
