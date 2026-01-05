"""
Sarva Gyaan Academy - Student Management System
Application Entry Point
"""
from app import create_app, db
from app.models import User, Student, Batch, Attendance, FeeStructure, FeeTransaction

app = create_app()

@app.shell_context_processor
def make_shell_context():
    """Make database models available in flask shell"""
    return {
        'db': db,
        'User': User,
        'Student': Student,
        'Batch': Batch,
        'Attendance': Attendance,
        'FeeStructure': FeeStructure,
        'FeeTransaction': FeeTransaction
    }

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
