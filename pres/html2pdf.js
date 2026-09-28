// Genera un PDF descargable con una diapositiva por página.
async function downloadPDF() {
    const button = document.querySelector('.download-btn');
    const presentation = document.getElementById('presentation');
    const originalLabel = button.textContent;

    if (!presentation) {
        alert('No se encontró la presentación.');
        return;
    }

    button.disabled = true;
    button.textContent = 'Generando PDF…';

    try {
        if (typeof window.html2pdf !== 'function') {
            await new Promise((resolve, reject) => {
                const library = document.createElement('script');
                library.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js';
                library.onload = resolve;
                library.onerror = () => reject(new Error('No se pudo cargar html2pdf. Comprueba la conexión a internet.'));
                document.head.appendChild(library);
            });
        }
        if (typeof window.html2pdf !== 'function') {
            throw new Error('html2pdf no está disponible.');
        }

        const slides = Array.from(presentation.querySelectorAll('.slide'));
        if (!slides.length) throw new Error('No se encontraron diapositivas.');

        const pdf = window.html2pdf().set({
            margin: 5,
            filename: 'OptiSignal-AI_Segundo_Corte.pdf',
            image: { type: 'jpeg', quality: 0.98 },
            html2canvas: { scale: 2, useCORS: true, allowTaint: false, backgroundColor: '#ffffff' },
            jsPDF: { orientation: 'landscape', unit: 'mm', format: 'a4' },
            pagebreak: { mode: ['css', 'legacy'] }
        });

        const pages = document.createElement('div');
        pages.style.cssText = 'position:fixed;left:0;top:0;width:287mm;background:white;z-index:-1;';
        slides.forEach((slide) => {
            const copy = slide.cloneNode(true);
            copy.style.cssText += ';width:287mm;height:200mm;min-height:200mm;max-height:200mm;box-sizing:border-box;overflow:hidden;break-after:page;page-break-after:always;';
            pages.appendChild(copy);
        });
        document.body.appendChild(pages);
        try {
            await pdf.from(pages).save();
        } finally {
            pages.remove();
        }
    } catch (error) {
        console.error('Error al generar el PDF:', error);
        alert('No se pudo generar el PDF: ' + error.message);
    } finally {
        button.disabled = false;
        button.textContent = originalLabel;
    }
}

window.addEventListener('DOMContentLoaded', () => {
    console.log('Presentación OptiSignal-AI cargada correctamente');
});


