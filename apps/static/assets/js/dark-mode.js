// BRM Theme Toggle functionality
document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('theme-toggle');
    const mainStyleLink = document.getElementById('main-style-link');

    // Check for saved theme preference or default to light mode
    const savedTheme = localStorage.getItem('brm-theme') || 'light';

    if (themeToggle) {
        if (savedTheme === 'dark') {
            themeToggle.checked = true;
            enableDarkMode();
        }

        themeToggle.addEventListener('change', function() {
            if (this.checked) {
                enableDarkMode();
                localStorage.setItem('brm-theme', 'dark');
            } else {
                enableLightMode();
                localStorage.setItem('brm-theme', 'light');
            }
        });
    }

    function enableDarkMode() {
        document.body.classList.add('dark-mode');
        if (mainStyleLink) {
            mainStyleLink.href = mainStyleLink.href.replace('style.css', 'dark.css');
        }
    }

    function enableLightMode() {
        document.body.classList.remove('dark-mode');
        if (mainStyleLink) {
            mainStyleLink.href = mainStyleLink.href.replace('dark.css', 'style.css');
        }
    }
});

// Dark mode toggle functionality
document.addEventListener('DOMContentLoaded', function() {
    // Check for saved theme preference or default to light mode
    const currentTheme = localStorage.getItem('theme') || 'light';
    const themeIcon = document.getElementById('theme-icon');

    if (currentTheme === 'dark') {
        document.body.classList.add('dark-mode');
        if (themeIcon) {
            themeIcon.className = 'feather icon-moon';
        }
    } else {
        if (themeIcon) {
            themeIcon.className = 'feather icon-sun';
        }
    }

    // Initialize theme switch if it exists
    const themeSwitch = document.getElementById("theme-switch");
    const themeIndicator = document.getElementById("theme-indicator");

    if (themeSwitch && themeIndicator) {
        const themeStates = ["light", "dark"];
        const indicators = ["icon-sun", "icon-moon"];

        function setTheme(theme) {
            localStorage.setItem("theme", themeStates[theme]);
        }

        function setIndicator(theme) {
            themeIndicator.classList.remove(indicators[0]);
            themeIndicator.classList.remove(indicators[1]);
            themeIndicator.classList.add(indicators[theme]);
        }

        function setPage(theme) {
            if (theme === 1) {
                document.body.classList.add("dark");
            } else {
                document.body.classList.remove("dark");
            }
        }

        // Initialize based on saved theme
        if (currentTheme === themeStates[0]) {
            setIndicator(0);
            setPage(0);
            themeSwitch.checked = true;
        }
        if (currentTheme === themeStates[1]) {
            setIndicator(1);
            setPage(1);
            themeSwitch.checked = false;
        }

        // Handle user interaction
        themeSwitch.addEventListener('change', function () {
            if (this.checked) {
                setTheme(0);
                setIndicator(0);
                setPage(0);
            } else {
                setTheme(1);
                setIndicator(1);
                setPage(1);
            }
        });
    }
});

// Function to toggle between light and dark themes
function toggleTheme() {
    const body = document.body;
    const themeIcon = document.getElementById('theme-icon');

    if (body.classList.contains('dark-mode')) {
        body.classList.remove('dark-mode');
        if (themeIcon) {
            themeIcon.className = 'feather icon-sun';
        }
        localStorage.setItem('theme', 'light');
    } else {
        body.classList.add('dark-mode');
        if (themeIcon) {
            themeIcon.className = 'feather icon-moon';
        }
        localStorage.setItem('theme', 'dark');
    }
}

// Function to toggle between light and dark themes (legacy)
function toggleDarkMode() {
    toggleTheme();
}