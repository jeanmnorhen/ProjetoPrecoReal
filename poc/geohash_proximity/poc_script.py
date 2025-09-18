import psycopg2
import time

# --- 1. Configuração da PoC ---

# Configurações de conexão com o banco de dados PostGIS (do docker-compose.yml)
db_params = {
    "host": "localhost",
    "port": "5432",
    "database": "precoreal_geo",
    "user": "user",
    "password": "password"
}

# Ponto central simulando a localização do usuário (latitude, longitude)
user_location = (-23.5505, -46.6333)  # São Paulo Centro

# Raio da busca em metros
search_radius_meters = 5000  # 5 km

# Lojas simuladas com suas coordenadas (latitude, longitude)
stores_data = [
    {"name": "Loja A (vizinho próximo)", "coords": (-23.551, -46.634)},
    {"name": "Loja B (no mesmo geohash)", "coords": (-23.550, -46.633)},
    {"name": "Loja C (vizinho mais distante)", "coords": (-23.545, -46.639)},
    {"name": "Loja D (bem distante)", "coords": (-23.682, -46.875)}, # Itapecerica da Serra
    {"name": "Loja E (outro vizinho)", "coords": (-23.555, -46.630)},
    {"name": "Loja F (longe)", "coords": (-22.906, -43.172)}, # Rio de Janeiro
    {"name": "Loja G (próximo)", "coords": (-23.552, -46.635)},
    {"name": "Loja H (próximo)", "coords": (-23.549, -46.632)},
    {"name": "Loja I (próximo)", "coords": (-23.553, -46.631)},
    {"name": "Loja J (distante)", "coords": (-23.500, -46.500)},
]

TABLE_NAME = "stores_geospatial_poc"

# --- 2. Funções de Interação com PostGIS ---

def get_db_connection():
    """Estabelece e retorna uma conexão com o banco de dados."""
    return psycopg2.connect(**db_params)

def setup_database(conn):
    """Cria a extensão PostGIS e a tabela de lojas."""
    print("\n--- Configurando o Banco de Dados ---")
    with conn.cursor() as cur:
        print("Ativando a extensão PostGIS (CREATE EXTENSION IF NOT EXISTS postgis)...")
        cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        
        print(f"Limpando tabela antiga (DROP TABLE IF EXISTS {TABLE_NAME})...")
        cur.execute(f"DROP TABLE IF EXISTS {TABLE_NAME};")

        print(f"Criando a tabela '{TABLE_NAME}' com coluna de GEOGRAPHY...")
        cur.execute(f"""
            CREATE TABLE {TABLE_NAME} (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255),
                location GEOGRAPHY(Point, 4326) -- 4326 é o SRID para WGS 84 (lat/lon)
            );
        """)
        
        print("Criando índice espacial (GIST) na coluna 'location' para otimizar consultas...")
        cur.execute(f"CREATE INDEX {TABLE_NAME}_location_idx ON {TABLE_NAME} USING GIST (location);")
        
    conn.commit()
    print("Configuração do banco de dados concluída.")

def add_stores_to_db(conn, stores):
    """Insere as lojas de teste no banco de dados."""
    print(f"\nAdicionando {len(stores)} lojas à tabela '{TABLE_NAME}'...")
    with conn.cursor() as cur:
        for store in stores:
            # A sintaxe para um ponto geográfico é 'SRID=4326;POINT(longitude latitude)'
            lon, lat = store["coords"][1], store["coords"][0]
            cur.execute(
                f"INSERT INTO {TABLE_NAME} (name, location) VALUES (%s, ST_SetSRID(ST_MakePoint(%s, %s), 4326));",
                (store["name"], lon, lat)
            )
    conn.commit()
    print("Lojas adicionadas.")

def query_proximity_postgis(conn, user_lat, user_lon, radius_m):
    """Consulta o PostGIS por lojas dentro de um raio e calcula a distância."""
    print(f"\nConsultando PostGIS por lojas em um raio de {radius_m / 1000:.1f} km...")
    
    results = []
    query_start_time = time.time()
    
    with conn.cursor() as cur:
        user_lon, user_lat = user_lon, user_lat
        user_point = f"SRID=4326;POINT({user_lon} {user_lat})"
        
        # ST_DWithin usa o índice espacial e é muito eficiente para encontrar geometrias dentro de uma distância.
        # ST_Distance calcula a distância real em metros para os candidatos encontrados.
        cur.execute(f"""
            SELECT
                name,
                ST_Distance(location, %s::geography) / 1000 AS distance_km
            FROM
                {TABLE_NAME}
            WHERE
                ST_DWithin(location, %s::geography, %s)
            ORDER BY
                distance_km;
        """, (user_point, user_point, radius_m))
        
        rows = cur.fetchall()
        for row in rows:
            results.append({"name": row[0], "distance_km": row[1]})
            
    query_end_time = time.time()
    query_time = query_end_time - query_start_time
    print(f"Consulta espacial no PostGIS levou: {query_time:.4f} segundos. Encontrados {len(results)} resultados.")
    
    return results, query_time

def cleanup_database(conn):
    """Remove a tabela de lojas criada pela PoC."""
    print(f"\n--- Limpando o Banco de Dados ---")
    with conn.cursor() as cur:
        print(f"Removendo a tabela '{TABLE_NAME}'...")
        cur.execute(f"DROP TABLE IF EXISTS {TABLE_NAME};")
    conn.commit()
    print("Limpeza concluída.")

# --- 3. Execução da PoC ---
if __name__ == "__main__":
    conn = None
    try:
        conn = get_db_connection()
        
        setup_database(conn)
        add_stores_to_db(conn, stores_data)

        results, query_time = query_proximity_postgis(
            conn, user_location[0], user_location[1], search_radius_meters
        )

        print("\n--- Resultados Finais (Lojas Próximas) ---")
        if results:
            for store in results:
                print(f"> {store['name']} - {store['distance_km']:.2f} km")
        else:
            print("Nenhuma loja encontrada dentro do raio de busca.")

        print(f"\nTempo total da consulta PostGIS: {query_time:.4f} segundos.")
        print("\n--- Conclusão da PoC ---")
        print("1. PostGIS com a função ST_DWithin é extremamente eficiente para consultas de proximidade.")
        print("2. A consulta é feita em uma única etapa, sem necessidade de refinamento manual.")
        print("3. O uso de um índice espacial (GIST) é fundamental para a performance em grandes volumes de dados.")
        print("4. Esta abordagem é mais robusta e escalável do que a busca por Geohash no Firestore para casos de uso geoespaciais complexos.")

    except psycopg2.Error as e:
        print(f"\nOcorreu um erro com o PostgreSQL: {e}")
    
    finally:
        if conn:
            # cleanup_database(conn) # Comentado para permitir a inspeção manual dos dados
            conn.close()
            print("\nConexão com o banco de dados fechada.")
