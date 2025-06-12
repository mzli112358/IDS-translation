// 主要JavaScript功能
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('collapsed');
}

// Make divider draggable for resizing panels
document.addEventListener('DOMContentLoaded', function() {
    const divider = document.getElementById('divider');
    const container = document.getElementById('split-container');
    const leftPanel = document.querySelector('.left-panel');
    const rightPanel = document.querySelector('.right-panel');
    
    if (divider && container && leftPanel && rightPanel) {
        divider.addEventListener('mousedown', function(e) {
            e.preventDefault();
            
            document.addEventListener('mousemove', resize);
            document.addEventListener('mouseup', stopResize);
            
            function resize(e) {
                const containerRect = container.getBoundingClientRect();
                const containerWidth = containerRect.width;
                const x = e.clientX - containerRect.left;
                const leftWidth = (x / containerWidth) * 100;
                
                leftPanel.style.width = `${leftWidth}%`;
                rightPanel.style.width = `${100 - leftWidth}%`;
            }
            
            function stopResize() {
                document.removeEventListener('mousemove', resize);
                document.removeEventListener('mouseup', stopResize);
            }
        });
    }
});