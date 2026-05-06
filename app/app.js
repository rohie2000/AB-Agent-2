const form = document.querySelector("#generator-form");
const statusBox = document.querySelector("#status-box");
const outputMeta = document.querySelector("#output-meta");
const previewFrame = document.querySelector("#preview-frame");
const openPreviewLink = document.querySelector("#open-preview");
const openPdfLink = document.querySelector("#open-pdf");
const generateButton = document.querySelector("#generate-button");
const demoButton = document.querySelector("#demo-button");

function setStatus(kind, message) {
  statusBox.dataset.state = kind;
  statusBox.textContent = message;
}

function collectPayload() {
  const formData = new FormData(form);
  return {
    topic: String(formData.get("topic") || "").trim(),
    learning_goal: String(formData.get("learning_goal") || "").trim(),
    target_group: String(formData.get("target_group") || "").trim(),
    focus: String(formData.get("focus") || "").trim(),
    image_preference: String(formData.get("image_preference") || "optional").trim(),
    template_variant: String(formData.get("template_variant") || "instructions").trim(),
    known_vocabulary: String(formData.get("known_vocabulary") || "")
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean),
  };
}

function setBusy(isBusy) {
  generateButton.disabled = isBusy;
  demoButton.disabled = isBusy;
  form.querySelectorAll("input, textarea, select").forEach((field) => {
    field.disabled = isBusy;
  });
}

async function submitRequest(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json();
  if (!response.ok || !data.ok) {
    throw new Error(data.error || "Die Anfrage konnte nicht verarbeitet werden.");
  }
  return data;
}

function applyResult(data) {
  setStatus(
    "success",
    `Arbeitsblaetter erzeugt: ${data.topic} (${data.level_count} Niveaustufen).`
  );
  outputMeta.innerHTML = `
    <strong>Modell:</strong> ${data.meta.model}<br>
    <strong>JSON:</strong> ${data.json_path}<br>
    <strong>HTML:</strong> ${data.html_path}<br>
    <strong>PDF:</strong> ${data.pdf_path}
  `;
  previewFrame.src = data.preview_url;
  openPreviewLink.href = data.preview_url;
  openPreviewLink.hidden = false;
  openPdfLink.href = data.pdf_url;
  openPdfLink.hidden = false;
}

async function handleGeneration(url) {
  try {
    setBusy(true);
    setStatus("loading", "Arbeitsblaetter werden erzeugt. Das kann kurz dauern.");
    outputMeta.textContent = "";
    openPreviewLink.hidden = true;
    openPdfLink.hidden = true;

    const payload = collectPayload();
    const data = await submitRequest(url, payload);
    applyResult(data);
  } catch (error) {
    setStatus("error", error.message);
  } finally {
    setBusy(false);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  await handleGeneration("/api/generate");
});

demoButton.addEventListener("click", async () => {
  await handleGeneration("/api/generate-demo");
});

setStatus("idle", "Bereit. Trage ein Thema ein oder starte zuerst die Demo.");
