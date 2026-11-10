# 🍽️ COLRIENT — Sistema de gestión

Sistema de gestión para restaurante que digitaliza la carta de menús:
**gestión de platos**, **ingredientes y recetas**, **gestión del menú**
(vigencia, precios e histórico) y la **interfaz del cliente** (carta digital
con filtros, promociones y recomendaciones).

---

## 1. Arquitectura (Cliente-Servidor)

```
   ┌────────────────────────────┐       HTTP / JSON        ┌────────────────────────────┐
   │        CLIENTE WEB         │ ───────────────────────► │        SERVIDOR API        │
   │   frontend/ (estático)     │   GET /api/v1/health     │   backend/ (FastAPI)       │
   │   HTML + CSS + JavaScript  │ ◄────────────────────── │   API REST  →  /api/v1/**   │
   │                            │    respuestas JSON      │   SQLAlchemy  →  SQLite    │
   └────────────────────────────┘                         └────────────────────────────┘
```

- **Servidor (backend):** API REST construida con **FastAPI**. Expone los
  servicios bajo el prefijo `/api/v1`, valida los datos con **Pydantic** y
  accede a la base de datos mediante **SQLAlchemy** (SQLite en desarrollo).
- **Cliente (frontend):** aplicación web estática (HTML/CSS/JS) que consume
  la API con `fetch`. La sirve el propio backend en la raíz `/`, y además
  **CORS está habilitado** para permitir consumir la API desde otros
  orígenes durante el desarrollo (p. ej. VS Code *Live Server*).

## 2. Estructura del proyecto

```
colrient/
├── README.md                    ← este archivo
├── .gitignore
├── backend/                     ← SERVIDOR (Python + FastAPI)
│   ├── main.py                  ← punto de entrada del servidor
│   ├── requirements.txt         ← dependencias
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       └── router.py    ← agrega los routers bajo /api/v1
│   │   ├── routers/            ← endpoints por módulo
│   │   │   ├── health.py       ← GET /api/v1/health (ruta de prueba)
│   │   │   ├── platos.py       ← gestión de platos (Sprint 1)
│   │   │   ├── ingredientes.py ← ingredientes y recetas (Sprint 2)
│   │   │   ├── menus.py        ← gestión del menú (Sprint 2)
│   │   │   ├── catalogos.py    ← categorías y regiones (Sprint 2)
│   │   │   └── cliente.py      ← interfaz del cliente (previsto)
│   │   ├── core/
│   │   │   └── config.py       ← configuración centralizada
│   │   ├── database.py         ← conexión SQLite + creación de tablas
│   │   ├── models.py           ← modelos ORM (Region, Categoria, Plato,
│   │   │                           Ingrediente, Receta, Menu)
│   │   ├── schemas.py          ← esquemas Pydantic de todos los módulos
│   │   └── services/           ← lógica de negocio por módulo
│   ├── uploads/                ← fotos de platos (se sirven en /uploads/)
│   └── tests/
│       ├── conftest.py         ← aislamiento de BD + fixtures compartidos
│       ├── test_health.py      ← prueba del endpoint de salud
│       ├── test_platos.py      ← pruebas del módulo de platos
│       ├── test_ingredientes.py ← pruebas de ingredientes y recetas
│       └── test_menus.py       ← pruebas del módulo de menús
└── frontend/                    ← CLIENTE WEB (estático)
    ├── index.html               ← panel administrativo (Bootstrap 5)
    ├── carta.html               ← carta digital del cliente (Bootstrap 5)
    ├── css/
    │   ├── styles.css           ← estilos propios sobre Bootstrap
    │   └── carta.css            ← estilos de la carta digital
    ├── js/
    │   ├── api.js               ← capa de acceso a la API (fetch/async)
    │   ├── ui.js                ← toasts, confirmación, badges, formato
    │   ├── platos.js            ← sección Gestión de Platos
    │   ├── recetas.js           ← sección Recetas / Ingredientes
    │   ├── menus.js              ← sección Gestión del Menú
    │   ├── carta.js              ← carta digital del cliente
    │   └── app.js                ← arranque y navegación del panel
    └── assets/
        └── img/sin-foto.svg     ← placeholder de foto
```

**Flujo por capas del backend** (arquitectura en capas, un paquete por módulo):

```
endpoint (app/routers) → modelo ORM (app/models.py) → base de datos (app/database.py)
```

### Modelo de datos (SQLAlchemy)

Definido en `backend/app/models.py` a partir del modelo relacional del sistema:

```
Region   1 --- N  Plato  N --- 1  Categoria  1 --- N  Menu
                      Plato  1 --- N  Receta     N --- 1  Ingrediente
```

| Tabla | Columnas | Notas |
|-------|----------|-------|
| `region` | id, nombre, descripcion | Regiones gastronómicas del país |
| `categoria` | id, nombre, descripcion | Sopas, carnes, postres, ... |
| `plato` | id, nombre, descripcion, precio, foto_url, estado, id_categoria, id_region | FK a categoria y region |
| `ingrediente` | id, nombre, unidad_medida | Insumos de cocina |
| `receta` | id_plato, id_ingrediente, cantidad | PK compuesta; une Plato con Ingrediente |
| `menu` | id, nombre, fecha_inicio, fecha_fin, estado, id_categoria | Vigencia validada por restricción |

## 3. Requisitos previos

| Requisito | Versión mínima |
|-----------|----------------|
| Python    | 3.10 o superior |
| pip       | 21 o superior   |

## 4. Instalación

```bash
# 1. Ubicarse en el backend del proyecto
cd colrient/backend

# 2. Crear y activar el entorno virtual
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows (PowerShell)

# 3. Instalar las dependencias
pip install -r requirements.txt
```

## 5. Ejecutar el servidor localmente

Con el entorno virtual activado y **desde `colrient/backend`**:

```bash
# Modo desarrollo (recarga automática ante cambios en el código)
uvicorn main:app --reload

# Alternativa explícita (host y puerto)
uvicorn main:app --reload --host 127.0.0.1 --port 8000

# Modo producción (sin recarga automática)
uvicorn main:app --host 0.0.0.0 --port 8000
```

Al arrancar, el servidor:

1. Crea automáticamente las tablas en la base de datos SQLite `backend/colrient.db`
   (si aún no existen), a partir de los modelos de `app/models.py`.
2. Registra el middleware **CORS** para los orígenes de desarrollo.
3. Publica la API en `/api/v1` y monta el cliente web estático en `/`.

### Datos de prueba (demo)

`backend/seed.py` pobla la base con un catálogo completo de demostración:
5 categorías, 4 regiones, 45 ingredientes, 19 platos típicos colombianos
(horarios de consumo, 5 recomendados, 4 promociones y 1 agotado), 18
recetas y 3 menús — uno publicado como **carta vigente**, uno histórico
y uno en borrador.

```bash
python seed.py            # puebla la base si aún no hay platos
python seed.py --reset    # borra todo y repuebla desde cero
```

Las fechas de los menús se calculan respecto a la fecha en que se
ejecuta, de modo que la carta vigente siempre esté dentro de su rango.
La suite de pruebas usa una base aislada, por lo que el poblado no
interfiere con ella.

## 6. Verificación

| Recurso                            | URL                                  |
|------------------------------------|--------------------------------------|
| Carta digital (cliente)            | http://127.0.0.1:8000/carta.html     |
| Panel administrativo               | http://127.0.0.1:8000/               |
| Ruta de prueba (health check)      | http://127.0.0.1:8000/api/v1/health  |
| Documentación interactiva (Swagger)| http://127.0.0.1:8000/docs           |
| Documentación alternativa (ReDoc)  | http://127.0.0.1:8000/redoc          |

Prueba rápida desde la terminal:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

Respuesta esperada:

```json
{
  "status": "ok",
  "app": "COLRIENT - Sistema de gestión",
  "version": "0.1.0",
  "timestamp": "2026-11-09T15:30:00.000000+00:00"
}
```

## 7. API del módulo de Gestión de Platos (Sprint 1)

Implementada en `app/routers/platos.py` con esquemas de validación en
`app/schemas.py`. Los ejemplos asumen que ya existen una categoría y una
región en la base de datos.

| Método | Ruta                          | Operación (caso de uso)                    | Éxito |
|--------|-------------------------------|--------------------------------------------|-------|
| POST   | `/api/v1/platos`              | Registrar plato (con horarios, promoción y recomendado) | 201 |
| GET    | `/api/v1/platos`              | Consultar platos (filtros: categoría, región, nombre, horario, recomendado, promoción) | 200 |
| PUT    | `/api/v1/platos/{id}`         | Editar información del plato               | 200 |
| DELETE | `/api/v1/platos/{id}`         | Eliminar plato (solo Gerente)              | 204 |
| POST   | `/api/v1/platos/{id}/foto`    | Cargar y almacenar la imagen del plato     | 200 |

Cada plato incluye además: `horarios` de consumo (desayuno, almuerzo,
cena; puede pertenecer a varios), `recomendado` (destacado en la carta
digital) y `precio_promocional` (opcional, siempre menor que el precio
normal).

Registrar un plato:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/platos \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Ajiaco", "descripcion": "Sopa típica bogotana",
       "precio": 18000.00, "id_categoria": 1, "id_region": 1}'
```

Consultar con filtros y editar:

```bash
curl "http://127.0.0.1:8000/api/v1/platos?categoria=1&region=1&nombre=aji"
curl -X PUT http://127.0.0.1:8000/api/v1/platos/1 \
  -H "Content-Type: application/json" -d '{"precio": 19500.50}'
```

Eliminar (operación exclusiva del Gerente/Administrador; mientras no
exista el módulo de autenticación, el rol se envía en la cabecera
`X-Rol`):

```bash
curl -X DELETE http://127.0.0.1:8000/api/v1/platos/1 -H "X-Rol: gerente"
```

Subir la foto del plato (JPEG/PNG/WebP, máximo 5 MB; se almacena en
`backend/uploads/platos/` y se sirve públicamente en `/uploads/...`):

```bash
curl -X POST http://127.0.0.1:8000/api/v1/platos/1/foto -F "foto=@ajiaco.jpg"
```

Manejo de excepciones HTTP:

| Código | Situación                                                          |
|--------|--------------------------------------------------------------------|
| 400    | Categoría o región inexistente; petición sin campos; archivo vacío   |
| 403    | Un rol distinto de Gerente intenta eliminar un plato                |
| 404    | No existe un plato con el id solicitado                             |
| 413    | La imagen supera el tamaño máximo permitido                         |
| 415    | Formato de imagen no permitido                                     |
| 422    | Datos inválidos (validación automática de los esquemas Pydantic)   |

## 8. API del módulo de Ingredientes y Recetas (Sprint 2)

Implementada en `app/routers/ingredientes.py`. La sustitución de un
ingrediente se realiza en dos pasos: eliminar el actual y asociar el nuevo.

| Método | Ruta                                                       | Operación                              | Éxito |
|--------|------------------------------------------------------------|----------------------------------------|-------|
| POST   | `/api/v1/ingredientes`                                     | Registrar ingrediente (sin duplicados) | 201 |
| GET    | `/api/v1/ingredientes`                                     | Listar el catálogo de ingredientes     | 200 |
| POST   | `/api/v1/platos/{id}/ingredientes`                        | Asociar ingrediente y cantidad         | 201 |
| GET    | `/api/v1/platos/{id}/receta`                              | Consultar la receta completa del plato | 200 |
| DELETE | `/api/v1/platos/{id_plato}/ingredientes/{id_ingrediente}` | Eliminar ingrediente de la receta      | 204 |

```bash
curl -X POST http://127.0.0.1:8000/api/v1/ingredientes \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Papa criolla", "unidad_medida": "kg"}'

curl -X POST http://127.0.0.1:8000/api/v1/platos/1/ingredientes \
  -H "Content-Type: application/json" \
  -d '{"id_ingrediente": 1, "cantidad": 0.5}'

curl http://127.0.0.1:8000/api/v1/platos/1/receta

curl -X DELETE http://127.0.0.1:8000/api/v1/platos/1/ingredientes/1 \
  -H "X-Rol: gerente"
```

Manejo de excepciones HTTP:

| Código | Situación                                                          |
|--------|--------------------------------------------------------------------|
| 400    | El ingrediente referenciado no existe                              |
| 404    | El plato no existe o el ingrediente no está asociado a su receta    |
| 409    | Nombre de ingrediente duplicado o ingrediente ya asociado al plato  |
| 422    | Datos inválidos (validación automática de los esquemas Pydantic)   |

## 9. API del módulo de Gestión del Menú (Sprint 2)

Implementada en `app/routers/menus.py`. Regla de negocio: **solo puede
existir un menú publicado (estado `activo`) a la vez**; al publicar uno,
los demás pasan automáticamente a `inactivo`.

| Método | Ruta                              | Operación                             | Éxito |
|--------|-----------------------------------|---------------------------------------|-------|
| POST   | `/api/v1/menus`                   | Crear menú por categoría con vigencia | 201 |
| GET    | `/api/v1/menus/historico`         | Histórico de menús (filtros)          | 200 |
| PUT    | `/api/v1/menus/{id}/publicar`     | Publicar la carta digital activa      | 200 |

```bash
curl -X POST http://127.0.0.1:8000/api/v1/menus \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Almuerzos noviembre", "fecha_inicio": "2026-11-01",
       "fecha_fin": "2026-11-30", "id_categoria": 1}'

curl "http://127.0.0.1:8000/api/v1/menus/historico?estado=activo"
curl -X PUT http://127.0.0.1:8000/api/v1/menus/1/publicar
```

Los menús se crean como borrador (`inactivo`) hasta que se publican.
El histórico acepta los filtros opcionales `categoria` y `estado`.

### Catálogos para los formularios

| Método | Ruta                   | Operación                    | Éxito |
|--------|------------------------|------------------------------|-------|
| GET    | `/api/v1/categorias`   | Listar categorías            | 200 |
| GET    | `/api/v1/regiones`     | Listar regiones              | 200 |

## 10. Interfaces web (frontend)

El backend sirve dos páginas estáticas con **Bootstrap 5** (vía CDN) y
JavaScript `async`/`fetch` contra la API REST:

### 10.1. Panel administrativo (`/` → `frontend/index.html`)

Barra lateral con tres secciones:

1. **Gestión de Platos** — tabla con badges de categoría/región/horario,
   filtros (categoría, región, nombre), precio con promoción tachada, y
   acciones *Ver foto*, *Editar*, *Eliminar*. El formulario modal
   registra/edita platos con vista previa de imagen, horarios de consumo
   (Desayuno/Almuerzo/Cena), precio promocional y marca de recomendado.
2. **Recetas / Ingredientes** — catálogo de ingredientes (alta sin
   duplicados) y editor de la receta de cada plato (asociar/quitar
   ingredientes con su cantidad).
3. **Gestión del Menú** — creación de menús por categoría con vigencia,
   histórico y publicación de la carta digital.

El selector **Rol** de la barra superior (Gerente/Cocinero) define el rol
enviado en la cabecera `X-Rol` de las operaciones restringidas.

### 10.2. Carta digital del cliente (`/carta.html` → `frontend/carta.html`)

Interfaz pública interactiva y responsiva (móvil/tablet/escritorio):

- **Catálogo tipo tarjetas** con imagen, nombre, descripción breve,
  región gastronómica, categoría, horarios y precio (formato COP).
- **Filtros dinámicos sin recargar la página**: por categoría, por
  horario de consumo (Desayuno, Almuerzo, Cena), búsqueda por
  nombre/descripción y opción "solo disponibles". Se aplican en
  JavaScript sobre el catálogo descargado de la API.
- **Secciones destacadas**: "Platos recomendados" (fila con
  desplazamiento horizontal) y "Promociones" (precio tachado con el
  descuento).
- **Banner de carta vigente** con el menú publicado (nombre y fechas).
- **Modal de detalle** con la imagen y la descripción ampliada.
- Diseño 100% responsivo con rejilla de Bootstrap (`row-cols-*`),
  desplazamiento horizontal con *scroll-snap* en recomendados y barra
  de filtros fija en escritorio.

La API se consume con rutas relativas (`/api/v1`), por lo que ambas
interfaces deben servirse desde el propio backend
(http://127.0.0.1:8000/).

## 11. Pruebas automatizadas

```bash
pip install pytest httpx    # dependencias de desarrollo
pytest                      # ejecutar desde colrient/backend
```

La suite incluye **43 pruebas**: health check, los endpoints del módulo de
platos (éxito, permisos, filtros, horarios, promociones, recomendados y
errores HTTP), ingredientes y recetas (duplicados, asociación, consulta,
eliminación/sustitución) y gestión del menú (vigencia, histórico con
filtros, publicación exclusiva). Las pruebas usan una base de datos y
una carpeta de subidas aisladas (`tests/conftest.py`).

## 12. Mapa de módulos

Cada módulo de COLRIENT se implementa siguiendo el mismo patrón de capas:

| Módulo COLRIENT         | Router API                     | Estado               | Modelo ORM                          |
|-------------------------|--------------------------------|----------------------|-------------------------------------|
| Gestión de platos       | `app/routers/platos.py`       | ✅ Sprint 1          | `app/models.py` (Plato)            |
| Ingredientes y recetas  | `app/routers/ingredientes.py` | ✅ Sprint 2          | `app/models.py` (Ingrediente, Receta) |
| Gestión del menú        | `app/routers/menus.py`        | ✅ Sprint 2          | `app/models.py` (Menu)             |
| Interfaz del cliente    | `frontend/carta.html`        | ✅ Sprint 3          | — (consume los demás módulos)      |

## 13. Configuración (variables de entorno opcionales)

| Variable               | Por defecto                    | Descripción                              |
|------------------------|--------------------------------|------------------------------------------|
| `COLRIENT_HOST`        | `127.0.0.1`                    | Host del servidor                       |
| `COLRIENT_PORT`        | `8000`                         | Puerto del servidor                     |
| `COLRIENT_DEBUG`       | `false`                        | Modo depuración                         |
| `COLRIENT_DATABASE_URL`| `sqlite:///./colrient.db`      | Cadena de conexión de la base de datos  |
| `COLRIENT_CORS_ORIGINS`| `localhost:8000,localhost:5500`| Orígenes CORS permitidos (separados por coma) |
| `COLRIENT_UPLOAD_DIR`  | `backend/uploads`               | Carpeta donde se guardan las fotos subidas |
