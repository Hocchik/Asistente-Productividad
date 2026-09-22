FROM python:3.11-slim

# Se corre como usuario sin privilegios, creado ANTES de copiar archivos para
# evitar problemas de permisos.
RUN useradd -m -u 1000 user
USER user

ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR $HOME/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=user . .

EXPOSE 7860

# Forma shell para que se expanda $PORT: Render lo inyecta; en local cae a 7860.
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-7860}
