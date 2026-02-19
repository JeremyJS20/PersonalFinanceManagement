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
                    form.reset();
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

            // Open Buttons (ID-specific AND Generic with data-pfm-modal-target)
            const openSelectors = `.${mEl.id}-open-btn, .modal-open-btn[data-pfm-modal-target="${mEl.id}"]`;
            document.querySelectorAll(openSelectors).forEach(btn => {
                btn.addEventListener('click', () => {
                    // Sync data attributes: e.g. data-group="X" -> elements with data-pfm-modal-bind="group"
                    Object.keys(btn.dataset).forEach(key => {
                        const bindKey = key.startsWith('pfmBind') ? key.replace('pfmBind', '').toLowerCase() : null;
                        if (bindKey) {
                            const bindEl = mEl.querySelector(`[data-pfm-modal-bind="${bindKey}"]`);
                            if (bindEl) {
                                if (bindEl.tagName === 'INPUT' || bindEl.tagName === 'TEXTAREA') {
                                    bindEl.value = btn.dataset[key];
                                } else {
                                    bindEl.textContent = btn.dataset[key];
                                }
                            }
                        }
                    });

                    modal.show();
                    if (modalContent) {
                        setTimeout(() => {
                            modalContent.classList.remove('scale-95', 'opacity-0');
                            modalContent.classList.add('scale-100', 'opacity-100');
                        }, 10);
                    }
                });
            });

            // Close Buttons (ID-specific AND Generic within the modal)
            const closeSelectors = `.${mEl.id}-close-btn, .modal-close-btn`;
            mEl.querySelectorAll(closeSelectors).forEach(btn => {
                btn.addEventListener('click', closeSmoothly);
            });

            // Global close buttons outside that might target this modal
            document.querySelectorAll(`.modal-close-btn[data-pfm-modal-hide="${mEl.id}"]`).forEach(btn => {
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

    // Generic Tab Switcher
    const tabGroups = document.querySelectorAll('[data-pfm-tab-group]');
    tabGroups.forEach(group => {
        const groupName = group.getAttribute('data-pfm-tab-group');
        const tabBtns = group.querySelectorAll('[data-pfm-tab-target]');
        const tabContents = document.querySelectorAll(`[data-pfm-tab-content]`);

        const setActiveTab = (target) => {
            // Update Buttons
            tabBtns.forEach(b => {
                const isActive = b.getAttribute('data-pfm-tab-target') === target;
                if (isActive) {
                    b.classList.add('bg-pfm-primary/10', 'text-pfm-primary', 'border-l-4', 'border-pfm-primary', 'font-semibold');
                    b.classList.remove('text-pfm-text-light', 'font-medium');
                } else {
                    b.classList.remove('bg-pfm-primary/10', 'text-pfm-primary', 'border-l-4', 'border-pfm-primary', 'font-semibold');
                    b.classList.add('text-pfm-text-light', 'font-medium');
                }
            });

            // Update Content
            tabContents.forEach(content => {
                if (content.getAttribute('data-pfm-tab-content') === target) {
                    content.classList.remove('hidden');
                } else {
                    content.classList.add('hidden');
                }
            });

            // Store State (Session)
            sessionStorage.setItem('activeTab-' + groupName, target);

            // Update URL and Cookie if this is the category-type tab group (to support server-side persistence)
            if (groupName === 'category-type') {
                // Update URL Parameter
                const url = new URL(window.location);
                url.searchParams.set('tab', target);
                window.history.replaceState({}, '', url);

                // Set Cookie (Expires in 30 days)
                const d = new Date();
                d.setTime(d.getTime() + (30 * 24 * 60 * 60 * 1000));
                document.cookie = `pfm_last_category_tab=${target};expires=${d.toUTCString()};path=/`;
            }

            // Re-initialize icons
            if (typeof lucide !== 'undefined') {
                lucide.createIcons();
            }
        };

        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const target = btn.getAttribute('data-pfm-tab-target');
                setActiveTab(target);
            });
        });

    });

    // Initialize Lucide Icons
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }

    // On-load URL sync for categories page (if server provided a tab but URL is missing it)
    if (window.location.pathname.includes('/categories/')) {
        const urlParams = new URLSearchParams(window.location.search);
        if (!urlParams.has('tab')) {
            const activeTabBtn = document.querySelector('[data-pfm-tab-group="category-type"] .bg-pfm-primary\\/10');
            if (activeTabBtn) {
                const target = activeTabBtn.getAttribute('data-pfm-tab-target');
                const url = new URL(window.location);
                url.searchParams.set('tab', target);
                window.history.replaceState({}, '', url);
            }
        }
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
