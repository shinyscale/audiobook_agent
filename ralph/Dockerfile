FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    nodejs \
    npm \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Install Claude CLI
RUN npm install -g @anthropic-ai/claude-code

# Create non-root user with same UID as typical host user
ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g ${GROUP_ID} ralph && \
    useradd -m -u ${USER_ID} -g ralph -s /bin/bash ralph && \
    echo "ralph ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Set up workspace
WORKDIR /workspace

# Copy project files
COPY . .

# Install project dependencies
RUN pip install --no-cache-dir -e ".[dev]"

# Download spaCy model
RUN python -m spacy download en_core_web_lg

# Fix ownership for ralph user
RUN chown -R ralph:ralph /workspace

# Set working directory to ralph
WORKDIR /workspace/ralph

# Make loop script executable
RUN chmod +x loop.sh

# Switch to non-root user
USER ralph

ENTRYPOINT ["/bin/bash"]
