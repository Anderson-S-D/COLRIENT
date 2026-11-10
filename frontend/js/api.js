/**
 * COLRIENT — Capa de acceso a la API REST (fetch / async).
 *
 * Todas las peticiones parten del prefijo /api/v1 del backend. Los
 * errores HTTP se convierten en excepciones con el mensaje devuelto
 * por la API (campo "detail"), incluida la validación 422 de Pydantic.
 */
const API_BASE_URL = "/api/v1";
const ROL_STORAGE_KEY = "colrient.rol";

/** Obtiene el rol activo (Gerente/Cocinero) elegido en la barra superior. */
function rolActual() {
    return localStorage.getItem(ROL_STORAGE_KEY) || "gerente";
}

/** Construye el mensaje de error a partir del cuerpo de la respuesta. */
function _mensajeError(cuerpo, estado) {
    if (typeof cuerpo.detail === "string") {
        return cuerpo.detail;
    }
    // Validación 422 de Pydantic: lista de campos con sus errores.
    if (Array.isArray(cuerpo.detail)) {
        return cuerpo.detail
            .map((e) => `Campo '${e.loc ? e.loc[e.loc.length - 1] : "?"}': ${e.msg}`)
            .join(" · ");
    }
    return `Error HTTP ${estado}`;
}

/** Ejecuta una petición HTTP contra la API y normaliza errores. */
async function _request(path, { metodo = "GET", cuerpo = null, formData = null, cabeceras = {} } = {}) {
    const opciones = {
        method: metodo,
        headers: { Accept: "application/json", ...cabeceras },
    };

    if (formData) {
        opciones.body = formData;                 // multipart: el navegador fija el Content-Type
    } else if (cuerpo !== null) {
        opciones.headers["Content-Type"] = "application/json";
        opciones.body = JSON.stringify(cuerpo);
    }

    const respuesta = await fetch(`${API_BASE_URL}${path}`, opciones);

    if (respuesta.status === 204) {
        return null;
    }

    const datos = await respuesta.json().catch(() => ({}));
    if (!respuesta.ok) {
        throw new Error(_mensajeError(datos, respuesta.status));
    }
    return datos;
}

const apiGet = (path) => _request(path);

const apiPost = (path, cuerpo) => _request(path, { metodo: "POST", cuerpo });

const apiPut = (path, cuerpo) => _request(path, { metodo: "PUT", cuerpo });

const apiDelete = (path) => _request(path, { metodo: "DELETE", cabeceras: { "X-Rol": rolActual() } });

const apiUpload = (path, formData) => _request(path, { metodo: "POST", formData });
