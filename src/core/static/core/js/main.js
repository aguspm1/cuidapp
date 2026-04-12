console.log("Archivo main.js cargado correctamente");

function mostrarPestana(pestana) {
    const secMeds = document.getElementById('seccion-meds');
    const secCal = document.getElementById('seccion-cal');
    const btnMeds = document.getElementById('btn-tab-meds');
    const btnCal = document.getElementById('btn-tab-cal');

    if (!secMeds || !secCal || !btnMeds || !btnCal) {
        console.error("No se encontraron los elementos necesarios");
        return;
    }

    if (pestana === 'calendario') {
        secMeds.style.display = 'none';
        secCal.style.display = 'block';
        
        btnMeds.classList.remove('active');
        btnCal.classList.add('active');
        
        console.log("Mostrando Calendario");
    } else if (pestana === 'medicamentos') {
        secMeds.style.display = 'block';
        secCal.style.display = 'none';
        
        btnCal.classList.remove('active');
        btnMeds.classList.add('active');
        
        console.log("Mostrando Medicamentos");
    }
}