document.addEventListener("DOMContentLoaded", () => {


  const toggle = document.getElementById('automationToggle');
  const statusText = document.getElementById('automationStatus');

async function loadAutomationState() {
  const res = await fetch('/blinds/automation');
  const state = await res.json();
  toggle.checked = state.automation;
  statusText.textContent = state.automation ? 'Automata Redőny: Be' : 'Automata Redőny: Ki';
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
        const data = await res.json();
        if (data.detail == 'Accepted'){
          statusMsg.classList.remove('fade-out');
          statusMsg.textContent = 'Siker!';
          statusMsg.style.color = 'green';
          statusMsg.style.opacity = 1;
        } else {
          statusMsg.classList.remove('fade-out');
          statusMsg.textContent = 'Arduino nem reagált!';
          statusMsg.style.color = 'orange';
          statusMsg.style.opacity = 1;
        }
        void statusMsg.offsetWidth; // Force reflow
        statusMsg.classList.add('fade-out')
      } else {
        statusMsg.textContent = 'Error sending command.';
        statusMsg.style.color = 'red';
      }

      setTimeout(() => {
        statusMsg.textContent = '';
      }, 5000);

    } catch (err) {
        document.getElementById('statusMsg').textContent = 'Network error.';
        document.getElementById('statusMsg').style.color = 'red';
    }
});

  loadAutomationState();
});