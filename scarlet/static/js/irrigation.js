document.addEventListener("DOMContentLoaded", function () {
  // Load and display all irrigation programs
  document.getElementById("add-program").addEventListener("click", function () {
    const row = document.getElementById("add-form-row");
    row.style.display = row.style.display === "none" ? "table-row" : "none";
  });

  document.getElementById("programs-body").addEventListener("click", async function (e) {
// CREATE new session
    if (e.target.classList.contains("create-session")) {
      const programId = e.target.dataset.programId;
      const row = e.target.closest("tr");
      const data = new FormData();

      row.querySelectorAll("input").forEach(input => {
        if (input.name) data.append(input.name, input.value);
      });

      const payload = {};
      for (const [key, value] of data.entries()) {
        payload[key] = key === "start_time" ? value : parseFloat(value);
      }

      fetch(`/irrigation/program/${programId}/session/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      })
      .then(res => res.json())
      .then(result => {
        loadPrograms(programId); // reload to show new session
      })
      .catch(err => {
        console.error("Failed to create session:", err);
      });
    }

    if (e.target.classList.contains("remove-row")) {
      const programId = e.target.dataset.id;

      if (!confirm("Delete this program and all its sessions?")) return;

      fetch(`/irrigation/program/${programId}/delete`, {
        method: "POST"
      })
      .then(res => {
        if (!res.ok) throw new Error(`Failed with status ${res.status}`);
        loadPrograms(); // refresh the list
      })
      .catch(err => {
        console.error("Failed to delete program:", err);
      });
    }


    // CANCEL new session row
    if (e.target.classList.contains("cancel-new-session")) {
      e.target.closest("tr").remove();
    }
    if (e.target.classList.contains("save-session")) {
        const sessionId = e.target.dataset.id;
        const row = e.target.closest("tr");
        const data = new FormData();

        row.querySelectorAll("input").forEach(input => {
            if (input.name) data.append(input.name, input.value);
        });

        const payload = {};
        for (const [key, value] of data.entries()) {
            payload[key] = key === "start_time" ? value : parseFloat(value);
        }

        fetch(`/irrigation/program/session/${sessionId}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        })
        .then(res => res.json())
        .then(result => {
            const expandedProgramId = e.target.dataset.programId;
            loadPrograms(expandedProgramId);
    
        })
        .catch(err => {
            console.error("Failed to update session:", err);
        });
        }
    
    if (e.target.classList.contains("edit-session")) {
        const sessionId = e.target.dataset.id;
        const row = e.target.closest("tr");

        const cells = row.querySelectorAll("td");
        const startTime = cells[0].textContent.trim();
        const zone1 = cells[1].textContent.trim();
        const zone2 = cells[2].textContent.trim();
        const zone3 = cells[3].textContent.trim();
        const zoneConnected = cells[4].textContent.trim();

        row.innerHTML = `
            <td><input type="time" name="start_time" value="${formatToHourMinute(startTime)}"></td>
            <td><input type="number" name="zone1" value="${zone1 === "-" ? "" : zone1}"></td>
            <td><input type="number" name="zone2" value="${zone2 === "-" ? "" : zone2}"></td>
            <td><input type="number" name="zone3" value="${zone3 === "-" ? "" : zone3}"></td>
            <td><input type="number" name="zone_connected" value="${zoneConnected === "-" ? "" : zoneConnected}"></td>
            <td>
            <button class="save-session" data-id="${sessionId}">💾</button>
            <button class="cancel-session">❌</button>
            </td>
        `;
        }


    if (e.target.classList.contains("cancel-session")) {
        const expandedProgramId = e.target.dataset.programId;
        loadPrograms(expandedProgramId); // Reload everything to restore original session view
    }

    if (e.target.classList.contains("delete-session")) {
      const programId = e.target.dataset.programId;
      const sessionId = e.target.dataset.id;

      if (!confirm("Are you sure you want to delete this session?")) return;

      fetch(`/irrigation/program/${programId}/session/${sessionId}/delete`, {
        method: "POST"
      })
      .then(res => {
        if (!res.ok) throw new Error(`Failed with status ${res.status}`);
        // Reload the program with sessions expanded
        loadPrograms(programId);
      })
      .catch(err => {
        console.error("Failed to delete session:", err);
      });
    }


    if (e.target.classList.contains("toggle-sessions")) {
        const programId = e.target.dataset.id;
        const row = e.target.closest("tr");

        // Check if sessions are already shown
        const nextRow = row.nextElementSibling;
        if (nextRow && nextRow.classList.contains("session-row")) {
        nextRow.remove();
        return;
        }

        // Fetch program data (if not already available)
        const res = await fetch(`/irrigation/program/${programId}`);
        const program = await res.json();

        const sessionTable = document.createElement("table");
        sessionTable.className = "session-table";
        sessionTable.style.width = "100%";
        sessionTable.innerHTML = `
            <thead>
                <tr>
                    <th>Start Time</th>
                    <th>Zone 1</th>
                    <th>Zone 2</th>
                    <th>Zone 3</th>
                    <th>Connected Zone</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
            ${program.sessions.map(session => `
                <tr data-session-id="${session.id}">
                    <td>${formatToHourMinute(session.start_time)}</td>
                    <td>${session.zone1 ?? "-"}</td>
                    <td>${session.zone2 ?? "-"}</td>
                    <td>${session.zone3 ?? "-"}</td>
                    <td>${session.zone_connected ?? "-"}</td>
                    <td>
                        <button class="edit-session" data-id="${session.id}" data-program-id="${program.id}">✏️</button>
                    </td>
                </tr>
            `).join("")}
            <tr>
                <td><input type="time" name="start_time" required></td>
                <td><input type="number" name="zone1" value="0"></td>
                <td><input type="number" name="zone2" value="0"></td>
                <td><input type="number" name="zone3" value="0"></td>
                <td><input type="number" name="zone_connected" value="0"></td>
                <td>
                    <button class="create-session" data-program-id="${program.id}">➕</button>
                </td>
            </tr>
            </tbody>
        `;


        const sessionRow = document.createElement("tr");
        sessionRow.className = "session-row";
        sessionRow.innerHTML = `
          <td colspan="7" style="background-color: #eef; padding: 10px;">
            <strong>Sessions for "${program.name}"</strong>
            <div style="margin-top: 10px;">
              <table style="width: 100%; border-collapse: collapse;">
                <thead>
                  <tr>
                    <th>Start Time</th>
                    <th>Zone 1</th>
                    <th>Zone 2</th>
                    <th>Zone 3</th>
                    <th>Connected Zone</th>
                    <th style="text-align: right;">
                      <button class="add-session" data-program-id="${program.id}" style="font-size: 0.9em;">➕ Add Session</button>
                    </th>
                  </tr>
                </thead>
                <tbody>
            ${program.sessions.map(session => `
                <tr data-session-id="${session.id}">
                    <td>${formatToHourMinute(session.start_time)}</td>
                    <td>${session.zone1 ?? "-"}</td>
                    <td>${session.zone2 ?? "-"}</td>
                    <td>${session.zone3 ?? "-"}</td>
                    <td>${session.zone_connected ?? "-"}</td>
                    <td>
                      <button class="edit-session" data-id="${session.id}" data-program-id="${program.id}">✏️</button>
                      <button class="delete-session" data-id="${session.id}" data-program-id="${program.id}">🗑️</button>
                    </td>


                </tr>
            `).join("")}
                </tbody>
              </table>
            </div>
          </td>
        `;

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
          <button class="create-session" data-program-id="${program.id}">💾</button>
          <button class="cancel-new-session">❌</button>
        </td>
      `;
      tbody.appendChild(newRow);
    });
   

        row.parentNode.insertBefore(sessionRow, row.nextSibling);
    }
    });
  function formatToHourMinute(rawTime) {
      return rawTime ? rawTime.split(":").slice(0, 2).join(":") : "";
  }

  document.getElementById("programs-body").addEventListener("click", function (e) {
    if (e.target.classList.contains("edit-row")) {
        const programId = e.target.dataset.id;
        const row = e.target.closest("tr");
        const cells = row.querySelectorAll("td");

        const name = cells[0].textContent.trim();
        const isActive = cells[1].textContent.includes("✔️");
        const frequency = cells[2].textContent.trim();
        const upperScore = cells[3].textContent.trim();
        const lowerScore = cells[4].textContent.trim();

        row.innerHTML = `
        <td><input type="text" name="name" value="${name}"></td>
        <td>
            <select name="is_active">
            <option value="true" ${isActive ? "selected" : ""}>✔️</option>
            <option value="false" ${!isActive ? "selected" : ""}>❌</option>
            </select>
        </td>
        <td><input type="number" name="frequency" value="${frequency}"></td>
        <td><input type="number" step="0.01" name="upper_score" value="${upperScore}"></td>
        <td><input type="number" step="0.01" name="lower_score" value="${lowerScore}"></td>
        <td>${cells[5].textContent}</td>
        <td>
            <button class="save-edit" data-id="${programId}">💾</button>
            <button class="cancel-edit">❌</button>
        </td>
        `;
    }

    if (e.target.classList.contains("cancel-edit")) {
        loadPrograms(); // Restore original row
    }

    if (e.target.classList.contains("save-edit")) {
        const programId = e.target.dataset.id;
        const row = e.target.closest("tr");
        const data = new FormData();

        row.querySelectorAll("input, select").forEach(input => {
        if (input.name) data.append(input.name, input.value);
        });

        const payload = {};
        for (const [key, value] of data.entries()) {
        if (key === "is_active") {
            payload[key] = value === "true";
        } else if (["frequency", "upper_score", "lower_score"].includes(key)) {
            payload[key] = parseFloat(value);
        } else {
            payload[key] = value;
        }
        }

        fetch(`/irrigation/program/${programId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
        })
        .then(res => res.json())
        .then(result => {
            loadPrograms(); // Refresh table
        })
        .catch(err => {
            console.error("Failed to update program:", err);
        });
    }
    });

    
  async function loadPrograms(expandedId = null) {
  try {
    const response = await fetch("/irrigation/program/all");
    const programs = await response.json();

    const tableBody = document.getElementById("programs-body");
    tableBody.innerHTML = "";

    programs.forEach(program => {
      const row = document.createElement("tr");

      row.innerHTML = `
      <td>${program.name || ""}</td>
      <td>${program.is_active ? "✔️" : "❌"}</td>
      <td>${program.frequency}</td>
      <td>${program.upper_score || ""}</td>
      <td>${program.lower_score || ""}</td>
      <td>${program.sessions?.length || 0} sessions</td>
      <td>
          <button class="toggle-sessions" data-id="${program.id}">⬇️</button>
          <button class="edit-row" data-id="${program.id}">✏️</button>
          <button class="remove-row" data-id="${program.id}">🗑️</button>
      </td>
      `;

      tableBody.appendChild(row);

      // Re-expand sessions if this is the one that was open
      if (expandedId && program.id == expandedId) {
        setTimeout(() => {
          row.querySelector(".toggle-sessions").click();
        }, 0);
      }
    });
  } catch (error) {
    console.error("Failed to load programs:", error);
  }
}

  // Refresh button
    document.getElementById("refresh-programs").addEventListener("click", loadPrograms);

    document.getElementById("submit-session").addEventListener("click", async () => {
    const programId = document.getElementById("session-program-id").value;
    const inputs = document.querySelectorAll("#add-sessions-container > div");

    const sessions = Array.from(inputs).map(div => ({
      start_time: div.querySelector("input[type='time']").value,
      duration_minutes: parseInt(div.querySelector("input[type='number']").value)
    }));

    for (const session of sessions) {
      const response = await fetch(`/irrigation/program/${programId}/session/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(session)
      });

      if (!response.ok) {
        alert("❌ Failed to add session.");
        return;
      }
    }

    alert("✅ Sessions added successfully!");
    document.getElementById("create-session-form").style.display = "none";
    loadPrograms(programId); // Refresh and re-expand
  });


  // Add session input fields dynamically
  window.addSessionField = function () {
    const container = document.getElementById("add-sessions-container");
    const index = container.children.length;

    const div = document.createElement("div");
    div.innerHTML = `
      <input type="time" name="session-${index}-start_time" required>
      <input type="number" name="session-${index}-duration_minutes" required>
      <button type="button" onclick="this.parentElement.remove()">❌</button>
    `;
    container.appendChild(div);
  };

  // Handle form submission for adding a new program
  document.getElementById("add-program-form").addEventListener("submit", async function (e) {
    e.preventDefault();
    const form = e.target;
    const data = new FormData(form);

    const sessions = [];
    const count = document.getElementById("add-sessions-container").children.length;
    for (let i = 0; i < count; i++) {
      sessions.push({
        start_time: data.get(`session-${i}-start_time`),
        duration_minutes: parseInt(data.get(`session-${i}-duration_minutes`))
      });
    }

    const payload = {
      name: data.get("name"),
      is_active: data.get("is_active") === "true",
      frequency: parseInt(data.get("frequency")),
      lower_score: parseFloat(data.get("lower_score")),
      upper_score: parseFloat(data.get("upper_score")),
      sessions: sessions
    };

    try {
      const res = await fetch("/irrigation/program", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const result = await res.json();

      if (res.ok) {
        form.reset();
        document.getElementById("add-sessions-container").innerHTML = "";
        loadPrograms(); // Refresh table
      }
    } catch (err) {
      document.getElementById("add-response-message").textContent = "❌ Failed to add program.";
      console.error(err);
    }
  });

  loadPrograms();
});

