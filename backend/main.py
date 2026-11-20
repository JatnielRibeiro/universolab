import json
import os
import re
import uuid
from typing import Literal

import fitz
import psycopg
from fastapi import FastAPI, Header, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field, ValidationError

app = FastAPI(title="ProvaLab API", version="1.1.0")

allowed_origins = [
    item.strip()
    for item in os.getenv(
        "PROVALAB_ALLOWED_ORIGINS",
        "https://jatnielribeiro.github.io,http://localhost:5500,http://127.0.0.1:5500",
    ).split(",")
    if item.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


def check_access(authorization: str | None):
    access_token = os.getenv("PROVALAB_ACCESS_TOKEN", "").strip()
    if access_token and authorization != f"Bearer {access_token}":
        raise HTTPException(status_code=401, detail="Código de acesso inválido.")


def database():
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise HTTPException(
            status_code=503,
            detail="Banco de dados não configurado. Defina DATABASE_URL no servidor.",
        )
    try:
        return psycopg.connect(database_url, row_factory=dict_row, connect_timeout=10)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Não foi possível conectar ao banco de dados. Verifique DATABASE_URL.") from exc


def ensure_schema():
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        return
    ddl = """
    CREATE TABLE IF NOT EXISTS provalab_assessments (
        id UUID PRIMARY KEY,
        title VARCHAR(180) NOT NULL,
        subject VARCHAR(100) NOT NULL,
        grade VARCHAR(120) NOT NULL,
        question_count INTEGER NOT NULL CHECK (question_count BETWEEN 1 AND 100),
        answer_key JSONB NOT NULL,
        source_filename VARCHAR(255) NOT NULL,
        extracted_text TEXT NOT NULL DEFAULT '',
        status VARCHAR(30) NOT NULL DEFAULT 'ready',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_provalab_assessments_created
        ON provalab_assessments (created_at DESC);
    CREATE TABLE IF NOT EXISTS provalab_questions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        subject VARCHAR(30) NOT NULL CHECK (subject IN ('Matemática','Física','Ciências')),
        school_stage VARCHAR(40) NOT NULL,
        grade VARCHAR(40) NOT NULL,
        topic VARCHAR(180) NOT NULL,
        subtopic VARCHAR(180) NOT NULL DEFAULT '',
        difficulty VARCHAR(20) NOT NULL CHECK (difficulty IN ('Fácil','Médio','Difícil')),
        bncc_code VARCHAR(20) NOT NULL DEFAULT '',
        bncc_description TEXT NOT NULL DEFAULT '',
        question_type VARCHAR(20) NOT NULL DEFAULT 'objective' CHECK (question_type IN ('objective','discursive')),
        statement TEXT NOT NULL,
        options JSONB NOT NULL DEFAULT '[]'::jsonb,
        answer TEXT NOT NULL DEFAULT '',
        explanation TEXT NOT NULL DEFAULT '',
        source_type VARCHAR(40) NOT NULL DEFAULT 'autoral',
        source_name VARCHAR(180) NOT NULL DEFAULT '',
        source_year INTEGER,
        source_question VARCHAR(40) NOT NULL DEFAULT '',
        source_url TEXT NOT NULL DEFAULT '',
        rights_status VARCHAR(40) NOT NULL DEFAULT 'autoral',
        reviewed BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_provalab_questions_filters
        ON provalab_questions (subject, school_stage, grade, difficulty);
    CREATE INDEX IF NOT EXISTS idx_provalab_questions_topic
        ON provalab_questions (subject, topic);
    CREATE INDEX IF NOT EXISTS idx_provalab_questions_bncc
        ON provalab_questions (bncc_code);
    """
    try:
        with psycopg.connect(database_url, connect_timeout=10) as conn:
            conn.execute(ddl)
    except Exception as exc:
        raise RuntimeError("Não foi possível preparar as tabelas do ProvaLab. Confira as permissões do banco.") from exc


@app.on_event("startup")
def startup():
    ensure_schema()


class GenerateRequest(BaseModel):
    subject: str = Field(min_length=2, max_length=80)
    grade: str = Field(min_length=2, max_length=100)
    topic: str = Field(min_length=2, max_length=300)
    count: int = Field(ge=1, le=20)
    level: Literal["Variado", "Fácil", "Médio", "Difícil"] = "Variado"
    question_type: Literal["objective", "discursive", "mixed"] = "objective"
    notes: str = Field(default="", max_length=1500)


class GeneratedQuestion(BaseModel):
    subject: str
    grade: str
    topic: str
    type: Literal["objective", "discursive"]
    level: str
    bncc: str = ""
    statement: str
    options: list[str] = Field(default_factory=list)
    answer: str = ""
    points: float = 1
    explanation: str = ""


class AssessmentCreate(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    subject: str = Field(min_length=2, max_length=100)
    grade: str = Field(min_length=2, max_length=120)
    question_count: int = Field(ge=1, le=100)
    answer_key: dict[str, str]
    source_filename: str = Field(min_length=1, max_length=255)
    extracted_text: str = Field(default="", max_length=200000)



ALLOWED_SUBJECTS = {"Matemática", "Física", "Ciências"}
ALLOWED_DIFFICULTIES = {"Fácil", "Médio", "Difícil"}


class QuestionInput(BaseModel):
    subject: Literal["Matemática", "Física", "Ciências"]
    school_stage: str = Field(min_length=3, max_length=40)
    grade: str = Field(min_length=2, max_length=40)
    topic: str = Field(min_length=2, max_length=180)
    subtopic: str = Field(default="", max_length=180)
    difficulty: Literal["Fácil", "Médio", "Difícil"]
    bncc_code: str = Field(default="", max_length=20)
    bncc_description: str = Field(default="", max_length=3000)
    question_type: Literal["objective", "discursive"] = "objective"
    statement: str = Field(min_length=10, max_length=12000)
    options: list[str] = Field(default_factory=list, max_length=5)
    answer: str = Field(default="", max_length=4000)
    explanation: str = Field(default="", max_length=12000)
    source_type: str = Field(default="autoral", max_length=40)
    source_name: str = Field(default="", max_length=180)
    source_year: int | None = Field(default=None, ge=1900, le=2100)
    source_question: str = Field(default="", max_length=40)
    source_url: str = Field(default="", max_length=1000)
    rights_status: str = Field(default="autoral", max_length=40)


class QuestionBulkCreate(BaseModel):
    questions: list[QuestionInput] = Field(min_length=1, max_length=500)


@app.get("/api/questions")
def list_questions(
    subject: str | None = None,
    school_stage: str | None = None,
    grade: str | None = None,
    difficulty: str | None = None,
    topic: str | None = None,
    limit: int = 100,
    offset: int = 0,
    authorization: str | None = Header(default=None),
):
    check_access(authorization)
    if subject and subject not in ALLOWED_SUBJECTS:
        raise HTTPException(status_code=422, detail="Disciplina fora do escopo do ProvaLab.")
    if difficulty and difficulty not in ALLOWED_DIFFICULTIES:
        raise HTTPException(status_code=422, detail="Nível de dificuldade inválido.")
    limit = max(1, min(limit, 500))
    offset = max(0, offset)
    clauses, params = [], []
    for column, value in (("subject", subject), ("school_stage", school_stage),
                          ("grade", grade), ("difficulty", difficulty)):
        if value:
            clauses.append(f"{column} = %s")
            params.append(value)
    if topic:
        clauses.append("topic ILIKE %s")
        params.append(f"%{topic}%")
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    try:
        with database() as conn:
            total = conn.execute("SELECT COUNT(*) AS total FROM provalab_questions" + where, params).fetchone()["total"]
            rows = conn.execute(
                "SELECT * FROM provalab_questions" + where +
                " ORDER BY subject, grade, topic, created_at DESC LIMIT %s OFFSET %s",
                [*params, limit, offset],
            ).fetchall()
        return {"total": total, "limit": limit, "offset": offset, "questions": [
            {**row, "id": str(row["id"]), "created_at": row["created_at"].isoformat(),
             "updated_at": row["updated_at"].isoformat()} for row in rows
        ]}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Não foi possível consultar o banco de questões.") from exc


@app.post("/api/questions/bulk")
def create_questions_bulk(
    payload: QuestionBulkCreate,
    authorization: str | None = Header(default=None),
):
    check_access(authorization)
    for q in payload.questions:
        if q.question_type == "objective" and (len(q.options) != 5 or q.answer not in {"A", "B", "C", "D", "E"}):
            raise HTTPException(status_code=422, detail="Questões objetivas precisam de cinco alternativas e gabarito A–E.")
        if q.question_type == "discursive" and q.options:
            raise HTTPException(status_code=422, detail="Questões discursivas não devem conter alternativas.")
    try:
        with database() as conn:
            for q in payload.questions:
                conn.execute(
                    """INSERT INTO provalab_questions
                    (subject, school_stage, grade, topic, subtopic, difficulty, bncc_code,
                     bncc_description, question_type, statement, options, answer, explanation,
                     source_type, source_name, source_year, source_question, source_url, rights_status)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT DO NOTHING""",
                    (q.subject, q.school_stage, q.grade, q.topic, q.subtopic, q.difficulty,
                     q.bncc_code, q.bncc_description, q.question_type, q.statement,
                     Jsonb(q.options), q.answer, q.explanation, q.source_type, q.source_name,
                     q.source_year, q.source_question, q.source_url, q.rights_status),
                )
        return {"inserted": len(payload.questions), "message": "Lote de questões processado."}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Não foi possível gravar o lote no banco de questões.") from exc


def parse_answer_key(text: str):
    header = re.search(
        r"(?im)\b(gabarito|respostas? corretas?|chave de respostas?)\b",
        text,
    )
    if not header:
        return {}, "no_key"
    section = text[header.end():]
    # Aceita formatos como 1-A, 01. B, Questão 3: C e 4) D.
    pattern = re.compile(
        r"(?i)(?:quest[aã]o\s*)?(\d{1,3})\s*[.\):\-]\s*([A-E])\b"
    )
    found = {}
    for match in pattern.finditer(section):
        number = str(int(match.group(1)))
        found[number] = match.group(2).upper()
    if not found:
        # Também aceita tabelas em que o número e a letra estão separados por espaço.
        pattern_space = re.compile(r"(?im)^\s*(\d{1,3})\s+([A-E])\s*$")
        for match in pattern_space.finditer(section):
            found[str(int(match.group(1)))] = match.group(2).upper()
    return found, "extracted" if found else "no_key"


@app.get("/health")
def health():
    configured = bool(os.getenv("DATABASE_URL", "").strip())
    return {
        "status": "ok",
        "service": "ProvaLab API",
        "database_configured": configured,
    }


@app.post("/api/assessments/preview")
async def preview_assessment(
    file: UploadFile = File(...),
    authorization: str | None = Header(default=None),
):
    check_access(authorization)
    filename = (file.filename or "avaliacao.pdf").replace("\\", "/").split("/")[-1]
    if not filename.lower().endswith(".pdf") or file.content_type not in ("application/pdf", "application/octet-stream", None):
        raise HTTPException(status_code=415, detail="Envie um arquivo PDF.")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="O arquivo enviado está vazio.")
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="O PDF deve ter no máximo 15 MB.")
    try:
        document = fitz.open(stream=content, filetype="pdf")
        extracted_text = "\n".join(page.get_text("text") for page in document).strip()
        page_count = document.page_count
        document.close()
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Não foi possível abrir este PDF. Verifique se o arquivo não está protegido ou corrompido.") from exc

    if len(extracted_text) < 20:
        return {
            "filename": filename,
            "page_count": page_count,
            "extracted_text": extracted_text,
            "answer_key": {},
            "question_count": 0,
            "extraction_status": "scanned_pdf",
            "message": "Este PDF parece ser digitalizado como imagem. A leitura OCR será adicionada em uma próxima etapa. Informe o gabarito manualmente para continuar.",
        }

    answer_key, status = parse_answer_key(extracted_text)
    inferred_count = max([int(key) for key in answer_key], default=0)
    return {
        "filename": filename,
        "page_count": page_count,
        "extracted_text": extracted_text[:200000],
        "answer_key": answer_key,
        "question_count": inferred_count,
        "extraction_status": status,
        "message": (
            "Gabarito identificado. Confira todas as respostas antes de salvar."
            if status == "extracted"
            else "O texto foi extraído, mas não identificamos um padrão de gabarito. Você pode preencher as respostas manualmente."
        ),
    }


@app.post("/api/assessments")
def create_assessment(
    payload: AssessmentCreate,
    authorization: str | None = Header(default=None),
):
    check_access(authorization)
    if not payload.answer_key:
        raise HTTPException(status_code=422, detail="Informe pelo menos uma resposta correta.")
    normalized = {}
    for key, value in payload.answer_key.items():
        try:
            number = str(int(key))
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail=f"Número de questão inválido: {key}.")
        answer = str(value).strip().upper()
        if not 1 <= int(number) <= payload.question_count:
            raise HTTPException(status_code=422, detail=f"A questão {number} está fora da quantidade informada.")
        if answer not in {"A", "B", "C", "D", "E"}:
            raise HTTPException(status_code=422, detail=f"Gabarito inválido na questão {number}. Use A, B, C, D ou E.")
        normalized[number] = answer

    assessment_id = uuid.uuid4()
    try:
        with database() as conn:
            conn.execute(
                """
                INSERT INTO provalab_assessments
                (id, title, subject, grade, question_count, answer_key, source_filename, extracted_text)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    assessment_id,
                    payload.title.strip(),
                    payload.subject.strip(),
                    payload.grade.strip(),
                    payload.question_count,
                    Jsonb(normalized),
                    payload.source_filename,
                    payload.extracted_text,
                ),
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Não foi possível salvar a avaliação no banco de dados.") from exc
    return {
        "id": str(assessment_id),
        "title": payload.title,
        "subject": payload.subject,
        "grade": payload.grade,
        "question_count": payload.question_count,
        "answer_key": normalized,
        "source_filename": payload.source_filename,
        "status": "ready",
    }


@app.get("/api/assessments")
def list_assessments(authorization: str | None = Header(default=None)):
    check_access(authorization)
    try:
        with database() as conn:
            rows = conn.execute(
                """
                SELECT id, title, subject, grade, question_count, answer_key,
                       source_filename, status, created_at
                FROM provalab_assessments
                ORDER BY created_at DESC
                LIMIT 100
                """
            ).fetchall()
        return {
            "assessments": [
                {
                    **row,
                    "id": str(row["id"]),
                    "created_at": row["created_at"].isoformat(),
                }
                for row in rows
            ]
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Não foi possível consultar o banco de dados.") from exc


@app.post("/api/generate-questions")
def generate_questions(
    payload: GenerateRequest,
    authorization: str | None = Header(default=None),
):
    check_access(authorization)
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=503, detail="A geração por IA é opcional e ainda não foi configurada neste servidor.")

    prompt = f"""
Gere {payload.count} questões de avaliação para a Educação Básica.
Disciplina: {payload.subject}
Etapa/ano: {payload.grade}
Conteúdo: {payload.topic}
Dificuldade: {payload.level}
Tipo: {payload.question_type}
Orientações adicionais do professor: {payload.notes or "Nenhuma"}

Regras pedagógicas:
- Escreva em português brasileiro, com linguagem apropriada à etapa informada.
- Crie questões originais, claras, sem ambiguidades e alinhadas ao conteúdo.
- Para objetivas, use exatamente cinco alternativas plausíveis e apenas uma correta.
- Para discursivas, use options como lista vazia e answer como string vazia.
- Não invente códigos BNCC. Use bncc vazio quando não tiver segurança sobre o código.
- Inclua resolução/justificativa no campo explanation.
- Retorne exatamente {payload.count} questões.

Retorne somente um objeto JSON válido com a propriedade questions contendo a lista.
"""
    try:
        client = OpenAI()
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-5.5"),
            instructions="Você é um elaborador pedagógico experiente. Retorne JSON válido, sem cercas Markdown.",
            input=prompt,
            text={"format": {"type": "json_object"}},
        )
        data = json.loads(response.output_text)
        raw_questions = data.get("questions", []) if isinstance(data, dict) else []
        questions = [GeneratedQuestion.model_validate(item) for item in raw_questions]
        if len(questions) != payload.count:
            raise ValueError(f"A IA retornou {len(questions)} questões; eram esperadas {payload.count}.")
        for question in questions:
            if question.type == "objective":
                if len(question.options) != 5 or question.answer not in ["A", "B", "C", "D", "E"]:
                    raise ValueError("Questão objetiva sem cinco alternativas ou gabarito válido.")
            else:
                question.options = []
                question.answer = ""
        return {"questions": [item.model_dump() for item in questions]}
    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"Não foi possível validar a resposta da IA: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Falha ao consultar o serviço de IA. Verifique modelo, créditos e configuração.") from exc
