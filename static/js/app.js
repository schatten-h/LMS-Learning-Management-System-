// Fonction utilitaire centralisée pour les appels à notre API FastAPI
async function apiCall(endpoint, method = 'GET', body = null) {
    const options = {
        method: method,
        headers: {},
        // Crucial pour faire transiter le cookie de session (Auth HTTP-Only)
        credentials: 'include' 
    };

    if (body) {
        if (body instanceof FormData) {
            options.body = body;
            // Ne surtout PAS forcer le 'Content-Type' avec FormData.
            // Le navigateur s'occupe de mettre 'multipart/form-data' tout seul.
        } else {
            options.headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(body);
        }
    }

    try {
        // Utilisation du endpoint tel quel (ex: '/api/auth/login')
        const response = await fetch(endpoint, options);
        
        // On tente de parser la réponse en JSON
        const data = await response.json().catch(() => ({})); 
        
        if (!response.ok) {
            throw new Error(data.detail || data.msg || "Une erreur est survenue sur le serveur.");
        }
        return data;
    } catch (error) {
        // Affichage global de l'erreur
        showMessage(error.message, "error");
        throw error;
    }
}

// Fonction pour afficher des notifications visuelles (toast/bannière)
function showMessage(text, type = "success") {
    const msgBox = document.getElementById("message-box");
    if (!msgBox) return;
    
    msgBox.textContent = text;
    // Ajoute la classe CSS correspondant au type (success, error, warning...)
    msgBox.className = type; 
    msgBox.style.display = "block";
    
    // Disparition automatique après 5 secondes
    setTimeout(() => {
        msgBox.style.display = "none";
    }, 5000);
}

// Fonction globale pour se déconnecter de la plateforme
async function logout() {
    try {
        // Appel explicite vers le routeur d'authentification
        await apiCall('/api/auth/logout', 'POST');
        // Nettoyage visuel et redirection vers la page de connexion
        window.location.href = '/login';
    } catch (e) {
        console.error("Erreur critique lors de la déconnexion :", e);
        // Redirection forcée en cas de désynchronisation
        window.location.href = '/login'; 
    }
}