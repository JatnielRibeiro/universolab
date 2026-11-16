import json
import os
from typing import Literal

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError

app = FastAPI(title="ProvaLab AI API", version="1.0.0")

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
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


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
    options: list[str] = []
    answer: str = ""
    points: float = 1
    explanation: str = ""


@app.get("/health")
def health():
    return {"status": "ok", "service": "ProvaLab AI API"}


@app.post("/api/generate-questions")
def generate_questions(
    payload: GenerateRequest,
    authorization: str | None = Header(default=None),
):
    access_token = os.getenv("PROVALAB_ACCESS_TOKEN", "").strip()
    if access_token and authorization != f"Bearer {access_token}":
        raise HTTPException(status_code=401, detail="Código de acesso inválido.")

    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=503, detail="A chave OPENAI_API_KEY não foi configurada no servidor.")

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
- Distribua a dificuldade quando o nível for Variado.
- Retorne exatamente {payload.count} questões.

Retorne somente um objeto JSON válido no formato:
{{
  "questions": [
    {{
      "subject": "disciplina",
      "grade": "etapa/ano",
      "topic": "conteúdo",
      "type": "objective",
      "level": "Média",
      "bncc": "",
      "statement": "enunciado",
      "options": ["A", "B", "C", "D", "E"],
      "answer": "B",
      "points": 1,
      "explanation": "resolução comentada"
    }}
  ]
}}
"""

    try:
        client = OpenAI()
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-5.5"),
            instructions=(
                "Você é um elaborador pedagógico experiente. Siga rigorosamente "
                "as especificações e retorne JSON válido, sem cercas Markdown."
            ),
            input=prompt,
            text={"format": {"type": "json_object"}},
        )
        data = json.loads(response.output_text)
        raw_questions = data.get("questions", []) if isinstance(data, dict) else []
        questions = [GeneratedQuestion.model_validate(item) for item in raw_questions]

        if len(questions) != payload.count:
            raise ValueError(
                f"A IA retornou {len(questions)} questões; eram esperadas {payload.count}."
            )

        for question in questions:
            if question.type == "objective":
                if len(question.options) != 5 or question.answer not in ["A", "B", "C", "D", "E"]:
                    raise ValueError("Uma questão objetiva veio sem cinco alternativas ou gabarito válido.")
            else:
                question.options = []
                question.answer = ""

        return {"questions": [item.model_dump() for item in questions]}

    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"Não foi possível validar a resposta da IA: {exc}") from exc
    except Exception as exc:
        # Não expõe detalhes internos nem segredos retornados pelo provedor.
        raise HTTPException(status_code=502, detail="Falha ao consultar o serviço de IA. Verifique o modelo, os créditos e a configuração da API.") from exc
