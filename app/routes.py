from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
import logging
import re

from app.models import db, User, Project, BusinessPlan, ChatSession, ChatMessage, AuditLog
from app.services.ai_service import IncubatorAI

logger = logging.getLogger(__name__)

# Blueprints
auth_bp = Blueprint("auth", __name__, url_prefix="")
dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")
project_bp = Blueprint("project", __name__, url_prefix="/project")
chat_bp = Blueprint("chat", __name__, url_prefix="/chat")


# ==================== AUTENTICACIÓN ====================

@auth_bp.route("/")
def index():
    """Página de inicio"""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard"))
    return render_template("auth/index.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Registro de usuario con validación de RUT único y consentimiento GDPR"""
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        rut = request.form.get("rut", "").strip()
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        age = request.form.get("age", "").strip()
        city = request.form.get("city", "").strip()
        consent = request.form.get("consent", "") == "on"  # Checkbox de consentimiento
        
        # Validaciones
        if not email or not password or not rut or not first_name or not last_name or not age or not city:
            flash("Todos los campos son requeridos", "error")
            return redirect(url_for("auth.register"))
        
        if not consent:
            flash("Debes aceptar la Política de Privacidad y autorizar el uso de tus datos", "error")
            return redirect(url_for("auth.register"))
        
        if len(password) < 8:
            flash("La contraseña debe tener al menos 8 caracteres", "error")
            return redirect(url_for("auth.register"))
        
        # Validar edad
        try:
            age_int = int(age)
            if age_int < 18 or age_int > 120:
                flash("Debes tener entre 18 y 120 años", "error")
                return redirect(url_for("auth.register"))
        except ValueError:
            flash("La edad debe ser un número válido", "error")
            return redirect(url_for("auth.register"))
        
        # Verificar RUT único
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("El email ya está registrado", "error")
            return redirect(url_for("auth.register"))
        
        existing_rut = User.query.filter_by(rut=rut).first()
        if existing_rut:
            flash("El RUT ya está registrado en el sistema (1 cuenta por RUT)", "error")
            return redirect(url_for("auth.register"))
        
        # Crear usuario
        user = User(
            email=email,
            rut=rut,
            first_name=first_name,
            last_name=last_name,
            age=age_int,
            city=city
        )
        user.set_password(password)
        
        # Registrar consentimiento GDPR con trazabilidad
        user.record_consent(
            ip_address=request.remote_addr,
            terms_version="1.0"
        )
        
        try:
            db.session.add(user)
            db.session.commit()
            
            # Log de auditoría
            audit = AuditLog(
                user_id=user.id,
                action="user_registration",
                resource_type="user",
                resource_id=user.id,
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent", ""),
                consent_given=True
            )
            db.session.add(audit)
            db.session.commit()
            
            flash("¡Registro exitoso! Por favor, inicia sesión.", "success")
            return redirect(url_for("auth.login"))
        
        except IntegrityError:
            db.session.rollback()
            flash("Error al registrar. Intenta de nuevo.", "error")
    
    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Login de usuario"""
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash("Tu cuenta ha sido desactivada", "error")
                return redirect(url_for("auth.login"))
            
            login_user(user, remember=request.form.get("remember") is not None)
            logger.info(f"User logged in: {user.email}")
            
            return redirect(request.args.get("next") or url_for("dashboard.dashboard"))
        else:
            flash("Email o contraseña incorrectos", "error")
    
    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    """Logout de usuario"""
    logger.info(f"User logged out: {current_user.email}")
    logout_user()
    flash("Has cerrado sesión correctamente", "success")
    return redirect(url_for("auth.index"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Solicitar recuperación de contraseña"""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard"))
    
    if request.method == "POST":
        email = request.form.get("email")
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generar token de recuperación
            reset_token = user.generate_reset_token()
            
            # Enviar correo
            from app.services.email_service import email_service
            success, message = email_service.send_password_reset_email(
                recipient_email=user.email,
                reset_token=reset_token,
                user_name=user.email.split("@")[0]
            )
            
            if success:
                flash(
                    "Se ha enviado un correo de recuperación a tu dirección de email. "
                    "Por favor revisa tu bandeja de entrada.",
                    "success"
                )
                logger.info(f"Password reset requested for: {email}")
            else:
                flash("Error al enviar el correo. Por favor intenta más tarde.", "error")
                logger.error(f"Failed to send reset email to: {email}")
        else:
            # No revelar si el correo existe o no (seguridad)
            flash(
                "Si existe una cuenta con ese correo, recibirás instrucciones de recuperación.",
                "success"
            )
        
        return redirect(url_for("auth.login"))
    
    return render_template("auth/forgot_password.html")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """Cambiar contraseña con token de recuperación"""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard"))
    
    # Buscar usuario con el token
    user = User.query.filter_by(reset_token=token).first()
    
    if not user or not user.verify_reset_token(token):
        flash("El enlace de recuperación es inválido o ha expirado.", "error")
        return redirect(url_for("auth.login"))
    
    if request.method == "POST":
        password = request.form.get("password")
        password_confirm = request.form.get("password_confirm")
        
        # Validaciones
        if not password or len(password) < 8:
            flash("La contraseña debe tener al menos 8 caracteres.", "error")
            return render_template("auth/reset_password.html", token=token)
        
        if password != password_confirm:
            flash("Las contraseñas no coinciden.", "error")
            return render_template("auth/reset_password.html", token=token)
        
        # Cambiar contraseña
        user.set_password(password)
        user.clear_reset_token()
        db.session.commit()
        
        flash("Tu contraseña ha sido cambiada exitosamente. Inicia sesión con tu nueva contraseña.", "success")
        logger.info(f"Password reset successful for: {user.email}")
        
        return redirect(url_for("auth.login"))
    
    return render_template("auth/reset_password.html", token=token)


# ==================== DASHBOARD ====================

@dashboard_bp.route("/")
@login_required
def dashboard():
    """Dashboard principal del usuario"""
    projects = Project.query.filter_by(user_id=current_user.id).order_by(
        Project.created_at.desc()
    ).all()
    
    # Sin límite diario de creación
    can_create = True
    
    return render_template(
        "dashboard/index.html",
        projects=projects,
        can_create_project=can_create
    )


# ==================== PROYECTOS ====================

@project_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_project():
    """Crear nuevo proyecto (con rate limiting)"""
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        raw_idea = request.form.get("raw_idea", "").strip()
        
        if not title or not raw_idea:
            flash("Título e idea son requeridos", "error")
            return redirect(url_for("project.create_project"))
        
        # Crear proyecto
        project = Project(
            user_id=current_user.id,
            title=title,
            raw_idea=raw_idea,
            status="ambiguous"
        )
        
        try:
            # Evaluar ambigüedad con IA
            ai = IncubatorAI(current_app.config["GEMINI_API_KEY"])
            variability_score, requires_clarification = ai.evaluate_ambiguity(raw_idea)
            project.variability_score = variability_score
            
            db.session.add(project)
            db.session.flush()
            
            # Log de auditoría
            audit = AuditLog(
                user_id=current_user.id,
                action="create_project",
                resource_type="project",
                resource_id=project.id,
                ip_address=request.remote_addr
            )
            db.session.add(audit)
            db.session.commit()
            
            flash(f"Proyecto '{title}' creado exitosamente", "success")
            
            # Redirigir al chat de clarificación
            if requires_clarification:
                return redirect(url_for("chat.clarification_chat", project_id=project.id))
            else:
                return redirect(url_for("chat.analysis_chat", project_id=project.id))
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating project: {e}")
            flash("Error al crear proyecto", "error")
    
    return render_template("project/create.html")


@project_bp.route("/<project_id>")
@login_required
def view_project(project_id):
    """Ver detalles del proyecto"""
    project = Project.query.get_or_404(project_id)
    
    # Verificar que el proyecto pertenezca al usuario
    if project.user_id != current_user.id:
        flash("No tienes acceso a este proyecto", "error")
        return redirect(url_for("dashboard.dashboard"))
    
    return render_template(
        "project/view.html",
        project=project
    )


# ==================== CHAT Y IA ====================

@chat_bp.route("/clarification/<project_id>")
@login_required
def clarification_chat(project_id):
    """Sesión de chat para clarificación de ambigüedad"""
    project = Project.query.get_or_404(project_id)
    
    if project.user_id != current_user.id:
        flash("No tienes acceso a este proyecto", "error")
        return redirect(url_for("dashboard.dashboard"))
    
    # Crear o recuperar sesión de clarificación
    session = ChatSession.query.filter_by(
        project_id=project_id,
        session_type="clarification"
    ).first()
    
    if not session:
        # Generar preguntas de clarificación
        ai = IncubatorAI(current_app.config["GEMINI_API_KEY"])
        raw_questions = ai.generate_clarification_questions(
            project.raw_idea,
            num_questions=current_app.config["AI_AMBIGUITY_QUESTIONS"]
        )
        seen = set()
        questions = []
        for q in raw_questions:
            nq = re.sub(r"\W+", " ", (q or "").strip().lower()).strip()
            if not nq or nq in seen:
                continue
            seen.add(nq)
            questions.append(q)
        
        session = ChatSession(
            project_id=project_id,
            session_type="clarification"
        )
        db.session.add(session)
        db.session.flush()
        
        # Agregar preguntas como mensajes del asistente
        for i, question in enumerate(questions, 1):
            msg = ChatMessage(
                session_id=session.id,
                role="assistant",
                content=f"**Pregunta {i}:** {question}"
            )
            db.session.add(msg)
        
        db.session.commit()
    
    messages = ChatMessage.query.filter_by(session_id=session.id).order_by(
        ChatMessage.created_at.asc()
    ).all()
    
    return render_template(
        "chat/clarification.html",
        project=project,
        session=session,
        messages=messages
    )


@chat_bp.route("/analysis/<project_id>")
@login_required
def analysis_chat(project_id):
    """Sesión de análisis y generación de plan de negocio"""
    project = Project.query.get_or_404(project_id)
    
    if project.user_id != current_user.id:
        flash("No tienes acceso a este proyecto", "error")
        return redirect(url_for("dashboard.dashboard"))
    
    # Crear o recuperar sesión de análisis
    session = ChatSession.query.filter_by(
        project_id=project_id,
        session_type="analysis"
    ).first()
    
    if not session:
        session = ChatSession(
            project_id=project_id,
            session_type="analysis"
        )
        db.session.add(session)
        db.session.commit()
    
    messages = ChatMessage.query.filter_by(session_id=session.id).order_by(
        ChatMessage.created_at.asc()
    ).all()
    
    return render_template(
        "chat/analysis.html",
        project=project,
        session=session,
        messages=messages
    )


@chat_bp.route("/send-message", methods=["POST"])
@login_required
def send_message():
    """Endpoint AJAX para enviar mensajes"""
    session_id = request.json.get("session_id")
    message_text = request.json.get("message", "").strip()
    
    # Validar sesión
    session = ChatSession.query.get_or_404(session_id)
    project = Project.query.get_or_404(session.project_id)
    
    if project.user_id != current_user.id:
        return jsonify({"error": "No autorizado"}), 403
    
    if not message_text:
        return jsonify({"error": "Mensaje vacío"}), 400
    
    # Verificar límite de mensajes (solo cuenta mensajes de usuario)
    user_msg_count = ChatMessage.query.filter_by(session_id=session_id, role="user").count()
    if user_msg_count >= current_app.config["MAX_CHAT_MESSAGES"]:
        session.lock_session()
        session.message_count = user_msg_count
        db.session.commit()
        return jsonify({
            "error": "Se alcanzó el límite de mensajes",
            "locked": True
        }), 429
    
    # Guardar mensaje del usuario
    user_message = ChatMessage(
        session_id=session_id,
        role="user",
        content=message_text
    )
    db.session.add(user_message)
    session.message_count = user_msg_count + 1  # Solo mensajes de usuario
    db.session.commit()
    
    # Generar respuesta de IA
    try:
        ai = IncubatorAI(current_app.config["GEMINI_API_KEY"])
        
        # Construir contexto de conversación
        conversation_context = "\n".join([
            f"{msg.role.upper()}: {msg.content}"
            for msg in ChatMessage.query.filter_by(session_id=session_id).all()
        ])

        # Identificar preguntas ya hechas (para evitar repeticiones)
        assistant_msgs = ChatMessage.query.filter_by(session_id=session_id, role="assistant").order_by(ChatMessage.created_at.asc()).all()
        asked_questions = []
        for msg in assistant_msgs:
            content = (msg.content or "").strip()
            if not content:
                continue
            if "Pregunta" in content or content.endswith("?"):
                cleaned = re.sub(r"^\*\*Pregunta\s*\d+:\*\*\s*", "", content).strip()
                if cleaned not in asked_questions:
                    asked_questions.append(cleaned)

        MIN_QUESTIONS = 3
        MAX_QUESTIONS = 5
        plan_already_exists = project.business_plan is not None
        
        # Generar respuesta según tipo de sesión
        if session.session_type == "clarification":
            context_signal = len(conversation_context) >= 80  # evitar plan con contexto vacío
            ready_for_plan = (
                session.message_count >= MIN_QUESTIONS
                and len(asked_questions) >= MIN_QUESTIONS
                and context_signal
            )

            if ready_for_plan and not plan_already_exists:
                plan = ai.generate_business_plan(
                    project.raw_idea,
                    clarifications=conversation_context
                )
                # Guardar/actualizar plan
                bp = project.business_plan or BusinessPlan(project_id=project.id)
                bp.problem_statement = plan.get("problem_statement", "")
                bp.value_proposition = plan.get("value_proposition", "")
                bp.target_market = plan.get("target_market", "")
                bp.revenue_model = plan.get("revenue_model", "")
                bp.cost_analysis = plan.get("cost_analysis", "")
                bp.technical_feasibility = plan.get("technical_feasibility", "")
                bp.risks_analysis = plan.get("risks_analysis", "")
                bp.scalability_potential = plan.get("scalability_potential", "")
                bp.validation_strategy = plan.get("validation_strategy", "")
                bp.overall_assessment = plan.get("overall_assessment", "")
                bp.viability_score = plan.get("viability_score", 0)
                bp.recommendation = plan.get("recommendation", "not_viable")
                db.session.add(bp)
                db.session.commit()
                plan_already_exists = True

            if plan_already_exists:
                bp = project.business_plan
                score = bp.viability_score or 0
                semaforo = "🟢" if score >= 80 else "🟡" if score >= 60 else "🔴"
                ai_response = (
                    f"Análisis 9 pilares → Problema: {bp.problem_statement}. "
                    f"Propuesta: {bp.value_proposition}. Mercado: {bp.target_market}. "
                    f"Ingresos: {bp.revenue_model}. Costos: {bp.cost_analysis}. "
                    f"Técnica: {bp.technical_feasibility}. Riesgos: {bp.risks_analysis}. "
                    f"Escalabilidad: {bp.scalability_potential}. Validación: {bp.validation_strategy}. "
                    f"Viabilidad: {score}/100 {semaforo}. Recomendación: {bp.recommendation}."
                )
            else:
                ai_response = ai.generate_clarification_reply(
                    project.raw_idea,
                    conversation_context,
                    user_turn=session.message_count,
                    asked_questions=asked_questions,
                    min_questions=MIN_QUESTIONS,
                    max_questions=MAX_QUESTIONS
                )
                is_question = ai_response.strip().endswith("?") and len(ai_response.strip()) <= 200
                if is_question:
                    norm_set = {re.sub(r"\W+", " ", q.lower()).strip() for q in asked_questions}
                    candidate_norm = re.sub(r"\W+", " ", ai_response.strip().lower()).strip()
                    if candidate_norm in norm_set:
                        for bank_q in ai.QUESTIONS_BANK:
                            bnorm = re.sub(r"\W+", " ", bank_q.strip().lower()).strip()
                            if bnorm and bnorm not in norm_set:
                                ai_response = bank_q
                                break
        else:
            # Análisis completo
            plan = ai.generate_business_plan(
                project.raw_idea,
                clarifications=conversation_context
            )
            # Por ahora, guardar el plan
            if not project.business_plan:
                bp = BusinessPlan(
                    project_id=project.id,
                    problem_statement=plan.get("problem_statement", ""),
                    value_proposition=plan.get("value_proposition", ""),
                    target_market=plan.get("target_market", ""),
                    revenue_model=plan.get("revenue_model", ""),
                    cost_analysis=plan.get("cost_analysis", ""),
                    technical_feasibility=plan.get("technical_feasibility", ""),
                    risks_analysis=plan.get("risks_analysis", ""),
                    scalability_potential=plan.get("scalability_potential", ""),
                    validation_strategy=plan.get("validation_strategy", ""),
                    overall_assessment=plan.get("overall_assessment", ""),
                    viability_score=plan.get("viability_score", 0),
                    recommendation=plan.get("recommendation", "not_viable")
                )
                db.session.add(bp)
                db.session.commit()
            
            ai_response = plan.get("overall_assessment", "Plan generado exitosamente")
        
        # Guardar respuesta de IA
        ai_message = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=ai_response
        )
        db.session.add(ai_message)
        
        # No incrementamos el contador para respuestas del asistente
        if session.message_count >= current_app.config["MAX_CHAT_MESSAGES"]:
            session.lock_session()
            
            # Agregar mensaje de cierre automático al alcanzar límite
            closing_message = ChatMessage(
                session_id=session_id,
                role="assistant",
                content="""Has superado el límite de mensajes de esta sesión.

Para continuar con el desarrollo de tu proyecto, te invitamos a agendar una reunión con nuestro equipo:

🔗 Reserva tu espacio aquí: https://calendar.app.google/cuDDtC9Y1tZVDPuD7

Podrás elegir el horario que mejor se adapte a tu disponibilidad. ¡Te esperamos!"""
            )
            db.session.add(closing_message)
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "response": ai_response,
            "locked": session.is_locked,
            "message_count": session.message_count,
            "max_messages": current_app.config["MAX_CHAT_MESSAGES"]
        })
    
    except Exception as e:
        logger.error(f"Error generating AI response: {e}")
        return jsonify({
            "error": "Error al generar respuesta"
        }), 500


# ==================== ERRORES ====================

@auth_bp.errorhandler(404)
def not_found(error):
    return render_template("errors/404.html"), 404


@auth_bp.errorhandler(500)
def server_error(error):
    return render_template("errors/500.html"), 500


# ==================== PRIVACIDAD Y GDPR ====================

@auth_bp.route("/privacy")
def privacy():
    """Página de política de privacidad (pública, sin autenticación)"""
    return render_template("privacy.html")


@dashboard_bp.route("/delete-account", methods=["GET", "POST"])
@login_required
def delete_account():
    """Eliminación de cuenta con confirmación (soft delete → hard delete en 30 días)"""
    if request.method == "POST":
        password_confirmation = request.form.get("password", "")
        
        # Verificar contraseña como medida de seguridad
        if not current_user.check_password(password_confirmation):
            flash("Contraseña incorrecta. No se pudo eliminar la cuenta.", "error")
            return redirect(url_for("dashboard.delete_account"))
        
        # Auditoría
        audit = AuditLog(
            user_id=current_user.id,
            action="account_deletion_requested",
            resource_type="user",
            resource_id=current_user.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
            consent_given=False
        )
        db.session.add(audit)
        
        # Soft delete inmediato
        current_user.schedule_deletion(days=30)
        
        # Cerrar sesión
        logout_user()
        
        flash(
            "Tu cuenta ha sido desactivada. Se eliminará permanentemente en 30 días. "
            "Si cambias de opinión, puedes iniciar sesión antes de esa fecha para cancelar la eliminación.",
            "warning"
        )
        return redirect(url_for("auth.index"))
    
    return render_template("dashboard/delete_account.html")


@auth_bp.route("/cancel-deletion", methods=["POST"])
@login_required
def cancel_deletion():
    """Cancelar eliminación programada (reactivar cuenta)"""
    if current_user.scheduled_deletion:
        current_user.cancel_deletion()
        
        # Auditoría
        audit = AuditLog(
            user_id=current_user.id,
            action="account_deletion_cancelled",
            resource_type="user",
            resource_id=current_user.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent")
        )
        db.session.add(audit)
        db.session.commit()
        
        flash("Tu cuenta ha sido reactivada exitosamente. ¡Bienvenido de vuelta!", "success")
    
    return redirect(url_for("dashboard.dashboard"))

