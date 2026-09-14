EXPO HEADS - FIX HAIR/GLASSES V3

Reemplazar en la raíz del proyecto:
- launcher.py
- avatar_selector.py
- face_analyzer.py

NO reemplazar:
- avatars_catalog.json
- carpeta data/avatars
- base SQLite

Cambios principales:
1. Anteojos V4: elimina HoughCircles (confundía ojos/cejas con lentes).
   Ahora busca marco bilateral + puente y devuelve None si es ambiguo.
2. Pelo V4: largo usa presencia de pelo texturado cerca/debajo de mandíbula;
   no confunde fácilmente auriculares/ropa/padding negro con pelo largo.
3. Textura: agrega straight/wavy/curly con confianza moderada.
4. Selector V5: anteojos sin detectar excluyen templates con anteojos cuando
   la confianza es alta; luego prioriza textura y largo de pelo con fallback.
5. Launcher: padding del scan pasa de negro a gris neutro para no parecer pelo.

Validación con la foto suministrada en el chat:
- bald: false
- hair_length: medium
- hair_texture: curly
- glasses: false (0.93)
- beard: false
- moustache: false

Esto evita el caso observado avatar_0014/0019 con anteojos y pelo largo recogido.
