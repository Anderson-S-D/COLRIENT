/**
 * COLRIENT — Sección "Gestión del Menú".
 *
 * Creación de menús por categoría con rango de vigencia, histórico de
 * menús y publicación de la carta digital (un solo menú activo).
 */

const MenusUI = (() => {
    let menusCache = [];

    /** Busca un menú en caché; si no está, refresca y reintenta. */
    async function _buscarMenu(id) {
        let menu = menusCache.find((m) => m.id === id);
        if (!menu) {
            await cargar();
            menu = menusCache.find((m) => m.id === id);
        }
        return menu ?? null;
    }

    /** Crea un menú a partir del formulario de la sección. */
    async function crear(evento) {
        evento.preventDefault();
        try {
            const menu = await apiPost("/menus", {
                nombre: document.getElementById("menu-nombre").value.trim(),
                fecha_inicio: document.getElementById("menu-inicio").value,
                fecha_fin: document.getElementById("menu-fin").value,
                id_categoria: Number(document.getElementById("menu-categoria").value),
            });
            document.getElementById("form-menu").reset();
            mostrarToast(`Menú '${menu.nombre}' creado como borrador.`, "success");
            await cargar();
        } catch (error) {
            mostrarToast(error.message, "danger");
        }
    }

    /** Carga y pinta el histórico de menús + la carta publicada actual. */
    async function cargar() {
        const menus = await apiGet("/menus/historico");
        menusCache = menus;
        document.getElementById("menus-vacio").classList.toggle("d-none", menus.length > 0);

        document.getElementById("tbody-menus").innerHTML = menus
            .map(
                (m) => `
                <tr>
                    <td>${m.id}</td>
                    <td><strong>${escapar(m.nombre)}</strong></td>
                    <td>${badgeCategoria(m.categoria.nombre)}</td>
                    <td class="text-nowrap">
                        ${formatearFecha(m.fecha_inicio)} → ${formatearFecha(m.fecha_fin)}
                    </td>
                    <td>${badgeEstado(m.estado)}</td>
                    <td class="text-end">
                        ${
                            m.estado === "activo"
                                ? `<span class="badge text-bg-success rounded-pill"><i class="bi bi-check2"></i> Publicado</span>`
                                : `<button class="btn btn-sm btn-outline-success btn-accion" title="Publicar carta digital"
                                        onclick="MenusUI.publicar(${m.id})">
                                        <i class="bi bi-megaphone"></i> Publicar
                                   </button>`
                        }
                    </td>
                </tr>`
            )
            .join("");

        const publicado = menus.find((m) => m.estado === "activo");
        const badge = document.getElementById("badge-menu-activo");
        if (publicado) {
            badge.textContent = `Carta publicada: ${publicado.nombre}`;
            badge.className = "badge text-bg-success";
        } else {
            badge.textContent = "Carta publicada: ninguna";
            badge.className = "badge text-bg-secondary";
        }
    }

    /** Publica un menú como carta digital activa (desactiva los demás). */
    async function publicar(id) {
        const menu = await _buscarMenu(id);
        if (!menu) {
            mostrarToast("El menú solicitado ya no existe.", "warning");
            return;
        }
        const confirmado = await confirmarAccion(
            "Publicar carta digital",
            `¿Publicar el menú '${menu.nombre}' (id=${id}) como carta activa? Los demás menús quedarán inactivos.`
        );
        if (!confirmado) return;
        try {
            await apiPut(`/menus/${id}/publicar`);
            mostrarToast(`Carta digital '${menu.nombre}' publicada.`, "success");
            await cargar();
        } catch (error) {
            mostrarToast(error.message, "danger");
        }
    }

    /** Registra los eventos y llena el select de categorías. */
    function iniciar(catalogos) {
        document.getElementById("form-menu").addEventListener("submit", crear);
        llenarSelect(document.getElementById("menu-categoria"), catalogos.categorias);
    }

    return { crear, cargar, publicar, iniciar };
})();
