# ProvaLab — banco de dados e importação de avaliações

## O que esta versão implementa

- Backend FastAPI independente de IA para importar avaliações em PDF.
- Extração de texto de PDFs digitais usando PyMuPDF.
- Tentativa de identificar gabaritos em formatos como `1-A`, `02. B`, `Questão 3: C`.
- Pré-visualização e conferência manual do gabarito no frontend.
- Persistência de avaliações e gabaritos em PostgreSQL.
- Consulta das avaliações salvas.
- A geração por IA permanece opcional e só funciona se `OPENAI_API_KEY` for configurada.

PDFs digitalizados como imagem ainda não passam por OCR. Nesses casos, o professor pode preencher o gabarito manualmente na tela de conferência. A leitura OMR dos cartões-resposta será uma fase posterior.

## 1. Criar banco PostgreSQL no Supabase

1. Acesse https://supabase.com e crie um projeto.
2. Abra **SQL Editor → New query**.
3. Copie e execute o conteúdo de `backend/schema.sql`.
4. Em **Project Settings → Database → Connection string**, escolha a conexão **Session pooler** e copie a URI PostgreSQL.
5. Não compartilhe a URI. Ela contém credenciais do banco.

## 2. Publicar/atualizar backend no Render

1. Abra o serviço Render já criado para o ProvaLab ou crie um Blueprint usando `render.yaml`.
2. Em **Environment**, configure `DATABASE_URL` com a URI do Supabase.
3. Mantenha `PROVALAB_ACCESS_TOKEN` gerado pelo Render.
4. Salve e aguarde o deploy ficar **Live**.
5. A chave `OPENAI_API_KEY` não é necessária para importar PDFs nem salvar avaliações. Configure-a apenas se quiser manter o gerador de questões por IA.

## 3. Configurar o ProvaLab

No módulo **Importar prova**, informe:
- URL do backend: endereço público do serviço Render.
- Código de acesso: valor de `PROVALAB_ACCESS_TOKEN`.

Depois:
1. Envie o PDF da prova com o gabarito.
2. Confira o gabarito identificado automaticamente.
3. Corrija ou complete as respostas na área de conferência.
4. Informe título, disciplina, etapa e quantidade de questões.
5. Clique em **Salvar avaliação no banco**.

## 4. Limitações e segurança desta versão

- A extração automática depende de texto selecionável e de um padrão de gabarito reconhecível.
- PDFs escaneados exigem OCR, que será implementado em uma próxima etapa.
- Esta versão inicial ainda usa um token compartilhado e não possui contas individuais de professores. Não armazene dados pessoais de alunos ou informações sensíveis até implementarmos autenticação, autorização por professor e políticas RLS.
- O token usado no navegador é visível para usuários com acesso ao site; ele serve apenas como barreira provisória, não como autenticação forte.
- O arquivo original não é arquivado nesta primeira versão; ficam salvos o nome do arquivo, o texto extraído e o gabarito conferido.
