/**
 * COLRIENT — Utilidades de interfaz (Bootstrap 5).
 *
 * Toasts de retroalimentación, diálogo de confirmación reutilizable,
 * badges de categoría/región y formateo de valores.
 */

/** Escapa texto para insertarlo con seguridad en HTML. */
function escapar(texto) {
    return String(texto ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

/** Muestra un toast de Bootstrap (tipo: success, danger, warning, primary). */
function mostrarToast(mensaje, tipo = "success") {
    const plantilla = document.createElement("div");
    plantilla.className = `toast align-items-center text-bg-${tipo} border-0`;
    plantilla.setAttribute("role", "alert");
    plantilla.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${escapar(mensaje)}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>`;
    document.getElementById("toasts").appendChild(plantilla);
    const toast = new bootstrap.Toast(plantilla, { delay: 3500 });
    toast.show();
    plantilla.addEventListener("hidden.bs.toast", () => plantilla.remove());
}

/** Diálogo de confirmación reutilizable basado en el modal de Bootstrap.
 *  Resuelve true si el usuario confirma la acción. */
function confirmarAccion(titulo, mensaje) {
    return new Promise((resolver) => {
        document.getElementById("confirmacion-titulo").textContent = titulo;
        document.getElementById("confirmacion-mensaje").textContent = mensaje;

        const modal = bootstrap.Modal.getOrCreateInstance(
            document.getElementById("modal-confirmacion")
        );
        const aceptar = document.getElementById("btn-confirmar-aceptar");
        const cancelar = document.getElementById("btn-confirmar-cancelar");

        const cerrar = (resultado) => {
            modal.hide();
            aceptar.onclick = null;
            cancelar.onclick = null;
            resolver(resultado);
        };
        aceptar.onclick = () => cerrar(true);
        cancelar.onclick = () => cerrar(false);

        modal.show();
    });
}

/** Badge coloreado para la categoría del plato o menú. */
function badgeCategoria(nombre) {
    return `<span class="badge badge-categoria rounded-pill">${escapar(nombre)}</span>`;
}

/** Badge coloreado para la región gastronómica. */
function badgeRegion(nombre) {
    return `<span class="badge badge-region rounded-pill">${escapar(nombre)}</span>`;
}

/** Badge de estado (disponible/agotado, activo/inactivo). */
function badgeEstado(estado) {
    const clase = estado === "disponible" || estado === "activo" ? "text-bg-success" : "text-bg-secondary";
    return `<span class="badge ${clase} rounded-pill">${escapar(estado)}</span>`;
}

/** Formatea un precio (serializado como texto por la API) en pesos. */
function formatearPrecio(precio) {
    return new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 }).format(
        Number(precio)
    );
}

/** Formatea una fecha ISO (YYYY-MM-DD) como fecha larga local. */
function formatearFecha(fechaIso) {
    return new Date(`${fechaIso}T00:00:00`).toLocaleDateString("es-CO", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    });
}

/** Llena un <select> con opciones {id, nombre}; conserva el valor actual. */
function llenarSelect(select, opciones, placeholder = null, valor = null) {
    const actual = valor ?? select.value;
    select.innerHTML = "";
    if (placeholder !== null) {
        select.appendChild(new Option(placeholder, ""));
    }
    for (const { id, nombre } of opciones) {
        select.appendChild(new Option(nombre, String(id)));
    }
    select.value = actual && select.querySelector(`option[value="${actual}"]`) ? actual : "";
}

/* --- Horarios de consumo, promociones y recomendados ------------------- */

/** Iconos y etiquetas de los horarios de consumo. */
const HORARIOS_UI = {
    desayuno: { icono: "bi-sunrise", etiqueta: "Desayuno" },
    almuerzo: { icono: "bi-sun", etiqueta: "Almuerzo" },
    cena: { icono: "bi-moon-stars", etiqueta: "Cena" },
};

/** Badge de horario de consumo (Desayuno, Almuerzo, Cena). */
function badgeHorario(horario) {
    const { icono, etiqueta } = HORARIOS_UI[horario] ?? { icono: "bi-clock", etiqueta: horario };
    return `<span class="badge badge-horario rounded-pill"><i class="bi ${icono}"></i> ${etiqueta}</span>`;
}

/** Bloque de precio: si hay promoción, tacha el precio normal y muestra
 *  el precio promocional junto al porcentaje de descuento. */
function bloquePrecio(precio, precioPromocional) {
    if (precioPromocional != null) {
        const descuento = Math.round((1 - Number(precioPromocional) / Number(precio)) * 100);
        return `
            <div class="small text-body-secondary"><s>${formatearPrecio(precio)}</s></div>
            <div class="text-success">${formatearPrecio(precioPromocional)}
                <span class="badge text-bg-danger rounded-pill">-${descuento}%</span>
            </div>`;
    }
    return formatearPrecio(precio);
}
