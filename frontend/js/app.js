/**
 * COLRIENT — Arranque del panel administrativo.
 *
 * Verifica el estado del servidor, carga los catálogos y las secciones,
 * y gestiona la navegación de la barra lateral.
 */

const App = (() => {
    const SECCIONES = {
        platos: {
            titulo: "Gestión de Platos",
            subtitulo: "Administración de la carta de platos del restaurante",
            cargar: () => PlatosUI.cargar(),
        },
        recetas: {
            titulo: "Recetas / Ingredientes",
            subtitulo: "Insumos de cocina y recetas asociadas a cada plato",
            cargar: async () => {
                await RefrescarUI.ingredientes();
                await RecetasUI.cargarPlatos();
                await RecetasUI.cargarReceta();
            },
        },
        menus: {
            titulo: "Gestión del Menú",
            subtitulo: "Cartas digitales por categoría con vigencia e histórico",
            cargar: () => MenusUI.cargar(),
        },
    };

    let seccionActual = "platos";

    /** Cambia la sección visible y actualiza la barra lateral. */
    async function mostrarSeccion(nombre) {
        if (!SECCIONES[nombre]) return;
        seccionActual = nombre;

        for (const clave of Object.keys(SECCIONES)) {
            document.getElementById(`seccion-${clave}`).classList.toggle("d-none", clave !== nombre);
        }
        document.querySelectorAll(".sidebar-nav .nav-link").forEach((enlace) => {
            enlace.classList.toggle("active", enlace.dataset.section === nombre);
        });
        document.getElementById("titulo-seccion").textContent = SECCIONES[nombre].titulo;
        document.getElementById("subtitulo-seccion").textContent = SECCIONES[nombre].subtitulo;

        await SECCIONES[nombre].cargar();
    }

    /** Comprueba el health check y pinta el badge de la barra lateral. */
    async function verificarServidor() {
        const badge = document.getElementById("badge-servidor");
        try {
            const salud = await apiGet("/health");
            badge.textContent = "en línea";
            badge.className = "badge text-bg-success ms-1";
            badge.title = `${salud.app} v${salud.version}`;
        } catch {
            badge.textContent = "sin conexión";
            badge.className = "badge text-bg-danger ms-1";
        }
    }

    /** Inicialización general del panel. */
    async function iniciar() {
        // Navegación de la barra lateral.
        document.querySelectorAll(".sidebar-nav .nav-link").forEach((enlace) => {
            enlace.addEventListener("click", (e) => {
                e.preventDefault();
                mostrarSeccion(enlace.dataset.section);
            });
        });

        // Rol activo (persistente) usado en las operaciones restringidas.
        const selectRol = document.getElementById("select-rol");
        selectRol.value = rolActual();
        selectRol.addEventListener("change", () => {
            localStorage.setItem(ROL_STORAGE_KEY, selectRol.value);
            mostrarToast(`Rol activo: ${selectRol.value}.`, "primary");
        });

        try {
            const [categorias, regiones] = await Promise.all([apiGet("/categorias"), apiGet("/regiones")]);
            PlatosUI.iniciar({ categorias, regiones });
            MenusUI.iniciar({ categorias, regiones });
            RecetasUI.iniciar();
            await mostrarSeccion("platos");
        } catch (error) {
            mostrarToast(`No se pudo inicializar el panel: ${error.message}`, "danger");
        }

        verificarServidor();
        setInterval(verificarServidor, 30000); // re-check periódico
    }

    document.addEventListener("DOMContentLoaded", iniciar);
})();
