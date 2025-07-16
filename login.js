document.addEventListener('DOMContentLoaded', async () => {
    const loginBtn = document.getElementById('login-submit');
    const usernameInput = document.getElementById('login-username');
    const passwordInput = document.getElementById('login-password');
    const togglePasswordBtn = document.getElementById('toggle-password');
    let multiUser = true;

    // Check if we're on the right page with the expected elements
    if (!loginBtn || !usernameInput || !passwordInput) {
        console.warn('Login page elements not found. Make sure you are on the login page.');
        return;
    }

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
        const username = usernameInput?.value?.trim();
        const password = passwordInput?.value;
        
        if (!username || !password) {
            alert('Please enter both username and password');
            return;
        }
        
        // Disable login button during request
        if (loginBtn) {
            loginBtn.disabled = true;
            loginBtn.textContent = 'Logging in...';
        }
        
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
                const errorData = await resp.json().catch(() => ({}));
                alert(errorData.message || 'Login failed. Please check your credentials.');
            }
        } catch (error) {
            console.error('Login error:', error);
            alert('Login error. Please check your connection and try again.');
        } finally {
            // Re-enable login button
            if (loginBtn) {
                loginBtn.disabled = false;
                loginBtn.textContent = 'Login';
            }
        }
    }

    // Add event listeners with proper null checking
    if (loginBtn) {
        loginBtn.addEventListener('click', attemptLogin);
    } else {
        console.warn('Login button not found');
    }
    
    if (usernameInput) {
        usernameInput.addEventListener('keydown', e => { 
            if (e.key === 'Enter') attemptLogin(); 
        });
    } else {
        console.warn('Username input not found');
    }
    
    if (passwordInput) {
        passwordInput.addEventListener('keydown', e => { 
            if (e.key === 'Enter') attemptLogin(); 
        });
    } else {
        console.warn('Password input not found');
    }
    
    if (togglePasswordBtn && passwordInput) {
        togglePasswordBtn.addEventListener('click', () => {
            const isHidden = passwordInput.getAttribute('type') === 'password';
            passwordInput.setAttribute('type', isHidden ? 'text' : 'password');
            togglePasswordBtn.innerHTML = isHidden ? '<i class="fas fa-eye-slash"></i>' : '<i class="fas fa-eye"></i>';
        });
    }
});
