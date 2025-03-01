from pymongo import MongoClient
from dotenv import load_dotenv
import os
import sys

# Load environment variables
load_dotenv()

class DatabaseConnection:
    _instance = None
    _client = None
    _db = None

    @classmethod
    def connect(cls):
        try:
            # Retrieve MongoDB connection string from environment variable
            mongo_uri = os.getenv('MONGO_URI')
            
            if not mongo_uri:
                raise ValueError("MongoDB URI not found in environment variables")
            
            # Create MongoDB client with updated parameters
            # In newer PyMongo versions, SSL options should be in the connection string
            if '?' in mongo_uri:
                mongo_uri += '&tlsInsecure=true'
            else:
                mongo_uri += '?tlsInsecure=true'
                
            cls._client = MongoClient(
                mongo_uri,
                connectTimeoutMS=30000,
                socketTimeoutMS=30000
            )
            
            # Verify connection
            cls._client.admin.command('ismaster')
            print("Successfully connected to MongoDB")
            
            # Set database
            cls._db = cls._client['college_project']
            
            return cls._db
        
        except Exception as e:
            print(f"Critical Error connecting to MongoDB: {e}")
            print("Exiting application due to database connection failure")
            sys.exit(1)  # Exit the application if database connection fails

    @classmethod
    def get_database(cls):
        """
        Get the database instance
        """
        if cls._db is None:
            cls._db = cls.connect()
        return cls._db

    @classmethod
    def get_collection(cls, collection_name):
        """
        Get a specific collection from the database
        """
        db = cls.get_database()
        return db[collection_name]

# Ensure connection is established when the module is imported
db_connection = DatabaseConnection.connect()