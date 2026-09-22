// Backend desplegado en Render. Sin barra final.
// Para desarrollo local, cambiar por "http://127.0.0.1:7860".
const BACKEND_URL = "https://asistente-productividad.onrender.com";

const textarea = document.getElementById("solicitud");
const boton = document.getElementById("btn-procesar");
const estado = document.getElementById("estado");
const resultado = document.getElementById("resultado");

boton.addEventListener("click", procesar);
textarea.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) procesar();
});

function mostrarEstado(texto, esError = false) {
  estado.textContent = texto;
  estado.classList.toggle("error", esError);
}

function escapar(valor) {
  const div = document.createElement("div");
  div.textContent = valor == null ? "" : String(valor);
  return div.innerHTML;
}

async function procesar() {
  const solicitud = textarea.value.trim();
  resultado.innerHTML = "";

  if (!solicitud) {
    mostrarEstado("Escribe una solicitud antes de continuar.", true);
    return;
  }

  boton.disabled = true;
  mostrarEstado("Procesando solicitud…");

  try {
    const respuesta = await fetch(`${BACKEND_URL}/procesar-solicitud`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ solicitud }),
    });

    const datos = await respuesta.json().catch(() => null);

    if (!respuesta.ok) {
      const detalle = datos && datos.detail ? datos.detail : `Error ${respuesta.status}`;
      throw new Error(detalle);
    }

    mostrarEstado("");
    pintar(datos);
  } catch (error) {
    mostrarEstado(`No se pudo procesar: ${error.message}`, true);
  } finally {
    boton.disabled = false;
  }
}

function pintar(datos) {
  if (!datos) {
    mostrarEstado("El servidor devolvió una respuesta vacía.", true);
    return;
  }

  if (datos.tipo === "respuesta_texto") {
    resultado.innerHTML = `
      <div class="mensaje-aclaracion">
        <h2>Faltan datos</h2>
        <p>${escapar(datos.mensaje)}</p>
      </div>`;
    return;
  }

  if (datos.tipo === "tarea_generada") {
    const tareas = datos.tareas_creadas || [];

    if (tareas.length === 0) {
      resultado.innerHTML = `
        <div class="mensaje-aclaracion">
          <h2>Sin tareas</h2>
          <p>No se generó ninguna tarea con esa solicitud. Intenta dar más detalles.</p>
        </div>`;
      return;
    }

    let html = tareas.map(tarjetaTarea).join("");

    const calculos = datos.calculos || [];
    if (calculos.length > 0) {
      const detalle = calculos
        .map((c) => {
          const args = c.argumentos || {};
          return `impacto ${escapar(args.impacto)} + urgencia ${escapar(args.urgencia)} → ${escapar(c.prioridad)}`;
        })
        .join("<br />");
      html += `<div class="calculos"><strong>Prioridad calculada:</strong><br />${detalle}</div>`;
    }

    resultado.innerHTML = html;
    return;
  }

  mostrarEstado("Respuesta no reconocida del servidor.", true);
}

function tarjetaTarea(tarea) {
  const participantes = Array.isArray(tarea.participantes)
    ? tarea.participantes.join(", ")
    : tarea.participantes || "—";
  const prioridad = (tarea.prioridad || "normal").toLowerCase();

  return `
    <article class="tarea">
      <h3>${escapar(tarea.titulo)}</h3>
      <dl>
        <dt>Fecha</dt><dd>${escapar(tarea.fecha)}</dd>
        <dt>Hora</dt><dd>${escapar(tarea.hora)}</dd>
        <dt>Participantes</dt><dd>${escapar(participantes)}</dd>
        <dt>Prioridad</dt><dd><span class="etiqueta ${escapar(prioridad)}">${escapar(prioridad)}</span></dd>
        <dt>Estado</dt><dd>${escapar(tarea.estado)}</dd>
      </dl>
    </article>`;
}
