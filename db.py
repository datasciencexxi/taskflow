import os
import time
import subprocess
import psycopg2
from psycopg2.extras import RealDictCursor

# Configuración de rutas de PostgreSQL portátil
PG_DIR = r"D:\IA\Tareas\pgsql"
PG_CTL = os.path.join(PG_DIR, "pgsql", "bin", "pg_ctl.exe")
DATA_DIR = os.path.join(PG_DIR, "data")
LOG_FILE = os.path.join(PG_DIR, "pgsql_log.txt")

def start_postgres_server():
    """Inicia el servidor PostgreSQL si no está corriendo."""
    if not os.path.exists(PG_CTL):
        raise RuntimeError("No se encontró el ejecutable pg_ctl.exe en la ruta especificada.")
    
    # Verificar estado
    res = subprocess.run([PG_CTL, "status", "-D", DATA_DIR], capture_output=True, text=True)
    if res.returncode != 0:
        print("Iniciando el servidor PostgreSQL local...")
        # Iniciar servidor
        subprocess.run([PG_CTL, "start", "-D", DATA_DIR, "-l", LOG_FILE])
        # Esperar a que esté listo para aceptar conexiones
        for _ in range(10):
            try:
                conn = psycopg2.connect(
                    host="127.0.0.1",
                    port=5432,
                    user="postgres",
                    database="postgres",
                    connect_timeout=1
                )
                conn.close()
                print("PostgreSQL está listo para aceptar conexiones.")
                return
            except psycopg2.OperationalError:
                time.sleep(1)
        raise RuntimeError("El servidor PostgreSQL no se inició en el tiempo esperado.")
    else:
        print("El servidor PostgreSQL ya está corriendo.")

def init_db():
    """Inicializa la base de datos y ejecuta el esquema si es necesario."""
    db_url = os.environ.get('DATABASE_URL')
    
    if db_url:
        print("Detectado DATABASE_URL. Conectando a la base de datos de producción...")
        conn_db = psycopg2.connect(db_url)
        db_created = False
    else:
        start_postgres_server()
        
        # 1. Crear base de datos 'tareas_db' si no existe
        conn = psycopg2.connect(
            host="127.0.0.1",
            port=5432,
            user="postgres",
            database="postgres"
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'tareas_db'")
        exists = cursor.fetchone()
        if not exists:
            print("Creando base de datos 'tareas_db'...")
            cursor.execute("CREATE DATABASE tareas_db")
            db_created = True
        else:
            db_created = False
            
        cursor.close()
        conn.close()
        
        conn_db = psycopg2.connect(
            host="127.0.0.1",
            port=5432,
            user="postgres",
            database="tareas_db"
        )

    # 2. Si se acaba de crear la base de datos o si las tablas no existen, correr schema.sql
    cursor_db = conn_db.cursor()
    
    # Verificar si la tabla 'tareas' existe
    cursor_db.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'tareas'
        );
    """)
    tables_exist = cursor_db.fetchone()[0]
    
    if db_created or not tables_exist:
        print("Ejecutando schema.sql para inicializar tablas...")
        schema_path = "schema.sql"
        if not os.path.exists(schema_path):
            schema_path = r"D:\IA\Tareas\schema.sql"
            
        if os.path.exists(schema_path):
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            cursor_db.execute(schema_sql)
            conn_db.commit()
            print("Tablas y datos semilla cargados correctamente.")
        else:
            print("Advertencia: No se encontró schema.sql")
            
    cursor_db.close()
    conn_db.close()

def get_db_connection():
    """Retorna una conexión a la base de datos."""
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        return psycopg2.connect(db_url)
    return psycopg2.connect(
        host="127.0.0.1",
        port=5432,
        user="postgres",
        database="tareas_db"
    )

def get_users():
    """Obtiene la lista de todos los usuarios."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT id, username, nombre_completo FROM usuarios ORDER BY nombre_completo")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return users

def get_tasks():
    """Obtiene todas las tareas con los nombres de su creador y responsable."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    query = """
        SELECT 
            t.id,
            t.titulo,
            t.descripcion,
            t.creador_id,
            uc.nombre_completo as creador_nombre,
            uc.username as creador_username,
            t.responsable_id,
            ur.nombre_completo as responsable_nombre,
            ur.username as responsable_username,
            t.fecha_generacion,
            t.fecha_vencimiento,
            t.estado
        FROM tareas t
        JOIN usuarios uc ON t.creador_id = uc.id
        JOIN usuarios ur ON t.responsable_id = ur.id
        ORDER BY t.fecha_vencimiento ASC, t.id DESC
    """
    cursor.execute(query)
    tasks = cursor.fetchall()
    
    # Formatear fechas para JSON
    for task in tasks:
        if task['fecha_generacion']:
            task['fecha_generacion'] = task['fecha_generacion'].isoformat()
        if task['fecha_vencimiento']:
            task['fecha_vencimiento'] = task['fecha_vencimiento'].isoformat()
            
    cursor.close()
    conn.close()
    return tasks

def get_task(task_id):
    """Obtiene una sola tarea por su ID."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    query = "SELECT id, titulo, descripcion, creador_id, responsable_id, estado FROM tareas WHERE id = %s"
    cursor.execute(query, (task_id,))
    task = cursor.fetchone()
    cursor.close()
    conn.close()
    return task

def create_task(titulo, descripcion, creador_id, responsable_id, fecha_vencimiento):
    """Crea una nueva tarea."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    query = """
        INSERT INTO tareas (titulo, descripcion, creador_id, responsable_id, fecha_vencimiento, estado)
        VALUES (%s, %s, %s, %s, %s, 'Pendiente')
        RETURNING id, titulo, descripcion, creador_id, responsable_id, fecha_generacion, fecha_vencimiento, estado
    """
    cursor.execute(query, (titulo, descripcion, creador_id, responsable_id, fecha_vencimiento))
    new_task = cursor.fetchone()
    conn.commit()
    
    if new_task['fecha_generacion']:
        new_task['fecha_generacion'] = new_task['fecha_generacion'].isoformat()
    if new_task['fecha_vencimiento']:
        new_task['fecha_vencimiento'] = new_task['fecha_vencimiento'].isoformat()
        
    cursor.close()
    conn.close()
    return new_task

def update_task_status(task_id, new_status):
    """Actualiza el estado de una tarea."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    query = "UPDATE tareas SET estado = %s WHERE id = %s RETURNING id, estado"
    cursor.execute(query, (new_status, task_id))
    updated = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()
    return updated
