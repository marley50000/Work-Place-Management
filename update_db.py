from wms import create_app, db
from sqlalchemy import text
import os

app = create_app()

with app.app_context():
    # Get database path
    db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
    
    # Backup the database first
    if os.path.exists(db_path):
        import shutil
        shutil.copy2(db_path, db_path + '.backup')
        print(f"Database backed up to {db_path}.backup")
    
    # More aggressive approach - recreate the message table
    try:
        # Save existing messages if possible
        try:
            db.session.execute(text("CREATE TABLE message_backup AS SELECT * FROM message"))
            print("Backed up existing messages")
        except Exception as e:
            print(f"Could not backup messages: {e}")
        
        # Drop and recreate the table
        db.session.execute(text("DROP TABLE IF EXISTS message"))
        db.session.execute(text("""
            CREATE TABLE message (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                date_sent DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                sender_id INTEGER NOT NULL,
                recipient_id INTEGER NOT NULL,
                read BOOLEAN NOT NULL DEFAULT 0,
                FOREIGN KEY (sender_id) REFERENCES user (id),
                FOREIGN KEY (recipient_id) REFERENCES user (id)
            )
        """))
        print("Recreated message table with all required columns")
        
        # Restore data if backup was successful
        try:
            db.session.execute(text("""
                INSERT INTO message (id, content, sender_id, recipient_id)
                SELECT id, content, sender_id, recipient_id FROM message_backup
            """))
            print("Restored message data")
        except Exception as e:
            print(f"Could not restore message data: {e}")
        
        # Drop backup table
        try:
            db.session.execute(text("DROP TABLE message_backup"))
        except:
            pass
            
    except Exception as e:
        print(f"Error recreating message table: {e}")
    
    db.session.commit()
    print("Database update completed")