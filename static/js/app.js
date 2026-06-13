// TaskFlow Client Application

// Application State
let users = [];
let allTasks = [];
let currentUser = null;
let currentFilter = 'all';

// DOM Elements
const activeUserSelect = document.getElementById('active-user-select');
const currentUserAvatar = document.getElementById('current-user-avatar');
const modalCreatorName = document.getElementById('modal-creator-name');
const taskResponsibleSelect = document.getElementById('task-responsible');
const tasksGrid = document.getElementById('tasks-grid');
const searchInput = document.getElementById('search-input');
const filterBtns = document.querySelectorAll('.filter-btn');
const openModalBtn = document.getElementById('open-modal-btn');
const closeModalBtn = document.getElementById('close-modal-btn');
const cancelTaskBtn = document.getElementById('cancel-task-btn');
const taskModal = document.getElementById('task-modal');
const taskForm = document.getElementById('task-form');
const taskDueDateInput = document.getElementById('task-due-date');
const notificationContainer = document.getElementById('notification-container');

// Stats Elements
const statPending = document.getElementById('stat-pending');
const statProgress = document.getElementById('stat-progress');
const statCompleted = document.getElementById('stat-completed');
const statTotal = document.getElementById('stat-total');

// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', async () => {
    // Establecer fecha de vencimiento mínima como hoy
    const today = new Date().toISOString().split('T')[0];
    taskDueDateInput.min = today;
    taskDueDateInput.value = today;

    // Cargar Datos Iniciales
    await loadUsers();
    await loadTasks();

    // Configurar Listeners de Eventos
    setupEventListeners();
});

// --- API FUNCTIONS ---

// Obtener la lista de usuarios
async function loadUsers() {
    try {
        const response = await fetch('/api/users');
        if (!response.ok) throw new Error('Error al cargar usuarios');
        users = await response.json();
        
        populateUserSelectors();
        
        // Establecer usuario por defecto (el primero de la lista)
        if (users.length > 0) {
            setCurrentUser(users[0].id);
        }
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// Obtener todas las tareas de la API
async function loadTasks() {
    try {
        const response = await fetch('/api/tasks');
        if (!response.ok) throw new Error('Error al cargar tareas');
        allTasks = await response.json();
        
        updateStats();
        renderTasks();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// Crear una nueva tarea
async function createTask(taskData) {
    if (!currentUser) {
        showToast('Debe seleccionar un usuario activo primero.', 'error');
        return;
    }

    try {
        const response = await fetch('/api/tasks', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-User-Id': currentUser.id
            },
            body: JSON.stringify(taskData)
        });

        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.error || 'Error al crear la tarea');
        }

        showToast('Tarea creada con éxito', 'success');
        closeModal();
        taskForm.reset();
        // Restablecer fecha predeterminada
        taskDueDateInput.value = new Date().toISOString().split('T')[0];
        
        await loadTasks();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// Cambiar el estado de una tarea
async function updateTaskStatus(taskId, newStatus) {
    if (!currentUser) {
        showToast('Debe seleccionar un usuario activo.', 'error');
        return;
    }

    try {
        const response = await fetch(`/api/tasks/${taskId}/status`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-User-Id': currentUser.id
            },
            body: JSON.stringify({ estado: newStatus })
        });

        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.error || 'Error al actualizar estado');
        }

        showToast('Estado de la tarea actualizado', 'success');
        await loadTasks(); // Recargar para reflejar cambios y estadísticas
    } catch (error) {
        showToast(error.message, 'error');
        // Re-renderizar para revertir el selector visual al valor correcto si falla
        renderTasks();
    }
}

// --- UI HELPERS & RENDER ---

function populateUserSelectors() {
    // Limpiar
    activeUserSelect.innerHTML = '';
    taskResponsibleSelect.innerHTML = '<option value="" disabled selected>Seleccione un responsable</option>';

    users.forEach(user => {
        // Selector de cabecera
        const optionActive = document.createElement('option');
        optionActive.value = user.id;
        optionActive.textContent = `${user.nombre_completo} (@${user.username})`;
        activeUserSelect.appendChild(optionActive);

        // Selector del modal de responsable
        const optionResp = document.createElement('option');
        optionResp.value = user.id;
        optionResp.textContent = user.nombre_completo;
        taskResponsibleSelect.appendChild(optionResp);
    });
}

function setCurrentUser(userId) {
    currentUser = users.find(u => u.id === parseInt(userId));
    if (currentUser) {
        // Actualizar avatar de la cabecera (iniciales)
        const initials = currentUser.nombre_completo.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
        currentUserAvatar.textContent = initials;
        
        // Actualizar nombre en el modal
        modalCreatorName.textContent = currentUser.nombre_completo;
        
        // Refrescar el tablero por si cambian permisos de edición visuales
        renderTasks();
    }
}

function updateStats() {
    const counts = {
        'Pendiente': 0,
        'En Progreso': 0,
        'Completada': 0
    };

    allTasks.forEach(task => {
        if (counts[task.estado] !== undefined) {
            counts[task.estado]++;
        }
    });

    statPending.textContent = counts['Pendiente'];
    statProgress.textContent = counts['En Progreso'];
    statCompleted.textContent = counts['Completada'];
    statTotal.textContent = allTasks.length;
}

function renderTasks() {
    const searchText = searchInput.value.toLowerCase().trim();
    
    // Filtrar tareas
    const filteredTasks = allTasks.filter(task => {
        // Filtro por Estado
        if (currentFilter !== 'all' && task.estado !== currentFilter) {
            return false;
        }
        // Filtro por búsqueda de texto
        if (searchText) {
            const matchesTitle = task.titulo.toLowerCase().includes(searchText);
            const matchesDesc = task.descripcion.toLowerCase().includes(searchText);
            const matchesCreator = task.creador_nombre.toLowerCase().includes(searchText);
            const matchesResp = task.responsable_nombre.toLowerCase().includes(searchText);
            return matchesTitle || matchesDesc || matchesCreator || matchesResp;
        }
        return true;
    });

    // Limpiar grilla
    tasksGrid.innerHTML = '';

    if (filteredTasks.length === 0) {
        tasksGrid.innerHTML = `
            <div class="empty-state">
                <i class="fa-solid fa-folder-open"></i>
                <h3>No se encontraron tareas</h3>
                <p>Prueba ajustando los filtros de búsqueda o crea una nueva tarea.</p>
            </div>
        `;
        return;
    }

    const todayDate = new Date();
    todayDate.setHours(0,0,0,0);

    filteredTasks.forEach(task => {
        const isCreator = currentUser && (task.creador_id === currentUser.id);
        
        // Formatear fechas legibles en español
        const dateGen = formatDate(task.fecha_generacion);
        const dateDue = formatDate(task.fecha_vencimiento);

        // Verificar si está vencida
        const dueDate = new Date(task.fecha_vencimiento);
        dueDate.setHours(23, 59, 59, 999); // Final del día de vencimiento
        const isOverdue = dueDate < todayDate && task.estado !== 'Completada';

        // Avatares mini (iniciales)
        const creatorInitials = getInitials(task.creador_nombre);
        const respInitials = getInitials(task.responsable_nombre);

        // Crear Tarjeta de Tarea
        const card = document.createElement('div');
        card.className = `task-card status-${slugify(task.estado)}`;
        
        // Estructura interna de la tarjeta
        card.innerHTML = `
            <div class="task-card-header">
                <h3 class="task-title">${escapeHTML(task.titulo)}</h3>
                <span class="status-badge ${slugify(task.estado)}">
                    ${getStatusIcon(task.estado)} ${task.estado}
                </span>
            </div>
            
            <p class="task-desc">${escapeHTML(task.descripcion || 'Sin descripción.')}</p>
            
            <div class="task-users-meta">
                <div class="meta-user-block">
                    <div class="mini-avatar creator-avatar" title="Creador: ${escapeHTML(task.creador_nombre)}">
                        ${creatorInitials}
                    </div>
                    <div class="user-meta-label">
                        <span class="role-title">Generó</span>
                        <span class="username-text">${escapeHTML(task.creador_nombre)}</span>
                    </div>
                </div>
                <div class="meta-user-block">
                    <div class="mini-avatar resp-avatar" title="Responsable: ${escapeHTML(task.responsable_nombre)}">
                        ${respInitials}
                    </div>
                    <div class="user-meta-label">
                        <span class="role-title">Responsable</span>
                        <span class="username-text">${escapeHTML(task.responsable_nombre)}</span>
                    </div>
                </div>
            </div>
            
            <div class="task-dates-meta">
                <div class="date-item">
                    <i class="fa-regular fa-calendar-plus" title="Fecha de Generación"></i>
                    <span>Creado: ${dateGen}</span>
                </div>
                <div class="date-item ${isOverdue ? 'overdue' : ''}">
                    <i class="fa-regular fa-calendar-check" title="Fecha de Vencimiento"></i>
                    <span>Vence: ${dateDue} ${isOverdue ? '<i class="fa-solid fa-circle-exclamation" title="¡Vencida!"></i>' : ''}</span>
                </div>
            </div>
            
            <div class="task-status-control">
                <span class="control-label"><i class="fa-solid fa-sliders"></i> Acciones:</span>
                <div class="control-action-area">
                    ${isCreator ? `
                        <div class="status-dropdown-wrapper">
                            <select class="status-select" data-task-id="${task.id}">
                                <option value="Pendiente" ${task.estado === 'Pendiente' ? 'selected' : ''}>Pendiente</option>
                                <option value="En Progreso" ${task.estado === 'En Progreso' ? 'selected' : ''}>En Progreso</option>
                                <option value="Completada" ${task.estado === 'Completada' ? 'selected' : ''}>Completada</option>
                            </select>
                        </div>
                    ` : `
                        <div class="locked-badge-container" data-tooltip="Solo el creador (${escapeHTML(task.creador_nombre)}) puede cambiar el estado">
                            <i class="fa-solid fa-lock locked-icon"></i>
                            <span style="font-size: 0.8rem; font-style: italic;">Estado bloqueado</span>
                        </div>
                    `}
                </div>
            </div>
        `;

        // Añadir event listener al dropdown si el usuario es creador
        if (isCreator) {
            const select = card.querySelector('.status-select');
            select.addEventListener('change', (e) => {
                updateTaskStatus(task.id, e.target.value);
            });
        }

        tasksGrid.appendChild(card);
    });
}

// --- LISTENERS Y DIÁLOGOS ---

function setupEventListeners() {
    // Cambio de usuario activo
    activeUserSelect.addEventListener('change', (e) => {
        setCurrentUser(e.target.value);
        showToast(`Cambiado al perfil de ${currentUser.nombre_completo}`, 'info');
    });

    // Filtros de estado
    filterBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = btn.dataset.filter;
            renderTasks();
        });
    });

    // Entrada de búsqueda
    searchInput.addEventListener('input', () => {
        renderTasks();
    });

    // Modal abrir/cerrar
    openModalBtn.addEventListener('click', openModal);
    closeModalBtn.addEventListener('click', closeModal);
    cancelTaskBtn.addEventListener('click', closeModal);
    
    // Cerrar modal al hacer clic fuera del card
    taskModal.addEventListener('click', (e) => {
        if (e.target === taskModal) closeModal();
    });

    // Envío del formulario
    taskForm.addEventListener('submit', (e) => {
        e.preventDefault();
        
        const taskData = {
            titulo: document.getElementById('task-title').value,
            descripcion: document.getElementById('task-desc').value,
            responsable_id: parseInt(taskResponsibleSelect.value),
            fecha_vencimiento: document.getElementById('task-due-date').value
        };

        createTask(taskData);
    });
}

function openModal() {
    if (!currentUser) {
        showToast('Debe seleccionar un usuario activo.', 'error');
        return;
    }
    taskModal.classList.add('open');
}

function closeModal() {
    taskModal.classList.remove('open');
}

// --- UTILITY FUNCTIONS ---

function getInitials(name) {
    if (!name) return '?';
    const parts = name.trim().split(' ');
    if (parts.length >= 2) {
        return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return parts[0].substring(0, 2).toUpperCase();
}

function formatDate(dateString) {
    if (!dateString) return '';
    // Obtener sólo la parte YYYY-MM-DD
    const datePart = dateString.split('T')[0];
    const [year, month, day] = datePart.split('-');
    return `${day}/${month}/${year}`;
}

function slugify(text) {
    return text.toString().toLowerCase()
        .replace(/\s+/g, '-')           // Reemplazar espacios por -
        .replace(/[^\w\-]+/g, '')       // Eliminar caracteres no válidos
        .replace(/\-\-+/g, '-')         // Reemplazar múltiples -
        .replace(/^-+/, '')             // Recortar - del inicio
        .replace(/-+$/, '');            // Recortar - del final
}

function getStatusIcon(status) {
    switch (status) {
        case 'Pendiente': return '<i class="fa-regular fa-clock"></i>';
        case 'En Progreso': return '<i class="fa-solid fa-spinner fa-spin-slow"></i>';
        case 'Completada': return '<i class="fa-solid fa-circle-check"></i>';
        default: return '';
    }
}

function escapeHTML(str) {
    if (!str) return '';
    return str.replace(/[&<>'"]/g, 
        tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag] || tag)
    );
}

// Generador de notificaciones premium (Toast)
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    let icon = 'fa-circle-info';
    if (type === 'success') icon = 'fa-circle-check';
    if (type === 'error') icon = 'fa-circle-exclamation';

    toast.innerHTML = `
        <i class="fa-solid ${icon}"></i>
        <div class="toast-content">${escapeHTML(message)}</div>
    `;

    notificationContainer.appendChild(toast);

    // Remover toast después de 4 segundos con una transición suave
    setTimeout(() => {
        toast.style.animation = 'slide-in 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) reverse forwards';
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 4000);
}
