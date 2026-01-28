document.addEventListener('DOMContentLoaded', function () {
    // Mobile Menu Toggle
    const btn = document.getElementById('mobile-menu-btn');
    const menu = document.getElementById('mobile-menu');

    if (btn && menu) {
        btn.addEventListener('click', () => {
            menu.classList.toggle('hidden');
        });
    }

    // Modal Logic
    let modalTargetsEl = document.querySelectorAll('.modal');

    modalTargetsEl.forEach(mEl => {
        const options = {
            closable: false, // Disable default close to handle animation manually
            onHide: () => {
                const form = mEl.querySelector('form');
                if (form) {
                    Array.from(form.elements).forEach(el => {
                        switch (el.type) {
                            case 'text': case 'password': case 'email': case 'number':
                            case 'url': case 'search': case 'tel': case 'textarea':
                                el.value = ''; break;
                            case 'checkbox': case 'radio':
                                el.checked = false; break;
                            case 'select-one': case 'select-multiple':
                                Array.from(el.options).forEach(option => option.selected = false); break;
                            case 'file':
                                el.value = null; break;
                            default:
                                el.value = '';
                        }
                    });
                }
            },
        };

        // Check if Flowbite Modal is available
        if (typeof Modal !== 'undefined') {
            const modal = new Modal(mEl, options);
            const modalContent = mEl.querySelector('.relative.bg-pfm-card');

            const closeSmoothly = () => {
                if (modalContent) {
                    modalContent.classList.remove('scale-100', 'opacity-100');
                    modalContent.classList.add('scale-95', 'opacity-0');
                    setTimeout(() => {
                        modal.hide();
                    }, 300);
                } else {
                    modal.hide();
                }
            };

            // Open Buttons
            document.querySelectorAll(`.${mEl.id}-open-btn`).forEach(btn => {
                btn.addEventListener('click', () => {
                    modal.show();
                    if (modalContent) {
                        setTimeout(() => {
                            modalContent.classList.remove('scale-95', 'opacity-0');
                            modalContent.classList.add('scale-100', 'opacity-100');
                        }, 10);
                    }
                });
            });

            // Close Buttons
            document.querySelectorAll(`.${mEl.id}-close-btn`).forEach(btn => {
                btn.addEventListener('click', closeSmoothly);
            });

            // Custom Backdrop Click Listener
            mEl.addEventListener('click', (e) => {
                if (e.target === mEl) {
                    closeSmoothly();
                }
            });

        } else {
            console.error('Flowbite Modal is not defined. Ensure Flowbite JS is loaded.');
        }
    });

    // Initialize Lucide Icons
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }

    // Theme Toggle Logic
    const themeToggleBtn = document.getElementById('theme-toggle');
    const html = document.documentElement;

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', function () {
            if (html.classList.contains('dark')) {
                html.classList.remove('dark');
                localStorage.setItem('color-theme', 'light');
            } else {
                html.classList.add('dark');
                localStorage.setItem('color-theme', 'dark');
            }
        });
    }
});
