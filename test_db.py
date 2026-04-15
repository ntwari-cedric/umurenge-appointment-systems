import psycopg2

# Your encoded password URL
DATABASE_URL = "postgresql://postgres:Cedric%40Ntwari@db.fpmqugcjvhidrjdgiijz.supabase.co:5432/postgres"

try:
    print("Attempting to connect to Supabase...")
    conn = psycopg2.connect(DATABASE_URL)
    print("✅ SUCCESS! Connected to Supabase PostgreSQL!")
    
    # Test if we can query
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    print(f"PostgreSQL version: {version[0]}")
    
    cursor.close()
    conn.close()
    print("✅ Connection test completed!")
    
except Exception as e:
    print(f"❌ Connection failed: {e}")
    print("\nTroubleshooting tips:")
    print("1. Check if your Supabase project is active (not paused)")
    print("2. Verify the password is correct (remember @ was encoded to %40)")
    print("3. Make sure you're connected to the internet")