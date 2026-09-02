FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system-level packages
RUN apt-get update && apt-get install -y \
    build-essential \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Django dependencies
COPY pyproject.toml uv.lock ./
RUN pip install --upgrade pip && pip install uv
RUN uv sync --no-dev
ENV PATH="/app/.venv/bin:$PATH"

# Node / Tailwind
COPY package.json package-lock.json ./
RUN npm ci

# Project files
COPY . .

# Build minify CSS and collectstatic
RUN npm run minify && python manage.py collectstatic --noinput

EXPOSE 8000

# Fixed: Use JSON array format for CMD (fixes the JSONArgsRecommended warning)
# Fixed: Use PORT environment variable with default fallback
# Fixed: Proper shell command with PORT variable expansion
CMD ["sh", "-c", "python manage.py migrate && daphne -b 0.0.0.0 -p ${PORT:-8000} _core.asgi:application"]