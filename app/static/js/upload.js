// 文件上传相关JavaScript
document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('file-input');
    const fileName = document.getElementById('file-name');
    const uploadBtn = document.getElementById('upload-btn');
    const pdfPreview = document.getElementById('pdf-preview');
    
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                fileName.textContent = this.files[0].name;
                uploadBtn.disabled = false;
                
                // Preview PDF (simplified - would need proper PDF.js implementation)
                const file = this.files[0];
                const fileURL = URL.createObjectURL(file);
                
                pdfPreview.innerHTML = `
                    <embed src="${fileURL}" type="application/pdf" width="100%" height="100%">
                    <p><a href="${fileURL}" target="_blank">Open in new tab</a></p>
                `;
            } else {
                fileName.textContent = 'No file selected';
                uploadBtn.disabled = true;
                pdfPreview.innerHTML = '<p>Uploaded PDF will appear here</p>';
            }
        });
    }
    
    if (uploadBtn) {
        uploadBtn.addEventListener('click', function() {
            if (fileInput.files.length > 0) {
                const formData = new FormData();
                formData.append('file', fileInput.files[0]);
                
                fetch('/upload', {
                    method: 'POST',
                    body: formData
                })
                .then(response => {
                    if (response.redirected) {
                        window.location.href = response.url;
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.success) {
                        alert('File uploaded successfully');
                    } else {
                        alert('Error uploading file: ' + (data.message || 'Unknown error'));
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Error uploading file');
                });
            }
        });
    }
});