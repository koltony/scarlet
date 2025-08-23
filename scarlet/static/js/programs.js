// console.log("✅ programs.js loaded");

// document.addEventListener("DOMContentLoaded", () => {
//     const tbody = document.getElementById("programs-body");
//     const addBtn = document.getElementById("add-program");

//     // Load all programs
//     fetch("/irrigation/program/all")
//         .then(res => res.json())
//         .then(programs => {
//             console.log("Fetched programs:", programs);
//             tbody.innerHTML = "";

//             if (!Array.isArray(programs) || programs.length === 0) {
//                 tbody.innerHTML = "<tr><td colspan='4'><em>No programs found</em></td></tr>";
//                 return;
//             }

//             programs.forEach(p => {
//                 const sessions = Array.isArray(p.sessions) ? p.sessions : [];

//                 // Main program row
//                 const tr = document.createElement("tr");
//                 tr.innerHTML = `
//                     <td>${p.name}</td>
//                     <td>${p.is_active ? "✅" : "❌"}</td>
//                     <td>${p.frequency}</td>
//                     <td>
//                         <button type="button" class="toggle-sessions" data-id="${p.id}">Sessions</button>
//                         <button type="button" class="toggle-program-edit" data-id="${p.id}">Edit</button>
//                     </td>
//                 `;
//                 tbody.appendChild(tr);

//                 // Program edit row
//                 const editRow = document.createElement("tr");
//                 editRow.classList.add("program-edit-row");
//                 editRow.style.display = "none";
//                 editRow.innerHTML = `
//                     <td colspan="4">
//                         <div class="edit-container">
//                             <label>Name: <input type="text" value="${p.name}" class="edit-name"></label>
//                             <label>Frequency: <input type="number" value="${p.frequency}" class="edit-freq"></label>
//                             <label>Active: <input type="checkbox" ${p.is_active ? "checked" : ""} class="edit-active"></label>
//                             <button type="button" class="save-program" data-id="${p.id}">Save</button>
//                             <button type="button" class="cancel-program">Cancel</button>
//                         </div>
//                     </td>
//                 `;
//                 tbody.appendChild(editRow);

//                 // Sessions row
//                 const sessionsRow = document.createElement("tr");
//                 sessionsRow.classList.add("sessions-row");
//                 sessionsRow.style.display = "none";
//                 sessionsRow.innerHTML = `
//                     <td colspan="4">
//                         <table class="session-table">
//                             <thead>
//                                 <tr>
//                                     <th>Start</th>
//                                     <th>Zone 1</th>
//                                     <th>Zone 2</th>
//                                     <th>Zone 3</th>
//                                     <th>Actions</th>
//                                 </tr>
//                             </thead>
//                             <tbody>
//                                 ${sessions.length
//                                     ? sessions.map(s => `
//                                         <tr class="sessions-show">
//                                             <td>${s.start_time ?? "<em>Not set</em>"}</td>
//                                             <td>${s.zone1 ?? "-"}</td>
//                                             <td>${s.zone2 ?? "-"}</td>
//                                             <td>${s.zone3 ?? "-"}</td>
//                                             <td>
//                                                 <button type="button" class="toggle-session-edit" data-id="${s.id}">Edit</button>
//                                             </td>
//                                         </tr>
//                                         <tr class="session-edit" style="display:none;">
//                                             <td><input type="text" value="${s.start_time ?? ""}" class="sess-start"></td>
//                                             <td><input type="text" value="${s.zone1 ?? ""}" class="sess-z1"></td>
//                                             <td><input type="text" value="${s.zone2 ?? ""}" class="sess-z2"></td>
//                                             <td><input type="text" value="${s.zone3 ?? ""}" class="sess-z3"></td>
//                                             <td>
//                                                 <button type="button" class="save-session" data-id="${s.id}">Save</button>
//                                                 <button type="button" class="cancel-session">Cancel</button>
//                                             </td>
//                                         </tr>
//                                     `).join('')
//                                     : `<tr><td colspan="5"><em>No sessions</em></td></tr>`
//                                 }
//                             </tbody>
//                         </table>
//                     </td>
//                 `;
//                 tbody.appendChild(sessionsRow);
//             });
//         })
//         .catch(err => {
//             console.error("Error fetching programs:", err);
//             tbody.innerHTML = "<tr><td colspan='4'><em>Error loading programs</em></td></tr>";
//         });

//     // Event delegation
//     tbody.addEventListener("click", e => {
//         const btn = e.target;

//         if (btn.classList.contains("toggle-sessions")) {
//             const sessionsRow = btn.closest("tr").nextElementSibling.nextElementSibling;
//             if (sessionsRow && sessionsRow.classList.contains("sessions-row")) {
//                 sessionsRow.style.display = sessionsRow.style.display === "none" ? "table-row" : "none";
//             }
//         }

//         if (btn.classList.contains("toggle-program-edit")) {
//             const row = btn.closest("tr").nextElementSibling;
//             row.style.display = row.style.display === "none" ? "table-row" : "none";
//         }

//         if (btn.classList.contains("save-program")) {
//             const row = btn.closest(".edit-container");
//             const id = btn.dataset.id;
//             const name = row.querySelector(".edit-name").value;
//             const freq = parseInt(row.querySelector(".edit-freq").value, 10);
//             const active = row.querySelector(".edit-active").checked;

//             fetch(`/irrigation/program/${id}`, {
//                 method: "PATCH",
//                 headers: { "Content-Type": "application/json" },
//                 body: JSON.stringify({ name, frequency: freq, is_active: active })
//             }).then(() => location.reload());
//         }

//         if (btn.classList.contains("cancel-program")) {
//             btn.closest("tr").style.display = "none";
//         }

//         if (btn.classList.contains("toggle-session-edit")) {
//             const editRow = btn.closest("tr").nextElementSibling;
//             if (editRow && editRow.classList.contains("session-edit")) {
//                 editRow.style.display = editRow.style.display === "none" ? "table-row" : "none";
//             }
//         }

//         if (btn.classList.contains("save-session")) {
//             const editRow = btn.closest(".session-edit");
//             const id = btn.dataset.id;
//             const start = editRow.querySelector(".sess-start").value;
//             const z1 = editRow.querySelector(".sess-z1").value;
//             const z2 = editRow.querySelector(".sess-z2").value;
//             const z3 = editRow.querySelector(".sess-z3").value;

//             fetch(`/irrigation/program/session/${id}`, {
//                 method: "PATCH",
//                 headers: { "Content-Type": "application/json" },
//                 body: JSON.stringify({ start_time: start, zone1: z1, zone2: z2, zone3: z3 })
//             }).then(() => location.reload());
//         }

//         if (btn.classList.contains("cancel-session")) {
//             btn.closest(".session-edit").style.display = "none";
//         }
//     });

//     // Add new program
//     addBtn.addEventListener("click", () => {
//         const name = prompt("Program name:");
//         const freq = prompt("Frequency:");
//         const active = confirm("Set as active?");
//         fetch("/irrigation/program", {
//             method: "POST",
//             headers: { "Content-Type": "application/json" },
//             body: JSON.stringify({
//                 name,
//                 frequency: parseInt(freq, 10),
//                 is_active: active,
//                 sessions: []
//             })
//         }).then(() => location.reload());
//     });
// });
