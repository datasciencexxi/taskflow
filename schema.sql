-- Esquema de la base de datos para Gestión de Tareas

-- Eliminar tablas si existen (para reinicio limpio)
DROP TABLE IF EXISTS tareas CASCADE;
DROP TABLE IF EXISTS usuarios CASCADE;

-- Tabla de Usuarios
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    nombre_completo VARCHAR(100) NOT NULL
);

-- Tabla de Tareas
CREATE TABLE tareas (
    id SERIAL PRIMARY KEY,
    titulo VARCHAR(255) NOT NULL,
    descripcion TEXT,
    creador_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    responsable_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    fecha_generacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_vencimiento DATE NOT NULL,
    estado VARCHAR(50) NOT NULL DEFAULT 'Pendiente' CHECK (estado IN ('Pendiente', 'En Progreso', 'Completada'))
);

-- Insertar usuarios iniciales para pruebas
INSERT INTO usuarios (username, nombre_completo) VALUES 
('alice', 'Alice Smith'),
('bob', 'Bob Jones'),
('charlie', 'Charlie Brown');

-- Insertar algunas tareas de ejemplo
INSERT INTO tareas (titulo, descripcion, creador_id, responsable_id, fecha_generacion, fecha_vencimiento, estado) VALUES
('Diseñar base de datos', 'Crear el esquema de PostgreSQL y poblar con datos de prueba.', 1, 2, CURRENT_TIMESTAMP, CURRENT_DATE + INTERVAL '2 days', 'En Progreso'),
('Implementar API REST', 'Desarrollar el backend en Flask con los endpoints necesarios.', 2, 1, CURRENT_TIMESTAMP, CURRENT_DATE + INTERVAL '5 days', 'Pendiente'),
('Maquetar Frontend', 'Crear la interfaz de usuario con HTML y Vanilla CSS.', 1, 3, CURRENT_TIMESTAMP, CURRENT_DATE + INTERVAL '3 days', 'Pendiente');
