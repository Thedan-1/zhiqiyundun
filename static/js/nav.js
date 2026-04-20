// static/js/nav.js

document.addEventListener('DOMContentLoaded', function() {
    const toggleButtons = document.querySelectorAll('.system-function-link.toggle-submenu');

    function syncOpenMenuHeights() {
        document.querySelectorAll('.system-function-submenu.show, .system-function-sub-submenu.show').forEach(menu => {
            menu.style.maxHeight = `${menu.scrollHeight}px`;
        });
    }

    toggleButtons.forEach(button => {
        button.addEventListener('click', function(event) {
            event.preventDefault(); // Prevent default link behavior for toggles

            const targetId = this.dataset.target;
            const targetMenu = document.querySelector(targetId);
            const arrowIcon = this.querySelector('.submenu-arrow');

            if (targetMenu) {
                // Toggle 'show' class for visibility
                targetMenu.classList.toggle('show');

                // Toggle 'active' class on the button itself
                this.classList.toggle('active');

                // Toggle arrow icon rotation
                if (arrowIcon) {
                    arrowIcon.classList.toggle('fa-chevron-down');
                    arrowIcon.classList.toggle('fa-chevron-up');
                }

                if (targetMenu.classList.contains('show')) {
                    targetMenu.style.maxHeight = `${targetMenu.scrollHeight}px`;
                } else {
                    targetMenu.style.maxHeight = '0px';
                }

                syncOpenMenuHeights();
            }
        });
    });

    // Initialize arrow icons based on 'show' class on page load
    document.querySelectorAll('.system-function-submenu, .system-function-sub-submenu').forEach(menu => {
        if (menu.classList.contains('show')) {
            menu.style.maxHeight = `${menu.scrollHeight}px`;
            const button = document.querySelector(`[data-target="#${menu.id}"]`);
            if (button) {
                const arrowIcon = button.querySelector('.submenu-arrow');
                if (arrowIcon) {
                    arrowIcon.classList.remove('fa-chevron-down');
                    arrowIcon.classList.add('fa-chevron-up');
                }
            }
        } else {
            menu.style.maxHeight = '0px';
        }
    });

    syncOpenMenuHeights();
});