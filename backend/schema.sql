-- ProvaLab: esquema inicial PostgreSQL
-- Pode ser executado no SQL Editor do Supabase.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS public.provalab_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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
    ON public.provalab_assessments (created_at DESC);

-- Esta primeira versão usa a API do backend para acessar a tabela.
-- Não habilite acesso público direto à tabela. Configure RLS e autenticação
-- individual dos professores antes de armazenar dados pessoais de alunos.


-- Banco pedagógico de questões do ProvaLab
CREATE TABLE IF NOT EXISTS public.provalab_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject VARCHAR(30) NOT NULL CHECK (subject IN ('Matemática','Física','Ciências')),
    school_stage VARCHAR(40) NOT NULL,
    grade VARCHAR(40) NOT NULL,
    topic VARCHAR(180) NOT NULL,
    subtopic VARCHAR(180) NOT NULL DEFAULT '',
    difficulty VARCHAR(20) NOT NULL CHECK (difficulty IN ('Fácil','Médio','Difícil')),
    bncc_code VARCHAR(20) NOT NULL DEFAULT '',
    bncc_description TEXT NOT NULL DEFAULT '',
    question_type VARCHAR(20) NOT NULL DEFAULT 'objective'
        CHECK (question_type IN ('objective','discursive')),
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
    ON public.provalab_questions (subject, school_stage, grade, difficulty);
CREATE INDEX IF NOT EXISTS idx_provalab_questions_topic
    ON public.provalab_questions (subject, topic);
CREATE INDEX IF NOT EXISTS idx_provalab_questions_bncc
    ON public.provalab_questions (bncc_code);
