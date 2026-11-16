# ProvaLab AI API — publicação

O frontend do ProvaLab está no GitHub Pages. A API deve ser publicada em um serviço backend (este repositório inclui um blueprint para Render).

## 1. Criar a chave OpenAI
1. Conclua o fluxo de criação de chave de API aberto no ChatGPT.
2. Guarde a chave com segurança. Não a coloque no HTML, JavaScript ou GitHub.
3. A chave deve ser configurada no servidor como `OPENAI_API_KEY`.

A API utiliza a Responses API e o SDK oficial Python da OpenAI.

## 2. Publicar no Render
1. Entre em https://render.com e conecte sua conta GitHub.
2. Escolha **New + → Blueprint**.
3. Selecione o repositório `JatnielRibeiro/universolab`.
4. O Render detectará `render.yaml` e criará o serviço `provalab-ai-api`.
5. Quando solicitado, informe `OPENAI_API_KEY` usando a chave criada.
6. Aguarde o deploy. O serviço terá uma URL semelhante a `https://provalab-ai-api.onrender.com`.
7. No painel do serviço, abra Environment e copie o valor de `PROVALAB_ACCESS_TOKEN` gerado automaticamente. Trate-o como senha.

## 3. Conectar o frontend
Na página ProvaLab, abra **Gerador inteligente** e informe:
- URL do backend: URL pública do serviço Render.
- Código de acesso: valor de `PROVALAB_ACCESS_TOKEN`.

Depois configure disciplina, etapa, conteúdo, quantidade, dificuldade e tipo e clique em **Gerar questões automaticamente**. Revise a saída e escolha **Adicionar todas ao banco de questões**.

## 4. Variáveis do servidor
- `OPENAI_API_KEY`: chave secreta da API OpenAI (obrigatória).
- `PROVALAB_ACCESS_TOKEN`: token de acesso do ProvaLab (gerado pelo Render).
- `OPENAI_MODEL`: modelo usado (padrão `gpt-5.5`).
- `PROVALAB_ALLOWED_ORIGINS`: origens permitidas pelo CORS (o blueprint inclui o GitHub Pages).

## 5. Verificação
Acesse `https://SUA-URL/health`. Resposta esperada:

```json
{"status":"ok","service":"ProvaLab AI API"}
```

## Segurança e custos
- Nunca publique `OPENAI_API_KEY` no frontend ou no repositório.
- O token de acesso do serviço também deve ser tratado como segredo.
- As chamadas à API geram consumo e cobrança na conta da API, conforme o modelo e o uso.
- Limite a quantidade por solicitação (máximo 20) e não compartilhe o token publicamente.
- Para produção com vários professores, evolua para autenticação individual, quotas por usuário, rate limiting, logs e persistência no banco de dados.
