
// Obtiene el contenedor del chat-body
const chatBodyContainer = document.getElementById('chat-body-container');

// Hace scroll hasta el final del contenedor
chatBodyContainer.scrollTop = chatBodyContainer.scrollHeight;

// Función para cargar el contenido actualizado desde la base de datos
function loadUpdatedContent() {
    // Obtiene el user_number del elemento HTML correspondiente
    const userNumber = document.getElementById('chat_number').value;
    const businessCode = document.getElementById('chat_business').value;

    // Realiza una llamada AJAX para obtener los datos actualizados con el parámetro user_number y business_code
    fetch(`/${businessCode}/${userNumber}/refresh_chat`)
        .then(response => response.json())
        .then(data => {
            // Actualiza el contenido en el contenedor
            const contentContainer = document.getElementById('content-container');

            // Inserta los nuevos mensajes en el contenedor si no están vacíos
            data.content.forEach(pair => {
                const { div_message, div_class } = pair;
                if (div_message.trim() !== '') {
                    const txtNode = document.createTextNode(div_message);
                    const div = document.createElement('div');
                    div.classList.add(div_class);
                    div.append(txtNode); // Utiliza el valor que retorna refresh_chat
                    contentContainer.append(div);
                    setScrollPosition();
                }
            });
        })
        .catch(error => {
            console.error('Error al obtener los datos actualizados:', error);
        });
}


// Carga inicial del contenido
loadUpdatedContent();

// Actualiza el contenido cada 10 segundos
setInterval(loadUpdatedContent, 5000);

const setScrollPosition = () => {
    if (chatBodyContainer.scrollHeight > 0) {
        chatBodyContainer.scrollTop = chatBodyContainer.scrollHeight;
    }
};