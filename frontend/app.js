import { api, jsonOptions, elapsed } from "./core.mjs";
const $ = id => document.getElementById(id);
const state = {
  page: "dashboard",
  provider: null,
  candidateId: localStorage.getItem("ais_candidate_id") || null,
  profile: null,
  cv: null,
  interview: { sessionId: localStorage.getItem("ais_session_id") || null, currentQuestion: null, submitting: false },
  questions: [],
  recentSessions: JSON.parse(localStorage.getItem("ais_recent_sessions") || "[]"),
  evaluationsBySession: {},
};
function feedback(id, text, error = false) { const el = $(id); if (!el) return; el.textContent = text; el.classList.toggle("error", error); }
function escapeHtml(value) { return String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[ch])); }
function loading(text = "Cargando…") { return `<div class="empty">${escapeHtml(text)}</div>`; }
function showPage(page) {
  state.page = page;
  document.querySelectorAll(".page").forEach(el => { el.hidden = el.id !== `${page}-page`; });
  document.querySelectorAll("[data-page]").forEach(btn => {
    const active = btn.dataset.page === page;
    btn.classList.toggle("active", active);
    if (active) btn.setAttribute("aria-current", "page"); else btn.removeAttribute("aria-current");
  });
  const titles = { dashboard:"Panel principal", profile:"Perfil del candidato", cv:"Análisis de CV", interview:"Simulador de entrevista", questions:"Banco de preguntas", results:"Resultados e historial", system:"Estado del sistema" };
  $("page-title").textContent = titles[page] || page;
  if (page === "dashboard") refreshDashboard();
  if (page === "profile") loadProfile();
  if (page === "cv") renderCvState();
  if (page === "interview") refreshInterviewView();
  if (page === "questions") loadQuestions();
  if (page === "results") refreshResults();
  if (page === "system") refreshStatus();
}
async function refreshStatus() {
  try {
    const { data } = await api("/api/v1/status");
    state.provider = data;
    const badge = $("connection");
    badge.textContent = data.status === "ready" ? "Conectado" : "No disponible";
    badge.className = `badge ${data.status === "ready" ? "good" : "bad"}`;
    $("backend-status").textContent = "Disponible";
    $("provider-status").textContent = data.status === "ready" ? "Disponible" : "No disponible";
    $("provider-model").textContent = `${data.provider} · ${data.model}`;
    $("provider-summary").textContent = `Proveedor: ${data.provider} · ${data.model} · ${data.status}`;
    $("status-updated").textContent = `Última comprobación: ${new Date().toLocaleString("es-MX")}`;
  } catch (error) {
    $("connection").textContent = "Sin conexión";
    $("connection").className = "badge bad";
    $("backend-status").textContent = "No disponible";
    $("provider-status").textContent = "No disponible";
    feedback("profile-feedback", error.message, true);
  }
}
async function loadProfile() {
  if (!state.candidateId) {
    $("profile-stored").innerHTML = "<div class=\"empty\">No se ha guardado ningún perfil.</div>";
    $("profile-id").textContent = "Sin identificador";
    return;
  }
  try {
    const { data } = await api(`/api/v1/candidates/${state.candidateId}`);
    state.profile = data;
    $("profile-id").textContent = data.id;
    const profile = data.academic_profile || {};
    $("profile-stored").innerHTML = `
      <div class="kv"><strong>Nombre</strong><span>${escapeHtml(data.full_name)}</span></div>
      <div class="kv"><strong>Correo</strong><span>${escapeHtml(data.email || "—")}</span></div>
      <div class="kv"><strong>Formación</strong><span>${escapeHtml(profile.academic_background || "—")}</span></div>
      <div class="kv"><strong>Experiencia</strong><span>${escapeHtml(profile.professional_background || "—")}</span></div>
    `;
    $("profile-name").value = data.full_name || "";
    $("profile-email").value = data.email || "";
    $("profile-academic").value = profile.academic_background || "";
    $("profile-professional").value = profile.professional_background || "";
  } catch (error) {
    feedback("profile-feedback", error.message, true);
  }
}
async function saveProfile(event) {
  event.preventDefault();
  const payload = {
    full_name: $("profile-name").value.trim(),
    email: $("profile-email").value.trim() || null,
    academic_background: $("profile-academic").value.trim() || null,
    professional_background: $("profile-professional").value.trim() || null,
  };
  try {
    let data;
    if (state.candidateId) {
      ({ data } = await api(`/api/v1/candidates/${state.candidateId}`, jsonOptions(payload, "PATCH")));
    } else {
      ({ data } = await api("/api/v1/candidates", jsonOptions(payload)));
      state.candidateId = data.id;
      localStorage.setItem("ais_candidate_id", data.id);
    }
    state.profile = data;
    feedback("profile-feedback", "Perfil guardado correctamente.");
    await loadProfile();
    await refreshDashboard();
  } catch (error) {
    feedback("profile-feedback", error.message, true);
  }
}
function cvId(cv) { return cv?.id || cv?.analysis_id; }
function renderRequirement(req) {
  const status = req.status === "evidence_found" ? "tag" : "tag";
  return `<div class="kv"><strong>${escapeHtml(req.requirement)}</strong><span>${escapeHtml(req.status)} · ${escapeHtml(req.evidence || req.notes || "")}</span></div>`;
}
function renderCv(data) {
  if (!data) { $("cv-analysis").innerHTML = "<div class=\"empty\">No hay CV analizado.</div>"; return; }
  state.cv = data;
  const analysis = data.analysis || data.result || {};
  const summary = data.summary || data.extraction_summary || {};
  const strengths = analysis.strengths || [];
  const missing = analysis.missing_or_unclear_evidence || [];
  const recs = analysis.recommendations || [];
  const reqs = analysis.requirement_classification || [];
  const improvements = analysis.wording_improvements || [];
  $("cv-analysis").innerHTML = `
    <div class="kv"><strong>Archivo</strong><span>${escapeHtml(data.file_name || "—")}</span></div>
    <div class="kv"><strong>Estado</strong><span>${escapeHtml(data.status || "—")}</span></div>
    <div class="kv"><strong>Resumen profesional</strong><span>${escapeHtml(analysis.professional_summary || "—")}</span></div>
    <h3>Fortalezas</h3>
    ${strengths.length ? strengths.map(x => `<p>• ${escapeHtml(x)}</p>`).join("") : "<p>Sin fortalezas identificadas.</p>"}
    <h3>Evidencia faltante o poco clara</h3>
    ${missing.length ? missing.map(x => `<p>• ${escapeHtml(x)}</p>`).join("") : "<p>Sin evidencia faltante identificada.</p>"}
    <h3>Clasificación de requisitos</h3>
    ${reqs.length ? reqs.map(renderRequirement).join("") : "<p>Sin clasificación disponible.</p>"}
    <h3>Recomendaciones</h3>
    ${recs.length ? recs.map(x => `<p>• ${escapeHtml(x)}</p>`).join("") : "<p>Sin recomendaciones.</p>"}
    <h3>Mejoras de redacción</h3>
    ${improvements.length ? improvements.map(x => `<p>• ${escapeHtml(x)}</p>`).join("") : "<p>Sin mejoras sugeridas.</p>"}
    <p class="feedback">${escapeHtml(analysis.feedback || "")}</p>
    <p class="feedback">${escapeHtml(analysis.disclaimer || "Análisis generado por IA para preparación del candidato. No constituye una decisión oficial de admisión.")}</p>
    <div class="form-actions"><button class="danger-button" id="delete-cv" type="button">Eliminar CV y datos asociados</button></div>
  `;
  const del = $("delete-cv");
  if (del) del.addEventListener("click", deleteCv);
  $("cv-status").innerHTML = `<div class="kv"><strong>Estado</strong><span>${escapeHtml(data.status)}</span></div><div class="kv"><strong>Analizado</strong><span>${escapeHtml(data.analyzed_at || data.analysis_date || "—")}</span></div>`;
}
function renderCvState() { if (state.cv) renderCv(state.cv); else $("cv-analysis").innerHTML = "<div class=\"empty\">No hay CV analizado.</div>"; }
async function uploadCv(event) {
  event.preventDefault();
  const file = $("cv-file").files[0];
  if (!file || !/\.pdf$/i.test(file.name)) { feedback("cv-upload-feedback", "Selecciona un archivo PDF válido.", true); return; }
  const form = new FormData();
  form.append("file", file);
  if (state.candidateId) form.append("candidate_id", state.candidateId);
  feedback("cv-upload-feedback", "Subiendo y analizando CV…");
  try {
    const { data } = await api("/api/v1/cv", { method: "POST", body: form }, 300000);
    const id = cvId(data);
    feedback("cv-upload-feedback", "CV subido. Iniciando análisis…");
    const { data: analyzed } = await api(`/api/v1/cv/${id}/analyze`, jsonOptions({}, "POST"), 300000);
    renderCv(analyzed);
    feedback("cv-upload-feedback", "Análisis completado.");
    await refreshDashboard();
  } catch (error) {
    feedback("cv-upload-feedback", error.message, true);
  }
}
async function deleteCv() {
  if (!state.cv) return;
  const id = cvId(state.cv);
  try {
    await api(`/api/v1/cv/${id}`, { method: "DELETE" });
    state.cv = null;
    $("cv-analysis").innerHTML = "<div class=\"empty\">CV eliminado.</div>";
    $("cv-status").innerHTML = "<div class=\"empty\">Sin estado disponible.</div>";
    feedback("cv-upload-feedback", "CV y datos asociados eliminados.");
    await refreshDashboard();
  } catch (error) {
    feedback("cv-upload-feedback", error.message, true);
  }
}
async function startInterview() {
  const mode = $("interview-mode").value;
  const name = $("interview-name").value.trim() || "Candidato de simulación";
  feedback("interview-setup-feedback", "Creando sesión…");
  try {
    const { data: session } = await api("/api/v1/interviews", jsonOptions({ mode, full_name: name }));
    const sessionId = session.session_id || session.id;
    state.interview.sessionId = sessionId;
    localStorage.setItem("ais_session_id", sessionId);
    const recent = [sessionId, ...state.recentSessions.filter(x => x !== sessionId)].slice(0, 10);
    state.recentSessions = recent;
    localStorage.setItem("ais_recent_sessions", JSON.stringify(recent));
    await api(`/api/v1/interviews/${sessionId}/start`, jsonOptions({}, "POST"));
    $("interview-setup").hidden = true;
    $("interview-session").hidden = false;
    await refreshInterview();
    feedback("interview-setup-feedback", "Entrevista iniciada.");
  } catch (error) {
    feedback("interview-setup-feedback", error.message, true);
  }
}
async function refreshInterview() {
  const sid = state.interview.sessionId;
  if (!sid) return;
  try {
    const { data: session } = await api(`/api/v1/interviews/${sid}`);
    const { data: current } = await api(`/api/v1/interviews/${sid}/current-question`);
    const { data: history } = await api(`/api/v1/interviews/${sid}/history`);
    state.interview.currentQuestion = current.current_question;
    const total = current.total_questions || session.question_count || 0;
    const position = current.position || session.current_position || 0;
    $("interview-status").textContent = session.status;
    $("interview-progress-label").textContent = `Pregunta ${position} de ${total}`;
    const pct = total ? Math.min(100, Math.round((position / total) * 100)) : 0;
    $("interview-progress").style.width = `${pct}%`;
    if (current.current_question) {
      $("current-question").textContent = current.current_question.prompt;
      $("question-category").textContent = current.current_question.category.replace(/_/g, " ").toUpperCase();
      $("question-difficulty").textContent = `Dificultad: ${current.current_question.difficulty}`;
    } else {
      $("current-question").textContent = session.status === "completed" ? "Entrevista finalizada." : "No hay pregunta actual.";
      $("question-category").textContent = "FINALIZADA";
      $("question-difficulty").textContent = "";
    }
    $("interview-history").innerHTML = history.items?.length
      ? history.items.map(item => `<div class="panel subtle"><strong>${escapeHtml(item.category)}</strong><p>${escapeHtml(item.prompt)}</p><p>${escapeHtml(item.answer)}</p><small>${escapeHtml(item.created_at)}</small></div>`).join("")
      : "<div class=\"empty\">Sin historial todavía.</div>";
  } catch (error) {
    feedback("answer-feedback", error.message, true);
  }
}
function refreshInterviewView() {
  if (state.interview.sessionId) {
    $("interview-setup").hidden = true;
    $("interview-session").hidden = false;
    refreshInterview();
  } else {
    $("interview-setup").hidden = false;
    $("interview-session").hidden = true;
  }
}
async function submitAnswer(event) {
  event.preventDefault();
  const sid = state.interview.sessionId;
  const question = state.interview.currentQuestion;
  if (!sid || !question) { feedback("answer-feedback", "No hay pregunta activa.", true); return; }
  if (state.interview.submitting) return;
  const answer = $("answer-input").value.trim();
  if (!answer) { feedback("answer-feedback", "Escribe una respuesta.", true); return; }
  state.interview.submitting = true;
  $("submit-answer").disabled = true;
  feedback("answer-feedback", "Enviando respuesta y generando evaluación…");
  try {
    const { data: submitted } = await api(`/api/v1/interviews/${sid}/answers`, jsonOptions({ question_id: question.id, answer }));
    try {
      const { data: evaluation } = await api(`/api/v1/evaluations/answers/${submitted.answer_id}/evaluate`, jsonOptions({}, "POST"), 300000);
      renderEvaluation(evaluation);
    } catch (error) {
      feedback("answer-feedback", `Respuesta guardada, pero no se pudo evaluar: ${error.message}`, true);
    }
    $("answer-input").value = "";
    await refreshInterview();
    feedback("answer-feedback", "Respuesta guardada.");
  } catch (error) {
    feedback("answer-feedback", error.message, true);
  } finally {
    state.interview.submitting = false;
    $("submit-answer").disabled = false;
  }
}
async function generateFollowup() {
  const sid = state.interview.sessionId;
  if (!sid) return;
  feedback("answer-feedback", "Generando pregunta de seguimiento…");
  try {
    const { data } = await api(`/api/v1/interviews/${sid}/follow-up`, jsonOptions({}, "POST"), 300000);
    if (data.should_ask && data.followup_question) {
      state.interview.currentQuestion = data.followup_question;
      feedback("answer-feedback", data.message || "Pregunta de seguimiento generada.");
    } else {
      feedback("answer-feedback", data.message || "No se generó pregunta de seguimiento.");
    }
    await refreshInterview();
  } catch (error) {
    feedback("answer-feedback", error.message, true);
  }
}
async function completeInterview() {
  const sid = state.interview.sessionId;
  if (!sid) return;
  try {
    await api(`/api/v1/interviews/${sid}/complete`, jsonOptions({}, "POST"));
    await refreshInterview();
    feedback("answer-feedback", "Entrevista finalizada.");
    await refreshDashboard();
  } catch (error) {
    feedback("answer-feedback", error.message, true);
  }
}
function renderEvaluation(ev) {
  if (!ev) return;
  const criteria = ev.criteria || [];
  const stress = ev.stress_management;
  const tech = ev.technical_accuracy;
  const el = $("evaluation-panel");
  el.innerHTML = `
    <div class="panel subtle">
      <div class="score">${escapeHtml(ev.overall_score ?? ev.score ?? "—")}</div>
      <p>Puntaje de preparación (no oficial).</p>
      <h3>Criterios</h3>
      ${criteria.length ? criteria.map(c => `<div class="kv"><strong>${escapeHtml(c.name || c.criterion || "Criterio")}</strong><span>${escapeHtml(c.score ?? "—")} · ${escapeHtml(c.explanation || c.status || "")}</span></div>`).join("") : "<p>Sin criterios.</p>"}
      <h3>Fortalezas</h3>
      ${(ev.strengths || []).map(x => `<p>• ${escapeHtml(x)}</p>`).join("") || "<p>Sin fortalezas.</p>"}
      <h3>Áreas de mejora</h3>
      ${(ev.weaknesses || ev.areas_for_improvement || []).map(x => `<p>• ${escapeHtml(x)}</p>`).join("") || "<p>Sin áreas registradas.</p>"}
      <h3>Recomendaciones</h3>
      ${(ev.recommendations || []).map(x => `<p>• ${escapeHtml(x)}</p>`).join("") || "<p>Sin recomendaciones.</p>"}
      <h3>Respuesta mejorada</h3>
      <p>${escapeHtml(ev.revised_answer || ev.improved_answer || "—")}</p>
      <p>${escapeHtml(ev.practice_tip || "")}</p>
      ${tech ? `<h3>Precisión técnica</h3><p>${escapeHtml(tech.classification || "")}</p>` : ""}
      ${stress ? `<div class="stress-box"><h3>Manejo del estrés</h3>
        <p><strong>Aborda:</strong> ${(stress.addresses || []).map(escapeHtml).join(", ") || "—"}</p>
        <p><strong>Falta:</strong> ${(stress.missing || []).map(escapeHtml).join(", ") || "—"}</p>
        <p><strong>Sugerencias:</strong> ${(stress.suggestions || []).map(escapeHtml).join(", ") || "—"}</p>
      </div>` : ""}
      <p class="feedback">${escapeHtml(ev.disclaimer || "")}</p>
    </div>
  `;
}
const categoryLabels = {
  academic_background: "Formación académica",
  motivation: "Motivación",
  programming: "Programación",
  algorithms: "Algoritmos",
  databases: "Bases de datos",
  ai_fundamentals: "Fundamentos de IA",
  research_interests: "Intereses de investigación",
  professional_experience: "Experiencia profesional",
  time_management_stress: "Manejo del estrés",
  ethics_professional_goals: "Ética y metas profesionales",
  follow_up: "Seguimiento",
};
async function loadQuestions() {
  try {
    const { data } = await api("/api/v1/questions");
    state.questions = data || [];
    const categories = [...new Set(state.questions.map(q => q.category))];
    const select = $("question-category-filter");
    select.innerHTML = `<option value="">Todas las categorías</option>` + categories.map(c => `<option value="${escapeHtml(c)}">${escapeHtml(categoryLabels[c] || c)}</option>`).join("");
    renderQuestions();
  } catch (error) {
    $("question-list").innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`;
  }
}
function renderQuestions() {
  const selected = $("question-category-filter")?.value || "";
  const list = selected ? state.questions.filter(q => q.category === selected) : state.questions;
  $("question-list").innerHTML = list.length
    ? list.map(q => `<article class="question-card-item"><div class="category">${escapeHtml(categoryLabels[q.category] || q.category)}</div><p>${escapeHtml(q.prompt)}</p><small>Dificultad: ${escapeHtml(q.difficulty)}</small><div class="form-actions"><button class="text-button" data-goto="interview" type="button">Practicar en entrevista</button></div></article>`).join("")
    : "<div class=\"empty\">No hay preguntas para esta categoría.</div>";
  document.querySelectorAll("[data-goto]").forEach(btn => btn.addEventListener("click", () => showPage(btn.dataset.goto)));
}
async function refreshResults() {
  try {
    const { data: sessions } = await api("/api/v1/sessions");
    const list = sessions || [];
    $("results-sessions").innerHTML = list.length
      ? list.map(s => {
          const sid = escapeHtml(s.id || s.session_id);
          const completed = s.status === "completed";
          return `<div class="panel subtle"><strong>${escapeHtml(s.mode)} · ${escapeHtml(s.status)}</strong><p>Sesion ${sid}</p><small>Preguntas: ${escapeHtml(s.question_count)} · ${escapeHtml(s.created_at)}</small><div class="form-actions"><button class="text-button" data-load-evaluations="${sid}" type="button">Ver evaluaciones</button><button class="primary-button" data-download-report="${sid}" type="button" ${completed ? "" : "disabled"} title="${completed ? "Descargar reporte PDF" : "Disponible cuando la entrevista este finalizada"}">Descargar reporte PDF</button></div><p class="feedback" data-report-status="${sid}" role="status"></p></div>`;
        }).join("")
      : "<div class=\"empty\">No hay sesiones.</div>";
    document.querySelectorAll("[data-load-evaluations]").forEach(btn => btn.addEventListener("click", () => loadEvaluations(btn.dataset.loadEvaluations)));
    document.querySelectorAll("[data-download-report]").forEach(btn => btn.addEventListener("click", () => downloadReport(btn.dataset.downloadReport, btn)));
  } catch (error) {
    $("results-sessions").innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`;
  }
}

async function downloadReport(sessionId, button) {
  if (!sessionId || button?.dataset.downloading === "true") return;
  const status = document.querySelector(`[data-report-status="${CSS.escape(sessionId)}"]`);
  if (button) { button.dataset.downloading = "true"; button.disabled = true; button.textContent = "Generando reporte..."; }
  if (status) status.textContent = "Generando reporte PDF...";
  try {
    const response = await fetch(`/api/v1/reports/${encodeURIComponent(sessionId)}`, { cache: "no-store" });
    if (!response.ok) {
      let message = `La peticion fallo (HTTP ${response.status}).`;
      try { const data = await response.json(); message = data?.error?.message || message; } catch {}
      throw new Error(message);
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const disposition = response.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename="?([^"]+)"?/);
    link.download = match ? match[1] : `reporte_entrevista_${sessionId.slice(0, 8)}.pdf`;
    link.href = url;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    if (status) status.textContent = "Reporte descargado.";
  } catch (error) {
    if (status) status.textContent = error.message;
  } finally {
    if (button) { button.dataset.downloading = "false"; button.disabled = false; button.textContent = "Descargar reporte PDF"; }
  }
}

async function loadEvaluations(sessionId) {
  try {
    const { data } = await api(`/api/v1/evaluations/${sessionId}/evaluations`);
    const items = data.items || data.evaluations || [];
    $("results-evaluations").innerHTML = items.length
      ? items.map(ev => `<div class="panel subtle"><strong>Puntaje ${escapeHtml(ev.overall_score ?? ev.score ?? "—")}</strong><p>${escapeHtml(ev.question_prompt || "")}</p><p>${escapeHtml((ev.strengths || []).join("; "))}</p><small>${escapeHtml(ev.created_at || "")}</small></div>`).join("")
      : "<div class=\"empty\">No hay evaluaciones para esta sesión.</div>";
  } catch (error) {
    $("results-evaluations").innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`;
  }
}
async function refreshDashboard() {
  const profileText = state.profile ? state.profile.full_name : (state.candidateId ? "Perfil guardado" : "Sin perfil guardado");
  $("dashboard-profile").textContent = profileText;
  $("dashboard-profile-detail").textContent = state.profile ? (state.profile.academic_profile?.academic_background || "Perfil académico disponible.") : "Crea o edita tu perfil del candidato.";
  $("dashboard-cv").textContent = state.cv ? (state.cv.status || "CV analizado") : "Sin análisis de CV";
  $("dashboard-cv-detail").textContent = state.cv ? (state.cv.analysis?.professional_summary || "Análisis disponible.") : "Sube un CV en PDF para identificar fortalezas y evidencia faltante.";
  $("dashboard-interview").textContent = state.interview.sessionId ? "Sesión disponible" : "Sin sesión reciente";
  $("dashboard-interview-detail").textContent = state.interview.sessionId ? `Sesión ${state.interview.sessionId}` : "Inicia una entrevista rápida, estándar o completa.";
  try {
    const sessions = await Promise.all(state.recentSessions.slice(0, 5).map(async id => {
      try { const { data } = await api(`/api/v1/interviews/${id}`); return data; } catch { return null; }
    }));
    const valid = sessions.filter(Boolean);
    $("recent-count").textContent = `${valid.length} sesiones`;
    $("recent-sessions").innerHTML = valid.length
      ? valid.map(s => `<div class="panel subtle"><strong>${escapeHtml(s.mode)} · ${escapeHtml(s.status)}</strong><p>Sesión ${escapeHtml(s.id || s.session_id)}</p><small>${escapeHtml(s.created_at)}</small></div>`).join("")
      : "<div class=\"empty\">No hay sesiones restauradas todavía.</div>";
  } catch {
    $("recent-sessions").innerHTML = "<div class=\"empty\">No se pudieron cargar las sesiones.</div>";
  }
}
async function restoreInterview() {
  if (!state.interview.sessionId) { feedback("interview-setup-feedback", "No hay sesión guardada.", true); return; }
  try {
    $("interview-setup").hidden = true;
    $("interview-session").hidden = false;
    await refreshInterview();
    feedback("interview-setup-feedback", "Sesión restaurada.");
  } catch (error) {
    feedback("interview-setup-feedback", error.message, true);
  }
}
// Event wiring
function wireEvents() {
  document.querySelectorAll("[data-page]").forEach(btn => btn.addEventListener("click", () => showPage(btn.dataset.page)));
  document.querySelectorAll("[data-goto]").forEach(btn => btn.addEventListener("click", () => showPage(btn.dataset.goto)));
  $("refresh-status")?.addEventListener("click", refreshStatus);
  $("profile-form")?.addEventListener("submit", saveProfile);
  $("profile-reset")?.addEventListener("click", () => {
    $("profile-name").value = ""; $("profile-email").value = ""; $("profile-academic").value = ""; $("profile-professional").value = "";
  });
  $("cv-form")?.addEventListener("submit", uploadCv);
  $("question-category-filter")?.addEventListener("change", renderQuestions);
  $("start-interview")?.addEventListener("click", startInterview);
  $("restore-interview")?.addEventListener("click", restoreInterview);
  $("answer-form")?.addEventListener("submit", submitAnswer);
  $("request-followup")?.addEventListener("click", generateFollowup);
  $("complete-interview")?.addEventListener("click", completeInterview);
}
async function init() {
  wireEvents();
  await refreshStatus();
  if (state.candidateId) await loadProfile();
  if (state.interview.sessionId) { /* restore lazily */ }
  showPage("dashboard");
  await refreshDashboard();
  if (state.interview.sessionId) {
    try { await refreshInterview(); } catch { state.interview.sessionId = null; localStorage.removeItem("ais_session_id"); }
  }
}
init();
