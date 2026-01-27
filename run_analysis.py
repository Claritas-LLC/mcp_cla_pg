import os
import sys
import json
import time
import subprocess
import traceback

# Add current directory to path
sys.path.append(os.getcwd())

# Configure Environment for the Server (MUST BE DONE BEFORE IMPORTING server)
# We use stdio transport to bypass HTTP auth checks for local script execution
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:55432/mcp_test"
os.environ["MCP_ALLOW_WRITE"] = "false" 
os.environ["MCP_LOG_LEVEL"] = "WARNING"
os.environ["MCP_TRANSPORT"] = "stdio" 

# Import the server module
try:
    import server
except ImportError:
    print("Error: Could not import server.py. Make sure you are in the project root.")
    sys.exit(1)

def invoke_tool(tool_obj, **kwargs):
    """Helper to invoke a FastMCP tool object"""
    if callable(tool_obj):
        return tool_obj(**kwargs)
    
    # Check for common underlying function attributes
    for attr in ("fn", "func", "function", "_fn"):
        inner = getattr(tool_obj, attr, None)
        if callable(inner):
            return inner(**kwargs)
            
    raise TypeError(f"Could not find callable for tool {tool_obj}")

def main():
    print("Starting PostgreSQL 9.6 container...")
    try:
        subprocess.run(["docker", "compose", "-f", "docker-compose.yml", "up", "-d", "postgres96"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to start docker containers: {e}")
        sys.exit(1)
    
    # Wait for DB to be ready using a real connection check
    print("Waiting for database to be ready...")
    
    from psycopg_pool import ConnectionPool
    from psycopg.rows import dict_row

    max_retries = 10
    retry_delay = 2
    
    # Use a temporary pool to check connectivity before letting the server module take over
    check_pool = ConnectionPool(os.environ["DATABASE_URL"], kwargs={"row_factory": dict_row})
    
    try:
        for i in range(max_retries):
            try:
                with check_pool.connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1")
                        print("Database is ready!")
                        break
            except Exception:
                if i < max_retries - 1:
                    print(f"Database not ready, retrying in {retry_delay}s... ({i+1}/{max_retries})")
                    time.sleep(retry_delay)
                else:
                    print("Error: Database failed to become ready after multiple attempts.")
                    check_pool.close()
                    sys.exit(1)
    finally:
        check_pool.close()

    try:
        # Check if we can connect to the DB
        
        # We don't want to mess with server.pool if it's already working, 
        # but since we imported server after setting env vars, it should be fine.
        
        print("\nExecuting db_pg96_database_security_performance_metrics(profile='oltp')...\n")
        
        result = invoke_tool(server.db_pg96_database_security_performance_metrics, profile="oltp")
        
        print(json.dumps(result, indent=2, default=str))

    except Exception as e:
        print(f"Error running tool: {e}")
        traceback.print_exc()
    finally:
        print("\nStopping containers...")
        subprocess.run(["docker", "compose", "-f", "docker-compose.yml", "down", "-v"], check=False)

if __name__ == "__main__":
    main()
