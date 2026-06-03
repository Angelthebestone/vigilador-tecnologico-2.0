<!--
Sync Impact Report
- Version change: 1.1.0 -> 1.2.0
- Modified principles: none (existing principles preserved as-is)
- Added sections:
  - Principios de Diseno de Software > Limpieza y Simplicidad (DRY, KISS, YAGNI, WET, AHA)
  - Principios de Diseno de Software > Cohesion y Conexion (LoD, Bajo Acoplamiento, Alta Cohesion, SoC)
  - Principios de Diseno de Software > Los 5 Principios SOLID (SRP, OCP, LSP, ISP, DIP)
  - Principios de Diseno de Software > Desarrollo y Arquitectura (CQS, CQRS, POLA, Convencion sobre Configuracion)
- Removed sections: none
- Templates requiring updates:
  - ✅ updated: .specify/templates/plan-template.md (Constitution Check now references design principles)
  - ✅ no changes needed: .specify/templates/spec-template.md
  - ✅ no changes needed: .specify/templates/tasks-template.md
- Follow-up TODOs: none
-->

# Constitucion del Proyecto: Vigilador Tecnologico 2.0

## Principios Fundamentales

### 1. Pensar Antes de Codificar

Antes de implementar, el autor MUST declarar supuestos explicitamente.
Si existen multiples interpretaciones de un requerimiento, MUST presentarlas
todas en vez de elegir una silenciosamente. Si existe un enfoque mas simple,
MUST senalarlo y argumentar si se descarta. Si algo es confuso, MUST detenerse,
nombrar la confusion y preguntar antes de proceder.

Rationale: Las asunciones ocultas generan soluciones incorrectas. Facilitar el
debate antes de codificar reduce retrabajo y alinea expectativas.

### 2. Simplicidad Obligatoria

Todo cambio MUST resolver el problema con la menor complejidad posible. Queda
prohibido agregar capas, banderas, abstracciones o funcionalidades no
solicitadas. El codigo MUST ser legible en una sola pasada por otro ingeniero.
Si se escriben 200 lineas y podrian ser 50, MUST reescribirse. No se permiten
abstracciones para codigo de uso unico, ni "flexibilidad" o "configurabilidad"
que no fue pedida, ni manejo de errores para escenarios imposibles.

Rationale: El exceso de ingenieria aumenta defectos, costo de mantenimiento y
tiempo de entrega. Una senior engineer diria "esto esta sobredisenado" si ve
complejidad innecesaria.

### 3. Modularidad Primero

Toda capacidad nueva MUST implementarse en modulos con responsabilidad unica y
interfaces claras. Ningun modulo SHOULD mezclar orquestacion, logica de dominio
y acceso a infraestructura en la misma unidad.

Rationale: La modularidad permite escalar el sistema, aislar cambios y reducir
regresiones.

### 4. Manejo de Errores Estricto

El manejo de errores MUST ser explicito, acotado y accionable. No se permite
uso excesivo de `try/except` ni cascadas de `if/else` defensivos sin causa
real. Se prohiben capturas amplias que oculten fallos; cada error MUST
propagarse o transformarse con contexto util.

Rationale: Silenciar errores o sobrevalidar degrada claridad y dificulta
operacion y depuracion.

### 5. Cambios Quirurgicos y Trazables

Cada linea modificada MUST estar directamente relacionada con el objetivo
solicitado. No se permiten refactors laterales ni limpiezas no pedidas. Todo
cambio MUST preservar convenciones existentes y mantener trazabilidad de fuente
-> decision -> resultado. No se MUST mejorar codigo adyacente, comentarios o
formato que no este relacionado con el cambio. Si un cambio produce codigo
huerfano (imports, variables, funciones sin uso), MUST eliminarse solo el
huerfano generado por ese cambio, no codigo muerto previo.

Rationale: Limitar el radio de cambio reduce riesgo y acelera revisiones. Cada
linea cambiada debe trazar directamente al objetivo.

### 6. Entrega Verificable

Toda entrega MUST definir criterios de exito verificables antes de implementar.
Una tarea se considera completa solo cuando el resultado observable cumple dichos
criterios y no deja comportamiento ambiguo. Las tareas se MUST transformar en
objetivos verificables: "agregar validacion" -> "escribir tests para entradas
invalidas, luego hacer que pasen". Para tareas multietapa, se MUST declarar un
plan breve con verificacion por paso.

Rationale: La verificacion explicita evita "parece funcionar" y reduce deuda.
Criterios debiles ("hacer que funcione") requieren aclaracion constante.

## Principios de Diseno de Software

### Limpieza y Simplicidad

- **DRY (Don't Repeat Yourself)**: No duplicar logica. Cada pieza de
  conocimiento MUST tener una representacion unica y no ambigua en el sistema.
- **KISS (Keep It Simple, Stupid)**: Mantener el diseno lo mas simple posible.
  La solucion mas simple que funciona es la correcta hasta que se demuestre lo
  contrario.
- **YAGNI (You Aren't Gonna Need It)**: No implementar funcionalidades hasta
  que sean estrictamente necesarias. El codigo especulativo es deuda diferida.
- **WET (Write Everything Twice)**: Tolerar duplicacion antes de abstraer
  incorrectamente. Abstraer solo despues de identificar patrones repetidos al
  menos dos veces.
- **AHA (Avoid Hasty Abstractions)**: Priorizar la claridad del codigo sobre
  la abstraccion prematura. La abstraccion incorrecta es mas danina que la
  duplicacion controlada.

Rationale: Estas reglas previenen el exceso de ingenieria y mantienen la base
de codigo evolucionable. La simplicidad no es un estado inicial sino el
resultado de decisiones deliberadas de diseno.

### Cohesion y Conexion

- **LoD (Ley de Demeter)**: Un modulo solo debe comunicarse con sus vecinos
  inmediatos. No encadenar llamadas a traves de objetos remotos. Un metodo
  solo MUST invocar metodos de: su propia clase, parametros recibidos,
  objetos que crea, o sus componentes directos.
- **Bajo Acoplamiento**: Minimizar dependencias entre modulos. Cada modulo
  MUST poder modificarse con impacto minimo en otros modulos. Preferir
  interfaces sobre clases concretas para puntos de conexion.
- **Alta Cohesion**: Agrupar elementos que pertenecen logicamente a la misma
  responsabilidad. Codigo que cambia por las mismas razones MUST estar junto.
  Codigo que cambia por razones diferentes MUST estar separado.
- **SoC (Separacion de Intereses)**: Dividir el programa en secciones con
  responsabilidades unicas y no solapadas. Cada concern MUST estar aislado
  en su propia capa o modulo.

Rationale: El equilibrio entre acoplamiento y cohesion determina la
mantenibilidad del sistema. Bajo acoplamiento + alta cohesion es el objetivo.

### Los 5 Principios SOLID

- **SRP (Responsabilidad Unica)**: Una clase o modulo MUST tener una unica
  razon para cambiar. Cada modulo debe estar enfocado en una sola
  responsabilidad del negocio.
- **OCP (Abierto/Cerrado)**: Las entidades MUST estar abiertas para extension
  pero cerradas para modificacion. Extender comportamiento sin alterar codigo
  existente usando herencia, composicion o inyeccion de dependencias.
- **LSP (Sustitucion de Liskov)**: Las subclases MUST ser sustituibles por
  sus clases base sin alterar la correccion del programa. Una subclase no
  MUST debilitar las precondiciones ni fortalecer las postcondiciones.
- **ISP (Segregacion de Interfaces)**: Es mejor tener multiples interfaces
  especificas que una interfaz general. Ningun cliente MUST depender de
  metodos que no usa.
- **DIP (Inversion de Dependencias)**: Depender de abstracciones, no de
  implementaciones concretas. Los modulos de alto nivel no MUST depender de
  modulos de bajo nivel. Ambos MUST depender de abstracciones.

Rationale: SOLID proporciona un marco probado para diseno orientado a objetos
que resiste el cambio y promueve la reutilizacion. Cada principio ataca una
fuente especifica de rigidez y fragilidad.

### Desarrollo y Arquitectura

- **CQS (Command-Query Separation)**: Un metodo MUST alterar estado O devolver
  datos, pero nunca ambos. Comandos (escritura) ejecutan acciones; consultas
  (lectura) retornan datos sin efectos secundarios.
- **CQRS (Command Query Responsibility Segregation)**: Separar los modelos de
  lectura y escritura de datos en diferentes abstracciones cuando los
  requisitos de lectura y escritura difieran significativamente. No forzar
  CQRS donde un modelo unificado es suficiente.
- **POLA (Principle of Least Astonishment)**: El codigo MUST comportarse de la
  manera que el usuario o desarrollador espera. Las interfaces, nombres y
  comportamiento no MUST producir resultados sorprendentes sin documentacion
  explicita.
- **Convencion sobre Configuracion**: Disminuir decisiones de configuracion
  usando convenciones y valores por defecto sensatos. La configuracion
  explicita solo MUST usarse cuando la convencion no aplica o necesita
  invalidarse.

Rationale: Estos principios reducen la carga cognitiva, mejoran la
predictibilidad del sistema y alinean el codigo con expectativas del dominio.

## Estandares de Ingenieria

1. El codigo MUST priorizar nombres claros y flujo lineal.
2. Las funciones SHOULD ser pequenas y enfocadas en una tarea.
3. Cada modulo MUST exponer contratos de entrada/salida claros.
4. Validaciones MUST cubrir casos reales del dominio, no escenarios
   especulativos.
5. Dependencias nuevas MUST justificarse por valor directo.
6. Comentarios MUST explicar decisiones no obvias, no describir obviedades.
7. No se MUST agregar funcionalidades no solicitadas, ni banderas, ni
   abstracciones sin justificacion directa.
8. Si el codigo puede ser significativamente mas corto sin perder claridad,
   MUST reescribirse.
9. Cada linea modificada MUST trazar directamente al objetivo declarado.

## Practicas de Codigo (Generales)

- Priorizar legibilidad y simplicidad sobre ingenio; el codigo debe leerse en una pasada.
- Mantener funciones pequenas y con una sola responsabilidad; separar logica pura de I/O.
- Limitar efectos secundarios: concentrarlos en los bordes del sistema y documentarlos.
- Evitar estado global mutable; cuando sea inevitable, encapsularlo y justificarlo.
- Validar entradas en los limites del sistema; mantener invariantes internas sin revalidar en cada capa.
- Manejar errores con contexto util; evitar capturas amplias o silenciosas.
- Escribir tests deterministas y repetibles; aislar dependencias externas con dobles de prueba.
- Registrar logs utiles y minimales; nunca exponer secretos, PII o credenciales.
- Medir antes de optimizar; optimizar solo rutas calientes con evidencia.
- Documentar decisiones no obvias y contratos de interfaz con ejemplos breves.

## Proceso de Desarrollo

1. Declarar supuestos y decisiones de diseno antes de implementar.
2. Definir alcance y criterios verificables antes de codificar.
3. Implementar el cambio minimo suficiente para cumplir el objetivo.
4. Revisar impacto solo en superficies relacionadas.
5. Registrar supuestos y decisiones de diseno cuando afecten mantenibilidad.
6. Mantener coherencia con esta constitucion en specs, planes y guias.

## Gobernanza

- Esta constitucion prevalece sobre guias locales de estilo.
- En conflicto entre velocidad y calidad estructural, MUST prevalecer calidad
  estructural.
- Cualquier enmienda MUST incluir:
  1. Justificacion explicita.
  2. Evaluacion de impacto en plantillas y flujo operativo.
  3. Actualizacion del reporte de sincronizacion en este archivo.
- Politica de versionado:
  - MAJOR: cambios incompatibles de gobernanza o eliminacion/redefinicion de
    principios.
  - MINOR: adicion de principios o expansion material de reglas.
  - PATCH: aclaraciones no semanticas, redaccion o correcciones menores.
- Revision de cumplimiento: MUST ejecutarse en cada ciclo de especificacion y
  planificacion.

**Version**: 1.2.0
**Ratificada**: 2026-05-10
**Ultima Enmienda**: 2026-05-19
