import os
import psycopg2
from dotenv import load_dotenv

def create_health_check():
    # Load environment variables from .env
    load_dotenv()

    db_name = os.getenv('DB_NAME')
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT')

    if not all([db_name, db_user, db_password, db_host, db_port]):
        print("Error: Missing database credentials in .env file.")
        return

    try:
        # Connect to the Supabase database
        conn = psycopg2.connect(
            dbname=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port
        )
        conn.autocommit = True
        cur = conn.cursor()

        print(f"Connecting to {db_host}...")

        # Create the health_check table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS public.health_check (
                id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
                created_at timestamptz DEFAULT now(),
                ping_text text DEFAULT 'ping'
            );
        """)
        print("Table 'public.health_check' created or already exists.")

        # Insert an initial row
        cur.execute("INSERT INTO public.health_check (ping_text) VALUES ('initial_setup');")
        print("Initial ping row inserted.")

        # Ensure the table is visible to the API
        # By default, public tables are visible. 
        # We might need to grant usage on the schema if it's not already there (usually is for 'public')
        cur.execute("GRANT ALL ON TABLE public.health_check TO postgres;")
        cur.execute("GRANT ALL ON TABLE public.health_check TO anon;")
        cur.execute("GRANT ALL ON TABLE public.health_check TO authenticated;")
        cur.execute("GRANT ALL ON TABLE public.health_check TO service_role;")
        
        # Disable RLS for this specific table to make health checks easy
        cur.execute("ALTER TABLE public.health_check DISABLE ROW LEVEL SECURITY;")
        print("RLS disabled for 'health_check' table to allow easy health check pings.")

        cur.close()
        conn.close()
        print("Database setup complete.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    create_health_check()
