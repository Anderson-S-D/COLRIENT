/**
 * COLRIENT — Sección "Gestión de Platos".
 *
 * Tabla con badges de región/categoría, acciones (ver foto, editar,
 * eliminar) y formulario modal para registrar/editar con vista previa
 * de imagen. Toda la comunicación es async/await contra la API REST.
 */

const PlatosUI = (() => {
    let modalPlato;
    let modalFoto;
    let platosCache = []; // última lista consultada (evita peticiones extra)

    /** Busca un plato en caché; si no está, refresca y reintenta. */
    async function _buscarPlato(id) {
        let plato = platosCache.find((p) => p.id === id);
        if (!plato) {
            await cargar();
            plato = platosCache.find((p) => p.id === id);
        }
        return plato ?? null;
    }

    /** Carga y pinta la tabla de platos aplicando los filtros activos. */
    async function cargar() {
        const params = new URLSearchParams();
        const categoria = document.getElementById("filtro-categoria").value;
        const region = document.getElementById("filtro-region").value;
        const nombre = document.getElementById("filtro-nombre").value.trim();
        if (categoria) params.set("categoria", categoria);
        if (region) params.set("region", region);
        if (nombre) params.set("nombre", nombre);

        const platos = await apiGet(`/platos${params.size ? `?${params}` : ""}`);
        platosCache = platos;
        render(platos);
    }

    /** Pinta las filas de la tabla de platos. */
    function render(platos) {
        const tbody = document.getElementById("tbody-platos");
        document.getElementById("platos-vacio").classList.toggle("d-none", platos.length > 0);

        tbody.innerHTML = platos
            .map(
                (p) => `
            <tr>
                <td>${p.id}</td>
                <td>
                    <strong>${escapar(p.nombre)}</strong>${p.recomendado ? ' <i class="bi bi-star-fill text-warning" title="Plato recomendado"></i>' : ""}
                    ${p.descripcion ? `<div class="small text-body-secondary">${escapar(p.descripcion)}</div>` : ""}
                </td>
                <td>${badgeCategoria(p.categoria.nombre)}</td>
                <td>${badgeRegion(p.region.nombre)}</td>
                <td>${p.horarios.length ? p.horarios.map(badgeHorario).join(" ") : `<span class="text-body-secondary small">—</span>`}</td>
                <td class="text-end">${bloquePrecio(p.precio, p.precio_promocional)}</td>
                <td>${badgeEstado(p.estado)}</td>
                <td>
                    ${
                        p.foto_url
                            ? `<img src="${escapar(p.foto_url)}" alt="Foto de ${escapar(p.nombre)}" class="foto-thumb" />`
                            : `<span class="text-body-secondary small">—</span>`
                    }
                </td>
                <td class="text-end text-nowrap">
                    <button class="btn btn-sm btn-outline-primary btn-accion" title="Ver foto"
                            onclick="PlatosUI.verFoto(${p.id})">
                        <i class="bi bi-eye"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-secondary btn-accion" title="Editar"
                            onclick="PlatosUI.abrirModal(${p.id})">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger btn-accion" title="Eliminar"
                            onclick="PlatosUI.eliminar(${p.id})">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            </tr>`
            )
            .join("");
    }

    /** Abre el modal de plato: sin id registra, con id edita. */
    async function abrirModal(id = null) {
        const form = document.getElementById("form-plato");
        form.reset();
        document.getElementById("plato-id").value = id ?? "";
        document.getElementById("plato-foto-preview").src = "assets/img/sin-foto.svg";
        document.getElementById("plato-foto-actual").textContent = "";

        const titulo = document.getElementById("modal-plato-titulo");
        const boton = document.getElementById("btn-guardar-plato");

        if (id === null) {
            titulo.textContent = "Registrar plato";
            boton.textContent = "Registrar";
        } else {
            const platoEditar = await _buscarPlato(id);
            if (!platoEditar) {
                mostrarToast("El plato solicitado ya no existe.", "warning");
                return;
            }
            titulo.textContent = `Editar plato #${id}`;
            boton.textContent = "Guardar cambios";
            document.getElementById("plato-nombre").value = platoEditar.nombre;
            document.getElementById("plato-descripcion").value = platoEditar.descripcion ?? "";
            document.getElementById("plato-precio").value = Number(platoEditar.precio);
            document.getElementById("plato-estado").value = platoEditar.estado;
            document.getElementById("plato-categoria").value = String(platoEditar.id_categoria);
            document.getElementById("plato-region").value = String(platoEditar.id_region);
            for (const horario of platoEditar.horarios) {
                document.getElementById(`plato-horario-${horario}`).checked = true;
            }
            document.getElementById("plato-promocion").value =
                platoEditar.precio_promocional != null ? Number(platoEditar.precio_promocional) : "";
            document.getElementById("plato-recomendado").checked = platoEditar.recomendado;
            if (platoEditar.foto_url) {
                document.getElementById("plato-foto-preview").src = platoEditar.foto_url;
                document.getElementById("plato-foto-actual").textContent =
                    "Foto actual (cargar una nueva la reemplaza).";
            }
        }
        modalPlato.show();
    }

    /** Registra o edita un plato y, si hay archivo, sube también la foto. */
    async function guardar(evento) {
        evento.preventDefault();
        const id = document.getElementById("plato-id").value;
        const cuerpo = {
            nombre: document.getElementById("plato-nombre").value.trim(),
            descripcion: document.getElementById("plato-descripcion").value.trim() || null,
            precio: Number(document.getElementById("plato-precio").value),
            estado: document.getElementById("plato-estado").value,
            id_categoria: Number(document.getElementById("plato-categoria").value),
            id_region: Number(document.getElementById("plato-region").value),
            horarios: Object.keys(HORARIOS_UI).filter(
                (h) => document.getElementById(`plato-horario-${h}`).checked
            ),
            recomendado: document.getElementById("plato-recomendado").checked,
            precio_promocional: document.getElementById("plato-promocion").value
                ? Number(document.getElementById("plato-promocion").value)
                : null,
        };

        try {
            const plato = id ? await apiPut(`/platos/${id}`, cuerpo) : await apiPost("/platos", cuerpo);

            const archivo = document.getElementById("plato-foto").files[0];
            if (archivo) {
                const formData = new FormData();
                formData.append("foto", archivo);
                await apiUpload(`/platos/${plato.id}/foto`, formData);
            }

            modalPlato.hide();
            mostrarToast(id ? "Plato actualizado correctamente." : `Plato '${plato.nombre}' registrado.`, "success");
            await cargar();
        } catch (error) {
            mostrarToast(error.message, "danger");
        }
    }

    /** Elimina un plato tras confirmar (requiere rol Gerente en la API). */
    async function eliminar(id) {
        const plato = await _buscarPlato(id);
        if (!plato) {
            mostrarToast("El plato solicitado ya no existe.", "warning");
            return;
        }
        const confirmado = await confirmarAccion(
            "Eliminar plato",
            `¿Eliminar el plato '${plato.nombre}' (id=${id})? Esta acción también borra su receta y su foto.`
        );
        if (!confirmado) return;
        try {
            await apiDelete(`/platos/${id}`);
            mostrarToast("Plato eliminado.", "success");
            await cargar();
        } catch (error) {
            mostrarToast(error.message, "danger");
        }
    }

    /** Muestra la foto del plato en un modal centrado. */
    async function verFoto(id) {
        const plato = await _buscarPlato(id);
        if (!plato) {
            mostrarToast("El plato solicitado ya no existe.", "warning");
            return;
        }
        document.getElementById("ver-foto-titulo").textContent = `Foto · ${plato.nombre}`;
        const img = document.getElementById("ver-foto-img");
        const vacio = document.getElementById("ver-foto-vacio");
        if (plato.foto_url) {
            img.src = plato.foto_url;
            img.classList.remove("d-none");
            vacio.classList.add("d-none");
        } else {
            img.classList.add("d-none");
            vacio.classList.remove("d-none");
        }
        modalFoto.show();
    }

    /** Vista previa de la imagen seleccionada en el formulario. */
    function previsualizar(input) {
        const archivo = input.files[0];
        if (!archivo) return;
        const lector = new FileReader();
        lector.onload = (e) => (document.getElementById("plato-foto-preview").src = e.target.result);
        lector.readAsDataURL(archivo);
    }

    /** Registra los eventos de la sección. */
    function iniciar(catalogos) {
        modalPlato = bootstrap.Modal.getOrCreateInstance(document.getElementById("modal-plato"));
        modalFoto = bootstrap.Modal.getOrCreateInstance(document.getElementById("modal-ver-foto"));

        document.getElementById("btn-nuevo-plato").addEventListener("click", () => abrirModal());
        document.getElementById("form-plato").addEventListener("submit", guardar);
        document.getElementById("plato-foto").addEventListener("change", (e) => previsualizar(e.target));

        // Enter en el buscador: refrescar la tabla, no recargar la página.
        document.getElementById("form-filtros").addEventListener("submit", (e) => {
            e.preventDefault();
            cargar();
        });

        for (const id of ["filtro-categoria", "filtro-region"]) {
            document.getElementById(id).addEventListener("change", cargar);
        }
        document.getElementById("filtro-nombre").addEventListener("input", () => {
            clearTimeout(cargar._espera);
            cargar._espera = setTimeout(cargar, 350); // debounce de búsqueda
        });

        // Los selects de categoría/región se alimentan de los catálogos.
        llenarSelect(
            document.getElementById("filtro-categoria"),
            catalogos.categorias,
            "Todas las categorías"
        );
        llenarSelect(document.getElementById("filtro-region"), catalogos.regiones, "Todas las regiones");
        llenarSelect(document.getElementById("plato-categoria"), catalogos.categorias);
        llenarSelect(document.getElementById("plato-region"), catalogos.regiones);
    }

    return { cargar, abrirModal, eliminar, verFoto, guardar, iniciar };
})();
