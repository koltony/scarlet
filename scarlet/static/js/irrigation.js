document.addEventListener("DOMContentLoaded", () => {
  const programsBody = document.getElementById("programs-body");

  const formatToHourMinute = time =>
    time ? time.split(":").slice(0, 2).join(":") : "";

  const collectFormData = (row, parseNumbers = true) => {
    const data = new FormData();
    row.querySelectorAll("input, select").forEach(input => {
      if (input.name) data.append(input.name, input.value);
    });
    const payload = {};
    for (const [key, value] of data.entries()) {
      if (key === "start_time") payload[key] = value;
      else if (parseNumbers) payload[key] = parseFloat(value);
      else payload[key] = value;
    }
    return payload;
  };

  const fetchJSON = async (url, options = {}) => {
    const res = await fetch(url, options);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  };

  const loadPrograms = async (expandedId = null) => {
    try {
      const programs = await fetchJSON("/irrigation/program/all");
      programsBody.innerHTML = "";

      programs.forEach(program => {
        const row = document.createElement("tr");
        row.innerHTML = `
          <td>${program.name || ""}</td>
          <td>${program.is_active ? "✅" : "❌"}</td>
          <td>${program.frequency}</td>
          <td>${program.lower_score || ""}</td>
          <td>${program.upper_score || ""}</td>
          <td>${program.sessions?.length || 0} napi futás</td>
          <td>
          <button class="edit-row" data-id="${program.id}"><i class="bi bi-pencil-fill"></i></button>
          <button class="remove-row" data-id="${program.id}"><i class="bi bi-x"></i></button>
          <button class="toggle-sessions" data-id="${program.id}"><i class="bi bi-chevron-down"></i></button>
          </td>
        `;
        programsBody.appendChild(row);

        if (expandedId && program.id == expandedId) {
          setTimeout(() => row.querySelector(".toggle-sessions").click(), 0);
        }
      });
    } catch (err) {
      console.error("Failed to load programs:", err);
    }
  };

  document.getElementById("add-program").addEventListener("click", () => {
    const row = document.getElementById("add-form-row");
    row.style.display = row.style.display === "none" ? "table-row" : "none";
  });

  programsBody.addEventListener("click", async e => {
    const btn = e.target.closest("button");
    const row = btn.closest("tr");

    try {
      if (btn.classList.contains("create-session")) {
        const payload = collectFormData(row);
        await fetchJSON(`/irrigation/program/${btn.dataset.programId}/session/create`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        loadPrograms(btn.dataset.programId);
      }

      if (btn.classList.contains("remove-row")) {
        if (!confirm("Delete this program and all its sessions?")) return;
        await fetch(`/irrigation/program/${btn.dataset.id}/delete`, { method: "POST" });
        loadPrograms();
      }

      if (btn.classList.contains("cancel-new-session")) {
        row.remove();
      }

      if (btn.classList.contains("save-session")) {
        const payload = collectFormData(row);
        await fetchJSON(`/irrigation/program/session/${btn.dataset.id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        loadPrograms(btn.dataset.programId);
      }

      if (btn.classList.contains("edit-session")) {
        const cells = row.querySelectorAll("td");
        const [startTime, zone1, zone2, zone3, zoneConnected] =
          Array.from(cells).map(td => td.textContent.trim());

        row.innerHTML = `
          <td><input type="time" name="start_time" value="${formatToHourMinute(startTime)}"></td>
          <td><input type="number" name="zone1" value="${zone1 === "-" ? "" : zone1}"></td>
          <td><input type="number" name="zone2" value="${zone2 === "-" ? "" : zone2}"></td>
          <td><input type="number" name="zone3" value="${zone3 === "-" ? "" : zone3}"></td>
          <td><input type="number" name="zone_connected" value="${zoneConnected === "-" ? "" : zoneConnected}"></td>
          <td>
            <button class="save-session" data-id="${btn.dataset.id}" data-program-id="${btn.dataset.programId}"><i class="bi bi-floppy2-fill"></i></button>
            <button class="cancel-session" data-program-id="${btn.dataset.programId}"><i class="bi bi-x-lg"></i></button>
          </td>
        `;
      }

      if (btn.classList.contains("cancel-session")) {
        loadPrograms(btn.dataset.programId);
      }

      if (btn.classList.contains("delete-session")) {
        if (!confirm("Are you sure you want to delete this session?")) return;
        await fetch(`/irrigation/program/${btn.dataset.programId}/session/${btn.dataset.id}/delete`, { method: "POST" });
        loadPrograms(btn.dataset.programId);
      }

    if (btn.classList.contains("toggle-sessions")) {
      const programId = btn.dataset.id;
      const hostRow = row;

      const nextRow = hostRow.nextElementSibling;
      if (nextRow && nextRow.classList.contains("session-row")) {
        nextRow.remove();
        return;
      }

      const program = await fetchJSON(`/irrigation/program/${programId}`);

      const sessionRow = document.createElement("tr");
      sessionRow.className = "session-row";
      sessionRow.innerHTML = `
        <td colspan="7" style="background-color:#eef; padding:10px;">
          <strong>Sessions</strong>
          <div style="margin-top:10px;">
            <table style="width:100%; border-collapse:collapse;">
              <thead>
                <tr>
                  <th>Start Time</th>
                  <th>Zone 1</th>
                  <th>Zone 2</th>
                  <th>Zone 3</th>
                  <th>Connected Zone</th>
                  <th style="text-align:right;">
                    <button class="add-session" data-program-id="${program.id}">✚</button>
                  </th>
                </tr>
              </thead>
              <tbody>
                ${program.sessions.map(s => `
                  <tr data-session-id="${s.id}">
                    <td>${formatToHourMinute(s.start_time)}</td>
                    <td>${s.zone1 ?? "-"}</td>
                    <td>${s.zone2 ?? "-"}</td>
                    <td>${s.zone3 ?? "-"}</td>
                    <td>${s.zone_connected ?? "-"}</td>
                    <td>
                      <button class="edit-session" data-id="${s.id}" data-program-id="${program.id}"><i class="bi bi-pencil-fill"></i></button>
                      <button class="delete-session" data-id="${s.id}" data-program-id="${program.id}"><i class="bi bi-trash3-fill"></i></button>
                    </td>
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </div>
        </td>
      `;

      // Inline add-session row builder
      sessionRow.querySelector(".add-session").addEventListener("click", () => {
        const tbody = sessionRow.querySelector("tbody");
        const newRow = document.createElement("tr");
        newRow.innerHTML = `
          <td><input type="time" name="start_time" required></td>
          <td><input type="number" name="zone1" value="0"></td>
          <td><input type="number" name="zone2" value="0"></td>
          <td><input type="number" name="zone3" value="0"></td>
          <td><input type="number" name="zone_connected" value="0"></td>
          <td>
            <button class="create-session" data-program-id="${program.id}"><i class="bi bi-floppy2-fill"></i></button>
            <button class="cancel-new-session"><i class="bi bi-x-lg"></i></button>
          </td>
        `;
        tbody.appendChild(newRow);
      });

      hostRow.parentNode.insertBefore(sessionRow, hostRow.nextSibling);
    }


      if (btn.classList.contains("edit-row")) {
        const cells = row.querySelectorAll("td");
        const [name, activeCell, frequency, lower, upper] =
          Array.from(cells).map(td => td.textContent.trim());
        const isActive = activeCell.includes("✅");

        row.innerHTML = `
          <td><input type="text" name="name" value="${name}"></td>
          <td>
            <select name="is_active">
              <option value="true" ${isActive ? "selected" : ""}>✅</option>
              <option value="false" ${!isActive ? "selected" : ""}>❌</option>
            </select>
          </td>
          <td><input type="number" name="frequency" value="${frequency}"></td>
          <td><input type="number" step="0.01" name="lower_score" value="${lower}"></td>
          <td><input type="number" step="0.01" name="upper_score" value="${upper}"></td>
          <td>${cells[5].textContent}</td>
          <td>
            <button class="save-edit" data-id="${btn.dataset.id}"><i class="bi bi-floppy2-fill"></i></button>
            <button class="cancel-edit"><i class="bi bi-x-lg"></i></button>
          </td>
        `;
      }

      if (btn.classList.contains("cancel-edit")) {
        loadPrograms();
      }

      if (btn.classList.contains("save-edit")) {
        const payload = collectFormData(row, false);
        payload.is_active = payload.is_active === "true";
        ["frequency", "lower_score", "upper_score"].forEach(k => {
          if (payload[k] !== undefined) payload[k] = parseFloat(payload[k]);
        });
        await fetchJSON(`/irrigation/program/${btn.dataset.id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        loadPrograms();
      }
    } catch (err) {
      console.error("Action failed:", err);
    }
  });

  document.getElementById("refresh-programs").addEventListener("click", loadPrograms);

  document.getElementById("add-program-form").addEventListener("submit", async function (e) {
    e.preventDefault();
    if (this.dataset.submitting === "true") return;
    this.dataset.submitting = "true";

    const form = e.target;
    const data = new FormData(form);

    const sessions = Array.from(document.getElementById("add-sessions-container").children)
      .map((_, i) => ({
        start_time: data.get(`session-${i}-start_time`),
        duration_minutes: parseInt(data.get(`session-${i}-duration_minutes`), 10)
      }));

    const payload = {
      name: data.get("name"),
      is_active: data.get("is_active") === "true",
      frequency: parseInt(data.get("frequency"), 10),
      lower_score: parseFloat(data.get("lower_score")),
      upper_score: parseFloat(data.get("upper_score")),
      sessions
    };

    try {
      const res = await fetch("/irrigation/program", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        form.reset();
        document.getElementById("add-sessions-container").innerHTML = "";
        loadPrograms();
      } else {
        document.getElementById("add-response-message").textContent = "❌ Failed to add program.";
      }
    } catch (err) {
      console.error(err);
      document.getElementById("add-response-message").textContent = "❌ Failed to add program.";
    }
    this.dataset.submitting = "false";
  });

  const sendBtn = document.getElementById("send-irrigation");
  sendBtn.addEventListener("click", async () => {
    const payload = {
      zone1: parseInt(document.getElementById("zone1").value) || 0,
      zone2: parseInt(document.getElementById("zone2").value) || 0,
      zone3: parseInt(document.getElementById("zone3").value) || 0,
      zone_connected: parseInt(document.getElementById("zone_connected").value) || 0,
      is_active: document.getElementById("is_active").checked ? "on" : "off"
    };

    try {
      const res = await fetch("/irrigation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      const data = await res.json();
      console.log("Irrigation updated:", data);
      // Optional: show a success message in the UI
    } catch (err) {
      console.error("Failed to update irrigation:", err);
      // Optional: show an error message in the UI
    }
  });

  const toggle = document.getElementById('automationToggle');
  const statusText = document.getElementById('automationStatus');

  // Fetch current state on load
  async function loadAutomationState() {
    const res = await fetch('/irrigation/automation');
    const state = await res.json();
    toggle.checked = state.automation;
    statusText.textContent = state ? 'Öntözőrendszer: Be' : 'Öntözőrendszer: Ki';
  }

  // Update state when toggled
  toggle.addEventListener('change', async () => {
    const newState = toggle.checked; // true or false
    statusText.textContent = newState ? 'Öntözőrendszer: Be' : 'Öntözőrendszer: Ki';

    await fetch('/irrigation/automation', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({automation: newState}) // or false
    });

  });

document.getElementById("add-program-form").addEventListener("submit", async function (e) {
  e.preventDefault();
  if (this.dataset.submitting === "true") return;
  this.dataset.submitting = "true";
    const form = e.target;
    const data = new FormData(form);

    const sessions = Array.from(document.getElementById("add-sessions-container").children)
      .map((_, i) => ({
        start_time: data.get(`session-${i}-start_time`),
        duration_minutes: parseInt(data.get(`session-${i}-duration_minutes`), 10)
      }));

    const payload = {
      name: data.get("name"),
      is_active: data.get("is_active") === "true",
      frequency: parseInt(data.get("frequency"), 10),
      lower_score: parseFloat(data.get("lower_score")),
      upper_score: parseFloat(data.get("upper_score")),
      sessions
    };

    try {
      const res = await fetch("/irrigation/program", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        form.reset();
        document.getElementById("add-sessions-container").innerHTML = "";
        loadPrograms();
      } else {
        document.getElementById("add-response-message").textContent = "❌ Failed to add program.";
      }
    } catch (err) {
      console.error(err);
      document.getElementById("add-response-message").textContent = "❌ Failed to add program.";
    }
    this.dataset.submitting = "false";
  });

    const svg = document.getElementById('score-svg');
  const marker = document.getElementById('score-marker');
  const valueEl = document.getElementById('score-value');
  const updatedEl = document.getElementById('score-updated');

  // Bar geometry (matches the SVG rect)
  const BAR_X = 40;    // left x
  const BAR_W = 560;   // width
  const MIN = 0;
  const MAX = 5;

  function clamp(n, min, max) { return Math.max(min, Math.min(max, n)); }

  function setScore(score) {
    const s = clamp(Number(score), MIN, MAX);
    const ratio = (s - MIN) / (MAX - MIN);
    const cx = BAR_X + ratio * BAR_W;

    marker.setAttribute('cx', cx.toString());
    valueEl.textContent = s.toFixed(2);
    const ts = new Date().toLocaleTimeString();
    updatedEl.textContent = `Frissítve: ${ts}`;

    // Optional pulse feedback
    svg.classList.add('updated');
    setTimeout(() => svg.classList.remove('updated'), 500);
  }

  async function fetchScore() {
    try {
      const res = await fetch('/open_weather/score', { headers: { 'Accept': 'application/json, text/plain, */*' }});
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      // Support both raw float and JSON object responses
      const text = await res.text();
      let score;
      try {
        const maybeJson = JSON.parse(text);
        score = typeof maybeJson === 'number' ? maybeJson : maybeJson.score ?? maybeJson.value ?? maybeJson;
      } catch {
        score = parseFloat(text);
      }
      if (Number.isNaN(score)) throw new Error('Invalid score payload');
      setScore(score);
    } catch (err) {
      console.error('Failed to load score:', err);
      updatedEl.textContent = 'Nem sikerült betölteni';
    }
  }

  loadAutomationState();
  loadPrograms();
  fetchScore();
});



