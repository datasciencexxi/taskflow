import unittest
import json
import os
import psycopg2

# Importar el servidor Flask y la base de datos
import server
import db

class TaskFlowTestCase(unittest.TestCase):
    def setUp(self):
        # Configurar la aplicación para pruebas
        server.app.config['TESTING'] = True
        self.app = server.app.test_client()
        
        # Asegurarse de que la base de datos esté inicializada
        db.init_db()
        
        # Limpiar y repoblar las tablas para tener un estado predecible en cada test
        conn = db.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("TRUNCATE TABLE tareas RESTART IDENTITY CASCADE;")
        cursor.execute("TRUNCATE TABLE usuarios RESTART IDENTITY CASCADE;")
        
        # Insertar datos de prueba fijos
        cursor.execute("INSERT INTO usuarios (username, nombre_completo) VALUES ('user1', 'Usuario A'), ('user2', 'Usuario B');")
        cursor.execute("""
            INSERT INTO tareas (titulo, descripcion, creador_id, responsable_id, fecha_vencimiento, estado)
            VALUES ('Tarea de Test 1', 'Descripcion 1', 1, 2, '2026-12-31', 'Pendiente');
        """)
        conn.commit()
        cursor.close()
        conn.close()

    def test_get_users(self):
        """Verifica que se obtengan los usuarios correctamente."""
        response = self.app.get('/api/users')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['username'], 'user1')
        self.assertEqual(data[1]['username'], 'user2')

    def test_get_tasks(self):
        """Verifica que se obtengan las tareas correctamente."""
        response = self.app.get('/api/tasks')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['titulo'], 'Tarea de Test 1')
        self.assertEqual(data[0]['creador_nombre'], 'Usuario A')
        self.assertEqual(data[0]['responsable_nombre'], 'Usuario B')

    def test_create_task_success(self):
        """Verifica que un usuario pueda crear una tarea."""
        task_payload = {
            "titulo": "Nueva Tarea Creada",
            "descripcion": "Descripción de la nueva tarea",
            "responsable_id": 2,
            "fecha_vencimiento": "2026-06-30"
        }
        response = self.app.post(
            '/api/tasks',
            headers={"X-User-Id": "1"},
            data=json.dumps(task_payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 21) # 21 es el código de éxito retornado por el server.py para creación
        data = json.loads(response.data)
        self.assertEqual(data['titulo'], 'Nueva Tarea Creada')
        self.assertEqual(data['creador_id'], 1)

    def test_create_task_missing_fields(self):
        """Verifica que falle la creación si faltan campos obligatorios."""
        task_payload = {
            "titulo": "",
            "responsable_id": 2,
            "fecha_vencimiento": "2026-06-30"
        }
        response = self.app.post(
            '/api/tasks',
            headers={"X-User-Id": "1"},
            data=json.dumps(task_payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)

    def test_update_status_by_creator_success(self):
        """Verifica que el creador de la tarea SÍ pueda cambiar su estado."""
        # La tarea 1 fue creada por user1 (id=1)
        status_payload = {"estado": "En Progreso"}
        response = self.app.put(
            '/api/tasks/1/status',
            headers={"X-User-Id": "1"},
            data=json.dumps(status_payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['estado'], 'En Progreso')

    def test_update_status_by_other_user_fails(self):
        """Verifica que si otro usuario (no creador) intenta cambiar el estado, se rechace con 403 Forbidden."""
        # La tarea 1 fue creada por user1 (id=1). user2 (id=2) intenta modificar el estado.
        status_payload = {"estado": "Completada"}
        response = self.app.put(
            '/api/tasks/1/status',
            headers={"X-User-Id": "2"},
            data=json.dumps(status_payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)
        data = json.loads(response.data)
        self.assertIn("Acceso denegado", data['error'])

if __name__ == '__main__':
    unittest.main()
