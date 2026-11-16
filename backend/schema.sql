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
