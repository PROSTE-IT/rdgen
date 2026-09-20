FROM python:3.13-alpine

RUN adduser -D user \
 && mkdir -p /opt/rdgen/data \
 && chown -R user:user /opt/rdgen
USER user

WORKDIR /opt/rdgen

COPY --chown=user:user . .
RUN pip install --no-cache-dir -r requirements.txt \
 && python manage.py migrate

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD wget --spider 0.0.0.0:8000

CMD ["sh", "-c", "python manage.py migrate --noinput && exec /home/user/.local/bin/gunicorn -c gunicorn.conf.py rdgen.wsgi:application"]
