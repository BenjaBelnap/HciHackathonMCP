"""
Oracle Database Query Service
Queries Oracle database object information using DESCRIBE
"""
import os
import oracledb
from dotenv import load_dotenv
from typing import Optional


class OracleQueryService:
    """Service to query Oracle database object information"""
    
    def __init__(self):
        """Initialize the Oracle connection using environment variables"""
        load_dotenv()
        
        self.username = os.getenv('ORACLE_USERNAME')
        self.password = os.getenv('ORACLE_PASSWORD')
        self.host = os.getenv('ORACLE_HOST')
        self.port = os.getenv('ORACLE_PORT', '1521')
        self.service_name = os.getenv('ORACLE_SERVICE_NAME')
        
        self._validate_config()
        self.connection = None
    
    def _validate_config(self):
        """Validate that all required configuration is present"""
        required_vars = ['ORACLE_USERNAME', 'ORACLE_PASSWORD', 'ORACLE_HOST', 'ORACLE_SERVICE_NAME']
        missing = [var for var in required_vars if not os.getenv(var)]
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    
    def connect(self):
        """Establish connection to Oracle database"""
        try:
            dsn = oracledb.makedsn(
                self.host,
                self.port,
                service_name=self.service_name
            )
            
            self.connection = oracledb.connect(
                user=self.username,
                password=self.password,
                dsn=dsn
            )
            print(f"Successfully connected to Oracle database at {self.host}")
            return True
        except Exception as e:
            print(f"Error connecting to Oracle database: {e}")
            raise
    
    def disconnect(self):
        """Close the database connection"""
        if self.connection:
            self.connection.close()
            print("Database connection closed")
    
    def search_objects(self, pattern: str, object_type: Optional[str] = None, owner: Optional[str] = None) -> list:
        """
        Search for database objects matching a pattern
        
        Args:
            pattern: Search pattern (e.g., 'patient' will find objects like '%PATIENT%')
            object_type: Optional filter by object type (TABLE, VIEW, etc.)
            owner: Optional schema owner filter
            
        Returns:
            List of dictionaries with object information
        """
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            
            # Build query to search for objects
            query = """
                SELECT DISTINCT
                    owner,
                    object_name,
                    object_type
                FROM all_objects
                WHERE object_name LIKE :pattern
            """
            
            # Add wildcards to pattern
            search_pattern = f"%{pattern.upper()}%"
            params = {'pattern': search_pattern}
            
            if object_type:
                query += " AND object_type = :object_type"
                params['object_type'] = object_type.upper()
            
            if owner:
                query += " AND owner = :owner"
                params['owner'] = owner.upper()
            
            query += " ORDER BY owner, object_type, object_name"
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            # Format results as list of dictionaries
            objects = [
                {
                    'owner': row[0],
                    'object_name': row[1],
                    'object_type': row[2]
                }
                for row in results
            ]
            
            cursor.close()
            return objects
            
        except Exception as e:
            raise Exception(f"Error searching for objects: {e}")
    
    def describe_object(self, object_name: str, owner: Optional[str] = None) -> str:
        """
        Describe an Oracle database object (table, view, etc.)
        Returns a formatted string similar to SQL*Plus DESCRIBE output
        
        Args:
            object_name: Name of the database object to describe (can be schema-qualified like SCHEMA.TABLE)
            owner: Optional schema owner (defaults to current user)
            
        Returns:
            Formatted string with DESCRIBE output
        """
        # Parse schema-qualified names (e.g., "SCHEMA.TABLE")
        if '.' in object_name and owner is None:
            parts = object_name.split('.', 1)  # Split on first dot only
            owner = parts[0]
            object_name = parts[1]
        
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            
            # Query to get column information (equivalent to DESCRIBE)
            query = """
                SELECT 
                    column_name,
                    nullable,
                    data_type,
                    data_length,
                    data_precision,
                    data_scale
                FROM all_tab_columns
                WHERE table_name = :object_name
            """
            
            params = {'object_name': object_name.upper()}
            
            if owner:
                query += " AND owner = :owner"
                params['owner'] = owner.upper()
            
            query += " ORDER BY column_id"
            
            cursor.execute(query, params)
            columns = cursor.fetchall()
            
            if not columns:
                return f"Object '{object_name}' not found"
            
            # Format output similar to DESCRIBE command
            output = []
            output.append("Name          Null? Type         ")
            output.append("------------- ----- ------------ ")
            
            for col in columns:
                col_name = col[0]
                nullable = "" if col[1] == 'Y' else "NOT NULL"
                data_type = col[2]
                data_length = col[3]
                data_precision = col[4]
                data_scale = col[5]
                
                # Format type string
                if data_type in ['VARCHAR2', 'CHAR', 'NVARCHAR2', 'NCHAR', 'RAW']:
                    type_str = f"{data_type}({data_length})"
                elif data_type == 'NUMBER':
                    if data_precision is not None:
                        if data_scale is not None and data_scale > 0:
                            type_str = f"{data_type}({data_precision},{data_scale})"
                        else:
                            type_str = f"{data_type}({data_precision})"
                    else:
                        type_str = data_type
                else:
                    type_str = data_type
                
                # Format line with proper spacing
                line = f"{col_name:<13} {nullable:<5} {type_str}"
                output.append(line)
            
            cursor.close()
            return "\n".join(output)
            
        except Exception as e:
            return f"Error describing object '{object_name}': {e}"
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


def main():
    """Example usage of the OracleQueryService"""
    service = OracleQueryService()
    
    try:
        service.connect()
        
        # Describe a table
        object_name = input("Enter object name to describe: ")
        result = service.describe_object(object_name)
        
        print("\n" + result)
            
    finally:
        service.disconnect()


if __name__ == "__main__":
    main()

    main()
