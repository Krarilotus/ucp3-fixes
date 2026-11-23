# Búsqueda de rutas

Un componente compartido para los módulos que cambian cómo encuentran su camino las unidades. Por sí solo no cambia nada en el juego.

Tanto Smarter Pathing (atajo de asesinos) como Gatehouse Fixes (reglas de ruta de puertas) modifican la búsqueda de rutas que el juego realiza cuando una unidad recibe un nuevo destino. La Búsqueda de rutas permite que funcionen juntos, ya que cada uno añade aquí su regla y cada regla ve la unidad correcta. Solo las versiones de esos módulos que dependen de ella la usan y la instalan automáticamente.
