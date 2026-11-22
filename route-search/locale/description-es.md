# Búsqueda de rutas

Un componente compartido para los módulos que cambian cómo encuentran su camino las unidades. Por sí solo no cambia nada en el juego.

Tanto Smarter Pathing (atajo de asesinos) como Gatehouse Fixes (reglas de ruta de puertas) necesitan la búsqueda de rutas del juego para cada unidad. Este módulo permite que funcionen juntos: cada uno añade aquí su regla y cada regla ve la unidad correcta. Otros módulos lo instalan automáticamente cuando lo necesitan.
