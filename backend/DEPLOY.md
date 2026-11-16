# ProvaLab API — banco de dados e publicação

O backend do ProvaLab atende a importação de provas em PDF, a conferência do gabarito e o armazenamento permanente em PostgreSQL. A geração por IA é opcional.

## 1. Criar o banco PostgreSQL

Recomendação: Supabase.

1. Crie um projeto em https://supabase.com.
2. Abra **SQL Editor → New query**.
3. Execute o conteúdo de `backend/schema.sql`.
4. Em **Project Settings → Database → Connection string**, selecione **Session pooler** e copie a URI PostgreSQL.
5. Guarde a URI em local seguro; ela contém usuário e senha do banco.

## 2. Publicar o backend no Render

1. Entre em https://render.com e conecte sua conta GitHub.
2. Abra o serviço existente do ProvaLab ou escolha **New + → Blueprint**.
3. Selecione o repositório `JatnielRibeiro/universolab`.
4. O Render detectará `render.yaml`.
5. Em **Environment**, configure `DATABASE_URL` com a URI PostgreSQL do Supabase.
6. Mantenha `PROVALAB_ACCESS_TOKEN` gerado pelo Render.
7. Salve e aguarde o serviço ficar **Live**.

A variável `OPENAI_API_KEY` não é necessária para importar PDFs, salvar avaliações ou consultar o banco. Só configure essa chave se quiser habilitar o gerador por IA.

## 3. Conectar a página ProvaLab

1. Abra o UniversoLab e entre em **ProvaLab → Importar prova**.
2. Informe a URL pública do backend Render.
3. Informe o valor de `PROVALAB_ACCESS_TOKEN`.
4. Selecione o PDF da avaliação com o gabarito.
5. Clique em **Analisar PDF e extrair gabarito**.
6. Confira e complete as respostas, informe título, disciplina e etapa/ano.
7. Clique em **Salvar avaliação no banco de dados**.

## 4. Formato de gabarito reconhecido

A extração automática procura um cabeçalho como **GABARITO** ou **RESPOSTAS CORRETAS** e padrões como:

- `1-A`
- `02. B`
- `Questão 3: C`
- `4) D`

Sempre revise o resultado antes de salvar. O sistema não deve presumir respostas que não conseguiu identificar.

## 5. Limitações desta primeira versão

- PDFs com texto selecionável podem ser extraídos automaticamente.
- PDFs digitalizados como imagem ainda não possuem OCR; o professor pode preencher o gabarito manualmente na tela de conferência.
- O arquivo PDF original não é arquivado nesta etapa; são persistidos o nome do arquivo, o texto extraído e o gabarito confirmado.
- A geração de cartões-resposta com QR Code e a correção OMR serão implementadas nas fases seguintes.

## 6. Segurança

Esta primeira versão usa um token compartilhado como proteção provisória e ainda não possui contas individuais de professores. Não armazene dados pessoais de alunos ou informações sensíveis até implementarmos autenticação individual, autorização por professor, políticas RLS e controle de acesso aos arquivos.

Nunca coloque a senha do PostgreSQL ou credenciais administrativas do Supabase no HTML, JavaScript ou repositório.
