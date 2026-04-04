// Este mensaje aparecerá en la consola del navegador para confirmar que funciona
console.log("Cuida APP: JavaScript cargado correctamente desde el pendrive.");



// Si el usuario toca el botón de "Tomar", podemos simular una acción de App
document.addEventListener('click', function(e) {
    if (e.target && e.target.textContent === 'TOMAR AHORA') {
        alert("¡Registro guardado! Se le notificará a tu tutor.");
        // Aquí después conectaremos con la base de datos para bajar el stock
    }
});