from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import bcrypt
from datetime import datetime, timedelta
import uuid

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """Modelo de usuario con validación de RUT único"""
    __tablename__ = "users"
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    rut = db.Column(db.String(12), unique=True, nullable=False, index=True)
    role = db.Column(db.Enum("user", "admin", "seller", name="user_role"), default="user")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_project_creation = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    # Password Recovery
    reset_token = db.Column(db.String(255), unique=True, nullable=True, index=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    
    # Relaciones
    projects = db.relationship("Project", back_populates="user", cascade="all, delete-orphan")
    audit_logs = db.relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    
    def set_password(self, password: str) -> None:
        """Hashear password con bcrypt usando la librería bcrypt"""
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        self.password_hash = hashed.decode("utf-8")
    
    def check_password(self, password: str) -> bool:
        """Verificar password usando bcrypt"""
        return bcrypt.checkpw(password.encode("utf-8"), self.password_hash.encode("utf-8"))
    
    def can_create_project(self) -> bool:
        """Validar rate limiting: máximo 2 proyectos por 24 horas"""
        if self.last_project_creation is None:
            return True
        time_elapsed = datetime.utcnow() - self.last_project_creation
        return time_elapsed >= timedelta(hours=24)
    
    def generate_reset_token(self) -> str:
        """Generar token de recuperación de contraseña (válido por 1 hora)"""
        self.reset_token = str(uuid.uuid4())
        self.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
        db.session.commit()
        return self.reset_token
    
    def verify_reset_token(self, token: str) -> bool:
        """Verificar si el token de recuperación es válido y no ha expirado"""
        if self.reset_token != token:
            return False
        if self.reset_token_expiry is None:
            return False
        if datetime.utcnow() > self.reset_token_expiry:
            return False
        return True
    
    def clear_reset_token(self) -> None:
        """Limpiar el token de recuperación después de ser usado"""
        self.reset_token = None
        self.reset_token_expiry = None
        db.session.commit()
    
    def __repr__(self) -> str:
        return f"<User {self.email} ({self.rut})>"


class Project(db.Model):
    """Modelo de proyecto de negocio"""
    __tablename__ = "projects"
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    raw_idea = db.Column(db.Text, nullable=False)
    variability_score = db.Column(db.Float, default=0.0)  # 0-100: Grado de ambigüedad
    status = db.Column(db.Enum("ambiguous", "ready", "in_analysis", "completed", name="project_status"), 
                       default="ambiguous")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    user = db.relationship("User", back_populates="projects")
    business_plan = db.relationship("BusinessPlan", back_populates="project", uselist=False, 
                                    cascade="all, delete-orphan")
    chat_sessions = db.relationship("ChatSession", back_populates="project", cascade="all, delete-orphan")
    
    __table_args__ = (
        db.Index("idx_user_created", "user_id", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<Project {self.title} ({self.status})>"


class BusinessPlan(db.Model):
    """Modelo de plan de negocio generado por IA"""
    __tablename__ = "business_plans"
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = db.Column(db.String(36), db.ForeignKey("projects.id"), nullable=False, unique=True)
    
    # Los 9 Pilares de Viabilidad
    problem_statement = db.Column(db.Text)  # Problema Real
    value_proposition = db.Column(db.Text)  # Propuesta de Valor
    target_market = db.Column(db.Text)  # Mercado
    revenue_model = db.Column(db.Text)  # Modelo de Ingresos
    cost_analysis = db.Column(db.Text)  # Costos
    technical_feasibility = db.Column(db.Text)  # Viabilidad Técnica
    risks_analysis = db.Column(db.Text)  # Riesgos
    scalability_potential = db.Column(db.Text)  # Escalabilidad
    validation_strategy = db.Column(db.Text)  # Validación
    
    # Síntesis y puntuación
    overall_assessment = db.Column(db.Text)  # Evaluación general
    viability_score = db.Column(db.Float)  # 0-100: Puntuación de viabilidad
    recommendation = db.Column(db.Enum("viable", "needs_pivot", "not_viable", name="recommendation_status"))
    
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    project = db.relationship("Project", back_populates="business_plan")
    
    def __repr__(self) -> str:
        return f"<BusinessPlan {self.project_id} ({self.recommendation})>"


class ChatSession(db.Model):
    """Modelo de sesión de chat independiente por proyecto"""
    __tablename__ = "chat_sessions"
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = db.Column(db.String(36), db.ForeignKey("projects.id"), nullable=False, index=True)
    message_count = db.Column(db.Integer, default=0)
    is_locked = db.Column(db.Boolean, default=False)  # Bloqueado al alcanzar límite
    session_type = db.Column(db.Enum("clarification", "analysis", "pivot", name="session_type"), 
                             default="clarification")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    project = db.relationship("Project", back_populates="chat_sessions")
    messages = db.relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    
    __table_args__ = (
        db.Index("idx_project_created", "project_id", "created_at"),
    )
    
    def can_add_message(self, max_messages: int = 10) -> bool:
        """Validar si se puede agregar un mensaje"""
        return not self.is_locked and self.message_count < max_messages
    
    def lock_session(self) -> None:
        """Bloquear sesión al alcanzar límite"""
        self.is_locked = True
    
    def __repr__(self) -> str:
        return f"<ChatSession {self.id} ({self.message_count} messages)>"


class ChatMessage(db.Model):
    """Modelo de mensajes en sesión de chat"""
    __tablename__ = "chat_messages"
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = db.Column(db.String(36), db.ForeignKey("chat_sessions.id"), nullable=False, index=True)
    role = db.Column(db.Enum("user", "assistant", name="message_role"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    session = db.relationship("ChatSession", back_populates="messages")
    
    __table_args__ = (
        db.Index("idx_session_created", "session_id", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<ChatMessage {self.role} @ {self.created_at}>"


class AuditLog(db.Model):
    """Modelo para auditoría y cumplimiento GDPR/LPD"""
    __tablename__ = "audit_logs"
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    action = db.Column(db.String(255), nullable=False)  # create_project, generate_plan, etc.
    resource_type = db.Column(db.String(50), nullable=False)  # project, business_plan, etc.
    resource_id = db.Column(db.String(36))
    consent_given = db.Column(db.Boolean, default=False)  # Consentimiento informado
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    user = db.relationship("User", back_populates="audit_logs")
    
    __table_args__ = (
        db.Index("idx_user_action", "user_id", "action", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<AuditLog {self.action} by {self.user_id}>"
