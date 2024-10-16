# syntax=docker/dockerfile:1
# Initialize device type args
# use build args in the docker build commmand with --build-arg="BUILDARG=true"
ARG USE_CUDA=false
ARG USE_OLLAMA=false
# Tested with cu117 for CUDA 11 and cu121 for CUDA 12 (default)
ARG USE_CUDA_VER=cu121
# any sentence transformer model; models to use can be found at https://huggingface.co/models?library=sentence-transformers
# Leaderboard: https://huggingface.co/spaces/mteb/leaderboard 
# for better performance and multilangauge support use "intfloat/multilingual-e5-large" (~2.5GB) or "intfloat/multilingual-e5-base" (~1.5GB)
# IMPORTANT: If you change the embedding model (sentence-transformers/all-MiniLM-L6-v2) and vice versa, you aren't able to use RAG Chat with your previous documents loaded in the WebUI! You need to re-embed them.
ARG USE_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
ARG USE_RERANKING_MODEL=""

######## WebUI frontend ########
FROM --platform=$BUILDPLATFORM node:21-alpine3.19 as build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

######## WebUI backend ########
FROM python:3.11-slim-bookworm as base

# Use args
ARG USE_CUDA
ARG USE_OLLAMA
ARG USE_CUDA_VER
ARG USE_EMBEDDING_MODEL
ARG USE_RERANKING_MODEL

## Basis ##
ENV ENV=prod \
    PORT=8080 \
    # pass build args to the build
    USE_OLLAMA_DOCKER=${USE_OLLAMA} \
    USE_CUDA_DOCKER=${USE_CUDA} \
    USE_CUDA_DOCKER_VER=${USE_CUDA_VER} \
    USE_EMBEDDING_MODEL_DOCKER=${USE_EMBEDDING_MODEL} \
    USE_RERANKING_MODEL_DOCKER=${USE_RERANKING_MODEL}

## Basis URL Config ##
ENV OLLAMA_BASE_URL="/ollama" \
    OPENAI_API_BASE_URL=""

## API Key and Security Config ##
ENV OPENAI_API_KEY="" \
    WEBUI_SECRET_KEY="" \
    SCARF_NO_ANALYTICS=true \
    DO_NOT_TRACK=true \
    ANONYMIZED_TELEMETRY=false

# Use locally bundled version of the LiteLLM cost map json
# to avoid repetitive startup connections
ENV LITELLM_LOCAL_MODEL_COST_MAP="True"

# Use to login with Microsoft Azure Application with for the SSO feature
ENV CLIENT_ID="" \
    CLIENT_SECRET="" \
    TENANT="" \
    REDIRECT_URI=""

# Use to send emails to HR
ENV HR_EMAIL=""

# Use to connect with Microsoft SQL Server Database
ENV MSSQL_SERVER="" \
    MSSQL_USER="" \
    MSSQL_PASSWORD="" \
    MSSQL_DATABASE="" \
    MSSQL_VIEW=""

#### Other models #########################################################
## whisper TTS model settings ##
ENV WHISPER_MODEL="base" \
    WHISPER_MODEL_DIR="/app/backend/data/cache/whisper/models"

## RAG Embedding model settings ##
ENV RAG_EMBEDDING_MODEL="$USE_EMBEDDING_MODEL_DOCKER" \
    RAG_RERANKING_MODEL="$USE_RERANKING_MODEL_DOCKER" \
    SENTENCE_TRANSFORMERS_HOME="/app/backend/data/cache/embedding/models"

## Hugging Face download cache ##
ENV HF_HOME="/app/backend/data/cache/embedding/models"
#### Other models ##########################################################

WORKDIR /app/backend

ENV HOME /root
RUN mkdir -p $HOME/.cache/chroma
RUN echo -n 00000000-0000-0000-0000-000000000000 > $HOME/.cache/chroma/telemetry_user_id

RUN if [ "$USE_OLLAMA" = "true" ]; then \
        apt-get update && \
        # for using camelot to read tables from pdf
        apt-get install -y ghostscript python3-opencv && \
        # Install pandoc and netcat
        apt-get install -y --no-install-recommends pandoc netcat-openbsd && \
        # for RAG OCR
        apt-get install -y --no-install-recommends ffmpeg libsm6 libxext6 && \
        # install helper tools
        apt-get install -y --no-install-recommends curl && \
        # install ollama
        curl -fsSL https://ollama.com/install.sh | sh && \
        # cleanup
        rm -rf /var/lib/apt/lists/*; \
    else \
        apt-get update && \
        # for using camelot to read tables from pdf
        apt-get install -y ghostscript python3-opencv && \
        # Install pandoc and netcat
        apt-get install -y --no-install-recommends pandoc netcat-openbsd && \
        # for RAG OCR
        apt-get install -y --no-install-recommends ffmpeg libsm6 libxext6 && \
        # cleanup
        rm -rf /var/lib/apt/lists/*; \
    fi

# Install Microsoft ODBC Driver for SQL Server
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential \
    curl \
    apt-utils \
    gnupg2 &&\
    rm -rf /var/lib/apt/lists/* && \
    pip install --upgrade pip

RUN apt-get update
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
RUN curl https://packages.microsoft.com/config/ubuntu/22.04/prod.list > /etc/apt/sources.list.d/mssql-release.list


RUN exit
RUN apt-get update
RUN env ACCEPT_EULA=Y apt-get install -y msodbcsql18 

COPY data/odbc.ini / 
RUN odbcinst -i -s -f /odbc.ini -l
RUN cat /etc/odbc.ini


# install python dependencies
COPY ./backend/requirements.txt ./requirements.txt

RUN pip3 install uv && \
    if [ "$USE_CUDA" = "true" ]; then \
        # If you use CUDA the whisper and embedding model will be downloaded on first use
        pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/$USE_CUDA_DOCKER_VER --no-cache-dir && \
        uv pip install --system -r requirements.txt --no-cache-dir && \
        python -c "import os; from sentence_transformers import SentenceTransformer; SentenceTransformer(os.environ['RAG_EMBEDDING_MODEL'], device='cpu')" && \
        python -c "import os; from faster_whisper import WhisperModel; WhisperModel(os.environ['WHISPER_MODEL'], device='cpu', compute_type='int8', download_root=os.environ['WHISPER_MODEL_DIR'])"; \
    else \
        pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu --no-cache-dir && \
        uv pip install --system -r requirements.txt --no-cache-dir && \
        python -c "import os; from sentence_transformers import SentenceTransformer; SentenceTransformer(os.environ['RAG_EMBEDDING_MODEL'], device='cpu')" && \
        python -c "import os; from faster_whisper import WhisperModel; WhisperModel(os.environ['WHISPER_MODEL'], device='cpu', compute_type='int8', download_root=os.environ['WHISPER_MODEL_DIR'])"; \
    fi



# copy embedding weight from build
# RUN mkdir -p /root/.cache/chroma/onnx_models/all-MiniLM-L6-v2
# COPY --from=build /app/onnx /root/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx

# copy built frontend files
COPY --from=build /app/build /app/build
COPY --from=build /app/CHANGELOG.md /app/CHANGELOG.md
COPY --from=build /app/package.json /app/package.json

# copy backend files
COPY ./backend .

EXPOSE 8080

CMD [ "bash", "start.sh"]
