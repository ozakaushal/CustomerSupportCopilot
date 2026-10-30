const messages = document.getElementById("messages");
const askForm = document.getElementById("askForm");
const questionBox = document.getElementById("question");
const stepsList = document.getElementById("steps");
const answeredBy = document.getElementById("answeredBy");
const sendBtn = askForm.querySelector("button");

const labels = {
  knowledge_base: "Knowledge base",
  web: "Web search",
  chat: "Direct reply",
  none: "No answer found",
};

// adds one chat bubble on the screen
function addMessage(type, text, source, sources) {
  const div = document.createElement("div");
  div.className = "msg " + type;
  div.textContent = text;

  // small tag showing where the answer came from
  if (source) {
    const tag = document.createElement("span");
    tag.className = "tag " + source;
    tag.textContent = labels[source] || source;
    div.appendChild(document.createElement("br"));
    div.appendChild(tag);
  }

  // list of files or links used for the answer
  if (sources && sources.length > 0) {
    const ul = document.createElement("ul");
    ul.className = "sources";
    sources.forEach((src) => {
      const li = document.createElement("li");
      if (src.url) {
        const a = document.createElement("a");
        a.href = src.url;
        a.target = "_blank";
        a.textContent = src.title;
        li.appendChild(a);
      } else {
        li.textContent = src.title;
      }
      ul.appendChild(li);
    });
    div.appendChild(ul);
  }

  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

// shows the graph steps in the right side panel
function showSteps(steps) {
  stepsList.innerHTML = "";
  steps.forEach((step) => {
    const li = document.createElement("li");
    li.textContent = step;
    stepsList.appendChild(li);
  });
}

// sends the question to the backend and shows the answer
async function askQuestion(question) {
  addMessage("user", question);
  questionBox.value = "";
  sendBtn.disabled = true;
  answeredBy.textContent = "thinking...";
  showSteps(["Working on it..."]);

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: question }),
    });
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || "Something went wrong");
    }

    addMessage("bot", data.answer, data.answered_by, data.sources);
    showSteps(data.steps);
    answeredBy.textContent = labels[data.answered_by] || data.answered_by;
  } catch (err) {
    addMessage("bot error", "Error: " + err.message);
    showSteps([]);
    answeredBy.textContent = "-";
  }

  sendBtn.disabled = false;
  questionBox.focus();
}

askForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const question = questionBox.value.trim();
  if (question) {
    askQuestion(question);
  }
});

// enter = send, shift + enter = new line
questionBox.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    askForm.requestSubmit();
  }
});

// clicking a suggestion asks that question
document.querySelectorAll(".suggestions button").forEach((btn) => {
  btn.addEventListener("click", () => askQuestion(btn.textContent));
});

// ---------- upload popup ----------

const dialog = document.getElementById("uploadDialog");
const uploadMsg = document.getElementById("uploadMsg");

document.getElementById("openUpload").addEventListener("click", () => {
  uploadMsg.textContent = "";
  dialog.showModal();
});

// uploads the selected file to the backend
async function uploadFile() {
  const file = document.getElementById("file").files[0];
  const token = document.getElementById("token").value;

  if (!file) {
    uploadMsg.textContent = "Please select a file first.";
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  uploadMsg.textContent = "Uploading...";

  try {
    const res = await fetch("/api/documents", {
      method: "POST",
      headers: { "X-Ingest-Token": token },
      body: formData,
    });
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || "Upload failed");
    }
    uploadMsg.textContent = data.file + " uploaded (" + data.chunks + " chunks)";
  } catch (err) {
    uploadMsg.textContent = "Error: " + err.message;
  }
}

document.getElementById("uploadBtn").addEventListener("click", uploadFile);
