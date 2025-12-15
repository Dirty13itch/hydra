#!/usr/bin/env bash
# Hydra Development Environment Setup Script
#
# Sets up hydra-dev (Ubuntu VM) for development work.
# Installs required tools, configures access to cluster services,
# and sets up the development environment.
#
# Run on: hydra-dev (Ubuntu 24.04 VM)
# Usage: curl -fsSL https://raw.githubusercontent.com/shaun/hydra/main/scripts/setup-dev-environment.sh | bash

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}→${NC} $1"; }
success() { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}!${NC} $1"; }
error() { echo -e "${RED}✗${NC} $1"; }

header() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"
}

# Configuration
HYDRA_REPO="${HYDRA_REPO:-https://github.com/shaun/hydra}"
INSTALL_DIR="${HOME}/hydra"
PYTHON_VERSION="3.11"

# Check we're on Ubuntu
check_os() {
    if [[ ! -f /etc/os-release ]]; then
        error "Cannot detect OS"
        exit 1
    fi

    source /etc/os-release
    if [[ "$ID" != "ubuntu" ]]; then
        warn "This script is designed for Ubuntu, detected: $ID"
    fi

    success "Running on $PRETTY_NAME"
}

# Install system packages
install_packages() {
    header "Installing System Packages"

    sudo apt-get update
    sudo apt-get install -y \
        build-essential \
        curl \
        git \
        wget \
        jq \
        htop \
        tmux \
        vim \
        neovim \
        openssh-client \
        python${PYTHON_VERSION} \
        python${PYTHON_VERSION}-venv \
        python${PYTHON_VERSION}-dev \
        python3-pip \
        pipx \
        nfs-common \
        sops \
        age \
        direnv

    success "System packages installed"
}

# Install Docker
install_docker() {
    header "Installing Docker"

    if command -v docker &>/dev/null; then
        success "Docker already installed"
        return
    fi

    # Add Docker's official GPG key
    sudo apt-get install -y ca-certificates curl gnupg
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg

    # Add repository
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
        $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
        sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Add user to docker group
    sudo usermod -aG docker "$USER"

    success "Docker installed"
    warn "Log out and back in for docker group to take effect"
}

# Install Tailscale
install_tailscale() {
    header "Installing Tailscale"

    if command -v tailscale &>/dev/null; then
        success "Tailscale already installed"
        return
    fi

    curl -fsSL https://tailscale.com/install.sh | sh

    success "Tailscale installed"
    log "Run 'sudo tailscale up' to connect to tailnet"
}

# Install development tools
install_dev_tools() {
    header "Installing Development Tools"

    # UV (fast Python package manager)
    if ! command -v uv &>/dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
        success "uv installed"
    fi

    # Poetry (alternative)
    if ! command -v poetry &>/dev/null; then
        pipx install poetry
        success "Poetry installed"
    fi

    # Pre-commit
    pipx install pre-commit
    success "pre-commit installed"

    # Rich CLI
    pipx install rich-cli
    success "rich-cli installed"

    # HTTPie
    pipx install httpie
    success "HTTPie installed"
}

# Install Claude Code (CLI)
install_claude_code() {
    header "Installing Claude Code"

    if command -v claude &>/dev/null; then
        success "Claude Code already installed"
        return
    fi

    # Check for Node.js
    if ! command -v node &>/dev/null; then
        log "Installing Node.js..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
        sudo apt-get install -y nodejs
    fi

    npm install -g @anthropic-ai/claude-code

    success "Claude Code installed"
    log "Run 'claude' to start"
}

# Configure SSH for cluster access
configure_ssh() {
    header "Configuring SSH"

    mkdir -p ~/.ssh
    chmod 700 ~/.ssh

    # Create SSH config for cluster
    cat >> ~/.ssh/config << 'EOF'

# Hydra Cluster
Host hydra-ai
    HostName 192.168.1.250
    User typhon
    IdentityFile ~/.ssh/id_ed25519

Host hydra-compute
    HostName 192.168.1.203
    User typhon
    IdentityFile ~/.ssh/id_ed25519

Host hydra-storage
    HostName 192.168.1.244
    User root
    IdentityFile ~/.ssh/id_ed25519

# Tailscale hosts
Host ts-hydra-ai
    HostName 100.84.120.44
    User typhon
    IdentityFile ~/.ssh/id_ed25519

Host ts-hydra-compute
    HostName 100.74.73.44
    User typhon
    IdentityFile ~/.ssh/id_ed25519

Host ts-hydra-storage
    HostName 100.111.54.59
    User root
    IdentityFile ~/.ssh/id_ed25519
EOF

    success "SSH config created"

    # Generate SSH key if needed
    if [[ ! -f ~/.ssh/id_ed25519 ]]; then
        log "Generating SSH key..."
        ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""
        success "SSH key generated"
        log "Add this public key to cluster nodes:"
        cat ~/.ssh/id_ed25519.pub
    fi
}

# Mount NFS shares
configure_nfs() {
    header "Configuring NFS Mounts"

    sudo mkdir -p /mnt/models /mnt/shared

    # Add to fstab if not present
    if ! grep -q "192.168.1.244:/mnt/user/models" /etc/fstab; then
        echo "192.168.1.244:/mnt/user/models /mnt/models nfs4 rsize=1048576,wsize=1048576,hard,intr,noatime,_netdev,x-systemd.automount 0 0" | sudo tee -a /etc/fstab
        echo "192.168.1.244:/mnt/user/hydra_shared /mnt/shared nfs4 rsize=1048576,wsize=1048576,hard,intr,noatime,_netdev,x-systemd.automount 0 0" | sudo tee -a /etc/fstab
        success "NFS mounts added to fstab"
    fi

    # Mount now
    sudo mount -a 2>/dev/null || warn "Could not mount NFS (check network)"
}

# Clone and setup Hydra repo
setup_hydra_repo() {
    header "Setting Up Hydra Repository"

    if [[ -d "$INSTALL_DIR" ]]; then
        log "Updating existing repo..."
        cd "$INSTALL_DIR"
        git pull
    else
        log "Cloning repository..."
        git clone "$HYDRA_REPO" "$INSTALL_DIR"
        cd "$INSTALL_DIR"
    fi

    # Create Python virtual environment
    log "Creating Python environment..."
    python${PYTHON_VERSION} -m venv .venv
    source .venv/bin/activate

    # Install dependencies
    pip install -U pip
    pip install -e ".[all]"

    success "Hydra repository ready at $INSTALL_DIR"
}

# Configure environment variables
configure_environment() {
    header "Configuring Environment"

    # Create environment file
    cat > ~/.hydra-env << 'EOF'
# Hydra Cluster Environment
export HYDRA_HOME="${HOME}/hydra"

# Service URLs
export LITELLM_URL="http://192.168.1.244:4000"
export TABBY_URL="http://192.168.1.250:5000"
export OLLAMA_URL="http://192.168.1.203:11434"
export QDRANT_URL="http://192.168.1.244:6333"
export MEILISEARCH_URL="http://192.168.1.244:7700"

# API Keys (set these manually)
# export LITELLM_API_KEY="sk-..."
# export ANTHROPIC_API_KEY="sk-ant-..."

# Python
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1

# Add tools to path
export PATH="${HYDRA_HOME}/scripts:${HOME}/.local/bin:${PATH}"

# Activate hydra venv if entering project
if [[ -f "${HYDRA_HOME}/.venv/bin/activate" ]]; then
    source "${HYDRA_HOME}/.venv/bin/activate"
fi
EOF

    # Add to bashrc
    if ! grep -q "source ~/.hydra-env" ~/.bashrc; then
        echo "source ~/.hydra-env" >> ~/.bashrc
    fi

    success "Environment configured"
    log "Run 'source ~/.bashrc' to activate"
}

# Create useful aliases
configure_aliases() {
    header "Creating Aliases"

    cat >> ~/.bash_aliases << 'EOF'

# Hydra Cluster Aliases
alias hstatus='hydra status'
alias hgpu='hydra gpu'
alias hmodels='hydra models'
alias hlogs='hydra logs'

# Quick SSH
alias sai='ssh hydra-ai'
alias sco='ssh hydra-compute'
alias sst='ssh hydra-storage'

# Docker on storage
alias hd='ssh hydra-storage docker'
alias hdc='ssh hydra-storage docker-compose -f /mnt/user/appdata/hydra-stack/docker-compose.yml'

# LLM quick test
alias llm='curl -s http://192.168.1.244:4000/v1/chat/completions -H "Content-Type: application/json" -d'

# Health check
alias hhealth='curl -s http://192.168.1.244:8600/health/summary | jq'
EOF

    success "Aliases created"
}

# Print summary
print_summary() {
    header "Setup Complete!"

    echo "Your development environment is ready."
    echo ""
    echo "Quick commands:"
    echo "  cd ~/hydra              # Go to project"
    echo "  hydra status            # Check cluster health"
    echo "  hgpu                    # GPU status"
    echo "  ssh hydra-ai            # SSH to inference node"
    echo ""
    echo "Next steps:"
    echo "  1. Add your SSH key to cluster nodes"
    echo "  2. Run 'sudo tailscale up' to join tailnet"
    echo "  3. Set API keys in ~/.hydra-env"
    echo "  4. Run 'source ~/.bashrc' to activate environment"
    echo ""
    echo "Documentation: $INSTALL_DIR/docs"
}

# Main
main() {
    header "Hydra Development Environment Setup"

    check_os
    install_packages
    install_docker
    install_tailscale
    install_dev_tools
    install_claude_code
    configure_ssh
    configure_nfs
    setup_hydra_repo
    configure_environment
    configure_aliases
    print_summary
}

main "$@"
