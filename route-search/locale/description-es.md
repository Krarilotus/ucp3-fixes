# Búsqueda de rutas

Un componente compartido para los módulos que cambian cómo encuentran su camino las unidades. Por sí solo no cambia nada en el juego.

Smarter Pathing (atajo para los asesinos) y Gatehouse Fixes (reglas para las rutas que pasan por las puertas) modifican la forma en que el juego busca una ruta cuando una unidad recibe un nuevo destino. El módulo «Búsqueda de rutas» permite que ambos funcionen juntos. Cada uno añade aquí su regla y cada regla tiene en cuenta la unidad para la que se busca la ruta. Solo las versiones de esos módulos que declaran «Búsqueda de rutas» como dependencia lo usan y lo instalan automáticamente.
