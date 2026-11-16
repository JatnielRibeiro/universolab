# ProvaLab — plano de produto e implementação

O ProvaLab é o ambiente de criação e gestão de avaliações integrado ao UniversoLab.

## Decisões de produto
- Criação híbrida: banco de questões próprio + assistência de IA.
- Abrangência: todas as disciplinas da Educação Básica.
- Estratégia: plataforma modular e evolutiva.

## Módulos
1. Banco de questões: disciplina, etapa/ano, conteúdo, tipo, dificuldade, habilidade BNCC, enunciado, alternativas, gabarito, pontuação e resolução.
2. Gerador com IA: configuração pedagógica, prompt estruturado e importação validada de questões em JSON.
3. Montagem de provas: metadados, seleção de questões, instruções, identificação da instituição e turma.
4. Minhas avaliações: listagem, visualização, impressão e exclusão.
5. Turmas: cadastro e organização por etapa e ano letivo.
6. Próximas fases: integração de IA no servidor, edição/reordenação de provas, exportação DOCX, cartões-resposta, OMR, correção e relatórios.

## Implementação atual — versão inicial
- Página `provalab.html` integrada ao menu UniversoLab.
- Cadastro de questões objetivas e discursivas.
- Catálogo de disciplinas da Educação Básica.
- Metadados de etapa, conteúdo, dificuldade e BNCC.
- Pesquisa e filtros do banco.
- Preparação de prompts para geração por IA.
- Importação de questões por JSON com validações básicas.
- Montagem de provas por seleção de questões.
- Cadastro de turmas.
- Visualização e impressão de prova / salvar em PDF pelo navegador.
- Persistência local no navegador usando localStorage.

## Limitações conhecidas
- Os dados ainda ficam no dispositivo/navegador; não há contas, nuvem ou sincronização.
- A geração com IA ainda prepara prompts e importa resultados; não há chamada automática a um provedor.
- A impressão é feita pelo diálogo do navegador; exportação DOCX nativa ainda não existe.
- Cartão-resposta, leitura óptica OMR e correção automática não fazem parte desta entrega.
- A validação de códigos BNCC é orientativa; a conferência curricular precisa ser feita pelo professor.

## Arquitetura-alvo
- Frontend: aplicação web responsiva.
- Backend: Python + FastAPI.
- Banco de dados: PostgreSQL.
- IA: integração server-side com provedor configurável; segredos nunca expostos no frontend.
- Documentos: geração PDF e DOCX no servidor.
- Correção: pipeline de leitura de imagem com validação de confiança e revisão humana de marcações incertas.

## Modelo de dados inicial
- Question: id, subject, grade, topic, type, level, bncc, statement, options, answer, points, explanation, source.
- Exam: id, code, title, subject, grade, class_id, date, instructions, school, question_ids, created_at.
- Class: id, name, grade, year, notes.
- Futuro: User, Institution, Student, AnswerSheet, Scan, ExamResult, SkillPerformance.

## Próximas entregas sugeridas
1. Melhorar edição, duplicação e ordenação de questões/provas.
2. Criar autenticação e API com persistência PostgreSQL.
3. Integrar geração real com IA via backend.
4. Implementar modelos de prova e exportação PDF/DOCX.
5. Desenvolver cartão-resposta e correção OMR com calibração e revisão manual.
6. Criar relatórios por estudante, turma, questão e habilidade.
