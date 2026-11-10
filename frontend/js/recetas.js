/**
 * COLRIENT — Sección "Recetas / Ingredientes".
 *
 * Registro de ingredientes (sin duplicados), consulta de la receta
 * completa de un plato, asociación de ingredientes con cantidad y
 * eliminación/sustitución dentro de la receta.
 */

const RecetasUI = (() => {
    let modalIngrediente;
    let recetaCache = null; // receta del plato seleccionado (para mensajes)

    /** Carga y pinta la tabla de ingredientes registrados. */
    async function cargarIngredientes() {
        const ingredientes = await apiGet("/ingredientes");
        document.getElementById("ingredientes-vacio").classList.toggle(
            "d-none",
            ingredientes.length > 0
        );
        document.getElementById("tbody-ingredientes").innerHTML = ingredientes
            .map(
                (i) => `
                <tr>
                    <td>${i.id}</td>
                    <td>${escapar(i.nombre)}</td>
                    <td><span class="badge text-bg-light border">${escapar(i.unidad_medida)}</span></td>
                </tr>`
            )
            .join("");
        return ingredientes;
    }

    /** Llena el <select> de platos disponible para consultar/editar su receta. */
    async function cargarPlatos() {
        const platos = await apiGet("/platos");
        llenarSelect(
            document.getElementById("select-plato-receta"),
            platos.map((p) => ({ id: p.id, nombre: `${p.id} · ${p.nombre}` })),
            "Seleccione un plato…"
        );
    }

    /** Carga la receta del plato seleccionado y la pinta. */
    async function cargarReceta() {
        const platoId = document.getElementById("select-plato-receta").value;
        const tbody = document.getElementById("tbody-receta");
        const vacio = document.getElementById("receta-vacio");

        if (!platoId) {
            tbody.innerHTML = "";
            vacio.classList.remove("d-none");
            return;
        }

        const receta = await apiGet(`/platos/${platoId}/receta`);
        recetaCache = receta;
        tbody.innerHTML = receta.recetas
            .map(
                (item) => `
                <tr>
                    <td>${escapar(item.ingrediente.nombre)}</td>
                    <td class="text-end">${escapar(item.cantidad)}</td>
                    <td>${escapar(item.ingrediente.unidad_medida)}</td>
                    <td class="text-end">
                        <button class="btn btn-sm btn-outline-danger btn-accion" title="Quitar de la receta"
                                onclick="RecetasUI.quitar(${platoId}, ${item.id_ingrediente})">
                            <i class="bi bi-dash-lg"></i> Quitar
                        </button>
                    </td>
                </tr>`
            )
            .join("");
        vacio.classList.toggle("d-none", receta.recetas.length > 0);
    }

    /** Asocia un ingrediente con su cantidad a la receta del plato activo. */
    async function asociar(evento) {
        evento.preventDefault();
        const platoId = document.getElementById("select-plato-receta").value;
        const idIngrediente = document.getElementById("asociar-ingrediente").value;
        const cantidad = document.getElementById("asociar-cantidad").value;

        if (!platoId || !idIngrediente) {
            mostrarToast("Seleccione el plato y el ingrediente a asociar.", "warning");
            return;
        }
        try {
            await apiPost(`/platos/${platoId}/ingredientes`, {
                id_ingrediente: Number(idIngrediente),
                cantidad: Number(cantidad),
            });
            document.getElementById("asociar-cantidad").value = "";
            mostrarToast("Ingrediente asociado a la receta.", "success");
            await cargarReceta();
        } catch (error) {
            mostrarToast(error.message, "danger");
        }
    }

    /** Elimina un ingrediente de la receta (paso 1 de la sustitución). */
    async function quitar(platoId, idIngrediente) {
        const item = recetaCache?.recetas.find((r) => r.id_ingrediente === idIngrediente);
        const nombre = item ? item.ingrediente.nombre : `id=${idIngrediente}`;
        const confirmado = await confirmarAccion(
            "Quitar ingrediente",
            `¿Quitar '${nombre}' de la receta? Podrá asociar otro ingrediente en su lugar.`
        );
        if (!confirmado) return;
        try {
            await apiDelete(`/platos/${platoId}/ingredientes/${idIngrediente}`);
            mostrarToast("Ingrediente quitado de la receta.", "success");
            await cargarReceta();
        } catch (error) {
            mostrarToast(error.message, "danger");
        }
    }

    /** Registra un ingrediente nuevo desde el modal. */
    async function guardarIngrediente(evento) {
        evento.preventDefault();
        try {
            const ingrediente = await apiPost("/ingredientes", {
                nombre: document.getElementById("ingrediente-nombre").value.trim(),
                unidad_medida: document.getElementById("ingrediente-unidad").value.trim(),
            });
            modalIngrediente.hide();
            document.getElementById("form-ingrediente").reset();
            mostrarToast(`Ingrediente '${ingrediente.nombre}' registrado.`, "success");
            await RefrescarUI.ingredientes(); // refresca selects y tablas
        } catch (error) {
            mostrarToast(error.message, "danger");
        }
    }

    /** Registra los eventos de la sección. */
    function iniciar() {
        modalIngrediente = bootstrap.Modal.getOrCreateInstance(
            document.getElementById("modal-ingrediente")
        );
        document.getElementById("btn-nuevo-ingrediente").addEventListener("click", () => modalIngrediente.show());
        document.getElementById("form-ingrediente").addEventListener("submit", guardarIngrediente);
        document.getElementById("select-plato-receta").addEventListener("change", cargarReceta);
        document.getElementById("form-asociar").addEventListener("submit", asociar);
    }

    return { cargarIngredientes, cargarPlatos, cargarReceta, quitar, iniciar };
})();

/** Refresca catálogos dependientes de ingredientes tras cambios. */
const RefrescarUI = {
    async ingredientes() {
        const ingredientes = await RecetasUI.cargarIngredientes();
        llenarSelect(
            document.getElementById("asociar-ingrediente"),
            ingredientes,
            "Ingrediente…"
        );
    },
};
