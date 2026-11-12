export default function (component) {
  const { parentElement } = component
  const root = parentElement
  const $ = selector => root.querySelector(selector)
  const $$ = selector => [...root.querySelectorAll(selector)]
  const container = $(".stride-root")
  if (!container || container.dataset.initialized === "true") return
  container.dataset.initialized = "true"

  const defaults = [
    { title: "Rodaje por el Retiro", distance: 8.2, minutes: 44, date: "Hoy · 07:15" },
    { title: "Series para ir más lejos", distance: 6.4, minutes: 31, date: "Ayer · 18:30" },
    { title: "Domingo de tirada larga", distance: 14, minutes: 79, date: "8 nov · 08:00" },
  ]
  const plans = [
    ["RODAJE SUAVE", "Empieza con calma", "5 km · Ritmo cómodo"],
    ["SERIES", "Un poco de velocidad", "6 × 400 m · Recuperación 90 s"],
    ["RECUPERACIÓN", "Hoy, disfruta del camino", "8 km · Zona 2 · 45 minutos"],
    ["DESCANSO", "Recargar también cuenta", "Movilidad suave · 15 minutos"],
    ["TEMPO", "Encuentra tu ritmo", "7 km · Ritmo controlado"],
    ["RODAJE SUAVE", "Sin prisa, sin pausa", "5 km · Ritmo cómodo"],
    ["TIRADA LARGA", "Un poquito más lejos", "14 km · Ritmo conversacional"],
  ]
  const training = {
    current: [
      ["LUN", "9", "Rodaje suave", "5 km · Planificado 30 min · Realizado 29 min", "Completado"],
      ["MAR", "10", "Series 6 × 400 m", "6,4 km · Planificado 35 min · Realizado 31 min", "Completado"],
      ["MIÉ", "11", "Rodaje de recuperación", "8 km · Zona 2 · 45 minutos", "Hoy"],
      ["JUE", "12", "Descanso y movilidad", "15 minutos · Recuperación", "Próximo"],
      ["VIE", "13", "Tempo progresivo", "7 km · Ritmo controlado", "Próximo"],
      ["DOM", "15", "Tirada larga", "14 km · Ritmo conversacional", "Próximo"],
    ],
    past: [
      ["DOM", "8", "Tirada larga · Semana 5", "14 km · Planificado 80 min · Realizado 79 min", "Completado"],
      ["VIE", "6", "Tempo · Semana 5", "6 km · Planificado 34 min · Realizado 33 min", "Completado"],
      ["MIÉ", "4", "Rodaje suave · Semana 5", "7 km · Planificado 42 min · Realizado 40 min", "Completado"],
    ],
    future: [
      ["LUN", "16", "Rodaje suave · Semana 7", "6 km · Zona 2 · Noviembre", "Próximo"],
      ["MIÉ", "18", "Intervalos · Semana 7", "5 × 800 m · Noviembre", "Próximo"],
      ["DOM", "22", "Tirada larga · Semana 7", "15 km · Ritmo conversacional · Noviembre", "Próximo"],
    ],
    library: [
      ["12", "SEM", "Tu primera media maratón", "5 oct – 27 dic 2026 · Semana 6 / 12", "Activo"],
      ["8", "SEM", "Base de 10 kilómetros", "10 ago – 4 oct 2026 · 8 semanas", "Completado"],
      ["6", "SEM", "Recuperación y nueva base", "28 dic 2026 – 7 feb 2027 · 6 semanas", "Próximo"],
    ],
  }

  function renderRuns() {
    const list = $("#sessions")
    list.replaceChildren()
    defaults.forEach(run => {
      const row = document.createElement("div")
      row.className = "session"
      const icon = document.createElement("div")
      icon.className = "route"
      icon.textContent = "↗"
      const info = document.createElement("div")
      const heading = document.createElement("h3")
      heading.textContent = run.title
      const date = document.createElement("small")
      date.textContent = run.date
      info.append(heading, date)
      const numbers = document.createElement("div")
      numbers.className = "numbers"
      const distance = document.createElement("b")
      distance.textContent = `${Number(run.distance).toLocaleString("es")} km`
      const duration = document.createElement("small")
      duration.textContent = `${run.minutes} min`
      numbers.append(distance, duration)
      row.append(icon, info, numbers)
      list.append(row)
    })
  }

  function renderChart() {
    const month = $("#period").value === "month"
    const values = month ? [150, 120, 135, 65, 100, 35, 55] : [150, 130, 150, 70, 100, 40, 65]
    const points = values.map((y, index) => [35 + index * 90, y])
    const path = points.map((point, index) => `${index ? "L" : "M"}${point.join(" ")}`).join(" ")
    $("#line").setAttribute("d", path)
    $("#area").setAttribute("d", `${path}L575 185H35Z`)
    $("#points").replaceChildren(...points.map(([x, y]) => {
      const point = document.createElementNS("http://www.w3.org/2000/svg", "circle")
      point.setAttribute("cx", x)
      point.setAttribute("cy", y)
      point.setAttribute("r", "4")
      point.setAttribute("fill", "white")
      point.setAttribute("stroke", "#3849e8")
      point.setAttribute("stroke-width", "2")
      return point
    }))
    const labels = month
      ? ["1 nov", "5 nov", "10 nov", "15 nov", "20 nov", "25 nov", "30 nov"]
      : ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    $("#axis").replaceChildren(...labels.map(label => {
      const axisLabel = document.createElement("span")
      axisLabel.textContent = label
      return axisLabel
    }))
  }

  let previousFocus
  function openChat() {
    previousFocus = root.activeElement
    $("#chatDrawer").hidden = false
    $("main").inert = true
    $("aside").inert = true
    $("#chatInput").focus()
  }

  function closeChat() {
    $("#chatDrawer").hidden = true
    $("main").inert = false
    $("aside").inert = false
    previousFocus?.focus()
  }

  function addMessage(text, isUser = false) {
    const message = document.createElement("div")
    message.className = `bubble${isUser ? " user" : ""}`
    message.textContent = text
    $("#messages").append(message)
    message.scrollIntoView({ block: "nearest" })
  }

  function ask(question) {
    if ($("#chatDrawer").hidden) openChat()
    addMessage(question, true)
    const lower = question.toLowerCase()
    let answer
    if (lower.includes("mañana")) {
      answer = "En este ejemplo, mañana jueves 12 tienes descanso y 15 minutos de movilidad. El viernes llega una sesión de tempo de 7 km. Puedes ver ambas en Mi entrenamiento."
    } else if (lower.includes("semana") || lower.includes("progreso")) {
      answer = "En los datos de ejemplo llevas 37 de los 50 km semanales: un 74% del objetivo. Para valorar tu evolución real necesitaría tus actividades y sensaciones. Podemos revisar la distribución de esfuerzo en tu plan."
    } else if (lower.includes("plan")) {
      answer = "Tu plan de ejemplo prepara una media maratón en 12 semanas. Estás en la semana 6, centrada en construir resistencia con rodajes, tempo y recuperación. En Mi entrenamiento puedes explorar sesiones pasadas y próximas."
    } else {
      answer = "Esta es una respuesta de demostración. En la versión conectada podría contrastar esta pregunta con tus carreras y tu plan. Si propusiera cambios, te mostraría las sesiones afectadas para que las confirmes antes de aplicarlos."
    }
    addMessage(answer)
  }

  function showView(view) {
    $("#overview").hidden = view === "plan"
    $("#training").hidden = view !== "plan"
    $$("[data-view]").forEach(button => button.classList.toggle("active", button.dataset.view === view))
    if (view === "history") $("#history").scrollIntoView({ behavior: "smooth" })
    else window.scrollTo({ top: 0 })
  }

  function selectPlan(key) {
    $$("[data-plan]").forEach(button => button.classList.toggle("active", button.dataset.plan === key))
    const headings = {
      current: "Semana 6 · 9–15 noviembre",
      past: "Sesiones anteriores · Noviembre",
      future: "Lo que viene · Noviembre",
      library: "Tu recorrido, plan a plan",
    }
    $("#planHeading").textContent = headings[key]
    const list = $("#planList")
    list.replaceChildren(...training[key].map(item => {
      const [day, date, title, summary, status] = item
      const row = document.createElement("div")
      row.className = "plan-row"
      const dateBox = document.createElement("div")
      dateBox.className = "date-box"
      dateBox.append(document.createTextNode(day))
      const dateValue = document.createElement("b")
      dateValue.textContent = date
      dateBox.append(dateValue)
      const details = document.createElement("div")
      const name = document.createElement("h3")
      name.textContent = title
      const description = document.createElement("p")
      description.textContent = summary
      const question = document.createElement("button")
      question.className = "ask-session"
      question.type = "button"
      question.textContent = "Preguntar al entrenador ↗"
      question.addEventListener("click", () => {
        $("#chatContext").textContent = `Sobre: ${title} · ${day} ${date}`
        ask(`Explícame ${title} del ${day} ${date}`)
      })
      details.append(name, description, question)
      const badge = document.createElement("span")
      badge.className = `status${status === "Completado" ? " done" : ""}`
      badge.textContent = status
      row.append(dateBox, details, badge)
      return row
    }))
  }

  $("#period").addEventListener("change", renderChart)
  $$("[data-view]").forEach(button => button.addEventListener("click", () => showView(button.dataset.view)))
  $$("[data-plan]").forEach(button => button.addEventListener("click", () => selectPlan(button.dataset.plan)))
  $$("[data-action='show-plan']").forEach(button => button.addEventListener("click", () => showView("plan")))
  $$("[data-action='ask-plan']").forEach(button => button.addEventListener("click", () => ask("Explícame mi plan de entrenamiento")))
  $$("[data-action='open-chat']").forEach(button => button.addEventListener("click", openChat))
  $$("[data-action='close-chat']").forEach(button => button.addEventListener("click", closeChat))
  $$("[data-suggestion]").forEach(button => button.addEventListener("click", () => ask(button.dataset.suggestion)))
  $("#quickChat").addEventListener("submit", event => {
    event.preventDefault()
    ask(event.currentTarget.querySelector("input").value)
    event.currentTarget.reset()
  })
  $("#chatForm").addEventListener("submit", event => {
    event.preventDefault()
    ask($("#chatInput").value)
    $("#chatForm").reset()
    $("#chatInput").focus()
  })

  const weekDays = ["LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM"]
  weekDays.forEach((label, index) => {
    const button = document.createElement("button")
    button.type = "button"
    button.className = "day"
    button.setAttribute("aria-label", `${label} ${9 + index}, ver entrenamiento`)
    const dayLabel = document.createElement("span")
    dayLabel.textContent = label
    const date = document.createElement("b")
    date.textContent = String(9 + index)
    button.append(dayLabel, date, document.createTextNode("·"))
    button.addEventListener("click", () => {
      $$(".day").forEach((day, dayIndex) => day.classList.toggle("chosen", dayIndex === index))
      const [category, title, description] = plans[index]
      const workout = $("#workout")
      workout.replaceChildren()
      const pill = document.createElement("span")
      pill.className = "pill"
      pill.textContent = category
      const heading = document.createElement("h3")
      heading.textContent = title
      const copy = document.createElement("p")
      copy.textContent = description
      workout.append(pill, heading, copy)
    })
    $("#days").append(button)
  })

  const onKeyDown = event => {
    if (event.key === "Escape" && !$("#chatDrawer").hidden) closeChat()
    if (event.key !== "Tab" || $("#chatDrawer").hidden) return
    const focusable = $$("#chatDrawer button, #chatDrawer input")
    if (!focusable.length) return
    const active = root.activeElement
    if (event.shiftKey && active === focusable[0]) {
      event.preventDefault()
      focusable.at(-1).focus()
    } else if (!event.shiftKey && active === focusable.at(-1)) {
      event.preventDefault()
      focusable[0].focus()
    }
  }

  renderRuns()
  renderChart()
  $$(".day")[2].click()
  selectPlan("current")
  root.addEventListener("keydown", onKeyDown)
  return () => root.removeEventListener("keydown", onKeyDown)
}
