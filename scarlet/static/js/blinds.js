document.addEventListener("DOMContentLoaded", () => {


  const toggle = document.getElementById('automationToggle');
  const statusText = document.getElementById('automationStatus');

  // Fetch current state on load
  async function loadAutomationState() {
    const res = await fetch('/blinds/automation');
    const state = await res.json();
    toggle.checked = state;
    statusText.textContent = state ? 'Automata Redőny: Be' : 'Automata Redőny: Ki';
  }

  // Update state when toggled
  toggle.addEventListener('change', async () => {
    const newState = toggle.checked; // true or false
    statusText.textContent = newState ? 'Automata Redőny: Be' : 'Automata Redőny: Ki';

    await fetch('/blinds/automation', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({automation: newState}) // or false
    });

  });

document.getElementById('sendBtn').addEventListener('click', async () => {
    const leftBlind = document.getElementById('leftBlind').value;
    const rightBlind = document.getElementById('rightBlind').value;

    try {
        const res = await fetch('/blinds', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                left_blind: leftBlind,
                right_blind: rightBlind
            })
        });

        if (res.ok) {
            document.getElementById('statusMsg').textContent = 'Siker!';
            document.getElementById('statusMsg').style.color = 'green';
        } else {
            document.getElementById('statusMsg').textContent = 'Error sending command.';
            document.getElementById('statusMsg').style.color = 'red';
        }
    } catch (err) {
        document.getElementById('statusMsg').textContent = 'Network error.';
        document.getElementById('statusMsg').style.color = 'red';
    }
});

  loadAutomationState();
});