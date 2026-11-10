/**
 * COLRIENT — Carta digital (interfaz del cliente).
 *
 * Catálogo de platos con filtros dinámicos por categoría y horario de
 * consumo (sin recargar la página), secciones destacadas de platos
 * recomendados y promociones, y modal de detalle con imagen y
 * descripción. Toda la información proviene de la API REST (fetch).
 */

const CartaUI = (() => {
    let platosCache = [];      // catálogo completo (una sola petición)
    let modalDetalle;

    /* ----------------------------------------------------------------
     * Carga inicial
     * ---------------------------------------------------------------- */

    /** Descarga catálogo, categorías y carta vigente; pinta la interfaz. */
    async function iniciar() {
        modalDetalle = bootstrap.Modal.getOrCreateInstance(document.getElementById("modal-detalle"));

        try {
            const [platos, categorias, activos] = await Promise.all([
                apiGet("/platos"),
                apiGet("/categorias"),
                apiGet("/menus/historico?estado=activo"),
            ]);
            platosCache = platos;

            llenarSelect(
                document.getElementById("filtro-categoria"),
                categorias,
                "Todas las categorías"
            );
            _pintarCartaVigente(activos[0] ?? null);
            render();
        } catch (error) {
            document.getElementById("contador-platos").textContent = "No se pudo cargar la carta.";
            mostrarToast(`No se pudo cargar la carta: ${error.message}`, "danger");
        }

        // Filtros dinámicos: cada cambio repinta sin recargar la página.
        document.getElementById("form-filtros-carta").addEventListener("submit", (e) => e.preventDefault());
        for (const id of ["filtro-categoria", "filtro-horario", "filtro-disponibles"]) {
            document.getElementById(id).addEventListener("change", render);
        }
        document.getElementById("filtro-nombre").addEventListener("input", render);
        document.getElementById("btn-limpiar").addEventListener("click", () => setTimeout(render, 0));
    }

    /* ----------------------------------------------------------------
     * Filtros (en memoria, sobre la caché del catálogo)
     * ---------------------------------------------------------------- */

    /** Aplica los filtros activos y devuelve los platos visibles. */
    function filtrar() {
        const categoria = document.getElementById("filtro-categoria").value;
        const horario = document.getElementById("filtro-horario").value;
        const texto = document.getElementById("filtro-nombre").value.trim().toLowerCase();
        const soloDisponibles = document.getElementById("filtro-disponibles").checked;

        return platosCache.filter((p) => {
            if (categoria && String(p.id_categoria) !== categoria) return false;
            if (horario && !p.horarios.includes(horario)) return false;
            if (soloDisponibles && p.estado !== "disponible") return false;
            if (texto) {
                const enNombre = p.nombre.toLowerCase().includes(texto);
                const enDescripcion = (p.descripcion ?? "").toLowerCase().includes(texto);
                if (!enNombre && !enDescripcion) return false;
            }
            return true;
        });
    }

    /** Repinta todas las secciones según los filtros activos. */
    function render() {
        const visibles = filtrar();
        _pintarCatalogo(visibles);

        // Secciones destacadas: solo platos disponibles, para no tentar
        // al cliente con algo agotado.
        const disponibles = platosCache.filter((p) => p.estado === "disponible");
        _pintarRecomendados(disponibles.filter((p) => p.recomendado));
        _pintarPromociones(disponibles.filter((p) => p.precio_promocional != null));

        const total = visibles.length;
        document.getElementById("contador-platos").textContent =
            total === 1 ? "1 plato encontrado" : `${total} platos encontrados`;
    }

    /* ----------------------------------------------------------------
     * Renderizado
     * ---------------------------------------------------------------- */

    /** Banner con la carta digital publicada (menú activo). */
    function _pintarCartaVigente(menu) {
        const contenedor = document.getElementById("carta-vigente");
        if (!menu) return; // sin carta publicada se oculta el banner
        document.getElementById("carta-vigente-texto").textContent =
            `Carta vigente: ${menu.nombre} · ${formatearFecha(menu.fecha_inicio)} a ${formatearFecha(menu.fecha_fin)}`;
        contenedor.classList.remove("d-none");
    }

    /** Tarjeta de un plato (usada en catálogo, promociones y destacados). */
    function _tarjeta(plato, opciones = {}) {
        const agotado = plato.estado === "agotado";
        const claseTarjeta = `card carta-card h-100 ${agotado ? "carta-agotado" : ""}`;
        const tarjeta = `
            <div class="${claseTarjeta}">
                <figure class="carta-foto">
                    <img src="${escapar(plato.foto_url ?? "assets/img/sin-foto.svg")}"
                         alt="Foto del plato ${escapar(plato.nombre)}" loading="lazy" />
                    ${agotado ? `<span class="badge text-bg-secondary position-absolute top-0 end-0 m-2">Agotado</span>` : ""}
                    ${plato.precio_promocional != null ? `<span class="badge text-bg-danger position-absolute top-0 start-0 m-2"><i class="bi bi-tags-fill"></i> Promo</span>` : ""}
                    ${plato.recomendado ? `<span class="badge text-bg-warning position-absolute bottom-0 start-0 m-2"><i class="bi bi-star-fill"></i> Recomendado</span>` : ""}
                </figure>
                <div class="card-body pb-2">
                    <div class="mb-1 d-flex flex-wrap gap-1">
                        ${badgeCategoria(plato.categoria.nombre)}
                        ${badgeRegion(plato.region.nombre)}
                        ${plato.horarios.map(badgeHorario).join("")}
                    </div>
                    <h3 class="h6 mb-1">${escapar(plato.nombre)}</h3>
                    <p class="small text-body-secondary carta-desc mb-0">
                        ${escapar(plato.descripcion ?? "Sin descripción.")}
                    </p>
                </div>
                <div class="card-footer bg-white d-flex justify-content-between align-items-center">
                    <div class="precio">${bloquePrecio(plato.precio, plato.precio_promocional)}</div>
                    <button class="btn btn-sm btn-outline-danger" title="Ver imagen y descripción"
                            onclick="CartaUI.verDetalle(${plato.id})">
                        <i class="bi bi-eye"></i><span class="d-none d-md-inline ms-1">Ver detalle</span>
                    </button>
                </div>
            </div>`;

        // En la fila de recomendados la card es hija directa del scroll.
        return opciones.compacta ? tarjeta : `<div class="col">${tarjeta}</div>`;
    }

    /** Catálogo principal con el estado vacío. */
    function _pintarCatalogo(platos) {
        const lista = document.getElementById("carta-lista");
        const vacio = document.getElementById("carta-vacio");
        lista.innerHTML = platos.map((p) => _tarjeta(p)).join("");
        vacio.classList.toggle("d-none", platos.length > 0);
    }

    /** Sección de recomendados (fila con desplazamiento horizontal). */
    function _pintarRecomendados(platos) {
        document.getElementById("contador-recomendados").textContent = platos.length;
        document.getElementById("recomendados-lista").innerHTML = platos
            .map((p) => _tarjeta(p, { compacta: true }))
            .join("");
        document.getElementById("recomendados-vacio").classList.toggle(
            "d-none", platos.length > 0
        );
    }

    /** Sección de promociones (rejilla). */
    function _pintarPromociones(platos) {
        document.getElementById("contador-promociones").textContent = platos.length;
        document.getElementById("promociones-lista").innerHTML = platos
            .map((p) => _tarjeta(p))
            .join("");
        document.getElementById("promociones-vacio").classList.toggle(
            "d-none", platos.length > 0
        );
    }

    /* ----------------------------------------------------------------
     * Detalle del plato (modal)
     * ---------------------------------------------------------------- */

    /** Abre el modal con la imagen y la descripción detallada. */
    function verDetalle(id) {
        const plato = platosCache.find((p) => p.id === id);
        if (!plato) return;

        document.getElementById("detalle-titulo").textContent = plato.nombre;
        document.getElementById("detalle-foto").src =
            plato.foto_url ?? "assets/img/sin-foto.svg";
        document.getElementById("detalle-badges").innerHTML =
            badgeCategoria(plato.categoria.nombre) +
            badgeRegion(plato.region.nombre) +
            plato.horarios.map(badgeHorario).join("");
        document.getElementById("detalle-descripcion").textContent =
            plato.descripcion ?? "Sin descripción disponible.";
        document.getElementById("detalle-estado").innerHTML = badgeEstado(plato.estado);
        document.getElementById("detalle-precio").innerHTML = bloquePrecio(
            plato.precio, plato.precio_promocional
        );
        modalDetalle.show();
    }

    return { iniciar, render, verDetalle };
})();

document.addEventListener("DOMContentLoaded", CartaUI.iniciar);
