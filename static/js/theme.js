// Theme Management
class ThemeManager {
    constructor() {
        this.checkbox = document.getElementById('darkModeToggle');
        this.init();
    }

    init() {
        this.loadThemePreference();
        this.setupEventListeners();
    }

    async loadThemePreference() {
        try {
            const response = await fetch('/theme/settings');
            const data = await response.json();
            this.applyTheme(data.theme || 'light');
        } catch (error) {
            console.error('Error loading theme:', error);
            this.applyTheme(localStorage.getItem('theme') || 'light');
        }
    }

    applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        if (this.checkbox) {
            this.checkbox.checked = theme === 'dark';
        }
        localStorage.setItem('theme', theme);
    }

    async toggleTheme() {
        const newTheme = this.checkbox.checked ? 'dark' : 'light';
        const oldTheme = localStorage.getItem('theme') || 'light';
        
        try {
            const response = await fetch('/theme/toggle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ theme: newTheme })
            });
            
            if (response.ok) {
                this.applyTheme(newTheme);
            } else {
                this.showError('Failed to update theme preference');
                this.checkbox.checked = !this.checkbox.checked;
                this.applyTheme(oldTheme);
            }
        } catch (error) {
            this.showError('Error updating theme');
            this.checkbox.checked = !this.checkbox.checked;
            this.applyTheme(oldTheme);
        }
    }

    showError(message) {
        // Add error notification UI here
        console.error(message);
    }

    setupEventListeners() {
        if (this.checkbox) {
            this.checkbox.addEventListener('change', () => this.toggleTheme());
        }

        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) this.loadThemePreference();
        });
    }
}

// Tips Modal Management
class TipsModal {
    constructor() {
        this.modal = document.getElementById('tipsModal');
        this.init();
    }

    init() {
        if (window.show_tips) {
            this.show();
        }
    }

    show() {
        this.modal?.classList.remove('hidden');
    }

    close() {
        this.modal?.classList.add('hidden');
    }
}

// Settings Modal Management
class SettingsModal {
    constructor() {
        this.modal = document.getElementById('settingsModal');
        this.init();
    }

    init() {
        this.setupEventListeners();
    }

    open() {
        this.modal?.classList.add('active');
        window.themeManager.loadThemePreference();
    }

    close() {
        this.modal?.classList.remove('active');
    }

    setupEventListeners() {
        this.modal?.addEventListener('click', (e) => {
            if (e.target === this.modal) this.close();
        });
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.themeManager = new ThemeManager();
    window.tipsModal = new TipsModal();
    window.settingsModal = new SettingsModal();
});