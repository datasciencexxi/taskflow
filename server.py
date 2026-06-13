import os
from flask import Flask, request, jsonify, send_from_directory
import db

app = Flask(__name__, static_folder='static')

# Asegurar que la base de datos esté inicializada al arrancar
try:
    db.init_db()
except Exception as e:
    print(f"Error inicializando la base de datos: {e}")

@app.route('/')
def index():
    """Sirve la página principal index.html."""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/users', methods=['GET'])
def get_users():
    """Obtiene la lista de usuarios."""
    try:
        users = db.get_users()
        return jsonify(users)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """Obtiene todas las tareas."""
    try:
        tasks = db.get_tasks()
        return jsonify(tasks)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks', methods=['POST'])
def create_task():
    """Crea una nueva tarea. Asigna como creador al usuario enviado en la cabecera X-User-Id."""
    user_id_header = request.headers.get('X-User-Id')
    if not user_id_header:
        return jsonify({"error": "Cabecera X-User-Id ausente. Debe iniciar sesión."}), 401
    
    try:
        creador_id = int(user_id_header)
    except ValueError:
        return jsonify({"error": "X-User-Id inválido."}), 400

    data = request.json or {}
    titulo = data.get('titulo')
    descripcion = data.get('descripcion', '')
    responsable_id = data.get('responsable_id')
    fecha_vencimiento = data.get('fecha_vencimiento')

    # Validaciones
    if not titulo or not titulo.strip():
        return jsonify({"error": "El título de la tarea es obligatorio."}), 400
    if not responsable_id:
        return jsonify({"error": "El responsable de la tarea es obligatorio."}), 400
    if not fecha_vencimiento:
        return jsonify({"error": "La fecha de vencimiento es obligatoria."}), 400

    try:
        # Verificar que el creador y el responsable existan
        users = {u['id'] for u in db.get_users()}
        if creador_id not in users:
            return jsonify({"error": "El usuario creador no existe."}), 400
        if int(responsable_id) not in users:
            return jsonify({"error": "El usuario responsable no existe."}), 400

        new_task = db.create_task(
            titulo=titulo.strip(),
            descripcion=descripcion.strip(),
            creador_id=creador_id,
            responsable_id=int(responsable_id),
            fecha_vencimiento=fecha_vencimiento
        )
        return jsonify(new_task), 21

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks/<int:task_id>/status', methods=['PUT'])
def update_task_status(task_id):
    """Actualiza el estado de una tarea. Valida que el usuario sea el creador."""
    user_id_header = request.headers.get('X-User-Id')
    if not user_id_header:
        return jsonify({"error": "Cabecera X-User-Id ausente."}), 401
    
    try:
        current_user_id = int(user_id_header)
    except ValueError:
        return jsonify({"error": "X-User-Id inválido."}), 400

    data = request.json or {}
    nuevo_estado = data.get('estado')

    if nuevo_estado not in ['Pendiente', 'En Progreso', 'Completada']:
        return jsonify({"error": "Estado inválido. Debe ser 'Pendiente', 'En Progreso' o 'Completada'."}), 400

    try:
        # 1. Obtener la tarea
        task = db.get_task(task_id)
        if not task:
            return jsonify({"error": f"No se encontró la tarea con ID {task_id}."}), 404

        # 2. Verificar permisos: sólo el creador puede modificar el estado
        if task['creador_id'] != current_user_id:
            return jsonify({
                "error": "Acceso denegado: Solo el creador de la tarea tiene permisos para cambiar su estado."
            }), 403

        # 3. Actualizar
        updated = db.update_task_status(task_id, nuevo_estado)
        return jsonify(updated)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Ejecutar en el puerto 5000
    app.run(host='0.0.0.0', port=5000, debug=True)
