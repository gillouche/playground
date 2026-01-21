FROM ghcr.io/actions/actions-runner:latest

# Switch to root to install dependencies
USER root

# Install Nix dependencies
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    curl \
    xz-utils \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV NIX_INSTALLER_NO_SANDBOX=1

RUN curl -L https://nixos.org/nix/install | sh -s -- \
    --daemon \
    --no-channel-add

# Switch to runner user for Nix installation
USER runner

RUN mkdir -p ~/.config/nix \
    && echo 'experimental-features = nix-command flakes' >> ~/.config/nix/nix.conf \
    && echo 'sandbox = false' >> ~/.config/nix/nix.conf \
    && echo '. ~/.nix-profile/etc/profile.d/nix.sh' >> ~/.bashrc
