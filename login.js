document.addEventListener('DOMContentLoaded', async () => {
    const loginBtn = document.getElementById('login-submit');
    const usernameInput = document.getElementById('login-username');
    const passwordInput = document.getElementById('login-password');
    const togglePasswordBtn = document.getElementById('toggle-password');

    // If the expected elements are missing, the wrong page was likely served.
    // Avoid throwing errors by exiting early and logging a warning so the user
    // can adjust the proxy configuration.
    if (!loginBtn || !usernameInput || !passwordInput) {
        console.warn('Login elements missing. Ensure login.html is served.');
        return;
    }
    let multiUser = true;

    try {
        const resp = await fetch('/api/app-config');
        if (resp.ok) {
            const cfg = await resp.json();
            multiUser = cfg.multi_user;
        }
    } catch (err) {
        console.error('Error fetching app config:', err);
    }

    if (!multiUser) {
        window.location.href = 'index.html';
        return;
    }

    async function restoreSession() {
        const saved = localStorage.getItem('notes-app-session');
        if (!saved) return false;
        try {
            const session = JSON.parse(saved);
            const resp = await fetch('/api/session-info', { headers: { 'Authorization': session.token } });
            if (resp.ok) {
                window.location.href = 'index.html';
                return true;
            }
        } catch {}
        localStorage.removeItem('notes-app-session');
        return false;
    }

    await restoreSession();

    async function attemptLogin() {
        const username = usernameInput.value.trim();
        const password = passwordInput.value;
        try {
            const resp = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            if (resp.ok) {
                const data = await resp.json();
                localStorage.setItem('notes-app-session', JSON.stringify({ token: data.token }));
                window.location.href = 'index.html';
            } else {
                alert('Login failed');
            }
        } catch {
            alert('Login error');
        }
    }

    if (loginBtn) {
        loginBtn.addEventListener('click', attemptLogin);
    }
    if (usernameInput) {
        usernameInput.addEventListener('keydown', e => { if (e.key === 'Enter') attemptLogin(); });
    }
    if (passwordInput) {
        passwordInput.addEventListener('keydown', e => { if (e.key === 'Enter') attemptLogin(); });
    }
    if (togglePasswordBtn && passwordInput) {
        togglePasswordBtn.addEventListener('click', () => {
            const isHidden = passwordInput.getAttribute('type') === 'password';
            passwordInput.setAttribute('type', isHidden ? 'text' : 'password');
            togglePasswordBtn.innerHTML = isHidden ? '<i class="fas fa-eye-slash"></i>' : '<i class="fas fa-eye"></i>';
        });
    }
});
