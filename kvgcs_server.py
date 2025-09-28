#!/usr/bin/env python3
"""
KV GC CRPF SILIGURI - FASTAPI TIMETABLE SERVER
Render.com Deployment Ready
Secure Authentication with Passcode: SCHSAKV3539
Always-On Server for Mobile App Integration
"""

from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
import sqlite3
import json
import os
import random
import string
import time
from datetime import datetime
import asyncio

# =============================================================================
# CONFIGURATION
# =============================================================================

SCHOOL_NAME = "KV GC CRPF SILIGURI"
SCHOOL_KEY = "KVGCS"
PASSCODE = "SCHSAKV3539"
API_VERSION = "v1"
DATABASE_FILE = "kvgcs_timetable.db"

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class TeacherCreate(BaseModel):
    teacher_name: str = Field(..., min_length=3, max_length=100)
    teacher_prefix: str = Field(..., min_length=2, max_length=10)
    subject_code: str = Field(default="", max_length=20)
    timetable: Dict[str, List[str]] = Field(default_factory=dict)

class TeacherUpdate(BaseModel):
    new_name: Optional[str] = Field(None, min_length=3, max_length=100)
    new_prefix: Optional[str] = Field(None, min_length=2, max_length=10)
    new_subject: Optional[str] = Field(None, max_length=20)
    new_timetable: Optional[Dict[str, List[str]]] = None

class ExcelGenerate(BaseModel):
    filename: Optional[str] = Field(default="timetable.csv", max_length=100)

class HealthResponse(BaseModel):
    status: str
    school: str
    school_key: str
    api_version: str
    server_time: str
    uptime_seconds: int
    environment: str

class StandardResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    timestamp: str

# =============================================================================
# TIMETABLE DATA
# =============================================================================

KVGCS_TIMETABLE_DATA = {
    'MR. PRIYABRATA PAUL (PP)': {
        'Monday': ['VIII MATHS', 'X MATHS', '', 'IX MATHS', '', 'VI MATHS', 'VII MATHS', ''],
        'Tuesday': ['VIII MATHS', 'X MATHS', 'IX MATHS', 'IX MATHS', '', 'VII MATHS', '', 'VI MATHS'],
        'Wednesday': ['VIII MATHS', 'X MATHS', '', 'IX MATHS', '', 'VI MATHS', 'VII MATHS', ''],
        'Thursday': ['VIII MATHS', 'X MATHS', 'X MATHS', 'IX MATHS', '', '', 'VII MATHS', 'VI MATHS'],
        'Friday': ['VIII MATHS', 'X MATHS', '', 'IX MATHS', '', 'VII MATHS', 'VI MATHS', ''],
        'Saturday': ['VIII MATHS', 'X MATHS', '', 'IX MATHS', '', 'VI MATHS', 'VII MATHS', 'CLA']
    },
    'MR. MAMUNOOR RAHMAN (MR)': {
        'Monday': ['X SST', '', 'IX SST', 'VI SST', '', '', 'IX SST', 'VII SST'],
        'Tuesday': ['X SST', 'VI SST', 'VIII SST', '', '', '', '', 'VII SST'],
        'Wednesday': ['X SST', '', 'VIII SST', 'VI SST', '', '', 'IX SST', 'VII SST'],
        'Thursday': ['X SST', 'IX SST', 'VIII SST', 'VI SST', '', '', 'X SST', 'VII SST'],
        'Friday': ['X SST', 'VI SST', 'VII SST', '', '', 'VIII SST', 'IX SST', ''],
        'Saturday': ['X SST', 'VI SST', 'VIII SST', '', '', 'VII SST', '', 'CLA']
    },
    'MS. TANUSREE BARMAN (TB)': {
        'Monday': ['VI - SC', 'VIII - SC', 'VII - SC', 'X - SC', '', 'IX - SC', '', ''],
        'Tuesday': ['VI - SC', '', 'VII - SC', 'X - SC', '', 'IX - SC', '', 'VIII - SC'],
        'Wednesday': ['VI - SC', 'VIII - SC', 'IX - SC', 'X - SC', '', 'IX - SC', 'X - SC', 'VII - SC'],
        'Thursday': ['VI - SC', 'VIII - SC', 'VII - SC', 'X - SC', '', 'IX - SC', '', ''],
        'Friday': ['VI - SC', 'VIII - SC', '', 'X - SC', '', 'IX - SC', 'VII - SC', ''],
        'Saturday': ['VI - SC', 'VIII - SC', 'VII - SC', 'X - SC', '', 'IX - SC', '', 'CLA']
    },
    'MR. MUKUND CHANDRA ROY (MCR)': {
        'Monday': ['VII - HINDI', 'IX - HINDI', 'X - HINDI', '', '', '', 'VI -HINDI', 'X HINDI'],
        'Tuesday': ['VII - HINDI', 'IX - HINDI', 'X - HINDI', 'VIII - HINDI', '', '', 'VI -HINDI', ''],
        'Wednesday': ['VII - HINDI', 'IX - HINDI', 'X - HINDI', 'VIII - HINDI', '', '', 'VI -HINDI', 'IX - HINDI'],
        'Thursday': ['VII - HINDI', '', 'IX - HINDI', 'VIII - HINDI', '', '', 'VI -HINDI', 'X - HINDI'],
        'Friday': ['VII - HINDI', 'IX - HINDI', 'X - HINDI', 'VIII - HINDI', '', '', '', ''],
        'Saturday': ['', 'IX - HINDI', 'X - HINDI', 'VIII - HINDI', '', '', 'VI -HINDI', 'CLA']
    },
    'MR. KRISHNA MINJ (KM)': {
        'Monday': ['', '', '', 'VIII - LIB', '', '', '', 'VI - LIB'],
        'Tuesday': ['', '', '', '', '', '', '', 'VII - LIB'],
        'Wednesday': ['', '', 'VI - LIB', '', '', 'VII - LIB', '', ''],
        'Thursday': ['', '', '', '', '', '', '', ''],
        'Friday': ['', '', 'IX - LIB', '', '', '', '', 'X - LIB'],
        'Saturday': ['', '', '', '', '', 'VIII - LIB', 'IX ACP', 'CLA']
    },
    'MRS. ANJU KUMARI SINGH (AKS)': {
        'Monday': ['IX - ENG', 'VII - ENG', '', '', '', 'X - ENG', 'VIII - ENG', 'VI - ENG'],
        'Tuesday': ['IX - ENG', '', 'VI - ENG', '', '', 'X - ENG', 'VIII - ENG', ''],
        'Wednesday': ['IX - ENG', 'VII - ENG', '', '', '', 'X - ENG', 'VIII - ENG', 'IX - ENG'],
        'Thursday': ['IX - ENG', 'VII - ENG', '', '', '', 'X - ENG', 'VIII - ENG', 'X - ENG'],
        'Friday': ['IX - ENG', 'VII - ENG', '', 'VI - ENG', '', 'X - ENG', '', 'VIII - ENG'],
        'Saturday': ['IX - ENG', 'VII - ENG', 'VI - ENG', '', '', 'X - ENG', '', 'CLA']
    },
    'MS. PUSPA KUMARI (PK)': {
        'Monday': ['', 'IX - SKT', 'X - SKT', '', '', 'VIII - SKT', '', 'X - SKT'],
        'Tuesday': ['', 'IX - SKT', 'X - SKT', '', '', 'VIII - SKT', '', 'VI - SKT'],
        'Wednesday': ['', 'IX - SKT', 'X - SKT', '', '', 'VIII - SKT', '', 'VI - SKT'],
        'Thursday': ['', 'VI - SKT', 'IX - SKT', '', '', 'VII - SKT', '', 'X - SKT'],
        'Friday': ['', 'IX - SKT', 'X - SKT', '', '', '', '', 'VII - SKT'],
        'Saturday': ['', 'IX - SKT', 'X - SKT', 'VII - SKT', '', '', '', 'CLA']
    },
    'MR. PROKASH ROY (PR)': {
        'Monday': ['', '', '', '', '', '', 'IX - GAMES', 'IX - GAMES'],
        'Tuesday': ['', '', '', '', '', '', 'X PHE', 'X - GAMES'],
        'Wednesday': ['', '', 'VII GAMES', 'VII GAMES', '', '', 'VIII - GAMES', 'VIII - GAMES'],
        'Thursday': ['', '', 'VI PHE', 'VII PHE', '', '', 'VIII PHE', 'VIII PHE'],
        'Friday': ['', '', 'VI PHE', 'VII PHE', '', '', 'X PHE', 'VI -GAMES'],
        'Saturday': ['', '', 'IX PHE', '', '', '', '', 'CLA']
    },
    'COMPUTER INSTRUCTOR': {
        'Monday': ['', '', 'VI - DL', 'D.L. (V-B)', '', 'VII - DL', '', ''],
        'Tuesday': ['', 'D.L. (III-B)', '', 'VII - DL', '', 'VI - DL', 'IX - AI', 'IX - AI'],
        'Wednesday': ['', '', 'D.L. (IV-B)', '', '', 'D.L. (III-A)', '', 'X - AI'],
        'Thursday': ['', 'D.L. (III-A)', '', 'D.L. (V-A)', '', 'VIII - DL', '', ''],
        'Friday': ['', 'D.L. (IV-B)', '', '', '', 'D.L. (IV-A)', '', 'VIII - DL'],
        'Saturday': ['', 'D.L. (III-B)', 'D.L. (IV-A)', 'GAME (II-A)', '', 'LIBRARY (III-A)', 'X - AI', 'CLA']
    },
    'MR. N.C. GUPTA (NCG)': {
        'Monday': ['', 'VI - AE', 'VIII - AE', '', '', '', 'X - AE', 'VII - AE'],
        'Tuesday': ['', 'VIII - AE', '', 'VI - AE', '', '', 'VII - AE', ''],
        'Wednesday': ['', '', '', '', '', '', '', ''],
        'Thursday': ['', '', '', '', '', 'VI - AE', '', 'IX - AE'],
        'Friday': ['', '', 'VIII - AE', '', '', '', 'IX - AE', 'X - AE'],
        'Saturday': ['VII - AE', '', '', 'VI - AE', '', '', 'VIII - AE', 'CLA']
    },
    'MR. UTTAM KUMAR (UK)': {
        'Monday': ['', '', '', 'VII - VE', '', '', 'VIII - VE', 'X - VE'],
        'Tuesday': ['', 'VII - VE', '', '', '', '', 'VIII - VE', ''],
        'Wednesday': ['', 'VI - VE', '', '', '', '', 'X - VE', ''],
        'Thursday': ['', '', '', '', '', '', 'IX - VE', 'VI - VE'],
        'Friday': ['', '', '', '', '', 'VI - VE', 'VIII - VE', 'VII - VE'],
        'Saturday': ['', '', '', '', '', '', '', 'CLA']
    },
    'MR. ARJUN DAS (AD)': {
        'Monday': ['', '', '', '', '', '', '', ''],
        'Tuesday': ['', '', '', '', '', '', '', ''],
        'Wednesday': ['', '', '', '', '', '', '', ''],
        'Thursday': ['', '', '', '', '', '', '', ''],
        'Friday': ['', '', '', '', '', '', '', ''],
        'Saturday': ['', '', '', '', '', '', '', '']
    },
}

# =============================================================================
# DATABASE MANAGEMENT
# =============================================================================

class KVGCSDatabase:
    def __init__(self, db_file=DATABASE_FILE):
        self.db_file = db_file
        self.init_database()
        self.setup_kvgcs_data()
    
    def init_database(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                school_key TEXT UNIQUE NOT NULL,
                school_name TEXT NOT NULL,
                passcode TEXT NOT NULL,
                api_version TEXT DEFAULT 'v1',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teachers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                school_key TEXT NOT NULL,
                teacher_key TEXT UNIQUE NOT NULL,
                teacher_name TEXT NOT NULL,
                teacher_prefix TEXT NOT NULL,
                subject_code TEXT DEFAULT '',
                timetable TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (school_key) REFERENCES schools (school_key)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                client_ip TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                method TEXT NOT NULL,
                passcode_used TEXT DEFAULT '',
                success BOOLEAN DEFAULT FALSE,
                response_size INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def setup_kvgcs_data(self):
        if self.get_school_data(SCHOOL_KEY):
            return
        
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO schools (school_key, school_name, passcode, api_version)
                VALUES (?, ?, ?, ?)
            ''', (SCHOOL_KEY, SCHOOL_NAME, PASSCODE, API_VERSION))
            
            for teacher_name, timetable in KVGCS_TIMETABLE_DATA.items():
                teacher_key = self.generate_teacher_key()
                teacher_prefix = self.detect_teacher_prefix(teacher_name)
                subject_code = self.extract_subject_code(teacher_name)
                timetable_json = json.dumps(timetable)
                
                cursor.execute('''
                    INSERT OR REPLACE INTO teachers 
                    (school_key, teacher_key, teacher_name, teacher_prefix, subject_code, timetable)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (SCHOOL_KEY, teacher_key, teacher_name, teacher_prefix, subject_code, timetable_json))
            
            conn.commit()
            print(f"✅ KV GC CRPF Siliguri data initialized successfully!")
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Error setting up KVGCS data: {e}")
            raise
        finally:
            conn.close()
    
    @staticmethod
    def generate_teacher_key():
        return ''.join(random.choices(string.digits + string.ascii_uppercase, k=4))
    
    @staticmethod
    def detect_teacher_prefix(name):
        name_upper = name.upper()
        if any(x in name_upper for x in ['MRS.', 'SMT.', 'MADAM']):
            return 'Mrs.'
        elif any(x in name_upper for x in ['MS.', 'MISS', 'KUMARI']):
            return 'Ms.'
        elif any(x in name_upper for x in ['DR.', 'DOCTOR']):
            return 'Dr.'
        elif any(x in name_upper for x in ['MR.', 'SHRI', 'SRI']):
            return 'Mr.'
        return 'Mr./Ms.'
    
    @staticmethod
    def extract_subject_code(teacher_name):
        name_upper = teacher_name.upper()
        if 'MATHS' in name_upper:
            return 'MATH'
        elif 'ENG' in name_upper:
            return 'ENG'
        elif 'SST' in name_upper:
            return 'SST'
        elif 'SC' in name_upper:
            return 'SCI'
        elif 'HINDI' in name_upper:
            return 'HIN'
        elif 'COMPUTER' in name_upper:
            return 'COMP'
        elif any(x in name_upper for x in ['GAMES', 'PHE']):
            return 'PE'
        elif 'SKT' in name_upper:
            return 'SKT'
        elif 'LIB' in name_upper:
            return 'LIB'
        elif 'AE' in name_upper:
            return 'AE'
        elif 'VE' in name_upper:
            return 'VE'
        return ''
    
    def authenticate(self, passcode):
        return passcode == PASSCODE
    
    def log_api_access(self, client_ip, endpoint, method, passcode_used, success, response_size=0):
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO api_logs (client_ip, endpoint, method, passcode_used, success, response_size)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (client_ip, endpoint, method, passcode_used, success, response_size))
            
            cursor.execute('''
                UPDATE schools SET last_accessed = CURRENT_TIMESTAMP, access_count = access_count + 1
                WHERE school_key = ?
            ''', (SCHOOL_KEY,))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"⚠️ Error logging API access: {e}")
    
    def get_school_data(self, school_key):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT school_name FROM schools WHERE school_key = ?', (school_key,))
            school_result = cursor.fetchone()
            
            if not school_result:
                return None
            
            cursor.execute('''
                SELECT teacher_key, teacher_name, teacher_prefix, subject_code, timetable 
                FROM teachers WHERE school_key = ?
            ''', (school_key,))
            teachers_result = cursor.fetchall()
            
            teachers_data = {}
            teacher_keys = {}
            teacher_prefixes = {}
            teacher_subjects = {}
            
            for teacher_key, teacher_name, teacher_prefix, subject_code, timetable_json in teachers_result:
                teachers_data[teacher_name] = json.loads(timetable_json)
                teacher_keys[teacher_name] = teacher_key
                teacher_prefixes[teacher_name] = teacher_prefix
                teacher_subjects[teacher_name] = subject_code
            
            return {
                'school_name': school_result[0],
                'school_key': school_key,
                'teachers': teachers_data,
                'teacher_keys': teacher_keys,
                'teacher_prefixes': teacher_prefixes,
                'teacher_subjects': teacher_subjects,
                'total_teachers': len(teachers_data),
                'api_version': API_VERSION
            }
            
        except Exception as e:
            print(f"❌ Error retrieving school data: {e}")
            return None
        finally:
            conn.close()
    
    def add_teacher(self, teacher_name, teacher_prefix, timetable, subject_code=''):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            teacher_key = self.generate_teacher_key()
            
            while True:
                cursor.execute('SELECT teacher_key FROM teachers WHERE teacher_key = ?', (teacher_key,))
                if not cursor.fetchone():
                    break
                teacher_key = self.generate_teacher_key()
            
            timetable_json = json.dumps(timetable)
            
            cursor.execute('''
                INSERT INTO teachers 
                (school_key, teacher_key, teacher_name, teacher_prefix, subject_code, timetable)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (SCHOOL_KEY, teacher_key, teacher_name, teacher_prefix, subject_code, timetable_json))
            
            conn.commit()
            return teacher_key
            
        except Exception as e:
            print(f"❌ Error adding teacher: {e}")
            return None
        finally:
            conn.close()
    
    def update_teacher(self, teacher_name, new_name=None, new_prefix=None, new_timetable=None, new_subject=None):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            updates = []
            params = []
            
            if new_name:
                updates.append('teacher_name = ?')
                params.append(new_name)
            if new_prefix:
                updates.append('teacher_prefix = ?')
                params.append(new_prefix)
            if new_timetable:
                updates.append('timetable = ?')
                params.append(json.dumps(new_timetable))
            if new_subject:
                updates.append('subject_code = ?')
                params.append(new_subject)
            
            if not updates:
                return False
            
            updates.append('updated_at = CURRENT_TIMESTAMP')
            params.extend([SCHOOL_KEY, teacher_name])
            
            query = f'''
                UPDATE teachers 
                SET {', '.join(updates)}
                WHERE school_key = ? AND teacher_name = ?
            '''
            
            cursor.execute(query, params)
            conn.commit()
            
            return cursor.rowcount > 0
            
        except Exception as e:
            print(f"❌ Error updating teacher: {e}")
            return False
        finally:
            conn.close()
    
    def remove_teacher(self, teacher_name):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT COUNT(*) FROM teachers WHERE school_key = ?', (SCHOOL_KEY,))
            count = cursor.fetchone()[0]
            
            if count <= 5:
                return False
            
            cursor.execute('DELETE FROM teachers WHERE school_key = ? AND teacher_name = ?',
                         (SCHOOL_KEY, teacher_name))
            conn.commit()
            
            return cursor.rowcount > 0
            
        except Exception as e:
            print(f"❌ Error removing teacher: {e}")
            return False
        finally:
            conn.close()

# =============================================================================
# FASTAPI APPLICATION
# =============================================================================

app = FastAPI(
    title="KV GC CRPF Siliguri Timetable API",
    description="High-Performance FastAPI Server for School Timetable Management - Render Deployment",
    version=API_VERSION,
    contact={
        "name": "KV GC CRPF Siliguri",
        "email": "contact@kvgcsiliguri.edu.in"
    }
)

# CORS middleware for mobile apps
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
db = KVGCSDatabase()
server_start_time = time.time()

# =============================================================================
# AUTHENTICATION DEPENDENCY
# =============================================================================

async def verify_passcode(
    request: Request,
    x_passcode: Optional[str] = Header(None, alias="X-Passcode")
):
    client_ip = request.client.host if request.client else "unknown"
    endpoint = str(request.url.path)
    method = request.method
    
    # Get passcode from header or query parameter
    passcode_used = x_passcode
    if not passcode_used:
        passcode_used = request.query_params.get('passcode')
    
    if not db.authenticate(passcode_used):
        db.log_api_access(client_ip, endpoint, method, passcode_used or '', False)
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Invalid or missing passcode"
        )
    
    # Log successful access
    db.log_api_access(client_ip, endpoint, method, passcode_used, True)
    return passcode_used

# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with server information"""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>KV GC CRPF Siliguri Timetable API</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
            .container {{ max-width: 800px; margin: auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            h1 {{ color: #2c3e50; }}
            .info {{ background: #e8f4fd; padding: 15px; border-radius: 5px; margin: 10px 0; }}
            .endpoint {{ background: #f8f9fa; padding: 10px; margin: 5px 0; border-radius: 5px; }}
            .method {{ font-weight: bold; color: #007bff; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏫 KV GC CRPF Siliguri Timetable API</h1>
            
            <div class="info">
                <h3>Server Information</h3>
                <p><strong>School:</strong> {SCHOOL_NAME}</p>
                <p><strong>API Version:</strong> {API_VERSION}</p>
                <p><strong>Environment:</strong> {"Production" if os.getenv("RENDER") else "Development"}</p>
                <p><strong>Status:</strong> Running</p>
                <p><strong>Uptime:</strong> {int(time.time() - server_start_time)} seconds</p>
            </div>
            
            <div class="info">
                <h3>Authentication</h3>
                <p><strong>Required Passcode:</strong> {PASSCODE}</p>
                <p>Include in header: <code>X-Passcode: {PASSCODE}</code></p>
                <p>Or as query parameter: <code>?passcode={PASSCODE}</code></p>
            </div>
            
            <h3>Available Endpoints</h3>
            
            <div class="endpoint">
                <span class="method">GET</span> /api/v1/health - Health check
            </div>
            <div class="endpoint">
                <span class="method">GET</span> /api/v1/school/data - Complete school data
            </div>
            <div class="endpoint">
                <span class="method">GET</span> /api/v1/teachers - All teachers timetable
            </div>
            <div class="endpoint">
                <span class="method">GET</span> /api/v1/teachers/keys - Teacher keys and prefixes
            </div>
            <div class="endpoint">
                <span class="method">GET</span> /api/v1/teachers/{{id}} - Specific teacher data
            </div>
            <div class="endpoint">
                <span class="method">POST</span> /api/v1/teachers - Add new teacher
            </div>
            <div class="endpoint">
                <span class="method">PUT</span> /api/v1/teachers/{{id}} - Update teacher
            </div>
            <div class="endpoint">
                <span class="method">DELETE</span> /api/v1/teachers/{{id}} - Remove teacher
            </div>
            <div class="endpoint">
                <span class="method">POST</span> /api/v1/generate/teacher-excel - Generate teachers Excel
            </div>
            <div class="endpoint">
                <span class="method">POST</span> /api/v1/generate/student-excel - Generate students Excel
            </div>
            
            <div class="info">
                <h3>Documentation</h3>
                <p><a href="/docs" target="_blank">Interactive API Documentation (Swagger UI)</a></p>
                <p><a href="/redoc" target="_blank">Alternative Documentation (ReDoc)</a></p>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check(passcode: str = Depends(verify_passcode)):
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        school=SCHOOL_NAME,
        school_key=SCHOOL_KEY,
        api_version=API_VERSION,
        server_time=datetime.now().isoformat(),
        uptime_seconds=int(time.time() - server_start_time),
        environment="Production" if os.getenv("RENDER") else "Development"
    )

@app.get("/api/v1/school/data")
async def get_school_data(passcode: str = Depends(verify_passcode)):
    """Get complete school data"""
    school_data = db.get_school_data(SCHOOL_KEY)
    
    if school_data:
        return {
            "success": True,
            "data": school_data,
            "timestamp": datetime.now().isoformat()
        }
    else:
        raise HTTPException(
            status_code=404,
            detail="School data not found"
        )

@app.get("/api/v1/teachers")
async def get_all_teachers(passcode: str = Depends(verify_passcode)):
    """Get all teachers timetable"""
    school_data = db.get_school_data(SCHOOL_KEY)
    
    if school_data:
        return {
            "success": True,
            "teachers": school_data['teachers'],
            "teacher_count": school_data['total_teachers'],
            "timestamp": datetime.now().isoformat()
        }
    else:
        raise HTTPException(
            status_code=404,
            detail="No teachers found"
        )

@app.get("/api/v1/teachers/keys")
async def get_teacher_keys(passcode: str = Depends(verify_passcode)):
    """Get all teacher keys"""
    school_data = db.get_school_data(SCHOOL_KEY)
    
    if school_data:
        return {
            "success": True,
            "teacher_keys": school_data['teacher_keys'],
            "teacher_prefixes": school_data['teacher_prefixes'],
            "teacher_subjects": school_data['teacher_subjects'],
            "timestamp": datetime.now().isoformat()
        }
    else:
        raise HTTPException(
            status_code=404,
            detail="No teacher keys found"
        )

@app.get("/api/v1/teachers/{teacher_identifier}")
async def get_teacher(teacher_identifier: str, passcode: str = Depends(verify_passcode)):
    """Get specific teacher data"""
    school_data = db.get_school_data(SCHOOL_KEY)
    
    if not school_data:
        raise HTTPException(
            status_code=404,
            detail="School data not found"
        )
    
    teacher_name = None
    
    # Search by key first
    for name, key in school_data['teacher_keys'].items():
        if key == teacher_identifier:
            teacher_name = name
            break
    
    # Search by name if not found by key
    if not teacher_name and teacher_identifier in school_data['teachers']:
        teacher_name = teacher_identifier
    
    if teacher_name:
        teacher_data = {
            'name': teacher_name,
            'key': school_data['teacher_keys'][teacher_name],
            'prefix': school_data['teacher_prefixes'][teacher_name],
            'subject': school_data['teacher_subjects'].get(teacher_name, ''),
            'timetable': school_data['teachers'][teacher_name]
        }
        
        return {
            "success": True,
            "teacher": teacher_data,
            "timestamp": datetime.now().isoformat()
        }
    else:
        raise HTTPException(
            status_code=404,
            detail="Teacher not found"
        )

@app.post("/api/v1/teachers", response_model=StandardResponse)
async def add_teacher(teacher: TeacherCreate, passcode: str = Depends(verify_passcode)):
    """Add new teacher"""
    # Create default timetable if not provided
    if not teacher.timetable:
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        teacher.timetable = {day: [''] * 8 for day in days}
    
    teacher_key = db.add_teacher(
        teacher.teacher_name,
        teacher.teacher_prefix,
        teacher.timetable,
        teacher.subject_code
    )
    
    if teacher_key:
        return StandardResponse(
            success=True,
            message=f"Teacher added successfully with key: {teacher_key}",
            timestamp=datetime.now().isoformat()
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="Failed to add teacher"
        )

@app.put("/api/v1/teachers/{teacher_identifier}", response_model=StandardResponse)
async def update_teacher(
    teacher_identifier: str, 
    teacher_update: TeacherUpdate,
    passcode: str = Depends(verify_passcode)
):
    """Update teacher information"""
    school_data = db.get_school_data(SCHOOL_KEY)
    teacher_name = None
    
    # Find by key or name
    for name, key in school_data['teacher_keys'].items():
        if key == teacher_identifier or name == teacher_identifier:
            teacher_name = name
            break
    
    if not teacher_name:
        raise HTTPException(
            status_code=404,
            detail="Teacher not found"
        )
    
    success = db.update_teacher(
        teacher_name,
        teacher_update.new_name,
        teacher_update.new_prefix,
        teacher_update.new_timetable,
        teacher_update.new_subject
    )
    
    if success:
        return StandardResponse(
            success=True,
            message="Teacher updated successfully",
            timestamp=datetime.now().isoformat()
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="Failed to update teacher"
        )

@app.delete("/api/v1/teachers/{teacher_identifier}", response_model=StandardResponse)
async def delete_teacher(teacher_identifier: str, passcode: str = Depends(verify_passcode)):
    """Remove teacher"""
    school_data = db.get_school_data(SCHOOL_KEY)
    teacher_name = None
    
    # Find by key or name
    for name, key in school_data['teacher_keys'].items():
        if key == teacher_identifier or name == teacher_identifier:
            teacher_name = name
            break
    
    if not teacher_name:
        raise HTTPException(
            status_code=404,
            detail="Teacher not found"
        )
    
    success = db.remove_teacher(teacher_name)
    
    if success:
        return StandardResponse(
            success=True,
            message="Teacher removed successfully",
            timestamp=datetime.now().isoformat()
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="Failed to remove teacher (minimum 5 teachers required)"
        )

@app.post("/api/v1/generate/teacher-excel")
async def generate_teacher_excel(
    excel_request: ExcelGenerate,
    passcode: str = Depends(verify_passcode)
):
    """Generate Excel timetable for all teachers"""
    school_data = db.get_school_data(SCHOOL_KEY)
    
    if not school_data:
        raise HTTPException(
            status_code=404,
            detail="School data not found"
        )
    
    try:
        content = []
        
        # Header
        content.append(f"{school_data['school_name']} - Teachers' Timetable")
        content.append("Generated on: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        content.append("")
        
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        periods = ['Period 1', 'Period 2', 'Period 3', 'Period 4', 'Period 5', 'Period 6', 'Period 7', 'Period 8']
        
        time_slots = [
            '8:50-9:30', '9:30-10:10', '10:10-10:50', '10:50-11:30',
            '12:00-12:40', '12:40-1:20', '1:20-2:00', '2:00-2:40'
        ]
        
        for teacher_name, timetable in school_data['teachers'].items():
            teacher_key = school_data['teacher_keys'].get(teacher_name, 'N/A')
            teacher_prefix = school_data['teacher_prefixes'].get(teacher_name, '')
            teacher_subject = school_data['teacher_subjects'].get(teacher_name, '')
            
            # Teacher header
            content.append("")
            content.append(f"{teacher_prefix} {teacher_name} (Key: {teacher_key}) - {teacher_subject}")
            content.append("=" * 80)
            
            # Table header
            header = "Day/Time," + ",".join([f"{periods[i]} ({time_slots[i]})" for i in range(8)])
            content.append(header)
            
            # Days data
            for day in days:
                if day in timetable:
                    periods_data = timetable[day][:8]
                    while len(periods_data) < 8:
                        periods_data.append("")
                    
                    clean_periods = []
                    for period in periods_data:
                        if period and period not in ['LUNCH', '']:
                            clean_periods.append(period)
                        else:
                            clean_periods.append("Free")
                    
                    row = f"{day}," + ",".join(clean_periods)
                    content.append(row)
            
            content.append("")
        
        # Summary
        content.append("")
        content.append("SUMMARY")
        content.append("=" * 20)
        content.append(f"Total Teachers: {len(school_data['teachers'])}")
        content.append(f"School Key: {school_data['school_key']}")
        content.append(f"Generated by: KV GC CRPF Siliguri FastAPI Server")
        
        file_content = '\n'.join(content)
        
        return {
            "success": True,
            "message": "Teacher timetable Excel generated successfully",
            "filename": excel_request.filename,
            "teachers_count": len(school_data['teachers']),
            "file_size": len(file_content),
            "content": file_content,
            "download_ready": True,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Generation error: {str(e)}"
        )

@app.post("/api/v1/generate/student-excel")
async def generate_student_excel(
    excel_request: ExcelGenerate,
    passcode: str = Depends(verify_passcode)
):
    """Generate Excel timetable for students by class"""
    school_data = db.get_school_data(SCHOOL_KEY)
    
    if not school_data:
        raise HTTPException(
            status_code=404,
            detail="School data not found"
        )
    
    try:
        # Build class schedules from teacher data
        class_schedules = {}
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        classes = ['VI', 'VII', 'VIII', 'IX', 'X']
        
        # Initialize class schedules
        for class_name in classes:
            class_schedules[class_name] = {
                day: [{'period': i+1, 'subject': '', 'teacher': '', 'time': ''} for i in range(8)]
                for day in days
            }
        
        time_slots = [
            '8:50-9:30', '9:30-10:10', '10:10-10:50', '10:50-11:30',
            '12:00-12:40', '12:40-1:20', '1:20-2:00', '2:00-2:40'
        ]
        
        # Process teacher timetables to extract class schedules
        for teacher_name, timetable in school_data['teachers'].items():
            teacher_prefix = school_data['teacher_prefixes'].get(teacher_name, '')
            
            for day in days:
                if day in timetable:
                    for period_idx, period_text in enumerate(timetable[day][:8]):
                        if period_text and period_text.strip():
                            # Extract class info from period text
                            for class_name in classes:
                                if class_name in period_text:
                                    # Extract subject
                                    subject = period_text.replace(class_name, '').strip(' -')
                                    
                                    if period_idx < 8:
                                        class_schedules[class_name][day][period_idx] = {
                                            'period': period_idx + 1,
                                            'subject': subject,
                                            'teacher': f"{teacher_prefix} {teacher_name}",
                                            'time': time_slots[period_idx]
                                        }
                                    break
        
        # Generate CSV content
        content = []
        content.append(f"{school_data['school_name']} - Students' Timetable")
        content.append("Generated on: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        content.append("")
        
        # Generate timetable for each class
        for class_name in classes:
            content.append("")
            content.append(f"CLASS {class_name} - TIMETABLE")
            content.append("=" * 50)
            
            # Table header
            header = "Day/Period," + ",".join([f"P{i+1} ({time_slots[i]})" for i in range(8)])
            content.append(header)
            
            # Days data
            for day in days:
                periods_info = class_schedules[class_name][day]
                
                row_data = [day]
                for period_info in periods_info:
                    if period_info['subject']:
                        cell_content = f"{period_info['subject']} - {period_info['teacher']}"
                    else:
                        cell_content = "Free Period"
                    row_data.append(cell_content)
                
                content.append(",".join(row_data))
            
            content.append("")
        
        # Overall summary
        content.append("")
        content.append("OVERALL SUMMARY")
        content.append("=" * 30)
        content.append(f"Total Classes: {len(classes)}")
        content.append(f"School: {school_data['school_name']}")
        content.append(f"Total Teachers: {len(school_data['teachers'])}")
        content.append(f"Generated by: KV GC CRPF Siliguri FastAPI Server")
        
        file_content = '\n'.join(content)
        
        return {
            "success": True,
            "message": "Student timetable Excel generated successfully",
            "filename": excel_request.filename,
            "classes_count": len(classes),
            "teachers_analyzed": len(school_data['teachers']),
            "file_size": len(file_content),
            "content": file_content,
            "class_schedules": class_schedules,
            "download_ready": True,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Generation error: {str(e)}"
        )

# =============================================================================
# RENDER DEPLOYMENT CONFIGURATION
# =============================================================================

# Health check for Render.com
@app.get("/health")
async def render_health_check():
    """Simple health check for Render.com"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

# Get port from environment variable (Render requirement)
PORT = int(os.getenv("PORT", 8888))

if __name__ == "__main__":
    import uvicorn
    
    print(f"""
🏫 KV GC CRPF SILIGURI FASTAPI SERVER - RENDER DEPLOYMENT
═══════════════════════════════════════════════════════════

🌟 Status: Starting FastAPI Server...
🔐 Passcode: {PASSCODE}
📊 API Version: {API_VERSION}
🗄️  Database: {DATABASE_FILE}
🌐 Environment: {"Production (Render)" if os.getenv("RENDER") else "Development"}
🚀 Port: {PORT}
""")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=PORT,
        log_level="info"
    )